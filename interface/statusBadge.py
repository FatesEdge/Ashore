"""Shared semantic connection-state presentation."""

from PyQt6.QtGui import QColor, QPalette


_STATE_COLORS = {
    'connected': QColor('#69ad78'),
    'disconnected': QColor('#d46b6b'),
    'connecting': QColor('#9aa0a6'),
    'neutral': QColor('#9aa0a6'),
}


def setConnectionBadge(label, text, state):
    """Apply a lightweight connection marker without forcing a repolish."""
    if isinstance(state, bool):
        state = 'connected' if state else 'disconnected'
    if state not in _STATE_COLORS:
        state = 'neutral'
    label.setText(f'● {text}')
    palette = label.palette()
    palette.setColor(QPalette.ColorRole.WindowText, _STATE_COLORS[state])
    label.setPalette(palette)
