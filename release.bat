set PYTHON=python


if exist venv rd /S /Q venv
if exist dist rd /S /Q dist
if exist build rd /S /Q build
if exist release rd /S /Q releaseв
%PYTHON% -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip install pyinstaller
venv\Scripts\pyinstaller main.py ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm-win64\ivm.dll;." ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\p10_elements_2.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\doc\ufiv.schema.json;epcore\doc" ^
--add-data "venv\Lib\site-packages\epcore\measurementmanager\ivcmp-win64\ivcmp.dll;." ^
--add-data "venv\Lib\site-packages\epsound\void.wav;epsound" ^
--add-data "media\*;media" ^
--add-data "gui\*;gui" ^
--icon=media\ico.ico

xcopy release_templates\win64* dist\* /S /E
rename dist release
cd release
rename main eplab
cd ..
if exist build rd /S /Q build
if exist dist rd /S /Q dist
if exist venv rd /S /Q venv
if exist *.spec del *.spec
