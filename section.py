#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2023/03/20 14:20:36
@File    :   section.py
@Software:   VSCode
@Author  :   PPPPAN 
@Version :   0.7.66
@Contact :   for_freedom_x64@live.com
'''

FILETYPE = ['iso', 'jpg', 'bmp', 'svg', 'gif', 'zip', 'rar', 'dmg', 'psd', 'exe', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'mp4', 'pdf', 'php', 'mkv', 'avi', 'mov', 'mpg', 'ppt', 'ai', 'swf', 'html', 'htm', 'js', 'css', 'bin', 'flac', 'aac', 'mp3', 'ini', 'db', 'tiff', 'java', 'cad', 'rss', 'sys', 'dwg', 'dwf', 'ps', 'aut', 'ace', 'eps', 'cdr', 'hlp', 'rtf']

import sys, os
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QHBoxLayout, QProgressBar, QFrame, QGridLayout, QSpacerItem,QSizePolicy
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import pyqtSignal, QSize

class Section(QFrame):
    count = 0
    doubleClickOut = pyqtSignal(tuple)
    openDirOut = pyqtSignal(str)
    cpUrlOut = pyqtSignal(str)
    removeDelOut = pyqtSignal(tuple)
    #生成资源文件目录访问路径
    #说明： pyinstaller工具打包的可执行文件，运行时sys。frozen会被设置成True
    #      因此可以通过sys.frozen的值区分是开发环境还是打包后的生成环境
    #
    #      打包后的生产环境，资源文件都放在sys._MEIPASS目录下
    #      修改main.spec中的datas，
    #      如datas=[('res', 'res')]，意思是当前目录下的res目录加入目标exe中，在运行时放在零时文件的根目录下，名称为res
    BASEPATH = ''
    if getattr(sys, 'frozen', False):
        BASEPATH = sys._MEIPASS + '/'

    def __init__(self, gid:str, fileName:str, status:str, fileSize:int, completedSize:int, speed:int, isTorrent:bool=False):
        super().__init__()
        Section.count += 1
        self.count = Section.count
        self.gid = gid              #得到索引号
        self.fileName = fileName    #得到文件名
        self.status = status
        self.fileSize = fileSize
        self.completedSize = completedSize
        self.speed = speed
        self.isTorrent = isTorrent
        self.initUI()
        self.setConnect()           #设置部件事件链接

    def initUI(self):
        self.setObjectName('Section')
        self.iconLabel = QLabel('icon')
        self.iconLabel.setFixedSize(50,50)
        self.iconLabel.setScaledContents(True)
        self.setIcon(self.status)
        self.nameLabel = QLabel(self.fileName)
        self.nameLabel.setFixedHeight(25)
        self.nameLabel.setMinimumWidth(100)
        self.sizeLable = QLabel(self.getFileSizeStr())
        self.sizeLable.setFixedSize(100,25)
        if self.fileSize == 0:
            self.rateLabel = QLabel('-')
        else:
            self.rateLabel = QLabel('{:.1f}%'.format(self.completedSize / self.fileSize * 100))
        self.rateLabel.setFixedSize(100,25)
        self.completedLabel = QLabel('已下载:')
        self.completedLabel.setFixedSize(50,25)
        # self.completedLabel.setMinimumWidth(100)
        self.speedLabel = QLabel(self.getSpeedStr())
        self.speedLabel.setFixedSize(100,25)
        temp = QWidget()
        temp.setFixedSize(23,23)
        self.aOrpBtn = QPushButton()
        self.aOrpBtn.setFixedSize(23,23)
        self.aOrpBtn.setFlat(True)
        if self.status == 'active' or self.status == 'waiting':
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/pause.png'))
            self.aOrpBtn.setIconSize(QSize(16,16))
            self.aOrpBtn.setToolTip('暂停任务')
            self.aOrpBtn.setStatusTip('暂停任务')
        elif self.status == 'paused':
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/play.png'))
            self.aOrpBtn.setIconSize(QSize(20,20))
            self.aOrpBtn.setToolTip('开始任务')
            self.aOrpBtn.setStatusTip('开始任务')
        elif self.status == 'completed':
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/openfile.png'))
            self.aOrpBtn.setIconSize(QSize(18,18))
            self.aOrpBtn.setToolTip('打开文件')
            self.aOrpBtn.setStatusTip('打开文件')
        elif self.status == 'error':
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/retry.png'))
            self.aOrpBtn.setIconSize(QSize(18,18))
            self.aOrpBtn.setToolTip('重试')
            self.aOrpBtn.setStatusTip('重试')
        self.openDirBtn = QPushButton()
        self.openDirBtn.setFixedSize(23,23)
        self.openDirBtn.setFlat(True)
        self.openDirBtn.setIconSize(QSize(16,16))
        self.openDirBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/openfolder.png'))
        self.openDirBtn.setToolTip('打开目录')
        self.openDirBtn.setStatusTip('打开文件所在目录')
        self.cpUrlBtn = QPushButton()
        self.cpUrlBtn.setFixedSize(23,23)
        self.cpUrlBtn.setFlat(True)
        self.cpUrlBtn.setIconSize(QSize(16,16))
        self.cpUrlBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/copy.png'))
        self.cpUrlBtn.setToolTip('复制下载链接')
        self.cpUrlBtn.setStatusTip('复制下载链接到剪贴板')
        self.removeBtn = QPushButton()
        self.removeBtn.setFixedSize(23,23)
        self.removeBtn.setFlat(True)
        self.removeBtn.setIconSize(QSize(20,20))
        self.removeBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/remove.png'))
        self.removeBtn.setToolTip('从列表中移除任务')
        self.removeBtn.setStatusTip('从列表中移除任务，不删除下载文件')
        self.delBtn = QPushButton()
        self.delBtn.setFixedSize(23,23)
        self.delBtn.setFlat(True)
        self.delBtn.setIconSize(QSize(16,16))
        self.delBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/del.png'))
        self.delBtn.setToolTip('彻底删除任务')
        self.delBtn.setStatusTip('从列表中移除任务，同时删除下载文件')

        btnLayout = QHBoxLayout()
        btnLayout.addWidget(temp)
        btnLayout.addWidget(self.aOrpBtn)
        btnLayout.addWidget(self.openDirBtn)
        btnLayout.addWidget(self.cpUrlBtn)
        btnLayout.addWidget(self.removeBtn)
        btnLayout.addWidget(self.delBtn)
        btnLayout.addStretch()
        btnLayout.setContentsMargins(0,5,0,0)
        self.aOrpBtn.hide()
        self.openDirBtn.hide()
        self.cpUrlBtn.hide()
        self.removeBtn.hide()
        self.delBtn.hide()
        infoLayout = QHBoxLayout()
        # infoLayout.addWidget(self.iconLabel)
        # infoLayout.addWidget(self.nameLabel)

        infoLayout.addWidget(self.sizeLable)
        infoLayout.addSpacerItem(QSpacerItem(10,10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        infoLayout.addWidget(self.completedLabel)
        infoLayout.addWidget(self.rateLabel)
        infoLayout.addWidget(self.speedLabel)
        self.progressBar = QProgressBar()
        self.progressBar.setFixedHeight(10)
        self.progressBar.setContentsMargins(0,0,0,0)
        # mainLayout = QVBoxLayout(self)
        # mainLayout.addLayout(infoLayout)
        # mainLayout.addWidget(self.progressBar)
        # mainLayout.setSpacing(0)
        # mainLayout.setContentsMargins(0,0,0,0)
        # mainLayout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        mainLayout = QGridLayout(self)
        mainLayout.addItem(QSpacerItem(10,0,QSizePolicy.Policy.Fixed),0,0,3,1)
        mainLayout.addWidget(self.iconLabel, 0, 1, 3, 1)
        mainLayout.addWidget(self.nameLabel, 0, 2, 1, 5)
        mainLayout.addLayout(btnLayout, 1, 2, 1, 5)
        mainLayout.addLayout(infoLayout, 2, 2, 1, 5)
        mainLayout.addWidget(self.progressBar, 3, 0, 1, 7)
        mainLayout.setContentsMargins(0,6,0,6)
        # mainLayout.setSpacing(0)
        self.setLayout(mainLayout)
        self.setFixedHeight(110)
        self.setMinimumWidth(800)
        self.setContentsMargins(5,5,5,0)
        self.setStyleSheet('Section{background-color: rgb(50,90,50);border: 2px solid #222333;border-radius:5;}Section:hover{border: 2px solid blue;border-radius:5;}')
        # self.setFrameStyle('border-radius:10px;border:1px solid rgb(100, 100,189)')
        # self.setColor()
        # self.setPalette(QPalette(Qt.blue))
        # self.setFrameShape(QFrame.Shape.Panel)   #设置外边框
        # self.setFrameShadow(QFrame.Shadow.Plain)  # 设置凸起
        # self.setLineWidth(3)
        # self.setMidLineWidth(3)

    def updateInfo(self, status:str, fileSize:int, completedSize:int, speed:int, fileName:str=None, isTorrent:bool=None):
        if fileName is not None and fileName != self.fileName:
            self.fileName = fileName
            self.nameLabel.setText(fileName)
        if isTorrent is not None:
            self.isTorrent = isTorrent
        self.fileSize = fileSize
        self.status = status
        self.speed = speed
        self.sizeLable.setText(self.getFileSizeStr())
        if fileSize != 0:
            self.rateLabel.setText('{:.1f}%'.format(completedSize / fileSize * 100))
            self.progressBar.setValue(int(completedSize / fileSize * 100))
        if status == 'active':
            self.speedLabel.setText(self.getSpeedStr())
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/pause.png'))
            self.aOrpBtn.setToolTip('暂停任务')
        elif status == 'paused':
            self.speedLabel.setText('已暂停')
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/play.png'))
            self.aOrpBtn.setToolTip('开始任务')
        elif status == 'waiting':
            self.speedLabel.setText('等待中')
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/pause.png'))
            self.aOrpBtn.setToolTip('暂停任务')
        elif status == 'error':
            self.speedLabel.setText('错误')
            self.aOrpBtn.setIcon(QIcon(self.BASEPATH + 'static/icon/icon.funtion/retry.png'))
            self.aOrpBtn.setToolTip('重试')
        elif status == 'completed':
            self.speedLabel.setText('已完成')
        self.setIcon(status)
    
    def setIcon(self, status:str):
        fileType = self.fileName.split('.')[-1]
        if status == 'active' or status == 'completed':
            if fileType in FILETYPE:
                self.iconLabel.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.ing/' + fileType + '.png'))
            elif self.isTorrent == True:
                self.iconLabel.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.ing/bt.png'))
            else:
                self.iconLabel.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.ing/paper.png'))
        else:
            if fileType in FILETYPE:
                self.iconLabel.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.stop/' + fileType + '.png'))
            elif self.isTorrent == True:
                self.iconLabel.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.stop/bt.png'))
            else:
                self.iconLabel.setPixmap(QPixmap(self.BASEPATH + 'static/icon/icon.stop/paper.png'))

    def mousePressEvent(self,event):
        # print('鼠标按下')
        pass
    def mouseReleaseEvent(self,event):
        # print('鼠标抬起')
        pass
    def mouseDoubleClickEvent(self,event):
        # print('双击:' + self.gid)
        self.doubleClickOut.emit((self.gid, self.status))

    def enterEvent(self, event):        #鼠标进入控件;
        # print('进入')
        self.aOrpBtn.show()
        self.openDirBtn.show()
        self.cpUrlBtn.show()
        self.removeBtn.show()
        self.delBtn.show()
        # self.setStyleSheet('#Section{border: 2px solid blue;border-radius:5;}')
    def leaveEvent(self, event):        #鼠标离开控件;
        # print('拿走')
        self.aOrpBtn.hide()
        self.openDirBtn.hide()
        self.cpUrlBtn.hide()
        self.removeBtn.hide()
        self.delBtn.hide()
        # self.setStyleSheet('#Section{border: 2px solid #222333;border-radius:5;}')
    def setConnect(self):
        self.aOrpBtn.clicked.connect(self.slotAOrPBtnClicked)
        self.openDirBtn.clicked.connect(self.slotOpenFolder)
        self.cpUrlBtn.clicked.connect(self.slotcpUrl)
        self.removeBtn.clicked.connect(self.slotRemove)
        self.delBtn.clicked.connect(self.slotDel)

    def slotAOrPBtnClicked(self):   #与双击效果相同
        self.doubleClickOut.emit((self.gid, self.status))

    def slotOpenFolder(self):       #打开文件夹
        self.openDirOut.emit(self.gid)

    def slotcpUrl(self):        #复制url
        self.cpUrlOut.emit(self.gid)

    def slotRemove(self):
        self.removeDelOut.emit((self.gid, False))
    
    def slotDel(self):
        self.removeDelOut.emit((self.gid, True))

    def bytesInt2Str(self, b:int) -> str:
        if b < 1024:
            s = str(b) + 'B'
        elif b < 1048576:
            s = '{:.2f}KB'.format(b/1024)
        elif b < 1073741824:
            s = '{:.2f}MB'.format(b/1048576)
        elif b < 1099511627776:
            s = '{:.2f}GB'.format(b/1073741824)
        else:
            s = '{:.2f}TB'.format(b/1099511627776)
        return s

    def getFileSizeStr(self) -> str:
        s = self.bytesInt2Str(self.fileSize)
        return s
    def getSpeedStr(self) -> str:
        s = self.bytesInt2Str(self.speed) + '/s'
        return s

if __name__ == '__main__':
    app = QApplication(sys.argv)
    exe = Section(gid='1122334455667788', fileName='title', status='active', fileSize=1024*1024, completedSize=1024*665, speed=1000)
    exe.show()
    h = exe.height()
    w = exe.width()
    print((w,h))
    sys.exit(app.exec())
