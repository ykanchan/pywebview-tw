"""Flask server module for serving individual wikis with API endpoints."""

from flask import Flask, jsonify, send_file
from pathlib import Path
import threading


class WikiFlaskServer:
    """Custom Flask server for serving individual wikis with API endpoints."""

    def __init__(self, wiki_id: str, wiki_path: str, wiki_api=None):
        """Initialize Flask server for a specific wiki.

        Args:
            wiki_id: UUID of the wiki
            wiki_path: Absolute path to the wiki HTML file
            wiki_api: Optional WikiWindowAPI instance for save operations
        """
        self.wiki_id = wiki_id
        self.wiki_path = Path(wiki_path)
        self.wiki_api = wiki_api
        self.port = None
        self.server_thread = None

        # Create Flask app
        self.app = Flask(__name__)

        # Disable Flask's logging for cleaner output
        import logging

        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/status", methods=["GET"])
        def status():
            """Return static status information."""
            return jsonify({"space": {"recipe": "default"}})

        @self.app.route("/")
        def serve_wiki():
            """Serve the wiki HTML file."""
            return send_file(str(self.wiki_path), mimetype="text/html")

    def start(self, port: int):
        """Start the Flask server in a background thread.

        Args:
            port: Port number to run the server on
        """
        self.port = port

        def run_server():
            self.app.run(
                host="127.0.0.1", port=self.port, debug=False, use_reloader=False
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        print(
            f"[WikiFlaskServer] Started server for wiki {self.wiki_id} on port {self.port}"
        )

    def get_url(self) -> str:
        """Get the URL of the Flask server.

        Returns:
            str: URL to access the wiki through the Flask server
        """
        if self.port is None:
            raise RuntimeError("Server not started yet")
        return f"http://127.0.0.1:{self.port}"
