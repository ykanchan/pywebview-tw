"""Tiddler storage module for managing TiddlyWiki tiddlers in SQLite."""

import sqlite3
import threading
import json
from pathlib import Path
from datetime import datetime


class TiddlerStore:
    """Manages tiddler storage in SQLite database for a specific wiki."""

    def __init__(self, wiki_id: str, wiki_dir: Path):
        """Initialize TiddlerStore for a specific wiki.

        Args:
            wiki_id: UUID of the wiki
            wiki_dir: Directory where the wiki files are stored
        """
        self.wiki_id = wiki_id
        self.wiki_dir = Path(wiki_dir)

        # Path to the persistent SQLite database file (stored alongside wiki HTML)
        self.db_path = self.wiki_dir / f"{wiki_id}_tiddlers.db"

        # Initialize file-based SQLite database
        self.db_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        # Use RLock (reentrant lock) to allow the same thread to acquire it multiple times
        self.db_lock = threading.RLock()
        self._init_database()

        print(f"[TiddlerStore] Using persistent DB at: {self.db_path}")

    def _iso_to_tiddlywiki_timestamp(self, iso_timestamp: str) -> str:
        """Convert ISO timestamp to TiddlyWiki timestamp format.

        Args:
            iso_timestamp: ISO format timestamp (e.g., '2026-01-06T22:54:28.206Z')

        Returns:
            str: TiddlyWiki format timestamp (e.g., '20260106225428206')
        """
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))

            # Format as TiddlyWiki timestamp: YYYYMMDDHHMMSSmmm
            tw_timestamp = dt.strftime("%Y%m%d%H%M%S") + f"{dt.microsecond // 1000:03d}"

            return tw_timestamp
        except Exception as e:
            print(f"[TiddlerStore] Error converting timestamp '{iso_timestamp}': {e}")
            # Return original timestamp as fallback
            return iso_timestamp

    def _init_database(self):
        """Initialize the SQLite database with 2-column JSON1 schema."""
        with self.db_lock:
            cursor = self.db_conn.cursor()

            # Create tiddlers table with JSON type for tiddler data
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tiddlers (
                    title TEXT PRIMARY KEY,
                    tiddler_data JSON NOT NULL
                )
            """
            )

            # Create an index on the modified field extracted from JSON for efficient sync queries
            # This allows fast queries like: WHERE json_extract(tiddler_data, '$.modified') > ?
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tiddler_modified
                ON tiddlers(json_extract(tiddler_data, '$.modified'))
                """
            )

            # Create metadata table to track HTML save timestamps
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS wiki_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            self.db_conn.commit()
            print(f"[TiddlerStore] Initialized SQLite DB for wiki {self.wiki_id}")

    def record_html_save(self):
        """Record the timestamp when the HTML file was saved.

        This timestamp is used on first sync to determine which tiddlers
        were modified after the HTML save (avoiding redundant loads).
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()

            # Get current time in TiddlyWiki format
            now = datetime.utcnow()
            tw_timestamp = (
                now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
            )

            cursor.execute(
                """
                REPLACE INTO wiki_metadata (key, value)
                VALUES ('last_html_save', ?)
                """,
                (tw_timestamp,),
            )
            self.db_conn.commit()
            print(f"[TiddlerStore] Recorded HTML save at: {tw_timestamp}")

    def get_last_html_save(self) -> str:
        """Get the timestamp of the last HTML save.

        Returns:
            str: TiddlyWiki format timestamp, or None if never saved
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT value FROM wiki_metadata WHERE key = 'last_html_save'"
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_tiddler(self, title: str) -> str:
        """Get a tiddler from the database.

        Args:
            title: Tiddler title

        Returns:
            str: Tiddler data as JSON string, or None if not found
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            cursor.execute(
                "SELECT tiddler_data FROM tiddlers WHERE title = ?",
                (title,),
            )
            row = cursor.fetchone()

            if row:
                # Return the JSON string directly - no need to parse
                return row[0]
            return None

    def put_tiddler(self, title: str, tiddler_json: str) -> dict:
        """Create or update a tiddler in the database.

        Args:
            title: Tiddler title
            tiddler_json: Tiddler data as JSON string (from TiddlyWiki's getTiddlerAsJson)

        Returns:
            dict: Success status
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()

            # SQLite's json() function validates and stores the JSON
            # No need to parse and re-serialize - pass string directly
            cursor.execute(
                """
                REPLACE INTO tiddlers (title, tiddler_data)
                VALUES (?, json(?))
                """,
                (title, tiddler_json),
            )
            self.db_conn.commit()

            print(f"[TiddlerStore] Saved tiddler: {title}")
            return {"success": True}

    def delete_tiddler(self, title: str) -> bool:
        """Delete a tiddler from the database.

        Args:
            title: Tiddler title

        Returns:
            bool: True if tiddler was deleted, False if it didn't exist
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()
            cursor.execute("DELETE FROM tiddlers WHERE title = ?", (title,))
            self.db_conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                print(f"[TiddlerStore] Deleted tiddler: {title}")
            return deleted

    def get_updated_tiddlers(
        self, since_timestamp: str = None, current_tiddlers: list = None
    ) -> dict:
        """Get tiddlers that have been modified or deleted since a given timestamp.

        Uses json_extract to query the 'modified' field from within the JSON data.

        On first sync (when since_timestamp is None), uses the last HTML save timestamp
        as the baseline to avoid loading tiddlers that are already in the HTML file.

        This function reports SQLite→TiddlyWiki changes only:
        - Modifications: Tiddlers in SQLite that were modified since last sync
        - Deletions: Tiddlers that exist in TiddlyWiki but were deleted from SQLite (external deletions)

        Args:
            since_timestamp: TiddlyWiki timestamp format (e.g., '20260106120000000')
                           or ISO format. If None, uses last HTML save timestamp.
            current_tiddlers: List of tiddler titles currently loaded in TiddlyWiki.
                            Used for deletion detection. If None, deletions won't be detected.

        Returns:
            dict: {
                'modifications': [list of tiddler titles that were modified in SQLite],
                'deletions': [list of tiddler titles that were deleted from SQLite]
            }
        """
        with self.db_lock:
            cursor = self.db_conn.cursor()

            if since_timestamp is None:
                # First sync after HTML load - use last HTML save timestamp as baseline
                # This avoids loading tiddlers that are already embedded in the HTML file
                last_html_save = self.get_last_html_save()

                if last_html_save is None:
                    # No HTML save recorded yet - return all tiddlers
                    # (New database or pre-existing database before this feature)
                    print(
                        "[TiddlerStore] First sync, no HTML save recorded - returning all tiddlers"
                    )
                    cursor.execute(
                        "SELECT title FROM tiddlers WHERE title NOT LIKE '$:/%'"
                    )
                    rows = cursor.fetchall()
                    modifications = [row[0] for row in rows]
                    print(f"[TiddlerStore] Found {len(modifications)} tiddlers")
                    return {"modifications": modifications, "deletions": []}

                # Return tiddlers modified AFTER the last HTML save
                print(
                    f"[TiddlerStore] First sync, using last HTML save as baseline: {last_html_save}"
                )
                cursor.execute(
                    """
                    SELECT title FROM tiddlers
                    WHERE json_extract(tiddler_data, '$.modified') > ?
                    AND title NOT LIKE '$:/%'
                    """,
                    (last_html_save,),
                )
                rows = cursor.fetchall()
                modifications = [row[0] for row in rows]
                print(
                    f"[TiddlerStore] Found {len(modifications)} tiddlers modified after HTML save"
                )

                # Detect deletions
                deletions = self._detect_deletions(cursor, current_tiddlers)

                return {"modifications": modifications, "deletions": deletions}
            else:
                # Subsequent syncs - use provided timestamp
                # Convert ISO timestamp to TiddlyWiki format for comparison
                tw_timestamp = self._iso_to_tiddlywiki_timestamp(since_timestamp)

                cursor.execute(
                    """
                    SELECT title FROM tiddlers
                    WHERE json_extract(tiddler_data, '$.modified') > ?
                    AND title NOT LIKE '$:/%'
                    """,
                    (tw_timestamp,),
                )
                rows = cursor.fetchall()
                modifications = [row[0] for row in rows]

                # Detect deletions
                deletions = self._detect_deletions(cursor, current_tiddlers)

                return {"modifications": modifications, "deletions": deletions}

    def _detect_deletions(self, cursor, current_tiddlers: list) -> list:
        """Detect tiddlers that were deleted from SQLite (external deletions).

        Reports SQLite→TiddlyWiki deletions: tiddlers that TiddlyWiki has in memory
        but are missing from SQLite (were deleted externally from the database).

        System tiddlers ($:/) are excluded as they are stored but not synced back.

        Args:
            cursor: Database cursor
            current_tiddlers: List of tiddler titles currently loaded in TiddlyWiki

        Returns:
            list: Titles of tiddlers that exist in TiddlyWiki but not in SQLite (were deleted from SQLite)
        """
        if current_tiddlers is None:
            # No current tiddlers provided - can't detect deletions
            return []

        # Get non-system tiddler titles from SQLite (exclude $:/)
        # System tiddlers are stored but never synced back, so ignore them for deletion detection
        cursor.execute("SELECT title FROM tiddlers WHERE title NOT LIKE '$:/%'")
        rows = cursor.fetchall()
        sqlite_tiddlers = set(row[0] for row in rows)

        # Filter out system tiddlers from current_tiddlers as well
        current_set = set(t for t in current_tiddlers if not t.startswith("$:/"))

        # Tiddlers in TiddlyWiki but NOT in SQLite were deleted from SQLite (external deletion)
        # This reports SQLite→TiddlyWiki changes (what TiddlyWiki needs to know about)
        deletions = list(current_set - sqlite_tiddlers)

        if deletions:
            print(
                f"[TiddlerStore] Detected {len(deletions)} external SQLite deletions: {deletions[:5]}"
            )

        return deletions

    def close(self):
        """Close the database connection."""
        if hasattr(self, "db_conn"):
            self.db_conn.close()
            print(f"[TiddlerStore] Closed database for wiki {self.wiki_id}")

    def __del__(self):
        """Clean up database connection when store is destroyed."""
        self.close()
