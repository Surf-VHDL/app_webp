@echo off
REM Script di setup e avvio self-contained per app_webp su Windows
REM - Prepara runtime Python locale (.venv o Python embedded)
REM - Scarica cwebp locale se assente
REM - Installa dipendenze Python nella cartella progetto

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "ROOT_DIR=%~dp0"
set "LOCAL_DIR=%ROOT_DIR%.local"
set "VENV_DIR=%ROOT_DIR%.venv"
set "PY_EMBED_DIR=%LOCAL_DIR%\python-embed"
set "PY_DEPS_DIR=%LOCAL_DIR%\pydeps"
set "WHEELHOUSE_DIR=%LOCAL_DIR%\wheelhouse"
set "WEBP_DIR=%LOCAL_DIR%\webp"
set "CWEBP_EXE="
set "BOOTSTRAP_PY="
set "RUN_PY="
set "USING_VENV=0"
set "OFFLINE_MODE=0"

if /I "%~1"=="--offline" set "OFFLINE_MODE=1"
if /I "%~1"=="/offline" set "OFFLINE_MODE=1"

set "PY_EMBED_VERSION=3.12.10"
set "PY_EMBED_ZIP=python-%PY_EMBED_VERSION%-embed-amd64.zip"
set "PY_EMBED_URL=https://www.python.org/ftp/python/%PY_EMBED_VERSION%/%PY_EMBED_ZIP%"
set "WEBP_VERSION=1.6.0"
set "WEBP_ZIP=libwebp-%WEBP_VERSION%-windows-x64.zip"
set "WEBP_URL=https://storage.googleapis.com/downloads.webmproject.org/releases/webp/%WEBP_ZIP%"
set "CWEBP_EXE=%WEBP_DIR%\libwebp-%WEBP_VERSION%-windows-x64\bin\cwebp.exe"

echo.
echo ========================================
echo app_webp - Windows Setup ^& Launcher
echo ========================================
echo.
if "%OFFLINE_MODE%"=="1" (
    echo Modalita offline attiva: nessun download da rete.
    echo.
)

if not exist "%LOCAL_DIR%" mkdir "%LOCAL_DIR%"

REM ========== PREPARA PYTHON ==========
echo [1/4] Preparo Python locale...

set "RUN_PY=%VENV_DIR%\Scripts\python.exe"
if exist "%RUN_PY%" (
    set "USING_VENV=1"
    echo   OK: uso venv locale esistente (.venv)
) else (
    set "BOOTSTRAP_PY=%PY_EMBED_DIR%\python.exe"

    if not exist "%BOOTSTRAP_PY%" (
        echo   Python embedded locale non trovato, avvio bootstrap locale...
        if "%OFFLINE_MODE%"=="1" (
            echo ERRORE: Python embedded locale assente e modalita offline attiva.
            echo Esegui una volta senza --offline per completare il bootstrap locale.
            pause
            exit /b 1
        )

        powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_EMBED_URL%' -OutFile '%LOCAL_DIR%\%PY_EMBED_ZIP%'"
        if errorlevel 1 (
            echo ERRORE: download Python embedded fallito.
            pause
            exit /b 1
        )

        if exist "%PY_EMBED_DIR%" rmdir /s /q "%PY_EMBED_DIR%"
        mkdir "%PY_EMBED_DIR%"
        powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%LOCAL_DIR%\%PY_EMBED_ZIP%' -DestinationPath '%PY_EMBED_DIR%' -Force"
        if errorlevel 1 (
            echo ERRORE: estrazione Python embedded fallita.
            pause
            exit /b 1
        )

        for %%f in ("%PY_EMBED_DIR%\python*._pth") do (
            powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%%~ff'; $c=Get-Content $p; if($c -notcontains 'import site'){ Add-Content -Path $p -Value 'import site' }"
        )

        if not exist "%LOCAL_DIR%\get-pip.py" (
            powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%LOCAL_DIR%\get-pip.py'"
            if errorlevel 1 (
                echo ERRORE: download get-pip.py fallito.
                pause
                exit /b 1
            )
        )

        "%BOOTSTRAP_PY%" "%LOCAL_DIR%\get-pip.py" --no-warn-script-location >nul 2>&1
        if errorlevel 1 (
            echo ERRORE: installazione pip su Python embedded fallita.
            pause
            exit /b 1
        )

        echo   OK: Python embedded locale pronto
    ) else (
        echo   OK: uso Python embedded locale
    )

    if not exist "%VENV_DIR%\Scripts\python.exe" (
        "%BOOTSTRAP_PY%" -m venv "%VENV_DIR%" >nul 2>&1
    )

    if exist "%VENV_DIR%\Scripts\python.exe" (
        set "RUN_PY=%VENV_DIR%\Scripts\python.exe"
        set "USING_VENV=1"
        echo   OK: venv locale creato in .venv
    ) else (
        set "RUN_PY=%BOOTSTRAP_PY%"
        set "USING_VENV=0"
        echo   ATTENZIONE: venv non disponibile, uso Python locale senza venv
    )
)

