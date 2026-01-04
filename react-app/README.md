# TiddlyWiki Manager - React Frontend

This is the React-based frontend for the TiddlyWiki Manager application.

## Development

### Prerequisites
- Node.js 16+ and npm

### Setup
```bash
npm install
```

### Development Server
```bash
npm run dev
```

This will start a development server at http://localhost:3000

### Build for Production
```bash
npm run build
```

This creates an optimized production build and outputs:
- `../src/assets/index.html` - Main HTML file
- `../src/assets/assets/` - JavaScript and CSS assets

### Preview Production Build
```bash
npm run preview
```

## Project Structure

```
src/
├── main.jsx              # Application entry point
├── App.jsx               # Main application component
├── components/           # React components
│   ├── Header.jsx
│   ├── WikiList.jsx
│   ├── WikiCard.jsx
│   ├── CreateWikiForm.jsx
│   └── Footer.jsx
└── styles/              # CSS stylesheets
    ├── index.css        # Global styles
    ├── App.css
    ├── Header.css
    ├── WikiList.css
    ├── WikiCard.css
    ├── CreateWikiForm.css
    └── Footer.css
```

## Integration with Python Backend

The React app communicates with the Python backend through the PyWebView JavaScript API:

- `window.pywebview.api.list_wikis()` - Get all wikis
- `window.pywebview.api.create_wiki(name, description)` - Create a new wiki
- `window.pywebview.api.delete_wiki(wiki_id)` - Delete a wiki
- `window.pywebview.api.open_wiki(wiki_id)` - Open a wiki in a new window
- `window.pywebview.api.get_platform()` - Get the current platform

## Building for Production

Before running the Python application, you must build the React app:

```bash
cd react-app
npm install
npm run build
```

Or use the build scripts from the project root:
- Unix/Mac/Linux: `./build.sh`
- Windows: `build.bat`

The built files will be output to `../src/assets/`, which the Python application will serve.
