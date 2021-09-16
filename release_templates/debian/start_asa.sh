path=$(pwd)
export LD_LIBRARY_PATH=$path/libs
cd eplab
./main xmlrpc://172.16.128.137 --ref virtualasa --config eplab_asa_options.json
