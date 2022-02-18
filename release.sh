rm -rf build
rm -rf dist
rm -rf release
rm -rf venv

python3 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
./venv/bin/python3 -m pip install pyinstaller
./venv/bin/pyinstaller main.py --clean --onefile --noconsole \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libasa.so:." \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/ivm02/ivm-debian/libivm.so:epcore/ivmeasurer/ivm02" \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/ivm10/ivm-debian/libivm.so:epcore/ivmeasurer/ivm10" \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/ASA_device_settings.json:epcore/ivmeasurer" \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/EyePoint_virtual_device_settings.json:epcore/ivmeasurer" \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/EyePoint_settings.json:epcore/ivmeasurer" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/p10_elements.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/p10_elements_2.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/ufiv.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/product/eplab_default_options.json:epcore/product" \
--add-data "./venv/lib/python3.6/site-packages/epcore/product/doc/eplab_schema.json:epcore/product/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/measurementmanager/ivcmp-debian/libivcmp.so:." \
--add-data "./venv/lib/python3.6/site-packages/epsound/void.wav:epsound" \
--add-data "./venv/lib/python3.6/site-packages/ivviewer/media/*:ivviewer/media" \
--add-data "./venv/lib/python3.6/site-packages/report_templates/*:report_templates" \
--add-data "./resources/eplab_asa_options.json:resources" \
--add-data "./resources/debian/*:resources/debian" \
--add-data "./media/*:media" \
--add-data "./gui/*:gui" \
--add-data "./cur.ini:." \
--icon media/ico.ico

mkdir ./dist/lib
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libasa.so ./dist/lib/libasa.so
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc.so.3.51 ./dist/lib/libxmlrpc.so.3.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_client.so.3.51 ./dist/lib/libxmlrpc_client.so.3.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_util.so.4.51 ./dist/lib/libxmlrpc_util.so.4.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_xmlparse.so.3.51 ./dist/lib/libxmlrpc_xmlparse.so.3.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_xmltok.so.3.51 ./dist/lib/libxmlrpc_xmltok.so.3.51
cp ./resources/readme.md ./dist/readme.md
cp ./resources/debian/install_libs.sh ./dist/install_libs.sh
mv dist release
mv ./release/main ./release/eplab
rm -rf build
rm -rf dist
rm -rf venv
rm -rf *.spec
