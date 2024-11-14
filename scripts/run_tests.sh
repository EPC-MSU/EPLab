cd ..
echo "--- Run all tests ---"
./venv/bin/python -m unittest discover -v
echo "--- Check flake8 ---"
./venv/bin/python -m pip install flake8
./venv/bin/python -m flake8 .
echo "--- Done ---"