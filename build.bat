@echo off
REM Build script for TiddlyWiki Manager (Windows)
REM This script builds the React frontend and outputs to src/assets/index.html

echo ======================================
echo TiddlyWiki Manager - Build Script
echo ======================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js 16+ from https://nodejs.org/
    exit /b 1
)

REM Check if npm is installed
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: npm is not installed!
    echo Please install npm (usually comes with Node.js^)
    exit /b 1
)

echo Node.js version:
node --version
echo npm version:
npm --version
echo.

REM Navigate to React app directory
cd react-app

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing npm dependencies...
    call npm install
    echo.
) else (
    echo npm dependencies already installed (skipping npm install^)
    echo To reinstall, delete node_modules and run this script again
    echo.
)

REM Build the React app
echo Building React application...
call npm run build

REM Check if build was successful
if exist "..\src\assets\index.html" (
    echo.
    echo ======================================
    echo Build completed successfully!
    echo ======================================
    echo.
    echo The React app has been built to: src\assets\index.html
    echo Assets are in: src\assets\assets\
    echo.
    echo You can now run the application with:
    echo   python src\main.py
    echo.
) else (
    echo.
    echo ======================================
    echo Build failed!
    echo ======================================
    echo.
    echo The index.html file was not created in src\assets\
    echo Please check the error messages above.
    exit /b 1
)

cd ..
