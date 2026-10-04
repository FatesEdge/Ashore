"""Scrollable collection of download task cards."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from interface.section import Section


class Page(QScrollArea):
    sectionAdded = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.sections = {}
        self.sectionLayout = QVBoxLayout()
        self.sectionLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sectionLayout.setSpacing(10)
        self.sectionListWidget = QWidget()
        self.sectionListWidget.setLayout(self.sectionLayout)
        self.setWidgetResizable(True)
        self.setWidget(self.sectionListWidget)

    def updateSections(self, missions):
        currentGids = set()
        for status, missionsByGid in missions.items():
            for gid, attributes in missionsByGid.items():
                currentGids.add(gid)
                section = self.sections.get(gid)
                if section is None:
                    section = Section(
                        gid=gid,
                        fileName=attributes['filename'],
                        status=status,
                        fileSize=attributes['totalLength'],
                        completedSize=attributes['completedLength'],
                        speed=attributes['downloadSpeed'],
                        isTorrent=attributes['isTorrent'])
                    self.sections[gid] = section
                    self.sectionLayout.addWidget(section)
                    self.sectionAdded.emit(section)
                else:
                    section.updateInfo(
                        status=status,
                        fileSize=attributes['totalLength'],
                        completedSize=attributes['completedLength'],
                        speed=attributes['downloadSpeed'],
                        fileName=attributes['filename'],
                        isTorrent=attributes['isTorrent'])

        for gid in set(self.sections) - currentGids:
            section = self.sections.pop(gid)
            self.sectionLayout.removeWidget(section)
            section.deleteLater()
