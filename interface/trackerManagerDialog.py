"""Tracker management and health-check dialog."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.trackerHealth import TrackerHealthWorker
from core.trackerSources import parseTrackers
from interface.languageManager import translate


class TrackerManagerDialog(QDialog):
    trackersChanged = pyqtSignal(list)
    healthSummaryChanged = pyqtSignal(int, int)

    def __init__(self, trackers, language='zh_CN', parent=None):
        super().__init__(parent)
        self.language = language
        self.worker = None
        self.setWindowTitle(self.tr('trackerManager'))
        self.setMinimumSize(760, 480)
        self.resize(860, 560)

        self.summaryLabel = QLabel()
        self.summaryLabel.setProperty('dialogStatus', True)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels((
            self.tr('trackerUrl'),
            self.tr('trackerHealth'),
            self.tr('trackerLatency'),
        ))
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.addBtn = QPushButton(self.tr('addTracker'))
        self.removeBtn = QPushButton(self.tr('removeTracker'))
        self.checkBtn = QPushButton(self.tr('checkTrackers'))
        self.applyBtn = QPushButton(self.tr('apply'))
        self.applyBtn.setProperty('primaryAction', True)
        self.closeBtn = QPushButton(self.tr('cancel'))

        actionLayout = QHBoxLayout()
        actionLayout.addWidget(self.addBtn)
        actionLayout.addWidget(self.removeBtn)
        actionLayout.addStretch(1)
        actionLayout.addWidget(self.checkBtn)

        footerLayout = QHBoxLayout()
        footerLayout.addStretch(1)
        footerLayout.addWidget(self.closeBtn)
        footerLayout.addWidget(self.applyBtn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)
        layout.addWidget(self.summaryLabel)
        layout.addWidget(self.table, 1)
        layout.addLayout(actionLayout)
        layout.addLayout(footerLayout)

        self.addBtn.clicked.connect(self.addTracker)
        self.removeBtn.clicked.connect(self.removeSelected)
        self.checkBtn.clicked.connect(self.checkTrackers)
        self.applyBtn.clicked.connect(self.applyChanges)
        self.closeBtn.clicked.connect(self.reject)

        self.setTrackers(trackers)

    def tr(self, key):
        return translate(self.language, key)

    def setTrackers(self, trackers):
        self.table.setRowCount(0)
        for url in parseTrackers('\n'.join(trackers)):
            self.appendTracker(url)
        self.updateSummary()

    def appendTracker(self, url=''):
        row = self.table.rowCount()
        self.table.insertRow(row)
        urlItem = QTableWidgetItem(url)
        statusItem = QTableWidgetItem(self.tr('notChecked'))
        latencyItem = QTableWidgetItem('—')
        statusItem.setFlags(statusItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
        latencyItem.setFlags(latencyItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, urlItem)
        self.table.setItem(row, 1, statusItem)
        self.table.setItem(row, 2, latencyItem)

    def addTracker(self):
        self.appendTracker()
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        self.table.editItem(self.table.currentItem())
        self.updateSummary()

    def removeSelected(self):
        rows = sorted(
            {index.row() for index in self.table.selectionModel().selectedRows()},
            reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.updateSummary()

    def trackers(self):
        values = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.text().strip():
                values.append(item.text().strip())
        return parseTrackers('\n'.join(values))

    def updateSummary(self, healthy=None, failed=None):
        count = len(self.trackers())
        if healthy is None:
            self.summaryLabel.setText(
                self.tr('trackerManagerSummary').format(count=count))
        else:
            self.summaryLabel.setText(
                self.tr('trackerHealthSummary').format(
                    count=count, healthy=healthy, failed=failed))

    def checkTrackers(self):
        if self.worker is not None and self.worker.isRunning():
            return
        trackers = self.trackers()
        if not trackers:
            self.updateSummary(0, 0)
            return
        self.setTrackers(trackers)
        self.checkBtn.setEnabled(False)
        self.checkBtn.setText(self.tr('checkingTrackers'))
        self.worker = TrackerHealthWorker(trackers, parent=self)
        self.worker.resultReady.connect(self.applyHealthResult)
        self.worker.completed.connect(self.finishHealthCheck)
        self.worker.finished.connect(self.clearWorker)
        self.worker.start()

    def applyHealthResult(self, row, status, latency, error):
        if row >= self.table.rowCount():
            return
        statusText = (
            self.tr('trackerHealthy')
            if status == 'healthy'
            else self.tr('trackerUnavailable'))
        self.table.item(row, 1).setText(statusText)
        self.table.item(row, 1).setToolTip(error or '')
        self.table.item(row, 2).setText(
            f'{latency} ms' if latency is not None else '—')

    def finishHealthCheck(self, healthy, failed):
        self.updateSummary(healthy, failed)
        self.healthSummaryChanged.emit(healthy, failed)

    def clearWorker(self):
        if self.worker is not None:
            self.worker.deleteLater()
        self.worker = None
        self.checkBtn.setEnabled(True)
        self.checkBtn.setText(self.tr('checkTrackers'))

    def applyChanges(self):
        trackers = self.trackers()
        self.trackersChanged.emit(trackers)
        self.accept()
