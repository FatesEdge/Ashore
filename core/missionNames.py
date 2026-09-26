"""Remember names learned from aria2 while the corresponding tasks still exist."""

import json
import os
import tempfile

from paths import CONFIG_DIR


class MissionNames:
    def __init__(self, path=None):
        self.path = path or CONFIG_DIR / 'missionNames.json'
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        self.names = {gid: name for gid, name in data.items()
                      if isinstance(gid, str) and isinstance(name, str) and name}
        self.saved = self.names.copy()

    def resolve(self, gid, candidate, retain):
        if retain and candidate:
            self.names[gid] = candidate
            return candidate
        return self.names.get(gid, candidate)

    def sync(self, gids):
        """Save only after a complete successful poll, dropping removed tasks."""
        present = set(gids)
        self.names = {gid: name for gid, name in self.names.items() if gid in present}
        if self.names == self.saved:
            return
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.missionNames-', delete=False) as file:
                temporary = file.name
                os.chmod(temporary, 0o600)
                json.dump(self.names, file, ensure_ascii=False)
            os.replace(temporary, self.path)
        except OSError:
            # A read-only config directory must not stop downloads.
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
        else:
            self.saved = self.names.copy()