if not exist "%RUN_PY%" (
    echo ERRORE: impossibile determinare un runtime Python locale valido.
    echo Esegui una volta senza --offline per completare il bootstrap locale.
    pause
    exit /b 1
)

set "PYTHON_VERSION="
for /f "usebackq delims=" %%i in (`"%RUN_PY%" --version 2^>^&1`) do (
    set "PYTHON_VERSION=%%i"
    goto :python_version_done
)
:python_version_done
if not defined PYTHON_VERSION set "PYTHON_VERSION=unknown"
echo   Runtime Python: !PYTHON_VERSION!

REM ========== PREPARA CWEBP ==========
echo.
echo [2/4] Verifico cwebp...

if exist "%CWEBP_EXE%" goto :cwebp_ready

where cwebp >nul 2>&1
if not errorlevel 1 (
    for /f "usebackq delims=" %%i in (`where cwebp`) do (
        set "CWEBP_EXE=%%i"
        goto :cwebp_ready
    )
)

echo   cwebp non trovato, scarico libwebp locale...
if "%OFFLINE_MODE%"=="1" (
    echo ERRORE: cwebp non trovato e modalita offline attiva.
    echo Esegui una volta senza --offline per scaricare libwebp locale.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%WEBP_URL%' -OutFile '%LOCAL_DIR%\%WEBP_ZIP%'"
if errorlevel 1 (
    echo ERRORE: download libwebp fallito.
    pause
    exit /b 1
)

if exist "%WEBP_DIR%" rmdir /s /q "%WEBP_DIR%"
mkdir "%WEBP_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path '%LOCAL_DIR%\%WEBP_ZIP%' -DestinationPath '%WEBP_DIR%' -Force"
if errorlevel 1 (
    echo ERRORE: estrazione libwebp fallita.
    pause
    exit /b 1
)

set "CWEBP_EXE="
for /r "%WEBP_DIR%" %%f in (cwebp.exe) do (
    set "CWEBP_EXE=%%f"
    goto :cwebp_ready
)

echo ERRORE: cwebp.exe non trovato dopo estrazione.
pause
exit /b 1

:cwebp_ready
if not exist "%CWEBP_EXE%" (
    set "CWEBP_EXE="
    for /r "%WEBP_DIR%" %%f in (cwebp.exe) do (
        set "CWEBP_EXE=%%f"
        goto :cwebp_path_found
    )
)

:cwebp_path_found
if not defined CWEBP_EXE (
    echo ERRORE: cwebp.exe non trovato nella cartella locale.
    pause
    exit /b 1
)
if not exist "%CWEBP_EXE%" (
    echo ERRORE: percorso cwebp non valido: %CWEBP_EXE%
    pause
    exit /b 1
)

for %%d in ("%CWEBP_EXE%") do set "CWEBP_DIR_PATH=%%~dpd"
set "PATH=%CWEBP_DIR_PATH%;%PATH%"

"%CWEBP_EXE%" -version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: cwebp non eseguibile: %CWEBP_EXE%
    pause
    exit /b 1
)

