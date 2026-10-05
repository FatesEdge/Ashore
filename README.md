<h1  align="center">Ashore</h1>

<p align="center">
  <a target="_blank" href="https://github.com/PanZK/Ashore"><img src="https://raw.githubusercontent.com/PanZK/Ashore/main/static/icon/functionIcons/icon0.png"></a></p>
<p align="center"><br>Ashore 是一个用Python编写的内核为aria2的界面管理程序。<br><br>
</p>

&emsp;&emsp;![](https://img.shields.io/badge/python-3.12%2B-blue)&ensp;![](https://img.shields.io/badge/PyQt-v6-yellowgreen)&ensp;![License](https://img.shields.io/badge/license-MPL--2.0-blue)&ensp;[Releases](https://github.com/FatesEdge/Ashore/releases)

---

## Origin

&emsp;下载器有很多，逐渐变得不好用，使用aria2后感觉很好，没有界面是一大特点，但用着也稍嫌费劲。网络上已有很多大佬做的各种界面程序基本都使用过感觉都非常棒，不过有时候太符合自己操作习惯，在再加上自己想练练手，遂coding小白就用Python做了一个。

## Features

- 下载内核部分直接使用[aria2](https://github.com/aria2/aria2)
- 程序界面使用[PyQt6](https://pypi.org/project/PyQt6/)制作
- RPC 默认端口为 `6801`，Ashore 会读取用户配置的端口与密钥
- RPC 默认仅允许本机访问；设置页可选择开放外部访问，并显示只读的授权令牌
- Ashore配置文件单独存放于ashore.conf文件中
- 程序中可对aria2的配置简单进行更改，后续可以加入更多配置选项（[Mac下配置Aria2](https://gist.github.com/sumpeter/9f71b26b0e79cfd3bae39c3bdf6cfd8c)这里讲的非常细致）
- 主界面显示 aria2 RPC 连接状态；WebSocket 通知促使任务立即刷新，定时查询用于同步进度及断线恢复
- 下载完成或出错时通过系统通知提示；已获取的任务名称保存在用户配置目录中
- 启动准备工作在后台执行，开屏窗口显示当前阶段；Tracker 超时不会阻止进入主界面
- 支持跟随系统、浅色、深色主题以及统一的主题颜色
- BT Tracker 首次运行自动获取，之后可选择在启动时按24小时周期自动更新

## Stand by

- Ubuntu 18.04 或更高版本
- MacOS 10.15 或更高版本

## Install

### 	MacOS

1. 确认已安装好[aria2](https://github.com/aria2/aria2)；
2. 下载 [release](https://github.com/FatesEdge/Ashore/releases) 中的 `dmg` 文件；
3. 双击运行 `dmg` 文件，将Ashorer拉进 `Applications` 文件夹；
4. 程序坞中找到，点击运行。

### 	Linux

1. 确认已安装好[aria2](https://github.com/aria2/aria2)；

2. 下载 [release](https://github.com/FatesEdge/Ashore/releases) 中的 Linux 包并解压；

3. 终端进入解压目录执行

   ```
   sudo ./install.sh
   ```

   如从源码打包，先按下文执行 `python3 make.py onefile`，然后在 `dist/Ashore.Linux.onefile/` 中运行上述安装脚本。

4. Ashore 安装在 `/opt/Ashore`，桌面入口安装在 `/usr/local/share/applications/ashore.desktop`。覆盖旧版时，安装脚本会显示旧版备份目录；确认新版本可用后可手动删除备份。用户配置仍在 `~/.config/ashore/`。

### 	Windows

- 尚未测试



## Usage

运行 Ashore 后，可在设置页配置 aria2、RPC、Tracker、界面主题和托盘图标。

## make

GitHub Actions 在 Linux 上运行测试、检查打包脚本，构建 `onefile` 并进行无界面启动检查；它不会安装程序或自动发布 Release。本机安装后的桌面关联和实际下载仍需手动验证。

1. 编程环境vscode、python3.10、pyqt6

2. 安装 `PyQt6` 和 `PyInstaller` 后，在项目根目录执行

   ```
   python3 make.py onefile
   # 如需目录形式：python3 make.py onedir
   ```

   Linux 包位于 `dist/Ashore.Linux.onefile/` 或 `dist/Ashore.Linux.onedir/`，两种包均有独立的 `install.sh`。`onefile` 只需分发包内的可执行文件、图标、桌面入口及安装脚本；`onedir` 必须完整保留 Ashore 目录（包括 PyInstaller 运行时文件）。构建成功后才替换旧的同名包。macOS 使用 `python3 make.py app` 或 `python3 make.py dmg`，需在 macOS 上执行。

首次运行时，配置写入 `~/.config/ashore/`（设置了 `XDG_CONFIG_HOME` 时使用对应目录）。RPC 默认只监听本机，不生成令牌。只有在设置页打开“允许外部访问 RPC”时，Ashore 才会生成令牌；令牌只能显示和复制，不能在界面中修改，请勿公开。端口、监听范围或令牌发生变化后，Ashore 会先通过当前 RPC 安全关闭 aria2，再用新配置启动；若当前进程拒绝关闭，配置仍会保留并明确提示手动重启。启动失败可查看同目录的 `aria2-startup.log`。

设置页同时显示 Ashore 实际使用的 HTTP 轮询地址、WebSocket 通知地址、两条通道的连接状态及 aria2 版本。HTTP 仍是任务状态的最终来源，WebSocket 用于及时触发刷新。

User Agent 使用可编辑下拉框：预设是 `ashore.conf` 中的完整 UA 字符串，也可以直接输入自定义值；当前选择仍保存到 `aria2.conf`。

首次配置不预置可能过期的 Tracker 地址。Ashore 首次启动时会在后台获取一次；以后仅在开启自动更新且上次成功更新超过24小时时重新获取。启动界面最多等待1秒，随后进入主界面并在后台继续。失败时保留已有列表、来源和成功时间。

开发运行时如需检查启动阶段耗时，可执行 `ASHORE_STARTUP_TRACE=1 python Ashore.py`。日志只输出各启动阶段及相对耗时，不记录下载地址、令牌或其他用户数据。

## 代码结构

- `Ashore.py`：应用入口、主窗口编排、连接状态和系统通知
- `core/aria2Client.py`：aria2 HTTP JSON-RPC 与任务整理
- `core/aria2Service.py`：aria2 进程生命周期、异步启动和轮询
- `core/aria2Events.py`：WebSocket 事件及重连；不可用时仍按间隔查询
- `core/trackerManager.py`、`core/trackerSources.py`：Tracker 更新策略、持久化、来源与校验
- `core/configStore.py`：配置读取与原子写入
- `interface/startupWindow.py`、`interface/themeManager.py`：启动反馈与统一主题
- `interface/`：下载页面、任务卡片、设置页和新建下载对话框
- `paths.py`：源代码及打包运行共用的资源、配置路径

## Development

1. 上一版是通过[aria2p](https://github.com/pawamoy/aria2p)实现，后面感觉过于繁琐，故自行写了一版，目前仍有许多不足，后续继续努力；
2. 后续可继续补充常用文件类型图标；
3. 目前手头没有Windows实体机及虚拟机，还未对win平台做测试；
4. 继续扩大简体中文、繁体中文、英语的翻译覆盖范围；
5. 后续考虑对任务管理添加多选功能。



---

<p align="center">
  Enjoy it!
</p>
