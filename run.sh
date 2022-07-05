# Replace x by correct IVM COM-port numbers
# You can find COM-port numbers by command in terminal:
# ls /dev | grep ttyACM
# If you have only one device, leave other COM-port just ttyACMx
IVM_TEST="com:///dev/ttyACMx"
IVM_REF="com:///dev/ttyACMx"
./venv/bin/python3 main.py $IVM_TEST --ref $IVM_REF