"""Dialog for adding URLs, magnets, and local torrent files."""

from pathlib import Path
from urllib.parse import unquote, urlsplit

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
)

from paths import systemDownloadDirectory


class AddNewDialog(QDialog):

    submitted = pyqtSignal(tuple)
    #发射元组信号[0]为url地址，其为字典，分为普通地址'urlList'和磁链地址'torrentList'两项内容

    def __init__(self, downloadPath: str | None = None, urlList: list | None = None):
        super().__init__()
        self.downloadPath = downloadPath or str(systemDownloadDirectory())
        self.text = QTextEdit()
        self.text.setPlaceholderText("请输入下载地址,多个地址请用Enter分割")
        if urlList is not None:
            self.text.setText('\n'.join(urlList))
        self.text.setAcceptRichText(False)
        self.dirEdit = QLineEdit(self.downloadPath)
        dirBtn = QPushButton('选择目录')
        confirmBtn = QPushButton('确认')
        cancelBtn = QPushButton('取消')
        mainLayout = QGridLayout()
        mainLayout.addWidget(self.text, 0, 0, 1, 7)
        mainLayout.addWidget(self.dirEdit, 1, 0, 1, 6)
        mainLayout.addWidget(dirBtn, 1, 6, 1, 1)
        mainLayout.addWidget(confirmBtn, 2, 2, 1, 1)
        mainLayout.addWidget(cancelBtn, 2, 4, 1, 1)
        mainLayout.setColumnMinimumWidth(0,100)
        self.setLayout(mainLayout)
        self.setMinimumSize(500, 300)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        dirBtn.clicked.connect(self.slotDir)
        confirmBtn.clicked.connect(self.slotConfirm)
        cancelBtn.clicked.connect(self.close)
    def slotDir(self):
        path = QFileDialog.getExistingDirectory(self,'Open dir', self.downloadPath, QFileDialog.Option.ShowDirsOnly)
        if path != '':
            self.dirEdit.setText(path)

    def slotConfirm(self):
        text = self.text.toPlainText()
        if text != '':
            urls = {'urlList': [], 'torrentList': []}
            for raw in text.splitlines():
                item = raw.strip()
                parsed = urlsplit(item)
                if parsed.scheme in ('http', 'https', 'ftp') and parsed.netloc:
                    target = 'torrentList' if unquote(parsed.path).lower().endswith('.torrent') else 'urlList'
                    urls[target].append(item)
                elif (
                        parsed.scheme == 'magnet'
                        and 'xt=urn:btih:' in parsed.query.lower()
                        or parsed.scheme == 'file'
                        and unquote(parsed.path).lower().endswith('.torrent')
                        or Path(item).is_file()
                        and item.lower().endswith('.torrent')):
                    urls['torrentList'].append(item)
            targetDir = self.dirEdit.text()
            self.submitted.emit((urls, targetDir))
        self.close()
