"""Inline Tracker list editor and health checker for the settings page."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.trackerHealth import TrackerHealthWorker
from core.trackerSources import parseTrackers
from interface.languageManager import translate


class TrackerManagerPanel(QWidget):
    trackersChanged = pyqtSignal(list)
    healthSummaryChanged = pyqtSignal(int, int)

    def __init__(self, trackers=(), language='zh_CN', parent=None):
        super().__init__(parent)
        self.language = language
        self.worker = None
        self.updatingTable = False
        self.setProperty('trackerManagerPanel', True)

        self.summaryLabel = QLabel()
        self.summaryLabel.setProperty('dialogStatus', True)

        self.table = QTableWidget(0, 3)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(220)

        self.addBtn = QPushButton()
        self.removeBtn = QPushButton()
        self.checkBtn = QPushButton()

        actionLayout = QHBoxLayout()
        actionLayout.setContentsMargins(0, 0, 0, 0)
        actionLayout.addWidget(self.addBtn)
        actionLayout.addWidget(self.removeBtn)
        actionLayout.addStretch(1)
        actionLayout.addWidget(self.checkBtn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 4)
        layout.setSpacing(8)
        layout.addWidget(self.summaryLabel)
        layout.addWidget(self.table)
        layout.addLayout(actionLayout)

        self.addBtn.clicked.connect(self.addTracker)
        self.removeBtn.clicked.connect(self.removeSelected)
        self.checkBtn.clicked.connect(self.checkTrackers)
        self.table.itemChanged.connect(self.tableItemChanged)

        self.setTrackers(trackers)
        self.retranslateUi()

    def tr(self, key):
        return translate(self.language, key)

    def setLanguage(self, language):
        self.language = language or 'zh_CN'
        self.retranslateUi()

    def retranslateUi(self):
        self.table.setHorizontalHeaderLabels((
            self.tr('trackerUrl'),
            self.tr('trackerHealth'),
            self.tr('trackerLatency'),
        ))
        self.addBtn.setText(self.tr('addTracker'))
        self.removeBtn.setText(self.tr('removeTracker'))
        self.checkBtn.setText(
            self.tr('checkingTrackers')
            if self.worker is not None and self.worker.isRunning()
            else self.tr('checkTrackers'))
        self.updateSummary()

    def setTrackers(self, trackers):
        self.updatingTable = True
        self.table.setRowCount(0)
        for url in parseTrackers('\n'.join(trackers)):
            self.appendTracker(url)
        self.updatingTable = False
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
        row = self.table.rowCount() - 1
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))
        self.updateSummary()

    def removeSelected(self):
        rows = sorted(
            {index.row() for index in self.table.selectionModel().selectedRows()},
            reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.emitTrackersChanged()

    def trackers(self):
        values = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and item.text().strip():
                values.append(item.text().strip())
        return parseTrackers('\n'.join(values))

    def tableItemChanged(self, item):
        if self.updatingTable or item.column() != 0:
            return
        self.emitTrackersChanged()

    def emitTrackersChanged(self):
        trackers = self.trackers()
        self.updateSummary()
        self.trackersChanged.emit(trackers)

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

    def stopHealthCheck(self):
        if self.worker is None or not self.worker.isRunning():
            return
        self.worker.requestInterruption()
        self.worker.wait(2500)

    def closeEvent(self, event):
        self.stopHealthCheck()
        super().closeEvent(event)
