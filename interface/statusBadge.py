"""Shared appearance for compact connection-state badges."""


CONNECTED_COLOR = '#2e7d32'
DISCONNECTED_COLOR = '#c62828'


def setConnectionBadge(label, text, connected):
    color = CONNECTED_COLOR if connected else DISCONNECTED_COLOR
    label.setText(text)
    label.setStyleSheet(
        f'QLabel {{ color: white; background-color: {color}; '
        'border-radius: 4px; padding: 2px 7px; font-weight: bold; }')
