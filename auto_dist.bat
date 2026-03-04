@echo off
:: Delete old files
del /Q .\dist\*.whl 2>nul
del /Q .\dist\*.tar.gz 2>nul
if exist .\build rmdir /S /Q .\build

:: Generar distribuciones
python setup.py sdist
python setup.py bdist_wheel

:: Subir a PyPI
::twine upload dist/*
python -m twine upload dist/*.whl dist/*.tar.gz
:: twine upload --repository testpypi dist/*