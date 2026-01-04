"""Multi-wiki TiddlyWiki Manager Application."""

__version__ = "2.0.0"

import webview
import os
import sys
from pathlib import Path

from api.wiki_manager import WikiManager
from api.window_manager import WindowManager


class MultiWikiApp:
    """Main application class for multi-wiki TiddlyWiki manager."""

    def __init__(self):
        """Initialize the application."""
        # Get the directory where this script is located
        self.base_path = Path(__file__).parent
        self.assets_path = self.base_path / "assets"

        # Initialize managers
        self.wiki_manager = WikiManager(str(self.base_path))
        self.window_manager = WindowManager()

        # Track pending wiki opens (for after webview.start())
        self._pending_wiki_opens = []

    # API methods exposed to JavaScript
    def create_wiki(self, name: str, description: str = "") -> dict:
        """Create a new wiki.

        Args:
            name: Name for the new wiki
            description: Optional description

        Returns:
            dict: Wiki metadata
        """
        try:
            wiki_data = self.wiki_manager.create_wiki(name, description)
            print(f"Created wiki: {wiki_data['name']} (ID: {wiki_data['id']})")
            return wiki_data
        except Exception as e:
            print(f"Error creating wiki: {e}")
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
            wikis = self.wiki_manager.list_wikis()
            print(f"Listed {len(wikis)} wikis")
            return wikis
        except Exception as e:
            print(f"Error listing wikis: {e}")
            raise

    def open_wiki(self, wiki_id: str) -> dict:
        """Open a wiki in a new window.

        Args:
            wiki_id: UUID of the wiki to open

        Returns:
            dict: Status information
        """
        try:
            wiki = self.wiki_manager.get_wiki(wiki_id)
            wiki_path = self.wiki_manager.get_wiki_path(wiki_id)

            # Update last opened timestamp
            self.wiki_manager.update_last_opened(wiki_id)

            # Create new window
            self.window_manager.create_wiki_window(
                wiki_id, str(wiki_path), wiki["name"]
            )

            print(f"Opened wiki: {wiki['name']} (ID: {wiki_id})")
            return {"status": "success", "wiki_id": wiki_id}

        except Exception as e:
            print(f"Error opening wiki: {e}")
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
    react_index_path = app.assets_path / "index.html"

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
        str(react_dist_path),
        width=1200,
        height=800,
        resizable=True,
        min_size=(800, 600),
    )

    app.window_manager.set_main_window(window)

    def on_loaded():
        """Called when the main window has loaded."""
        print("TiddlyWiki Manager started successfully!")
        print(f"Version: {__version__}")
        print(f"Base path: {app.base_path}")
        print(f"Data directory: {app.wiki_manager.data_dir}")

    # Start the application
    webview.start(on_loaded, window, debug=True, js_api=app)


if __name__ == "__main__":
    main()
