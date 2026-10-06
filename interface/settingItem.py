"""Reusable settings item composition."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout, QLayout, QSizePolicy, QVBoxLayout, QWidget,
)


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
