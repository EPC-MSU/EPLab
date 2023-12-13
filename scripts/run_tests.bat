cd ..
echo --- Run all tests ---
venv\Scripts\python -m unittest discover -v
echo --- Check flake8 ---
venv\Scripts\python -m pip install flake8
venv\Scripts\python -m flake8 .
echo --- Done ---
pause