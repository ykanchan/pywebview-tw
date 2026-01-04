# TiddlyWiki Manager v2.0

A multi-wiki TiddlyWiki management application with a modern React-based interface and Python backend using PyWebView.

## Features

- 📚 **Multi-Wiki Management**: Create, manage, and organize multiple TiddlyWiki instances
- 🎨 **Modern UI**: Clean, responsive React-based interface
- 🪟 **Multi-Window Support**: Open multiple wikis simultaneously (desktop platforms)
- 🔍 **Search & Filter**: Quickly find wikis by name or description
- 💾 **Metadata Tracking**: Track creation dates, last opened times, and file sizes
- 📱 **Cross-Platform**: Works on Windows, macOS, Linux, and Android

## Architecture

The application consists of two main components:

1. **Python Backend** (`src/api/`): Handles wiki file management, metadata persistence, and window management
2. **React Frontend** (`src/assets/react-app/`): Provides the user interface for wiki management

### Project Structure

```
.
├── src/
│   ├── main.py                    # Application entry point
│   ├── api/                       # Python backend
│   │   ├── wiki_manager.py        # Wiki CRUD operations
│   │   └── window_manager.py      # Multi-window management
│   ├── assets/
│   │   ├── base.html              # TiddlyWiki template
│   │   ├── index.html             # Built React app (after build)
│   │   └── assets/                # Built React assets (CSS, JS)
│   └── data/
│       ├── wikis.json             # Wiki metadata
│       └── wikis/                 # Wiki HTML files
├── react-app/                     # React frontend source
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── styles/
│   └── package.json
├── plugin/                        # TiddlyWiki saver plugin
├── plans/                         # Architecture documentation
├── build.sh                       # Build script (Unix/Mac)
└── build.bat                      # Build script (Windows)
```

## Installation & Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm

### Step 1: Install Python Dependencies

```bash
pip install pywebview
```

### Step 2: Build the React Frontend

**On Unix/Mac/Linux:**
```bash
./build.sh
```

**On Windows:**
```bash
build.bat
```

**Or manually:**
```bash
cd react-app
npm install
npm run build
cd ..
```

### Step 3: Run the Application

```bash
python src/main.py
```

## Development

### React Development

To work on the React frontend with hot reload:

```bash
cd react-app
npm run dev
```

This starts a development server at http://localhost:3000

Note: When developing, the PyWebView API won't be available in the browser. The app includes fallback handling for this.

### Python Development

The Python backend can be modified directly. Run the application with:

```bash
python src/main.py
```

## Usage

### Creating a Wiki

1. Click the "New Wiki" button in the header
2. Enter a name and optional description
3. Click "Create Wiki"

The new wiki will be created from the `base.html` template and appear in your wiki list.

### Opening a Wiki

Click the "Open" button on any wiki card. On desktop platforms, this opens the wiki in a new window. On mobile, it navigates to the wiki within the app.

### Deleting a Wiki

Click the "Delete" button on any wiki card and confirm the deletion. This removes both the wiki file and its metadata.

### Searching Wikis

Use the search box in the header to filter wikis by name or description.

## API Reference

The Python backend exposes the following methods to the React frontend via PyWebView:

### `list_wikis()`
Returns a list of all wikis with their metadata.

**Returns:** `list[dict]`

### `create_wiki(name: str, description: str = "")`
Creates a new wiki from the base template.

**Parameters:**
- `name`: Wiki name (required)
- `description`: Wiki description (optional)

**Returns:** `dict` - Wiki metadata

### `delete_wiki(wiki_id: str)`
Deletes a wiki by its ID.

**Parameters:**
- `wiki_id`: UUID of the wiki

**Returns:** `bool` - Success status

### `open_wiki(wiki_id: str)`
Opens a wiki in a new window (desktop) or navigates to it (mobile).

**Parameters:**
- `wiki_id`: UUID of the wiki

**Returns:** `dict` - Status information

### `get_platform()`
Returns the current platform name.

**Returns:** `str` - Platform identifier

## Building for Production

### Desktop Application

Package the application using PyInstaller:

```bash
# Build React app first
./build.sh  # or build.bat on Windows

# Package with PyInstaller
pyinstaller --name="TiddlyWiki Manager" \
            --windowed \
            --add-data="src/assets:assets" \
            --add-data="src/data:data" \
            src/main.py
```

### Android Application

Use Buildozer (configuration already included in `buildozer.spec`):

```bash
buildozer android debug
```

## Wiki Metadata Schema

Wikis are tracked in `src/data/wikis.json`:

```json
{
  "wikis": [
    {
      "id": "unique-uuid",
      "name": "My Wiki",
      "description": "A personal knowledge base",
      "filename": "wiki_abc123.html",
      "created_at": "2026-01-04T12:00:00Z",
      "last_opened": "2026-01-04T14:30:00Z",
      "file_size": 2048576
    }
  ],
  "settings": {
    "last_wiki_id": 1,
    "default_wiki": null
  }
}
```

## Troubleshooting

### "React app not built" Error

If you see this error when running the application:

```bash
cd src/assets/react-app
npm install
npm run build
```

### Wiki Not Opening

Ensure the wiki file exists in `src/data/wikis/` and the metadata is correct in `wikis.json`.

### PyWebView API Not Available

This typically happens during development. The API is only available when running through PyWebView, not in a regular browser.

## Contributing

Contributions are welcome! Please see the architecture documentation in the `plans/` directory for detailed implementation specifications.

## License

This project uses TiddlyWiki, which is licensed under the BSD 3-Clause License.

## Version History

### v2.0.0 (Current)
- Complete rewrite with React frontend
- Multi-wiki management system
- Modern, responsive UI
- Enhanced metadata tracking

### v1.0.0
- Initial single-wiki implementation
- Basic PyWebView integration

## Credits

- Built with [PyWebView](https://pywebview.flowrl.com/)
- Frontend powered by [React](https://react.dev/)
- Build tooling by [Vite](https://vitejs.dev/)
- Wiki engine: [TiddlyWiki](https://tiddlywiki.com/)
