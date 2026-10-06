"""Scrollable collection of download task cards."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from interface.languageManager import resolveLanguage
from interface.section import Section


class Page(QScrollArea):
    sectionAdded = pyqtSignal(object)

    def __init__(self, language=None):
        super().__init__()
        self.language = resolveLanguage(language)
        self.sections = {}
        self.setProperty('downloadPage', True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.viewport().setProperty('pageViewport', True)

        self.sectionLayout = QVBoxLayout()
        self.sectionLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sectionLayout.setContentsMargins(14, 14, 14, 14)
        self.sectionLayout.setSpacing(10)

        self.sectionListWidget = QWidget()
        self.sectionListWidget.setProperty('pageBody', True)
        self.sectionListWidget.setLayout(self.sectionLayout)

        self.setWidgetResizable(True)
        self.setWidget(self.sectionListWidget)

    def setLanguage(self, language):
        self.language = resolveLanguage(language)
        for section in self.sections.values():
            section.setLanguage(language)

    def focusSection(self, gid):
        section = self.sections.get(gid)
        if section is None:
            return False
        self.ensureWidgetVisible(section, 24, 24)
        section.setFocus(Qt.FocusReason.OtherFocusReason)
        return True

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
                        isTorrent=attributes['isTorrent'],
                        files=attributes.get('files', []),
                        language=self.language)
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
                        isTorrent=attributes['isTorrent'],
                        files=attributes.get('files', []))

        for gid in set(self.sections) - currentGids:
            section = self.sections.pop(gid)
            self.sectionLayout.removeWidget(section)
            section.deleteLater()
