REM Replace x by correct IVM COM-port numbers.
REM You can find COM-port number in Windows Device Manager.
REM If you have only one device, leave other COM-port just COMx.

cd ..
set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
set IVM_TEST=com:\\.\COMx
set IVM_REF=com:\\.\COMx
venv\Scripts\python main.py
pause