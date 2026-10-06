"""Reusable settings item and section-header composition."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLayout, QSizePolicy, QVBoxLayout, QWidget,
)


class SettingsSectionHeader(QWidget):
    """Major settings section title followed by a horizontal divider."""

    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.setProperty('settingsSectionHeader', True)

        self.titleLabel = QLabel(text)
        self.titleLabel.setProperty('settingsSectionTitle', True)

        self.divider = QFrame()
        self.divider.setProperty('settingsSectionDivider', True)
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 6)
        layout.setSpacing(10)
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.divider, 1)

    def setText(self, text):
        self.titleLabel.setText(text)

    def text(self):
        return self.titleLabel.text()


class SettingItem(QWidget):
    """A settings title followed by an indented control block."""

    FIELD_INDENT = 18

    def __init__(self, label, field, parent=None):
        super().__init__(parent)
        self.setProperty('settingItem', True)
        self.label = label
        self.label.setProperty('settingsFormLabel', True)
        self.label.setWordWrap(True)
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(4)
        layout.addWidget(self.label)

        self.fieldHost = QWidget(self)
        self.fieldHost.setProperty('settingFieldHost', True)
        fieldHostLayout = QHBoxLayout(self.fieldHost)
        fieldHostLayout.setContentsMargins(self.FIELD_INDENT, 0, 0, 0)
        fieldHostLayout.setSpacing(0)

        if isinstance(field, QLayout):
            field.setContentsMargins(0, 0, 0, 0)
            fieldWidget = QWidget(self.fieldHost)
            fieldWidget.setProperty('settingFieldBody', True)
            fieldWidget.setLayout(field)
            fieldWidget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            fieldHostLayout.addWidget(fieldWidget, 1)
            self.field = fieldWidget
        else:
            self.field = field
            if field.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding:
                fieldHostLayout.addWidget(field, 1)
            else:
                fieldHostLayout.addWidget(
                    field, 0, Qt.AlignmentFlag.AlignLeft)
                fieldHostLayout.addStretch(1)

        self.fieldHost.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.fieldHost)

    def titleText(self):
        return self.label.text()
