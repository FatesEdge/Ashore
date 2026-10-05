"""Shared semantic connection-state presentation."""


def setConnectionBadge(label, text, state):
    """Apply a lightweight state marker; ThemeManager owns its appearance."""
    if isinstance(state, bool):
        state = 'connected' if state else 'disconnected'
    if state not in {'connected', 'disconnected', 'connecting', 'neutral'}:
        state = 'neutral'
    label.setText(f'● {text}')
    label.setProperty('connectionBadge', True)
    label.setProperty('connectionState', state)
    style = label.style()
    style.unpolish(label)
    style.polish(label)
    label.update()
