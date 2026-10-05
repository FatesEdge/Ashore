"""New-download dialog with validation, drag/drop, and optional HTTP fields."""

from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTextEdit, QToolButton,
    QVBoxLayout,
)

from core.downloadRequest import DownloadRequest, parseDownloadInputs
from interface.actionIcons import actionIcon
from interface.languageManager import translate
from paths import systemDownloadDirectory


class AddNewDialog(QDialog):
    submitted = pyqtSignal(object)

    def __init__(
            self, downloadPath: str | None = None,
            urlList: list | None = None, parent=None, language='zh_CN'):
        super().__init__(parent)
        self.downloadPath = downloadPath or str(systemDownloadDirectory())
        self.language = language
        self.parsedInputs = parseDownloadInputs(urlList or [])
        self.setWindowTitle(self.tr('newDownloadTitle'))
        self.setMinimumSize(620, 430)
        self.resize(680, 500)
        self.setAcceptDrops(True)
        self.initUI()
        if urlList:
            self.text.setPlainText('\n'.join(urlList))
        self.validate()

    def tr(self, key):
        return translate(self.language, key)

    def initUI(self):
        self.text = QTextEdit()
        self.text.setAcceptRichText(False)
        self.text.setPlaceholderText(self.tr('downloadInputPlaceholder'))
        self.text.setMinimumHeight(150)

        self.validationLabel = QLabel()
        self.validationLabel.setProperty('dialogStatus', True)
        self.errorLabel = QLabel()
        self.errorLabel.setProperty('dialogError', True)
        self.errorLabel.setWordWrap(True)
        self.errorLabel.hide()

        self.openTorrentBtn = QPushButton(self.tr('openTorrent'))
        self.openTorrentBtn.setIcon(actionIcon('open-file', size=18))
        inputTools = QHBoxLayout()
        inputTools.setContentsMargins(0, 0, 0, 0)
        inputTools.addWidget(self.openTorrentBtn)
        inputTools.addStretch(1)

        self.dirEdit = QLineEdit(self.downloadPath)
        self.dirEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.dirBtn = QPushButton(self.tr('chooseDirectory'))
        self.dirBtn.setIcon(actionIcon('open-folder', size=18))
        directoryRow = QHBoxLayout()
        directoryRow.setContentsMargins(0, 0, 0, 0)
        directoryRow.addWidget(self.dirEdit, 1)
        directoryRow.addWidget(self.dirBtn)

        self.advancedToggle = QToolButton()
        self.advancedToggle.setText(self.tr('advancedOptions'))
        self.advancedToggle.setCheckable(True)
        self.advancedToggle.setArrowType(Qt.ArrowType.RightArrow)
        self.advancedToggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advancedToggle.setProperty('advancedToggle', True)

        self.advancedPanel = QFrame()
        self.advancedPanel.setProperty('advancedPanel', True)
        advancedForm = QFormLayout(self.advancedPanel)
        advancedForm.setContentsMargins(12, 10, 12, 10)
        advancedForm.setVerticalSpacing(8)

        self.fileNameEdit = QLineEdit()
        self.fileNameEdit.setPlaceholderText(self.tr('fileNameHint'))
        advancedForm.addRow(self.tr('fileName'), self.fileNameEdit)

        self.refererEdit = QLineEdit()
        self.refererEdit.setPlaceholderText(self.tr('leaveDefault'))
        advancedForm.addRow('Referer:', self.refererEdit)

        self.userAgentEdit = QLineEdit()
        self.userAgentEdit.setPlaceholderText(self.tr('userAgentHint'))
        advancedForm.addRow('User-Agent:', self.userAgentEdit)

        self.headersEdit = QTextEdit()
        self.headersEdit.setMaximumHeight(84)
        self.headersEdit.setPlaceholderText(self.tr('headersHint'))
        advancedForm.addRow('HTTP Headers:', self.headersEdit)

        self.cookieEdit = QLineEdit()
        self.cookieEdit.setPlaceholderText(self.tr('cookieHint'))
        advancedForm.addRow('Cookie:', self.cookieEdit)

        self.checksumEdit = QLineEdit()
        self.checksumEdit.setPlaceholderText(self.tr('checksumHint'))
        advancedForm.addRow('Checksum:', self.checksumEdit)

        advancedHint = QLabel(self.tr('advancedDownloadHint'))
        advancedHint.setWordWrap(True)
        advancedHint.setProperty('dialogStatus', True)
        advancedForm.addRow('', advancedHint)
        self.advancedPanel.hide()

        self.cancelBtn = QPushButton(self.tr('cancel'))
        self.confirmBtn = QPushButton(self.tr('startDownload'))
        self.confirmBtn.setProperty('primaryAction', True)
        self.confirmBtn.setIcon(actionIcon(
            'download', color=self.palette().color(
                QPalette.ColorRole.HighlightedText), size=18))
        buttonRow = QHBoxLayout()
        buttonRow.addStretch(1)
        buttonRow.addWidget(self.cancelBtn)
        buttonRow.addWidget(self.confirmBtn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(QLabel(self.tr('downloadInputLabel')))
        layout.addWidget(self.text)
        layout.addLayout(inputTools)
        layout.addWidget(self.validationLabel)
        layout.addWidget(self.errorLabel)
        layout.addSpacing(4)
        layout.addWidget(QLabel(self.tr('saveTo')))
        layout.addLayout(directoryRow)
        layout.addWidget(self.advancedToggle)
        layout.addWidget(self.advancedPanel)
        layout.addStretch(1)
        layout.addLayout(buttonRow)

        self.text.textChanged.connect(self.validate)
        self.dirEdit.textChanged.connect(self.validate)
        self.headersEdit.textChanged.connect(self.validate)
        self.checksumEdit.textChanged.connect(self.validate)
        self.openTorrentBtn.clicked.connect(self.openTorrentFiles)
        self.dirBtn.clicked.connect(self.chooseDirectory)
        self.advancedToggle.toggled.connect(self.toggleAdvanced)
        self.cancelBtn.clicked.connect(self.reject)
        self.confirmBtn.clicked.connect(self.submit)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, 'dirBtn'):
            self.openTorrentBtn.setIcon(actionIcon('open-file', size=18))
            self.dirBtn.setIcon(actionIcon('open-folder', size=18))
            self.confirmBtn.setIcon(actionIcon(
                'download', color=self.palette().color(
                    QPalette.ColorRole.HighlightedText), size=18))

    def toggleAdvanced(self, checked):
        self.advancedPanel.setVisible(checked)
        self.advancedToggle.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        if checked:
            self.resize(max(self.width(), 680), max(self.height(), 680))
        self.validate()

    def chooseDirectory(self):
        path = QFileDialog.getExistingDirectory(
            self, self.tr('chooseDirectory'), self.dirEdit.text(),
            QFileDialog.Option.ShowDirsOnly)
        if path:
            self.dirEdit.setText(path)

    def openTorrentFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr('openTorrent'), str(Path.home()),
            'Torrent files (*.torrent)')
        if files:
            self.appendInputs(files)

    def appendInputs(self, values):
        current = self.text.toPlainText().strip()
        extra = '\n'.join(str(value) for value in values if str(value).strip())
        self.text.setPlainText(
            f'{current}\n{extra}'.strip() if current else extra)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        values = []
        if mime.hasUrls():
            for url in mime.urls():
                values.append(
                    url.toLocalFile() if url.isLocalFile() else url.toString())
        elif mime.hasText():
            values = [mime.text()]
        self.appendInputs(values)
        event.acceptProposedAction()

    def advancedErrors(self):
        errors = []
        if self.advancedToggle.isChecked():
            for line in self.headersEdit.toPlainText().splitlines():
                line = line.strip()
                if line and ':' not in line:
                    errors.append(self.tr('invalidHeader').format(line=line))
            checksum = self.checksumEdit.text().strip()
            if checksum and ('=' not in checksum or checksum.startswith('=')):
                errors.append(self.tr('checksumFormat'))
        return errors

    def validate(self):
        self.parsedInputs = parseDownloadInputs(self.text.toPlainText())
        valid = self.parsedInputs.validCount
        invalid = len(self.parsedInputs.invalid)
        summary = self.tr('validTaskCount').format(count=valid)
        if invalid:
            summary += ' · ' + self.tr('invalidInputCount').format(
                count=invalid)
        self.validationLabel.setText(summary)

        errors = []
        if self.parsedInputs.invalid:
            preview = '；'.join(self.parsedInputs.invalid[:3])
            if len(self.parsedInputs.invalid) > 3:
                preview += '；…'
            errors.append(self.tr('invalidInputPrompt').format(items=preview))
        errors.extend(self.advancedErrors())
        if not self.dirEdit.text().strip():
            errors.append(self.tr('chooseDownloadDir'))

        singleRename = (
            len(self.parsedInputs.items) == 1
            and self.parsedInputs.items[0].supportsOutputName)
        self.fileNameEdit.setEnabled(singleRename)

        self.errorLabel.setText('\n'.join(errors))
        self.errorLabel.setVisible(bool(errors))
        self.confirmBtn.setEnabled(valid > 0 and not errors)

    def buildOptions(self):
        if not self.advancedToggle.isChecked():
            return {}

        options = {}
        if self.fileNameEdit.isEnabled() and self.fileNameEdit.text().strip():
            options['out'] = self.fileNameEdit.text().strip()
        if self.refererEdit.text().strip():
            options['referer'] = self.refererEdit.text().strip()
        if self.userAgentEdit.text().strip():
            options['user-agent'] = self.userAgentEdit.text().strip()

        headers = [
            line.strip()
            for line in self.headersEdit.toPlainText().splitlines()
            if line.strip()]
        if self.cookieEdit.text().strip():
            headers.append('Cookie: ' + self.cookieEdit.text().strip())
        if headers:
            options['header'] = headers

        if self.checksumEdit.text().strip():
            options['checksum'] = self.checksumEdit.text().strip()
        return options

    def submit(self):
        self.validate()
        if not self.confirmBtn.isEnabled():
            return
        request = DownloadRequest(
            items=self.parsedInputs.items,
            targetDir=self.dirEdit.text().strip(),
            options=self.buildOptions(),
        )
        self.submitted.emit(request)
        self.accept()
