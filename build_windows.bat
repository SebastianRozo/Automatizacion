@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller ^
  --noconsole ^
  --onefile ^
  --name AutomatizacionPoliedro ^
  --hidden-import="selenium.webdriver.chrome.webdriver" ^
  --add-binary "app\browser\drivers\chromedriver.exe;app\browser\drivers" ^
  desktop_app.py

echo.
echo Build finalizado. Ejecutable: dist\AutomatizacionPoliedro.exe
pause
