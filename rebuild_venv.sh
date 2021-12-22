rm -rf venv
rm -rf lib

python3 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt

mkdir ./lib
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc.so.3.51 ./lib/libxmlrpc.so.3.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_client.so.3.51 ./dist/lib/libxmlrpc_client.so.3.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_util.so.4.51 ./lib/libxmlrpc_util.so.4.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_xmlparse.so.3.51 ./lib/libxmlrpc_xmlparse.so.3.51
cp ./venv/lib/python3.6/site-packages/epcore/ivmeasurer/asa10/libasa-debian/libxmlrpc_xmltok.so.3.51 ./lib/libxmlrpc_xmltok.so.3.51

ln -s ./lib/libxmlrpc.so.3.51 ./lib/libxmlrpc.so.3
ln -s ./lib/libxmlrpc_client.so.3.51 ./lib/libxmlrpc_client.so.3
ln -s ./lib/libxmlrpc_util.so.4.51 ./lib/libxmlrpc_util.so.4
ln -s ./lib/libxmlrpc_xmlparse.so.3.51 ./lib/libxmlrpc_xmlparse.so.3
ln -s ./lib/libxmlrpc_xmltok.so.3.51 ./lib/libxmlrpc_xmltok.so.3
path=$(pwd)
echo "$path/lib" > eplab_lib_config.conf
sudo cp eplab_lib_config.conf /etc/ld.so.conf.d
sudo ldconfig