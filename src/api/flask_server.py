"""Flask server module for serving individual wikis with API endpoints."""

from flask import Flask, jsonify, send_file, request, Response
from pathlib import Path
from urllib.parse import quote
import threading
import json
import sqlite3


class WikiFlaskServer:
    """Custom Flask server for serving individual wikis with API endpoints."""

    def __init__(self, wiki_id: str, wiki_path: str, wiki_api=None, window=None):
        """Initialize Flask server for a specific wiki.

        Args:
            wiki_id: UUID of the wiki
            wiki_path: Absolute path to the wiki HTML file
            wiki_api: Optional WikiWindowAPI instance for save operations
            window: Optional pywebview Window instance for JavaScript execution
        """
        self.wiki_id = wiki_id
        self.wiki_path = Path(wiki_path)
        self.wiki_api = wiki_api
        self.window = window
        self.port = None
        self.server_thread = None

        # Path to the persistent SQLite database file (stored alongside wiki HTML)
        wiki_dir = self.wiki_path.parent
        self.db_path = wiki_dir / f"{wiki_id}_tiddlers.db"

        # Initialize file-based SQLite database
        self.db_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        # Use RLock (reentrant lock) to allow the same thread to acquire it multiple times
        self.db_lock = threading.RLock()
        self._init_database()

        print(f"[WikiFlaskServer] Using persistent DB at: {self.db_path}")

        # Create Flask app
        self.app = Flask(__name__)

        # Disable Flask's logging for cleaner output
        import logging

        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        # Setup routes
        self._setup_routes()

    def _init_database(self):
        """Initialize the in-memory SQLite database with tiddlers table."""
        with self.db_lock:
            cursor = self.db_conn.cursor()
            # Create tiddlers table with all fields as separate columns
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tiddlers (
                    title TEXT PRIMARY KEY,
                    bag TEXT,
                    created TEXT,
                    creator TEXT,
                    modified TEXT,
                    modifier TEXT,
                    permissions TEXT,
                    recipe TEXT,
                    revision INTEGER,
                    tags TEXT,
                    text TEXT,
                    type TEXT,
                    uri TEXT,
                    fields TEXT
                )
            """
            )
            self.db_conn.commit()
            print(
                f"[WikiFlaskServer] Initialized in-memory SQLite DB for wiki {self.wiki_id}"
            )

    def _convert_tags_to_string(self, tags) -> str:
        """Convert tags array to TiddlyWiki format string.

        Args:
            tags: Tags as list/array or string

        Returns:
            str: Space-separated string with [[brackets]] for tags with spaces
        """
        if tags is None:
            return None

        # If already a string, return as-is
        if isinstance(tags, str):
            return tags

        # If it's a list, convert to TiddlyWiki format
        if isinstance(tags, list):
            result_tags = []
            for tag in tags:
                tag_str = str(tag)
                # Wrap in [[]] if tag contains spaces
                if " " in tag_str:
                    result_tags.append(f"[[{tag_str}]]")
                else:
                    result_tags.append(tag_str)
            return " ".join(result_tags)

        # For any other type, convert to string
        return str(tags)

    def _get_tiddler(self, title: str) -> dict:
        """Get a tiddler from the database.

        Args:
            title: Tiddler title

        Returns:
            dict: Tiddler data or None if not found
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            cursor.execute(
                """
                SELECT title, bag, created, creator, modified, modifier, permissions,
                       recipe, revision, tags, text, type, uri, fields
                FROM tiddlers WHERE title = ?
            """,
                (title,),
            )
            row = cursor.fetchone()

            if row:
                # Build tiddler dict from row data
                tiddler = {}
                fields_map = [
                    "title",
                    "bag",
                    "created",
                    "creator",
                    "modified",
                    "modifier",
                    "permissions",
                    "recipe",
                    "revision",
                    "tags",
                    "text",
                    "type",
                    "uri",
                    "fields",
                ]

                for idx, field_name in enumerate(fields_map):
                    value = row[idx]
                    if value is not None:
                        # Parse fields as JSON if it's the fields column
                        if field_name == "fields":
                            try:
                                tiddler[field_name] = json.loads(value)
                            except (json.JSONDecodeError, TypeError):
                                tiddler[field_name] = value
                        else:
                            tiddler[field_name] = value

                return tiddler
            return None

    def _get_current_revision(self, title: str) -> int:
        """Get the current revision number for a tiddler.

        Args:
            title: Tiddler title

        Returns:
            int: Current revision number, or 0 if tiddler doesn't exist
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT revision FROM tiddlers WHERE title = ?", (title,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
            return 0

    def _get_all_tiddlers_flat(self) -> list:
        """Get all tiddlers with flattened fields (excluding text).

        Returns:
            list: List of tiddler dictionaries with fields flattened
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            # Get all tiddlers excluding the text field
            cursor.execute(
                """
                SELECT title, bag, created, creator, modified, modifier, permissions,
                       recipe, revision, tags, type, uri, fields
                FROM tiddlers
            """
            )
            rows = cursor.fetchall()

            result = []
            fields_map = [
                "title",
                "bag",
                "created",
                "creator",
                "modified",
                "modifier",
                "permissions",
                "recipe",
                "revision",
                "tags",
                "type",
                "uri",
                "fields",
            ]

            for row in rows:
                tiddler = {}
                fields_obj = None
                title_value = None

                # Build tiddler dict from row data
                for idx, field_name in enumerate(fields_map):
                    value = row[idx]
                    if value is not None:
                        if field_name == "title":
                            title_value = value
                            tiddler[field_name] = value
                        elif field_name == "fields":
                            # Store fields object for later flattening
                            try:
                                fields_obj = json.loads(value)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        else:
                            tiddler[field_name] = value

                # Skip system tiddlers (titles starting with "$:/")
                if title_value and title_value.startswith("$:/"):
                    continue

                # Flatten fields object into top level
                if fields_obj and isinstance(fields_obj, dict):
                    for key, val in fields_obj.items():
                        tiddler[key] = val

                result.append(tiddler)

            return result

    def _put_tiddler(self, title: str, tiddler_data: dict) -> int:
        """Create or update a tiddler in the database with revision tracking.

        Args:
            title: Tiddler title
            tiddler_data: Tiddler data as dictionary

        Returns:
            int: New revision number
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()

            # Get current revision and increment it
            current_revision = self._get_current_revision(title)
            new_revision = current_revision + 1

            # Extract fields from tiddler data
            bag = tiddler_data.get("bag")
            created = tiddler_data.get("created")
            creator = tiddler_data.get("creator")
            modified = tiddler_data.get("modified")
            modifier = tiddler_data.get("modifier")
            permissions = tiddler_data.get("permissions")
            recipe = tiddler_data.get("recipe")
            # Ignore revision from incoming data, use our auto-incremented value
            tags = tiddler_data.get("tags")
            text = tiddler_data.get("text")
            tiddler_type = tiddler_data.get("type")
            uri = tiddler_data.get("uri")
            fields = tiddler_data.get("fields")

            # Convert tags to TiddlyWiki format string (space-separated with [[]] for tags with spaces)
            tags = self._convert_tags_to_string(tags)

            # Convert fields to JSON string if it's a dict/object
            if fields is not None and isinstance(fields, (dict, list)):
                fields = json.dumps(fields, ensure_ascii=False)

            # Use REPLACE to insert or update, with new revision
            cursor.execute(
                """
                REPLACE INTO tiddlers 
                (title, bag, created, creator, modified, modifier, permissions, 
                 recipe, revision, tags, text, type, uri, fields)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    title,
                    bag,
                    created,
                    creator,
                    modified,
                    modifier,
                    permissions,
                    recipe,
                    new_revision,
                    tags,
                    text,
                    tiddler_type,
                    uri,
                    fields,
                ),
            )
            self.db_conn.commit()

            return new_revision

    def _delete_tiddler(self, title: str):
        """Delete a tiddler from the database.

        Args:
            title: Tiddler title
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            cursor.execute("DELETE FROM tiddlers WHERE title = ?", (title,))
            self.db_conn.commit()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route("/status", methods=["GET"])
        def status():
            """Return static status information."""
            return jsonify({"space": {"recipe": "default"}})

        @self.app.route("/recipes/default/tiddlers.json", methods=["GET"])
        def get_all_tiddlers():
            """Get all tiddlers with flattened fields (excluding text).

            Returns:
                Response: JSON array of all tiddlers with fields flattened
            """
            tiddlers = self._get_all_tiddlers_flat()
            return Response(
                json.dumps(tiddlers, ensure_ascii=False),
                status=200,
                mimetype="application/json",
            )

        @self.app.route("/recipes/default/tiddlers/<path:title>", methods=["GET"])
        def get_tiddler(title):
            """Get a tiddler by title.

            Args:
                title: Tiddler title (Flask automatically decodes URL encoding)

            Returns:
                Response: JSON response with tiddler data or 404
            """
            # Flask's <path:title> automatically decodes URL-encoded characters
            # Get tiddler from database
            tiddler_data = self._get_tiddler(title)

            # Check if tiddler exists
            if tiddler_data is not None:
                # Return tiddler with proper content type
                return Response(
                    json.dumps(tiddler_data, ensure_ascii=False),
                    status=200,
                    mimetype="application/json",
                )
            else:
                # Return 404 if not found
                return Response("", status=404)

        @self.app.route("/recipes/default/tiddlers/<path:title>", methods=["PUT"])
        def put_tiddler(title):
            """Create or update a tiddler with revision tracking.

            Args:
                title: Tiddler title (Flask automatically decodes URL encoding)

            Returns:
                Response: Success response with ETag header
            """
            # Flask's <path:title> automatically decodes URL-encoded characters
            # Get JSON payload from request
            tiddler_data = request.get_json()

            # Store the tiddler in database and get new revision
            new_revision = self._put_tiddler(title, tiddler_data)

            # Create ETag header with format: "default/<title>/<revision>:"
            # URL-encode the title for the ETag (equivalent to JavaScript's encodeURIComponent)
            encoded_title = quote(title, safe="")
            etag_value = f'"default/{encoded_title}/{new_revision}:"'

            # Return success response with ETag header
            response = Response("", status=204)
            response.headers["ETag"] = etag_value
            return response

        @self.app.route("/bags/default/tiddlers/<path:title>", methods=["DELETE"])
        def delete_tiddler(title):
            """Delete a tiddler.

            Args:
                title: Tiddler title (Flask automatically decodes URL encoding)

            Returns:
                Response: 204 No Content (always, whether found or not)
            """
            # Flask's <path:title> automatically decodes URL-encoded characters
            # Delete the tiddler (no error if it doesn't exist)
            self._delete_tiddler(title)

            # Always return 204 No Content
            return Response("", status=204)

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

    def __del__(self):
        """Clean up database connection when server is destroyed."""
        if hasattr(self, "db_conn"):
            self.db_conn.close()
