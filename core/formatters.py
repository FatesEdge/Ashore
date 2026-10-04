"""Shared human-readable value formatting."""


def formatBytes(value):
    value = max(0, int(value))
    units = ('B', 'KB', 'MB', 'GB', 'TB')
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f'{int(amount)}{unit}' if unit == 'B' else f'{amount:.2f}{unit}'
        amount /= 1024


def formatSpeed(value):
    return f'{formatBytes(value)}/s'
