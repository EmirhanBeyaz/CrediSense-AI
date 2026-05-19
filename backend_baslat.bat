@echo off
cd /d "%~dp0"
echo CrediSense AI backend baslatiliyor...
echo Adres: http://127.0.0.1:8000
echo Bu pencere acik kaldigi surece frontend API ve Gmail dogrulama calisir.
python -B -m uvicorn backend.credisense.api:app --host 127.0.0.1 --port 8000 --reload
pause
