"""Wiki management module for creating, deleting, and managing TiddlyWiki instances."""

import os
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path


class WikiManager:
    """Manages TiddlyWiki instances including creation, deletion, and metadata."""

    def __init__(self, base_dir: str):
        """Initialize WikiManager with base directory.

        Args:
            base_dir: Base directory path for the application
        """
        # Store paths as strings to avoid PyWebView serialization issues
        base_path = Path(base_dir)
        self._base_dir_str = str(base_path)
        self._data_dir_str = str(base_path / "app" / "data")
        self._wikis_dir_str = str(base_path / "app" / "data" / "wikis")
        self._metadata_file_str = str(base_path / "app" / "data" / "wikis.json")
        self._base_template_str = str(base_path / "app" / "data" / "base.html")

        # Ensure directories exist
        Path(self._wikis_dir_str).mkdir(parents=True, exist_ok=True)
        self._initialize_metadata()

    # Private methods to access paths as Path objects internally
    def _get_base_dir(self):
        return Path(self._base_dir_str)

    def _get_data_dir(self):
        return Path(self._data_dir_str)

    def _get_wikis_dir(self):
        return Path(self._wikis_dir_str)

    def _get_metadata_file(self):
        return Path(self._metadata_file_str)

    def _get_base_template(self):
        return Path(self._base_template_str)

    def _initialize_metadata(self):
        """Initialize metadata file if it doesn't exist."""
        if not self._get_metadata_file().exists():
            initial_data = {
                "wikis": [],
                "settings": {"last_wiki_id": 0, "default_wiki": None},
            }
            self._save_metadata(initial_data)

    def _load_metadata(self):
        """Load wiki metadata from JSON file.

        Returns:
            dict: Wiki metadata dictionary
        """
        try:
            with open(self._metadata_file_str, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_metadata()
            return self._load_metadata()

    def _save_metadata(self, data):
        """Save wiki metadata to JSON file.

        Args:
            data: Metadata dictionary to save
        """
        with open(self._metadata_file_str, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _generate_unique_filename(self):
        """Generate unique filename for wiki.

        Returns:
            str: Unique filename with .html extension
        """
        return f"wiki_{uuid.uuid4().hex[:8]}.html"

    def _get_file_size(self, filepath):
        """Get file size in bytes.

        Args:
            filepath: Path to file

        Returns:
            int: File size in bytes, 0 if file doesn't exist
        """
        try:
            return os.path.getsize(filepath)
        except OSError:
            return 0

    def create_wiki(self, name: str, description: str = "") -> dict:
        """Create a new wiki from base template.

        Args:
            name: Name for the new wiki
            description: Optional description for the wiki

        Returns:
            dict: Wiki metadata dictionary

        Raises:
            FileNotFoundError: If base template doesn't exist
            Exception: If wiki creation fails
        """
        base_template = self._get_base_template()
        if not base_template.exists():
            raise FileNotFoundError(f"Base template not found: {base_template}")

        # Generate unique wiki data
        wiki_id = str(uuid.uuid4())
        filename = self._generate_unique_filename()
        wiki_path = self._get_wikis_dir() / filename

        try:
            # Copy base template to new wiki file
            # Use copy() instead of copy2() to avoid permission issues on Android
            # copy2() tries to preserve metadata which Android doesn't support
            shutil.copy(base_template, wiki_path)

            # Create wiki metadata
            wiki_data = {
                "id": wiki_id,
                "name": name.strip(),
                "description": description.strip(),
                "filename": filename,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "last_opened": None,
                "file_size": self._get_file_size(wiki_path),
            }

            # Update metadata
            metadata = self._load_metadata()
            metadata["wikis"].append(wiki_data)
            metadata["settings"]["last_wiki_id"] += 1
            self._save_metadata(metadata)

            return wiki_data

        except Exception as e:
            # Clean up on failure
            if wiki_path.exists():
                wiki_path.unlink()
            raise Exception(f"Failed to create wiki: {str(e)}")

    def delete_wiki(self, wiki_id: str) -> bool:
        """Delete a wiki by ID.

        Args:
            wiki_id: UUID of the wiki to delete

        Returns:
            bool: True if deletion was successful

        Raises:
            ValueError: If wiki not found
            Exception: If deletion fails
        """
        metadata = self._load_metadata()
        wiki_to_delete = None
        wiki_index = None

        # Find wiki in metadata
        for i, wiki in enumerate(metadata["wikis"]):
            if wiki["id"] == wiki_id:
                wiki_to_delete = wiki
                wiki_index = i
                break

        if wiki_to_delete is None:
            raise ValueError(f"Wiki not found: {wiki_id}")

        try:
            # Delete wiki file
            wiki_path = self._get_wikis_dir() / wiki_to_delete["filename"]
            if wiki_path.exists():
                wiki_path.unlink()

            # Remove from metadata
            metadata["wikis"].pop(wiki_index)
            self._save_metadata(metadata)

            return True

        except Exception as e:
            raise Exception(f"Failed to delete wiki: {str(e)}")

    def list_wikis(self) -> list:
        """List all wikis with updated file sizes.

        Returns:
            list: List of wiki metadata dictionaries
        """
        metadata = self._load_metadata()

        # Update file sizes
        for wiki in metadata["wikis"]:
            wiki_path = self._get_wikis_dir() / wiki["filename"]
            wiki["file_size"] = self._get_file_size(wiki_path)

        # Save updated metadata
        self._save_metadata(metadata)

        return metadata["wikis"]

    def get_wiki(self, wiki_id: str) -> dict:
        """Get wiki metadata by ID.

        Args:
            wiki_id: UUID of the wiki

        Returns:
            dict: Wiki metadata dictionary

        Raises:
            ValueError: If wiki not found
        """
        metadata = self._load_metadata()

        for wiki in metadata["wikis"]:
            if wiki["id"] == wiki_id:
                # Update file size
                wiki_path = self._get_wikis_dir() / wiki["filename"]
                wiki["file_size"] = self._get_file_size(wiki_path)
                return wiki

        raise ValueError(f"Wiki not found: {wiki_id}")

    def get_wiki_path(self, wiki_id: str) -> Path:
        """Get file path for wiki.

        Args:
            wiki_id: UUID of the wiki

        Returns:
            Path: Full path to wiki file

        Raises:
            ValueError: If wiki not found
        """
        wiki = self.get_wiki(wiki_id)
        return self._get_wikis_dir() / wiki["filename"]

    def update_last_opened(self, wiki_id: str):
        """Update last opened timestamp for wiki.

        Args:
            wiki_id: UUID of the wiki

        Raises:
            ValueError: If wiki not found
        """
        metadata = self._load_metadata()

        for wiki in metadata["wikis"]:
            if wiki["id"] == wiki_id:
                wiki["last_opened"] = datetime.utcnow().isoformat() + "Z"
                self._save_metadata(metadata)
                return

        raise ValueError(f"Wiki not found: {wiki_id}")
