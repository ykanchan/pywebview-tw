# TiddlyWiki Manager v2.0

A multi-wiki TiddlyWiki management application with a modern React-based interface and Python backend using PyWebView.

## Features

- 📚 **Multi-Wiki Management**: Create, manage, and organize multiple TiddlyWiki instances
- 🎨 **Modern UI**: Clean, responsive React-based interface
- 🪟 **Multi-Window Support**: Open multiple wikis simultaneously in separate windows (desktop)
- 📱 **Mobile Support**: Single-window navigation optimized for Android
- 🔍 **Search & Filter**: Quickly find wikis by name or description
- 💾 **Metadata Tracking**: Track creation dates, last opened times, and file sizes
- 🖥️ **Cross-Platform**: Works on Windows, macOS, Linux, and Android with platform-specific optimizations

## Architecture

The application consists of three main components:

1. **Python Backend** (`src/api/`): Handles wiki file management, metadata persistence, window management, and tiddler storage
2. **React Frontend** (`react-app/`): Provides the user interface for wiki management
3. **TiddlyWiki Sync Adaptor** (`plugin/src/`): JavaScript plugin for real-time tiddler synchronization via PyWebView bridge

### Platform-Specific Behavior

**Desktop (macOS, Windows, Linux)**:
- Opens each wiki in a separate PyWebView window
- Each window has its own dedicated API instance for independent save operations
- Supports multiple wikis open simultaneously

**Mobile (Android)**:
- Uses single-window navigation to switch between wikis
- Tracks the currently open wiki for save operations
- Optimized for touch interaction and mobile performance

**Platform Detection**: The application automatically detects the platform using Android-specific environment variables (`ANDROID_ARGUMENT`, `ANDROID_PRIVATE`, `ANDROID_ROOT`) for reliable identification.

### Project Structure

```
.
├── src/
│   ├── main.py                    # Application entry point
│   ├── api/                       # Python backend
│   │   ├── wiki_manager.py        # Wiki CRUD operations
│   │   ├── window_manager.py      # Multi-window management
│   │   └── tiddler_store.py       # SQLite tiddler storage
│   ├── assets/
│   │   ├── base.html              # TiddlyWiki template
│   │   ├── index.html             # Built React app (after build)
│   │   └── assets/                # Built React assets (CSS, JS)
│   └── data/
│       ├── wikis.json             # Wiki metadata
│       └── wikis/                 # Wiki HTML files and SQLite databases
├── react-app/                     # React frontend source
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── styles/
│   └── package.json
├── plugin/                        # TiddlyWiki plugins
│   └── src/
│       ├── saver.js               # Full HTML export saver
│       └── syncadaptor.js         # Real-time tiddler sync adaptor
├── plans/                         # Architecture documentation
├── build.sh                       # Build script (Unix/Mac)
└── build.bat                      # Build script (Windows)
```

### Storage Architecture

Each wiki uses a **dual-storage approach**:

1. **SQLite Database** (`{wiki_id}_tiddlers.db`): Primary storage for individual tiddlers
   - Fast granular access to tiddlers
   - Supports real-time synchronization
   - Revision tracking for each tiddler
   - Thread-safe operations

2. **HTML File** (`{wiki_name}.html`): TiddlyWiki HTML with embedded plugin
   - Used as the entry point for loading the wiki
   - Can be exported with all tiddlers for portability (via saver plugin)
   - Backward compatible with standard TiddlyWiki files

## Installation & Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

or directly:

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

Click the "Open" button on any wiki card:
- **Desktop**: Opens the wiki in a new, separate window
- **Mobile**: Navigates to the wiki within the same app window

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
cd react-app
npm install
npm run build
```

### Wiki Not Opening

Ensure the wiki file exists in `src/app/data/wikis/` and the metadata is correct in `wikis.json`.

### Multi-Window Not Working on Desktop

If wikis are opening in the same window instead of separate windows on desktop:
1. Check the console logs for platform detection messages
2. Ensure Android-specific modules (like `jnius`) are not installed in your desktop Python environment
3. The platform detection should show "Desktop platform" in the logs

### PyWebView API Not Available

This typically happens during development. The API is only available when running through PyWebView, not in a regular browser.

### Android Build Issues

If you encounter issues building for Android:
1. Ensure Buildozer is properly configured
2. Check that all required Android SDK components are installed
3. Review the `buildozer.spec` file for correct paths and permissions

## Contributing

Contributions are welcome! Please see the architecture documentation in the `plans/` directory for detailed implementation specifications.

## License

This project uses TiddlyWiki, which is licensed under the BSD 3-Clause License.

## Version History

### v2.1.0 (Current - 2026-01-06)
- **Major Architecture Refactoring**: Removed Flask dependency
- Implemented direct PyWebView bridge communication for tiddler operations
- New SQLite-based tiddler storage via [`TiddlerStore`](src/api/tiddler_store.py) class
- Added JavaScript sync adaptor ([`syncadaptor.js`](plugin/src/syncadaptor.js)) for real-time tiddler synchronization
- Enhanced [`WikiWindowAPI`](src/main.py:14) with tiddler CRUD methods (get_status, get_skinny_tiddlers, get_tiddler, put_tiddler, delete_tiddler)
- Simplified window management - HTML files loaded directly via PyWebView
- Retained existing saver plugin for future full HTML export features
- Improved performance by eliminating HTTP/Flask overhead
- Dual-storage architecture: SQLite for fast access + HTML for portability

### v2.0.1 (2026-01-05)
- Fixed platform detection using Android environment variables
- Improved multi-window support on desktop
- Enhanced per-window API instances
- Updated file path structure for better cross-platform compatibility

### v2.0.0 (2026-01-04)
- Complete rewrite with React frontend
- Multi-wiki management system
- Modern, responsive UI
- Enhanced metadata tracking
- Cross-platform support (desktop and Android)

### v1.0.0
- Initial single-wiki implementation
- Basic PyWebView integration

## Credits

- Built with [PyWebView](https://pywebview.flowrl.com/)
- Frontend powered by [React](https://react.dev/)
- Build tooling by [Vite](https://vitejs.dev/)
- Wiki engine: [TiddlyWiki](https://tiddlywiki.com/)
