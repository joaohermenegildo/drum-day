@echo off
echo Gerando executavel .exe com PyInstaller...
call venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --onefile --windowed --name "DrumDay" --add-data "templates;templates" --add-data "static;static" app.py
echo.
echo EXE gerado na pasta dist/DrumDay.exe
pause
