./venv/Scripts/Activate.ps1
pip3 install --upgrade pip setuptools wheel
cd ./playquick
python ./setup.py bdist_wheel
python ./setup.py sdist