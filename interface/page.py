#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Time    :   2023/03/20 22:41:51
@File    :   page.py
@Software:   VSCode
@Author  :   PPPPAN 
@Version :   1.0
@Contact :   for_freedom_x64@live.com
'''

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from interface.section import Section

class Page(QScrollArea):
    sectionAdded = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.sectionsDic = {}
        self.initUI()
    
    def initUI(self):
        self.sectionLayout = QVBoxLayout()
        self.sectionLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sectionLayout.setSpacing(10)
        self.sectionListWidget = QWidget()
        self.sectionListWidget.setLayout(self.sectionLayout)
        self.sectionListWidget.setMinimumSize(815,50)
        self.sectionListWidget.adjustSize()
        self.setWidget(self.sectionListWidget)
        self.setMinimumSize(830, 400)

    def resizeEvent(self,event):
        self.sectionListWidget.resize(event.size().width()-5,self.sectionListWidget.height())
        self.update()
    
    def updateSections(self, missionsDic:dict):    #刷新界面
        tempList = []
        w = self.sectionListWidget.width()
        for status,missions in missionsDic.items():
            for key,attribute in missions.items():
                if self.sectionsDic.get(key) == None:
                    #不在已有列表中，新建实例并添加进布局
                    self.sectionsDic.update({key : Section(gid=key, fileName=attribute['filename'], status=status, fileSize=attribute['totalLength'], completedSize=attribute['completedLength'], speed=attribute['downloadSpeed'], isTorrent=attribute['isTorrent'])})
                    self.sectionLayout.addWidget(self.sectionsDic[key])
                    self.sectionAdded.emit(self.sectionsDic[key])
                    h = self.sectionListWidget.height()
                    self.sectionListWidget.resize(w, h+120)
                else:
                    #在已有列表中，更新信息
                    self.sectionsDic[key].updateInfo(status=status, fileSize=attribute['totalLength'], completedSize=attribute['completedLength'], speed=attribute['downloadSpeed'], fileName=attribute['filename'], isTorrent=attribute['isTorrent'])
                tempList.append(key)
        #把不在列表内的删除
        for gid,item in list(self.sectionsDic.items()):
            if gid not in tempList:
                self.sectionLayout.removeWidget(item)
                self.sectionsDic.pop(gid, '删除失败')
                item.deleteLater()
                h = self.sectionListWidget.height()
                self.sectionListWidget.resize(w, h-120)
        self.update()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    exe = Page()
    exe.show()
    sys.exit(app.exec())
