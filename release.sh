rm -rf venv
rm -rf dist
rm -rf build
rm -rf release
python3 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
./venv/bin/python3 -m pip install pyinstaller
./venv/bin/pyinstaller main.py \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/ivm-debian/libivm.so:." \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/p10_elements.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/p10_elements_2.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/ufiv.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/measurementmanager/ivcmp-debian/libivcmp.so:." \
--add-data "./venv/lib/python3.6/site-packages/epsound/void.wav:epsound" \
--add-data "./media/*:media" \
--add-data "./gui/*:gui" \
--icon=media/ico.ico


cp ./release_templates/debian/* ./dist -R
mv dist release
mv ./release/main ./release/eplab
rm -rf build
rm -rf dist
rm -rf venv
rm -rf *.spec