set "CWEBP_VERSION="
for /f "usebackq delims=" %%i in (`"%CWEBP_EXE%" -version 2^>^&1`) do (
    set "CWEBP_VERSION=%%i"
    goto :cwebp_version_done
)
:cwebp_version_done
if not defined CWEBP_VERSION set "CWEBP_VERSION=unknown"
echo   OK: cwebp !CWEBP_VERSION! (%CWEBP_EXE%)

REM ========== INSTALLA DIPENDENZE PYTHON ==========
echo.
echo [3/4] Installo dipendenze Python locali...
if not exist "requirements.txt" (
    echo ERRORE: requirements.txt non trovato!
    pause
    exit /b 1
)

if not exist "%WHEELHOUSE_DIR%" mkdir "%WHEELHOUSE_DIR%"

if "%USING_VENV%"=="1" (
    "%RUN_PY%" -c "import PySide6" >nul 2>&1
    if errorlevel 1 (
        if "%OFFLINE_MODE%"=="1" (
            if not exist "%WHEELHOUSE_DIR%\*.whl" (
                echo ERRORE: nessuna wheel locale disponibile in %WHEELHOUSE_DIR%.
                echo Esegui una volta senza --offline per popolare la cache locale.
                pause
                exit /b 1
            )
            "%RUN_PY%" -m pip install --no-index --find-links "%WHEELHOUSE_DIR%" -r requirements.txt
            if errorlevel 1 (
                echo ERRORE: installazione offline dipendenze nel venv fallita.
                pause
                exit /b 1
            )
        ) else (
            "%RUN_PY%" -m pip install --quiet --upgrade pip >nul 2>&1
            "%RUN_PY%" -m pip download --dest "%WHEELHOUSE_DIR%" -r requirements.txt >nul 2>&1
            "%RUN_PY%" -m pip install --quiet -r requirements.txt
            if errorlevel 1 (
                echo ERRORE: installazione dipendenze nel venv fallita.
                pause
                exit /b 1
            )
        )
    ) else (
        echo   Dipendenze gia presenti nel runtime locale
    )
) else (
    if not exist "%PY_DEPS_DIR%" mkdir "%PY_DEPS_DIR%"
    set "PYTHONPATH=%PY_DEPS_DIR%;%PYTHONPATH%"
    "%RUN_PY%" -c "import sys; sys.path.insert(0, r'%PY_DEPS_DIR%'); import PySide6" >nul 2>&1
    if errorlevel 1 (
        if "%OFFLINE_MODE%"=="1" (
            if not exist "%WHEELHOUSE_DIR%\*.whl" (
                echo ERRORE: nessuna wheel locale disponibile in %WHEELHOUSE_DIR%.
                echo Esegui una volta senza --offline per popolare la cache locale.
                pause
                exit /b 1
            )
            "%RUN_PY%" -m pip install --upgrade --no-index --find-links "%WHEELHOUSE_DIR%" --target "%PY_DEPS_DIR%" -r requirements.txt
            if errorlevel 1 (
                echo ERRORE: installazione offline dipendenze locali fallita.
                pause
                exit /b 1
            )
        ) else (
            "%RUN_PY%" -m pip install --quiet --upgrade pip >nul 2>&1
            "%RUN_PY%" -m pip download --dest "%WHEELHOUSE_DIR%" -r requirements.txt >nul 2>&1
            "%RUN_PY%" -m pip install --quiet --upgrade --target "%PY_DEPS_DIR%" -r requirements.txt
            if errorlevel 1 (
                echo ERRORE: installazione dipendenze locali fallita.
                pause
                exit /b 1
            )
        )
    ) else (
        echo   Dipendenze gia presenti nel runtime locale
    )
)
echo   OK: dipendenze pronte

REM ========== AVVIA APP ==========
echo.
echo [4/4] Avvio app...
echo.
if "%USING_VENV%"=="1" (
    "%RUN_PY%" app_webp.py
) else (
    "%RUN_PY%" -c "import runpy, sys; sys.path.insert(0, r'%PY_DEPS_DIR%'); runpy.run_path('app_webp.py', run_name='__main__')"
)
if errorlevel 1 (
    echo.
    echo ERRORE durante l'esecuzione dell'app!
    echo.
    pause
    exit /b 1
)

endlocal
exit /b 0
