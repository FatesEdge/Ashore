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
if [ ! -e "$package_dir/Ashore" ] || [ ! -f "$package_dir/icon.png" ]; then
    echo '安装包不完整：缺少 Ashore 或 icon.png。' >&2
    exit 1
fi

install -d -m 755 /opt/Ashore /usr/local/share/applications
if [ -d "$package_dir/Ashore" ]; then
    cp -R "$package_dir/Ashore/." /opt/Ashore/
else
    cp "$package_dir/Ashore" /opt/Ashore/Ashore
fi
install -m 644 "$package_dir/icon.png" /opt/Ashore/icon.png
install -m 644 "$package_dir/ashore.desktop" /usr/local/share/applications/ashore.desktop
chmod -R a+rX /opt/Ashore
chmod a+x /opt/Ashore/Ashore
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/local/share/applications
fi
echo 'Ashore 已安装到 /opt/Ashore。'
