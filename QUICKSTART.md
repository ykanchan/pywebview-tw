# Quick Start Guide

Get the TiddlyWiki Manager up and running in 3 simple steps!

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm (comes with Node.js)

## Step 1: Install Python Dependencies

```bash
pip install pywebview
```

## Step 2: Build the React Frontend

### On macOS/Linux:
```bash
chmod +x build.sh
./build.sh
```

### On Windows:
```bash
build.bat
```

### Or manually:
```bash
cd react-app
npm install
npm run build
cd ..
```

## Step 3: Run the Application

```bash
python src/main.py
```

That's it! The TiddlyWiki Manager should now open in a window.

## First Steps

1. **Create your first wiki**: Click the "New Wiki" button in the header
2. **Enter a name**: Give your wiki a descriptive name
3. **Add a description** (optional): Help identify your wiki later
4. **Click "Create Wiki"**: Your new wiki will appear in the list
5. **Open your wiki**: Click the "Open" button to start editing

## Troubleshooting

### "React app not built" error
Run the build script again:
```bash
./build.sh  # or build.bat on Windows
```

### "pywebview not found" error
Install pywebview:
```bash
pip install pywebview
```

### Build script permission denied (macOS/Linux)
Make the script executable:
```bash
chmod +x build.sh
```

## What's Next?

- Read the full [README.md](README.md) for detailed documentation
- Check out the [plans/](plans/) folder for architecture details
- Explore the React app source in [react-app/src/](react-app/src/)

## Project Structure

```
.
├── src/
│   ├── main.py              # Start here - main application
│   ├── api/                 # Python backend
│   ├── assets/              # Built React app goes here
│   └── data/                # Your wikis are stored here
├── react-app/               # React frontend source
├── build.sh / build.bat     # Build scripts
└── README.md                # Full documentation
```

## Development Mode

To work on the React frontend with hot reload:

```bash
cd react-app
npm run dev
```

This starts a development server at http://localhost:3000

Note: The PyWebView API won't be available in the browser during development.

## Need Help?

- Check the [README.md](README.md) for comprehensive documentation
- Review the architecture in [plans/multi-wiki-architecture.md](plans/multi-wiki-architecture.md)
- Look at implementation details in [plans/implementation-specifications.md](plans/implementation-specifications.md)

Happy wiki-ing! 📚
