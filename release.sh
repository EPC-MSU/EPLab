rm -rf build
rm -rf dist
rm -rf release
rm -rf venv
python3 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
./venv/bin/python3 -m pip install pyinstaller
./venv/bin/pyinstaller main.py \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/ivm02/ivm-debian/libivm.so:epcore/ivmeasurer/ivm02" \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/ivm10/ivm-debian/libivm.so:epcore/ivmeasurer/ivm10" \
--add-data "./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libasa.so:." \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/p10_elements.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/p10_elements_2.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/doc/ufiv.schema.json:epcore/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/product/eplab_default_options.json:epcore/product" \
--add-data "./venv/lib/python3.6/site-packages/epcore/product/doc/eplab_schema.json:epcore/product/doc" \
--add-data "./venv/lib/python3.6/site-packages/epcore/measurementmanager/ivcmp-debian/libivcmp.so:." \
--add-data "./venv/lib/python3.6/site-packages/epsound/void.wav:epsound" \
--add-data "./media/*:media" \
--add-data "./gui/*:gui" \
--add-data "./cur.ini:." \
--icon=media/ico.ico

cp ./release_templates/debian/* ./dist -R
cp ./eplab_asa_options.json ./dist/main/eplab_asa_options.json
mkdir ./dist/libs
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc.so.3.51 ./dist/libs/libxmlrpc.so.3.51
ln ./dist/libs/libxmlrpc.so.3.51 ./dist/libs/libxmlrpc.so.3
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_client.so.3.51 ./dist/libs/libxmlrpc_client.so.3.51
ln ./dist/libs/libxmlrpc_client.so.3.51 ./dist/libs/libxmlrpc_client.so.3
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_util.so.4.51 ./dist/libs/libxmlrpc_util.so.4.51
ln ./dist/libs/libxmlrpc_util.so.4.51 ./dist/libs/libxmlrpc_util.so.4
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_xmlparse.so.3.51 ./dist/libs/libxmlrpc_xmlparse.so.3.51
ln ./dist/libs/libxmlrpc_xmlparse.so.3.51 ./dist/libs/libxmlrpc_xmlparse.so.3
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_xmltok.so.3.51 ./dist/libs/libxmlrpc_xmltok.so.3.51
ln ./dist/libs/libxmlrpc_xmltok.so.3.51 ./dist/libs/libxmlrpc_xmltok.so.3
mv dist release
mv ./release/main ./release/eplab
rm -rf build
rm -rf dist
rm -rf venv
rm -rf *.spec
