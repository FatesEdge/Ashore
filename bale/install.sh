#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo '请使用 sudo 运行安装脚本。' >&2
    exit 1
fi
if ! command -v aria2c >/dev/null 2>&1; then
    echo '未检测到 aria2c。请先安装 aria2。' >&2
    exit 1
fi

package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -f "$package_dir/icon.png" ] || [ ! -f "$package_dir/ashore.desktop" ]; then
    echo '安装包不完整：缺少 icon.png 或 ashore.desktop。' >&2
    exit 1
fi
if [ -d "$package_dir/Ashore" ]; then
    executable="$package_dir/Ashore/Ashore"
else
    executable="$package_dir/Ashore"
fi
if [ ! -f "$executable" ]; then
    echo '安装包不完整：缺少 Ashore 可执行文件。' >&2
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
    echo '安装失败，原有安装已恢复。' >&2
    exit 1
fi
trap - EXIT
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/local/share/applications || echo '桌面数据库刷新失败，请手动刷新。' >&2
fi
echo 'Ashore 已安装到 /opt/Ashore。'
if [ -n "$backup" ]; then
    echo "原有安装已备份到 $backup。"
fi
