"""Multi-wiki TiddlyWiki Manager Application."""

__version__ = "2.0.0"

import webview
import os
import sys
from pathlib import Path

from api.wiki_manager import WikiManager
from api.window_manager import WindowManager
from api.tiddler_store import TiddlerStore


class WikiWindowAPI:
    """API for individual wiki windows - each window gets its own instance."""

    def __init__(self, wiki_id: str, wiki_path: str, wiki_manager: WikiManager):
        """Initialize API for a specific wiki window.

        Args:
            wiki_id: UUID of the wiki
            wiki_path: Path to the wiki file
            wiki_manager: WikiManager instance for operations
        """
        self.wiki_id = wiki_id
        self.wiki_path = wiki_path
        self.wiki_manager = wiki_manager

        # Initialize TiddlerStore for this wiki (private to avoid PyWebView serialization issues)
        wiki_dir = Path(wiki_path).parent
        self._tiddler_store = TiddlerStore(wiki_id, wiki_dir)
        print(f"[WikiWindowAPI] Initialized TiddlerStore for wiki {wiki_id}")

    def save(self, payload: dict) -> str:
        """Save wiki content for this specific wiki (full HTML save).

        This is used by the saver plugin for full HTML exports.

        Args:
            payload: Dictionary with 'text' (HTML content)

        Returns:
            str: Success message
        """
        try:
            print(f"[WikiWindowAPI] save called for wiki: {self.wiki_id}")

            html_content = payload.get("text", "")
            if not html_content:
                raise ValueError("No content to save")

            print(f"[WikiWindowAPI] Content length: {len(html_content)} bytes")
            print(f"[WikiWindowAPI] Saving to: {self.wiki_path}")

            # Write the content to the file
            with open(self.wiki_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            # Record the HTML save timestamp for smart first-sync
            self._tiddler_store.record_html_save()

            print(f"[WikiWindowAPI] Save successful")
            return "Save successful"

        except Exception as e:
            print(f"[WikiWindowAPI] Error saving: {e}")
            import traceback

            traceback.print_exc()
            raise

    # Tiddler sync adaptor methods
    def get_updated_tiddlers(
        self, since_timestamp: str = None, current_tiddlers: list = None
    ) -> dict:
        """Get tiddlers that have been modified since a given timestamp.

        This method is used by the sync adaptor for efficient synchronization.
        It returns only the titles of tiddlers that have changed, not the full content.

        Args:
            since_timestamp: ISO format timestamp. If None, returns all tiddlers.
            current_tiddlers: List of tiddler titles currently loaded in TiddlyWiki.
                            Used for deletion detection.

        Returns:
            dict: {
                'modifications': [list of tiddler titles],
                'deletions': [list of deleted tiddler titles]
            }
        """
        try:
            result = self._tiddler_store.get_updated_tiddlers(
                since_timestamp, current_tiddlers
            )
            return result
        except Exception as e:
            print(f"[WikiWindowAPI] Error getting updated tiddlers: {e}")
            import traceback

            traceback.print_exc()
            raise

    def get_tiddler(self, title: str) -> str:
        """Get a complete tiddler by title.

        Args:
            title: Tiddler title

        Returns:
            str: Complete tiddler data as JSON string, or None if not found
        """
        try:
            print(f"[WikiWindowAPI] get_tiddler called: {title}")
            tiddler_json = self._tiddler_store.get_tiddler(title)
            if tiddler_json:
                print(f"[WikiWindowAPI] Found tiddler: {title}")
            else:
                print(f"[WikiWindowAPI] Tiddler not found: {title}")
            return tiddler_json
        except Exception as e:
            print(f"[WikiWindowAPI] Error getting tiddler: {e}")
            import traceback

            traceback.print_exc()
            raise

    def put_tiddler(self, title: str, tiddler_json: str) -> dict:
        """Create or update a tiddler.

        Args:
            title: Tiddler title
            tiddler_json: Tiddler data as JSON string (from TiddlyWiki's getTiddlerAsJson)

        Returns:
            dict: Response indicating success
        """
        try:
            print(f"[WikiWindowAPI] put_tiddler called: {title}")

            # Store the tiddler - pass JSON string directly
            result = self._tiddler_store.put_tiddler(title, tiddler_json)

            return result
        except Exception as e:
            print(f"[WikiWindowAPI] Error putting tiddler: {e}")
            import traceback

            traceback.print_exc()
            raise

    def delete_tiddler(self, title: str) -> dict:
        """Delete a tiddler.

        Args:
            title: Tiddler title

        Returns:
            dict: Response indicating success
        """
        try:
            print(f"[WikiWindowAPI] delete_tiddler called: {title}")
            deleted = self._tiddler_store.delete_tiddler(title)

            if deleted:
                print(f"[WikiWindowAPI] Deleted tiddler: {title}")
            else:
                print(f"[WikiWindowAPI] Tiddler not found (already deleted?): {title}")

            return {"status": "success"}
        except Exception as e:
            print(f"[WikiWindowAPI] Error deleting tiddler: {e}")
            import traceback

            traceback.print_exc()
            raise


class MultiWikiApp:
    """Main application class for multi-wiki TiddlyWiki manager."""

    def __init__(self):
        """Initialize the application."""
        # Get the directory where this script is located
        base_path = Path(__file__).parent

        # Store as strings to avoid PyWebView serialization issues with Path objects
        self._base_path_str = str(base_path)
        self._app_path_str = str(base_path / "app")

        # Initialize managers
        self.wiki_manager = WikiManager(self._base_path_str)
        self.window_manager = WindowManager()

        # Track current wiki for save operations (used on mobile)
        self._current_wiki_id = None

    # API methods exposed to JavaScript
    def test_api(self) -> str:
        """Test method to verify API is working.

        Returns:
            str: Test message
        """
        print("[API] test_api called")
        return "API is working!"

    def create_wiki(self, name: str, description: str = "") -> dict:
        """Create a new wiki.

        Args:
            name: Name for the new wiki
            description: Optional description

        Returns:
            dict: Wiki metadata
        """
        try:
            print(
                f"[API] create_wiki called: name='{name}', description='{description}'"
            )
            wiki_data = self.wiki_manager.create_wiki(name, description)
            print(f"[API] Created wiki: {wiki_data['name']} (ID: {wiki_data['id']})")
            return wiki_data
        except Exception as e:
            print(f"[API] Error creating wiki: {e}")
            raise

    def delete_wiki(self, wiki_id: str) -> bool:
        """Delete a wiki.

        Args:
            wiki_id: UUID of the wiki to delete

        Returns:
            bool: True if successful
        """
        try:
            result = self.wiki_manager.delete_wiki(wiki_id)
            print(f"Deleted wiki: {wiki_id}")
            return result
        except Exception as e:
            print(f"Error deleting wiki: {e}")
            raise

    def list_wikis(self) -> list:
        """List all wikis.

        Returns:
            list: List of wiki metadata dictionaries
        """
        try:
            print(f"[API] list_wikis called")
            print(f"[API] Base path: {self._base_path_str}")
            print(f"[API] Data dir: {self.wiki_manager._data_dir_str}")
            print(f"[API] Metadata file: {self.wiki_manager._metadata_file_str}")
            wikis = self.wiki_manager.list_wikis()
            print(f"[API] Listed {len(wikis)} wikis")
            for wiki in wikis:
                print(f"[API]   - {wiki['name']} (ID: {wiki['id']})")
            return wikis
        except Exception as e:
            print(f"[API] Error listing wikis: {e}")
            import traceback

            traceback.print_exc()
            raise

    def open_wiki(self, wiki_id: str) -> dict:
        """Open a wiki in a new window (desktop) or navigate to it (mobile).

        Args:
            wiki_id: UUID of the wiki to open

        Returns:
            dict: Status information with wiki_url for mobile navigation
        """
        try:
            print(f"[API] open_wiki called: wiki_id='{wiki_id}'")
            wiki = self.wiki_manager.get_wiki(wiki_id)
            wiki_path = self.wiki_manager.get_wiki_path(wiki_id)
            print(f"[API] Wiki path: {wiki_path}")
            print(f"[API] Wiki path exists: {wiki_path.exists()}")

            # Update last opened timestamp
            self.wiki_manager.update_last_opened(wiki_id)

            # Check if we're on Android (mobile)
            # Use multiple detection methods for reliability:
            # 1. Check sys.platform (Python-for-Android reports 'linux' but we check env vars)
            # 2. Check for Android-specific environment variables set by Python-for-Android
            is_android_env = (
                os.environ.get("ANDROID_ARGUMENT") is not None
                or os.environ.get("ANDROID_PRIVATE") is not None
                or os.environ.get("ANDROID_ROOT") is not None
            )

            # sys.platform on Android is 'linux', but we need env vars to confirm it's Android
            is_mobile = is_android_env

            if is_mobile:
                print(f"[API] Platform detection: Android detected (env vars present)")
            else:
                print(f"[API] Platform detection: Desktop platform")
                print(f"[API] sys.platform = {sys.platform}")

            if is_mobile:
                # On mobile, return the wiki path for navigation
                # The React app will handle navigation
                print(f"[API] Mobile platform detected, returning wiki path")
                # Set the current wiki ID for save operations
                self._current_wiki_id = wiki_id
                print(f"[API] Set current wiki ID to: {wiki_id}")
                # PyWebView HTTP server root is app/, wikis are in app/data/wikis/
                # So the URL is relative: data/wikis/filename.html
                wiki_filename = wiki["filename"]
                wiki_url = f"data/wikis/{wiki_filename}"
                print(f"[API] Wiki URL (relative to app/): {wiki_url}")
                return {
                    "status": "success",
                    "wiki_id": wiki_id,
                    "wiki_url": wiki_url,
                    "wiki_name": wiki["name"],
                    "is_mobile": True,
                }
            else:
                # On desktop, create new window
                print(
                    f"[API] Desktop platform, creating window for wiki: {wiki['name']}"
                )
                # Convert to absolute path for desktop
                abs_wiki_path = wiki_path.resolve()
                print(f"[API] Absolute wiki path: {abs_wiki_path}")

                # Create a dedicated API instance for this wiki window
                wiki_api = WikiWindowAPI(wiki_id, str(abs_wiki_path), self.wiki_manager)

                self.window_manager.create_wiki_window(
                    wiki_id, str(abs_wiki_path), wiki["name"], js_api=wiki_api
                )
                print(f"[API] Opened wiki: {wiki['name']} (ID: {wiki_id})")
                return {"status": "success", "wiki_id": wiki_id, "is_mobile": False}

        except Exception as e:
            print(f"[API] Error opening wiki: {e}")
            import traceback

            traceback.print_exc()
            raise

    def save(self, payload: dict) -> str:
        """Save wiki content.

        This is called by the TiddlyWiki saver plugin when the user saves changes.
        The payload contains the full HTML content of the wiki.

        Args:
            payload: Dictionary with 'text' (HTML content), 'action', 'timestamp'

        Returns:
            str: Success message
        """
        try:
            print(f"[API] save called")

            # Get the HTML content
            html_content = payload.get("text", "")
            if not html_content:
                raise ValueError("No content to save")

            print(f"[API] Content length: {len(html_content)} bytes")

            # Get the current wiki ID (set when wiki was opened)
            if not self._current_wiki_id:
                raise ValueError("No wiki is currently open")

            print(f"[API] Saving to wiki ID: {self._current_wiki_id}")

            # Get the wiki file path
            wiki_path = self.wiki_manager.get_wiki_path(self._current_wiki_id)
            print(f"[API] Wiki file path: {wiki_path}")

            # Write the content to the file
            with open(wiki_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"[API] Save successful")
            return "Save successful"

        except Exception as e:
            print(f"[API] Error saving: {e}")
            import traceback

            traceback.print_exc()
            raise

    def get_platform(self) -> str:
        """Get the current platform.

        Returns:
            str: Platform name (e.g., 'darwin', 'linux', 'win32', 'android')
        """
        return sys.platform


def main():
    """Main entry point for the application."""
    app = MultiWikiApp()

    # Path to the React app index.html (built from react-app folder)
    react_index_path = Path(app._app_path_str) / "index.html"

    # Check if the React app has been built
    if not react_index_path.exists():
        print("=" * 60)
        print("ERROR: React app not built!")
        print("=" * 60)
        print(f"Expected path: {react_index_path}")
        print("\nPlease build the React app first:")
        print("  cd react-app")
        print("  npm install")
        print("  npm run build")
        print("=" * 60)
        sys.exit(1)

    # Create main window with React app
    window = webview.create_window(
        "TiddlyWiki Manager",
        str(react_index_path),
        width=1200,
        height=800,
        resizable=True,
        min_size=(800, 600),
        js_api=app,
        text_select=True,
    )

    app.window_manager.set_main_window(window)

    def on_loaded():
        """Called when the main window has loaded."""
        print("TiddlyWiki Manager started successfully!")
        print(f"Version: {__version__}")
        print(f"Base path: {app._base_path_str}")
        print(f"App directory: {app._app_path_str}")
        print(f"Data directory: {app.wiki_manager._data_dir_str}")

    # Start the application with SSL enabled for Android compatibility
    # This uses HTTPS with a self-signed certificate, which Android accepts
    webview.start(on_loaded, debug=True, ssl=True)


if __name__ == "__main__":
    main()
