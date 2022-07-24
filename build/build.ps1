./venv/Scripts/Activate.ps1
pip install --upgrade pip setuptools wheel
python ./src/setup.py bdist_wheel
python ./src/setup.py sdist