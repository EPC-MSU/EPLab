set PYTHON=python
python -c "import struct; print(8 * struct.calcsize(\"P\"))" > result.txt
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
if %target_platform%==32 venv\Scripts\pyinstaller main.py --clean --onefile ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win32\asa.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win32\libxmlrpc.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win32\libxmlrpc_client.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win32\libxmlrpc_util.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win32\libxmlrpc_xmlparse.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\asa10\libasa-win32\libxmlrpc_xmltok.dll;." ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm02\ivm-win32\ivm.dll;epcore\ivmeasurer\ivm02" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm10\ivm-win32\ivm.dll;epcore\ivmeasurer\ivm10" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ASA_device_settings.json;epcore\ivmeasurer" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\EyePoint_virtual_device_settings.json;epcore\ivmeasurer" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements_2.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\ufiv.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\product\eplab_default_options.json;epcore\product" ^
--add-data "venv\Lib\site-packages\epcore\product\doc\eplab_schema.json;epcore\product\doc" ^
--add-data "venv\Lib\site-packages\epcore\measurementmanager\ivcmp-win32\ivcmp.dll;." ^
--add-data "venv\Lib\site-packages\epsound\void.wav;epsound" ^
--add-data "venv\Lib\site-packages\ivviewer\media\*;ivviewer\media" ^
--add-data "venv\Lib\site-packages\report_templates\*;report_templates" ^
--add-data "resources\eplab_asa_options.json;resources" ^
--add-data "resources\win32\*;resources\win32." ^
--add-data "media\*;media" ^
--add-data "gui\*;gui" ^
--add-data "cur.ini;." ^
--hidden-import=PyQt5.sip ^
--icon media\ico.ico

if %target_platform%==64 venv\Scripts\pyinstaller main.py --clean --onefile ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm02\ivm-win64\ivm.dll;epcore\ivmeasurer\ivm02" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm10\ivm-win64\ivm.dll;epcore\ivmeasurer\ivm10" ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\EyePoint_virtual_device_settings.json;epcore\ivmeasurer" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements_2.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\ufiv.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\product\eplab_default_options.json;epcore\product" ^
--add-data "venv\Lib\site-packages\epcore\product\doc\eplab_schema.json;epcore\product\doc" ^
--add-data "venv\Lib\site-packages\epcore\measurementmanager\ivcmp-win64\ivcmp.dll;." ^
--add-data "venv\Lib\site-packages\epsound\void.wav;epsound" ^
--add-data "venv\Lib\site-packages\ivviewer\media\*;ivviewer\media" ^
--add-data "venv\Lib\site-packages\report_templates\*;report_templates" ^
--add-data "resources\eplab_asa_options.json;resources" ^
--add-data "resources\win64\*;resources\win64." ^
--add-data "media\*;media" ^
--add-data "gui\*;gui" ^
--add-data "cur.ini;." ^
--hidden-import=PyQt5.sip ^
--icon media\ico.ico

xcopy resources\win%target_platform%\driver\* dist\driver\* /S /E
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