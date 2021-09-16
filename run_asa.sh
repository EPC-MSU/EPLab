IVM_ASA_TEST=xmlrpc://172.16.128.137
IVM_ASA_REF=virtualasa
venv/bin/python3 main.py $IVM_ASA_TEST --ref $IVM_ASA_REF --config eplab_asa_options.json
