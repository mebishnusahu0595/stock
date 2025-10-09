@echo off
echo ========================================
echo  AUTO TRADING LOGIC TESTER
echo ========================================
echo.
echo Choose testing method:
echo.
echo 1. Run Python Console Tests
echo 2. Open Web-based Test Interface  
echo 3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Starting Python console tests...
    echo.
    python test_auto_trading.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo Opening web-based test interface...
    echo.
    start test_auto_trading.html
    echo Web interface opened in your default browser.
    pause
) else if "%choice%"=="3" (
    echo.
    echo Goodbye!
    exit
) else (
    echo.
    echo Invalid choice. Please try again.
    pause
    goto :start
)

:start
cls
goto :eof
