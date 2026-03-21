@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

echo ============================================
echo   Instalator aplikacji BHP / medycyna pracy
echo ============================================
echo.

where py >nul 2>nul
if %errorlevel% neq 0 (
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [BLAD] Nie znaleziono Pythona.
        echo Zainstaluj Python 3.11+ i zaznacz opcje "Add Python to PATH".
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python
    )
) else (
    set PYTHON_CMD=py
)

echo [1/5] Tworzenie srodowiska virtualenv...
%PYTHON_CMD% -m venv venv
if %errorlevel% neq 0 (
    echo [BLAD] Nie udalo sie utworzyc virtualenv.
    pause
    exit /b 1
)

echo [2/5] Aktywacja srodowiska...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [BLAD] Nie udalo sie aktywowac virtualenv.
    pause
    exit /b 1
)

echo [3/5] Aktualizacja pip...
python -m pip install --upgrade pip

echo [4/5] Instalacja zaleznosci...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [BLAD] Instalacja zaleznosci nie powiodla sie.
    pause
    exit /b 1
)

echo [5/5] Tworzenie skrotow startowych...
(
    echo @echo off
    echo cd /d %%~dp0
    echo call venv\Scripts\activate.bat
    echo start "" http://localhost:8501
    echo streamlit run app.py
) > start_app.bat

(
    echo Set WshShell = CreateObject("WScript.Shell")
    echo sLinkFile = WshShell.SpecialFolders("Desktop") ^& "\\Aplikacja BHP.lnk"
    echo Set oLink = WshShell.CreateShortcut(sLinkFile)
    echo oLink.TargetPath = "%~dp0start_app.bat"
    echo oLink.WorkingDirectory = "%~dp0"
    echo oLink.IconLocation = "%SystemRoot%\\System32\\SHELL32.dll,220"
    echo oLink.Save
) > utworz_skrot.vbs
cscript //nologo utworz_skrot.vbs >nul 2>nul
if exist utworz_skrot.vbs del /f /q utworz_skrot.vbs >nul 2>nul

(
    echo Set WshShell = CreateObject("WScript.Shell")
    echo WshShell.Run chr(34) ^& "%~dp0start_app.bat" ^& chr(34), 0
    echo Set WshShell = Nothing
) > autostart_hidden.vbs

echo.
echo Instalacja zakonczona.
echo Na pulpicie utworzono skrot: Aplikacja BHP
echo Do autostartu uzyj pliku: autostart_hidden.vbs
pause
