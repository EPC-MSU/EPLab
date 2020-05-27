set PYTHON=C:\Python36\python


rd /S /Q venv
%PYTHON% -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt

venv\Scripts\python -m pip install pyinstaller
rd /S /Q dist
rd /S /Q build
venv\Scripts\pyinstaller main.py ^
--add-data "venv\Lib\site-packages\epcore\ivmeasurer\ivm-win64\ivm.dll;." ^
--add-data "venv\Lib\site-packages\epcore\measurementmanager\ivcmp-win64\ivcmp.dll;." ^
--add-dava "venv\Lib\site-packages\epsound\void.wav;." ^
--add-data "media\*;media" ^
--add-data "gui\*;gui" ^
--icon=media\ico.ico