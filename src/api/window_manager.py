"""Window management module for handling multiple pywebview windows."""

import webview
from typing import Dict, List, Optional


class WindowManager:
    """Manages multiple pywebview windows for wiki viewing."""

    def __init__(self):
        """Initialize WindowManager."""
        self.wiki_windows: Dict[str, webview.Window] = {}
        self.main_window: Optional[webview.Window] = None

    def set_main_window(self, window: webview.Window):
        """Set the main application window.

        Args:
            window: The main pywebview window instance
        """
        self.main_window = window

    def create_wiki_window(
        self, wiki_id: str, wiki_path: str, wiki_name: str, js_api=None
    ) -> webview.Window:
        """Create a new window for a wiki, loading the HTML file directly.

        Args:
            wiki_id: UUID of the wiki
            wiki_path: File path to the wiki HTML file (should be absolute path)
            wiki_name: Display name for the wiki
            js_api: Optional API object to expose to the wiki window

        Returns:
            webview.Window: The created window instance
        """
        if wiki_id in self.wiki_windows:
            # Window already exists, focus it
            existing_window = self.wiki_windows[wiki_id]
            try:
                # Try to focus existing window (platform dependent)
                return existing_window
            except:
                # Window might be closed, remove from tracking
                del self.wiki_windows[wiki_id]

        # Create new window loading the wiki HTML file directly
        print(f"[WindowManager] Creating window for: {wiki_name}")
        print(f"[WindowManager] Wiki path: {wiki_path}")

        window = webview.create_window(
            title=f"TiddlyWiki - {wiki_name}",
            url=wiki_path,  # Load HTML file directly via pywebview
            width=1200,
            height=800,
            resizable=True,
            js_api=js_api,  # Expose API to this window
            text_select=True,
        )

        # Enable downloads for this wiki window
        if hasattr(webview, "settings"):
            webview.settings["ALLOW_DOWNLOADS"] = True
            print(f"[WindowManager] Downloads enabled for wiki: {wiki_name}")

        # Register closing event handler to remove window from tracking
        def on_closing():
            print(f"[WindowManager] Wiki window closing: {wiki_name} (ID: {wiki_id})")

            if wiki_id in self.wiki_windows:
                del self.wiki_windows[wiki_id]
                print(f"[WindowManager] Removed wiki {wiki_id} from tracking")

        window.events.closing += on_closing

        self.wiki_windows[wiki_id] = window
        print(f"[WindowManager] Window created and tracked for wiki: {wiki_name}")
        return window

    def close_wiki_window(self, wiki_id: str) -> bool:
        """Close a wiki window.

        Args:
            wiki_id: UUID of the wiki

        Returns:
            bool: True if window was closed successfully
        """
        if wiki_id in self.wiki_windows:
            try:
                window = self.wiki_windows[wiki_id]
                # Note: pywebview doesn't have a direct close method
                # Window closing is handled by the OS/user
                del self.wiki_windows[wiki_id]
                return True
            except:
                return False
        return False

    def list_open_windows(self) -> List[str]:
        """List currently open wiki windows.

        Returns:
            list: List of wiki IDs with open windows
        """
        return list(self.wiki_windows.keys())

    def cleanup_closed_windows(self):
        """Remove references to closed windows.

        This would need to be called periodically or on window events.
        Implementation depends on pywebview capabilities.
        """
        # This is a placeholder for future implementation
        # pywebview doesn't provide easy window state checking
        pass
