cd ..
rm -rf venv
python3 -m venv venv
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
export PYTHONPATH=$(dirname "$0")
for f in */
do
dir=${f%*/}
echo "Test $dir"
./venv/bin/python3 test.py "$dir"
done;