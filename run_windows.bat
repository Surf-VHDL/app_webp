@echo off
REM Script di setup e avvio per app_webp su Windows
REM Controlla e installa: Python, libwebp, dipendenze Python
REM Poi avvia l'app

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ========================================
echo app_webp - Windows Setup & Launcher
echo ========================================
echo.

REM ========== CONTROLLA PYTHON ==========
echo [1/4] Verifica Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERRORE: Python non trovato!
    echo.
    echo Soluzione:
    echo 1. Scarica Python 3.10+ da https://www.python.org
    echo 2. Durante l'installazione, SPUNTA "Add Python to PATH"
    echo 3. Riavvia il prompt dei comandi
    echo 4. Esegui di nuovo questo script
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo   OK: Python !PYTHON_VERSION! trovato
)

REM ========== CONTROLLA CWEBP ==========
echo.
echo [2/4] Verifica libwebp (cwebp)...
cwebp -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ATTENZIONE: cwebp non trovato!
    echo.
    echo L'app richiede libwebp per convertire le immagini.
    echo.
    echo Opzioni di installazione:
    echo.
    echo Opzione A - Scarica manualmente (CONSIGLIATO):
    echo   1. Visita: https://github.com/webmproject/libwebp/releases
    echo   2. Scarica libwebp-X.X.X-windows-x64.zip
    echo   3. Estrai il file
    echo   4. Aggiungi la cartella 'bin' al PATH di Windows
    echo   5. Riavvia il prompt dei comandi
    echo.
    echo Opzione B - Usa Chocolatey (se installato):
    echo   choco install libwebp
    echo.
    echo Dopo l'installazione, esegui di nuovo questo script.
    echo.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('cwebp -version 2^>^&1') do set CWEBP_VERSION=%%i
    echo   OK: cwebp !CWEBP_VERSION! trovato
)

REM ========== INSTALLA DIPENDENZE PYTHON ==========
echo.
echo [3/4] Installa dipendenze Python...
if not exist "requirements.txt" (
    echo ERRORE: requirements.txt non trovato!
    pause
    exit /b 1
)

python -m pip install --quiet --upgrade pip >nul 2>&1
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERRORE durante l'installazione delle dipendenze Python!
    echo.
    pause
    exit /b 1
) else (
    echo   OK: Dipendenze installate
)

REM ========== AVVIA L'APP ==========
echo.
echo [4/4] Avvio dell'app...
echo.
python app_webp.py
if errorlevel 1 (
    echo.
    echo ERRORE durante l'esecuzione dell'app!
    echo.
    pause
    exit /b 1
)

endlocal
exit /b 0
