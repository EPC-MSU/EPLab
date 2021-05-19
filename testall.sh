rm -rf venv

set -e

python3.6 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/python -m pip install -r requirements.txt

export PYTHONPATH=$(dirname "$0")

./venv/bin/python test.py tests