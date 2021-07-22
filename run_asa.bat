set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
set IVM_ASA_TEST=xmlrpc:172.16.128.137
set IVM_ASA_REF=virtualasa
venv\Scripts\python main.py %IVM_ASA_TEST% --ref %IVM_ASA_REF% --config eplab_asa_options.json
pause