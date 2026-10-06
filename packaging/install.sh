#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo 'Run this installer with sudo.' >&2
    exit 1
fi

package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -f "$package_dir/icon.png" ] || [ ! -f "$package_dir/ashore.desktop" ]; then
    echo 'The package is incomplete: icon.png or ashore.desktop is missing.' >&2
    exit 1
fi
if [ -d "$package_dir/Ashore" ]; then
    executable="$package_dir/Ashore/Ashore"
else
    executable="$package_dir/Ashore"
fi
if [ ! -f "$executable" ]; then
    echo 'The package is incomplete: the Ashore executable is missing.' >&2
    exit 1
fi

install -d -m 755 /usr/local/share/applications
staging=$(mktemp -d /opt/.Ashore.new.XXXXXX)
trap 'if [ -d "$staging" ]; then rm -r -- "$staging"; fi' EXIT
if [ -d "$package_dir/Ashore" ]; then
    cp -R "$package_dir/Ashore/." "$staging/"
else
    cp "$package_dir/Ashore" "$staging/Ashore"
fi
install -m 644 "$package_dir/icon.png" "$staging/icon.png"
chmod -R a+rX "$staging"
chmod a+x "$staging/Ashore"
install -m 644 "$package_dir/ashore.desktop" /usr/local/share/applications/ashore.desktop

backup=''
if [ -e /opt/Ashore ] || [ -L /opt/Ashore ]; then
    backup=$(mktemp -d /opt/.Ashore.previous.XXXXXX)
    rmdir "$backup"
    mv /opt/Ashore "$backup"
fi
if ! mv "$staging" /opt/Ashore; then
    if [ -n "$backup" ]; then
        mv "$backup" /opt/Ashore
    fi
    echo 'Installation failed; the previous Ashore installation was restored.' >&2
    exit 1
fi
trap - EXIT
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/local/share/applications || echo 'Could not refresh the desktop database; refresh it manually if needed.' >&2
fi
echo 'Ashore was installed to /opt/Ashore.'
if [ -n "$backup" ]; then
    echo "The previous installation was backed up to $backup."
fi
