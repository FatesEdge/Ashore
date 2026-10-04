"""Centralized user-interface translations for Ashore's application shell."""


LANGUAGES = {
    'zh_CN': '简体中文',
    'zh_TW': '繁體中文',
    'en': 'English',
}


TEXT = {
    'zh_CN': {
        'file': '文件', 'edit': '编辑', 'window': '窗口', 'help': '帮助',
        'new': '新建下载', 'saveSession': '保存会话', 'restart': '重启 Aria2',
        'quit': '退出程序', 'startAll': '开始全部', 'pauseAll': '暂停全部',
        'show': '显示窗口', 'hide': '关闭窗口', 'about': '关于 Ashore',
        'showMain': '显示主窗口', 'trayQuit': '退出',
        'downloading': '下载中', 'downloaded': '已完成', 'settings': '设置',
    },
    'zh_TW': {
        'file': '檔案', 'edit': '編輯', 'window': '視窗', 'help': '說明',
        'new': '新增下載', 'saveSession': '儲存工作階段', 'restart': '重新啟動 Aria2',
        'quit': '結束程式', 'startAll': '全部開始', 'pauseAll': '全部暫停',
        'show': '顯示視窗', 'hide': '關閉視窗', 'about': '關於 Ashore',
        'showMain': '顯示主視窗', 'trayQuit': '結束',
        'downloading': '下載中', 'downloaded': '已完成', 'settings': '設定',
    },
    'en': {
        'file': 'File', 'edit': 'Edit', 'window': 'Window', 'help': 'Help',
        'new': 'New Download', 'saveSession': 'Save Session', 'restart': 'Restart Aria2',
        'quit': 'Quit Ashore', 'startAll': 'Start All', 'pauseAll': 'Pause All',
        'show': 'Show Window', 'hide': 'Hide Window', 'about': 'About Ashore',
        'showMain': 'Show Main Window', 'trayQuit': 'Quit',
        'downloading': 'Downloading', 'downloaded': 'Completed', 'settings': 'Settings',
    },
}


def translate(language, key):
    return TEXT.get(language, TEXT['zh_CN']).get(key, TEXT['zh_CN'].get(key, key))
