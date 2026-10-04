#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2023/03/25 15:06:43
@File    :   addNewDialog.py
@Software:   VSCode
@Author  :   PPPPAN 
@Version :   0.7.66
@Contact :   for_freedom_x64@live.com
'''

import sys
from pathlib import Path
from urllib.parse import urlsplit, unquote
from PyQt6.QtWidgets import QApplication, QPushButton, QFileDialog, QDialog, QTextEdit, QLineEdit, QGridLayout
from PyQt6.QtCore import Qt, pyqtSignal
from paths import systemDownloadDirectory

class AddNewDialog(QDialog):

    sinOut = pyqtSignal(tuple)
    #发射元组信号[0]为url地址，其为字典，分为普通地址'urlList'和磁链地址'torrentList'两项内容

    def __init__(self, downloadPath:str=None, urlList:list=None):
        super().__init__()
        self.downloadPath = downloadPath or str(systemDownloadDirectory())
        self.text = QTextEdit()
        self.text.setPlaceholderText("请输入下载地址,多个地址请用Enter分割")
        if urlList != None:
            urls = ''
            for url in urlList:
                urls += url + '\n'
            self.text.setText(urls)
        self.text.setAcceptRichText(False)
        self.dirEdit = QLineEdit(self.downloadPath)
        dirBtn = QPushButton('选择目录')
        dirBtn.setFixedWidth(100)
        confirmBtn = QPushButton('确认')
        confirmBtn.setFixedWidth(100)
        cancelBtn = QPushButton('取消')
        cancelBtn.setFixedWidth(100)
        mainLayout = QGridLayout()
        mainLayout.addWidget(self.text, 0, 0, 1, 7)
        mainLayout.addWidget(self.dirEdit, 1, 0, 1, 6)
        mainLayout.addWidget(dirBtn, 1, 6, 1, 1)
        mainLayout.addWidget(confirmBtn, 2, 2, 1, 1)
        mainLayout.addWidget(cancelBtn, 2, 4, 1, 1)
        mainLayout.setColumnMinimumWidth(0,100)
        self.setLayout(mainLayout)
        self.setMinimumSize(500, 300)
        self.setWindowModality(Qt.WindowModality.NonModal)  # 非模态，可与其他窗口交互
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
            #校验是否为url或magnet
            for raw in text.splitlines():
                item = raw.strip()
                parsed = urlsplit(item)
                if parsed.scheme in ('http', 'https', 'ftp') and parsed.netloc:
                    target = 'torrentList' if unquote(parsed.path).lower().endswith('.torrent') else 'urlList'
                    urls[target].append(item)
                elif parsed.scheme == 'magnet' and 'xt=urn:btih:' in parsed.query.lower():
                    urls['torrentList'].append(item)
                elif parsed.scheme == 'file' and unquote(parsed.path).lower().endswith('.torrent'):
                    urls['torrentList'].append(item)
                elif Path(item).is_file() and item.lower().endswith('.torrent'):
                    urls['torrentList'].append(item)
            dir = self.dirEdit.text()
            self.sinOut.emit((urls,dir))
        self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    exe = AddNewDialog(urlList=['aaa'])
    exe.show()
    sys.exit(app.exec())
