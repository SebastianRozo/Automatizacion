@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller ^
  --noconsole ^
  --onefile ^
  --name AutomatizacionPoliedro ^
  --add-data "app\template\plantillaExcel\M-GO-FT-02 Formato Consolidado pago de volantes V1.-1.xlsx;app\template\plantillaExcel" ^
  desktop_app.py

echo.
echo Build finalizado. Ejecutable: dist\AutomatizacionPoliedro.exe
pause
