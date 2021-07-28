set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
set IVM_TEST=com:\\.\COMx
set IVM_REF=com:\\.\COMx
venv\scripts\python main.py %IVM_TEST% --ref %IVM_REF%
