rm -f ./lib/libxmlrpc.so.3
rm -f ./lib/libxmlrpc_client.so.3
rm -f ./lib/libxmlrpc_util.so.4
rm -f ./lib/libxmlrpc_xmlparse.so.3
rm -f ./lib/libxmlrpc_xmltok.so.3
ln -s ./lib/libxmlrpc.so.3.51 ./lib/libxmlrpc.so.3
ln -s ./lib/libxmlrpc_client.so.3.51 ./lib/libxmlrpc_client.so.3
ln -s ./lib/libxmlrpc_util.so.4.51 ./lib/libxmlrpc_util.so.4
ln -s ./lib/libxmlrpc_xmlparse.so.3.51 ./lib/libxmlrpc_xmlparse.so.3
ln -s ./lib/libxmlrpc_xmltok.so.3.51 ./lib/libxmlrpc_xmltok.so.3
path=$(pwd)
echo "$path/lib" > eplab_lib_config.conf
sudo cp eplab_lib_config.conf /etc/ld.so.conf.d
sudo ldconfig
