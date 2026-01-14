"""Window management module for handling multiple pywebview windows."""

import webview
import json
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

    def _inject_tiddlers_and_boot(self, window: webview.Window, js_api):
        """Inject tiddlers from SQLite into TiddlyWiki and trigger boot.

        This method is called after the window has loaded.

        Args:
            window: The webview window instance
            js_api: The API object with access to _tiddler_store
        """
        try:
            print("[WindowManager] Injecting tiddlers and booting TiddlyWiki...")

            # Get tiddlers from SQLite
            if js_api and hasattr(js_api, "_tiddler_store"):
                tiddlers = js_api._tiddler_store.get_all_tiddlers_as_list()
                print(f"[WindowManager] Retrieved {len(tiddlers)} tiddlers from SQLite")

                # Convert tiddlers list to JSON string
                tiddlers_json = json.dumps(tiddlers, ensure_ascii=False)

                # JavaScript code to inject tiddlers and boot TiddlyWiki
                js_code = f"""
                (function() {{
                    try {{
                        // Parse tiddlers from JSON
                        var tiddlers = {tiddlers_json};
                        
                        // Ensure $tw.preloadTiddlers exists
                        if (window.$tw && $tw.preloadTiddlers) {{
                            // Push each tiddler to preloadTiddlers array
                            tiddlers.forEach(function(tiddler) {{
                                $tw.preloadTiddlers.push(tiddler);
                            }});
                            
                            console.log('[PyWebView] Injected ' + tiddlers.length + ' tiddlers');
                            
                            // Boot TiddlyWiki
                            if ($tw.boot && typeof $tw.boot.boot === 'function') {{
                                $tw.boot.boot();
                                console.log('[PyWebView] TiddlyWiki booted successfully');
                                return 'SUCCESS: Injected ' + tiddlers.length + ' tiddlers and booted TiddlyWiki';
                            }} else {{
                                console.error('[PyWebView] $tw.boot.boot() not found');
                                return 'ERROR: $tw.boot.boot() not found';
                            }}
                        }} else {{
                            console.error('[PyWebView] $tw.preloadTiddlers not found');
                            return 'ERROR: $tw.preloadTiddlers not found';
                        }}
                    }} catch (e) {{
                        console.error('[PyWebView] Error injecting tiddlers:', e);
                        return 'ERROR: ' + e.message;
                    }}
                }})();
                """

                # Execute the JavaScript
                result = window.evaluate_js(js_code)
                print(f"[WindowManager] Injection result: {result}")
            else:
                print(
                    "[WindowManager] No tiddler store available, booting TiddlyWiki without injection"
                )
                # Just boot TiddlyWiki without injecting tiddlers
                window.evaluate_js(
                    "if (window.$tw && $tw.boot && $tw.boot.boot) { $tw.boot.boot(); }"
                )

        except Exception as e:
            print(f"[WindowManager] Error during tiddler injection: {e}")
            import traceback

            traceback.print_exc()
            # Try to boot anyway
            try:
                window.evaluate_js(
                    "if (window.$tw && $tw.boot && $tw.boot.boot) { $tw.boot.boot(); }"
                )
            except:
                pass

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

        # Register loaded event handler to inject tiddlers after page loads
        def on_loaded():
            print(f"[WindowManager] Wiki window loaded: {wiki_name}")
            self._inject_tiddlers_and_boot(window, js_api)

        window.events.loaded += on_loaded

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
