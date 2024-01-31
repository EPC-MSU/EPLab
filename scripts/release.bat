cd ..
set PYTHON=python
%PYTHON% -c "import struct; print(8 * struct.calcsize(\"P\"))" > result.txt
set /p target_platform=<result.txt
echo %target_platform%
del result.txt
echo %target_platform%

if exist build rd /S /Q build
if exist dist rd /S /Q dist
if exist release rd /S /Q release
if exist venv rd /S /Q venv
%PYTHON% -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip install pyinstaller
venv\Scripts\pyinstaller main.py --clean --onefile --noconsole ^
--add-data "break_signatures\*;break_signatures" ^
--add-data "cur.ini;." ^
--add-data "gui\*;gui" ^
--add-data "media\*;media" ^
--add-data "resources\eplab_asa_options.json;resources" ^
--add-data "resources\win%target_platform%\*;resources\win%target_platform%" ^
--add-data "venv\Lib\site-packages\epcore\analogmultiplexer\epmux\epmux-win%target_platform%\epmux.dll;." ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements_2.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\ufiv.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ASA_device_settings.json;epcore\ivmeasurer" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win%target_platform%\asa.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win%target_platform%\libxmlrpc.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win%target_platform%\libxmlrpc_client.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win%target_platform%\libxmlrpc_util.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win%target_platform%\libxmlrpc_xmlparse.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win%target_platform%\libxmlrpc_xmltok.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\EyePoint_settings.json;epcore\ivmeasurer" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\EyePoint_virtual_device_settings.json;epcore\ivmeasurer" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm02\ivm-win%target_platform%\ivm.dll;epcore\ivmeasurer\ivm02\ivm-win%target_platform%" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm10\ivm-win%target_platform%\ivm.dll;epcore\ivmeasurer\ivm10\ivm-win%target_platform%" ^
--add-data "venv\Lib\site-packages\epcore\measurementmanager\ivcmp-win%target_platform%\ivcmp.dll;." ^
--add-data "venv\Lib\site-packages\epcore\product\doc\eplab_schema.json;epcore\product\doc" ^
--add-data "venv\Lib\site-packages\epcore\product\eplab_default_options.json;epcore\product" ^
--add-data "venv\Lib\site-packages\epsound\void.wav;epsound" ^
--add-data "venv\Lib\site-packages\ivviewer\media\*;ivviewer\media" ^
--add-data "venv\Lib\site-packages\report_generator\locales\en\LC_MESSAGES\*;report_generator\locales\en\LC_MESSAGES" ^
--add-data "venv\Lib\site-packages\report_templates\*;report_templates" ^
--hidden-import=PyQt5.sip ^
--icon media\icon.ico ^
--splash media\banner.png

xcopy resources\win%target_platform%\drivers\* dist\drivers\* /S /E
copy resources\readme.md dist
rename dist release
cd release
rename main.exe eplab.exe
cd ..
if exist build rd /S /Q build
if exist dist rd /S /Q dist
if exist venv rd /S /Q venv
if exist *.spec del *.spec
pause