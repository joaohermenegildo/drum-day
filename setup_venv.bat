@echo off
echo ============================================
echo  Drum Day - Configurando ambiente virtual
echo ============================================
echo.

python -m venv venv
call venv\Scripts\activate.bat

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo ============================================
echo  Tudo pronto! Para rodar o programa use:
echo  run.bat
echo ============================================
pause
