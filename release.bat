set PYTHON=python
python -c "import struct; print(8 * struct.calcsize(\"P\"))" > result.txt
set /p target_platform=<result.txt
echo %target_platform%
del result.txt
echo %target_platform%

if exist venv rd /S /Q venv
if exist dist rd /S /Q dist
if exist build rd /S /Q build
if exist release rd /S /Q release
%PYTHON% -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip install pyinstaller
venv\Scripts\pyinstaller main.py ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm-win%target_platform%\ivm.dll;." ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements_2.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\ufiv.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\product\eplab_default_options.json;epcore\product" ^
--add-data "venv\Lib\site-packages\epcore\product\doc\eplab_schema.json;epcore\product\doc" ^
--add-data "venv\Lib\site-packages\epcore\measurementmanager\ivcmp-win%target_platform%\ivcmp.dll;." ^
--add-data "venv\Lib\site-packages\epsound\void.wav;epsound" ^
--add-data "media\*;media" ^
--add-data "gui\*;gui" ^
--add-data "cur.ini;." ^
--hidden-import=PyQt5.sip ^
--icon=media\ico.ico

xcopy release_templates\win%target_platform%\* dist\* /S /E
rename dist release
cd release
rename main eplab
cd ..
if exist build rd /S /Q build
if exist dist rd /S /Q dist
if exist venv rd /S /Q venv
if exist *.spec del *.spec
