#!/bin/bash

# Build script for TiddlyWiki Manager
# This script builds the React frontend and outputs to src/assets/index.html

set -e  # Exit on error

echo "======================================"
echo "TiddlyWiki Manager - Build Script"
echo "======================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed!"
    echo "Please install Node.js 16+ from https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm is not installed!"
    echo "Please install npm (usually comes with Node.js)"
    exit 1
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"
echo ""

# Navigate to React app directory
cd react-app

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install
    echo ""
else
    echo "npm dependencies already installed (skipping npm install)"
    echo "To reinstall, delete node_modules and run this script again"
    echo ""
fi

# Build the React app
echo "Building React application..."
npm run build

# Check if build was successful
if [ -f "../src/assets/index.html" ]; then
    echo ""
    echo "======================================"
    echo "Build completed successfully!"
    echo "======================================"
    echo ""
    echo "The React app has been built to: src/assets/index.html"
    echo "Assets are in: src/assets/assets/"
    echo ""
    echo "You can now run the application with:"
    echo "  python src/main.py"
    echo ""
else
    echo ""
    echo "======================================"
    echo "Build failed!"
    echo "======================================"
    echo ""
    echo "The index.html file was not created in src/assets/"
    echo "Please check the error messages above."
    exit 1
fi
