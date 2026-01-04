# Implementation Specifications

## React Component Detailed Design

### App.js - Main Application Component
```jsx
import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import WikiList from './components/WikiList';
import CreateWikiForm from './components/CreateWikiForm';
import Footer from './components/Footer';
import './App.css';

function App() {
  const [wikis, setWikis] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadWikis();
  }, []);

  const loadWikis = async () => {
    setLoading(true);
    try {
      const wikiList = await window.pywebview.api.list_wikis();
      setWikis(wikiList);
    } catch (error) {
      console.error('Failed to load wikis:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWiki = async (wikiData) => {
    try {
      await window.pywebview.api.create_wiki(wikiData.name, wikiData.description);
      await loadWikis(); // Refresh list
      setShowCreateForm(false);
    } catch (error) {
      console.error('Failed to create wiki:', error);
    }
  };

  const handleOpenWiki = async (wikiId) => {
    try {
      await window.pywebview.api.open_wiki(wikiId);
    } catch (error) {
      console.error('Failed to open wiki:', error);
    }
  };

  const handleDeleteWiki = async (wikiId) => {
    if (window.confirm('Are you sure you want to delete this wiki?')) {
      try {
        await window.pywebview.api.delete_wiki(wikiId);
        await loadWikis(); // Refresh list
      } catch (error) {
        console.error('Failed to delete wiki:', error);
      }
    }
  };

  const filteredWikis = wikis.filter(wiki =>
    wiki.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    wiki.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="app">
      <Header 
        onCreateNew={() => setShowCreateForm(true)}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
      />
      
      {showCreateForm && (
        <CreateWikiForm
          onSubmit={handleCreateWiki}
          onCancel={() => setShowCreateForm(false)}
        />
      )}

      <WikiList
        wikis={filteredWikis}
        onOpenWiki={handleOpenWiki}
        onDeleteWiki={handleDeleteWiki}
        loading={loading}
      />

      <Footer />
    </div>
  );
}

export default App;
```

### components/WikiList.js
```jsx
import React from 'react';
import WikiCard from './WikiCard';
import './WikiList.css';

const WikiList = ({ wikis, onOpenWiki, onDeleteWiki, loading }) => {
  if (loading) {
    return <div className="loading">Loading wikis...</div>;
  }

  if (wikis.length === 0) {
    return (
      <div className="empty-state">
        <h2>No wikis found</h2>
        <p>Create your first wiki to get started!</p>
      </div>
    );
  }

  return (
    <div className="wiki-list">
      <div className="wiki-grid">
        {wikis.map(wiki => (
          <WikiCard
            key={wiki.id}
            wiki={wiki}
            onOpen={() => onOpenWiki(wiki.id)}
            onDelete={() => onDeleteWiki(wiki.id)}
          />
        ))}
      </div>
    </div>
  );
};

export default WikiList;
```

### components/WikiCard.js
```jsx
import React from 'react';
import './WikiCard.css';

const WikiCard = ({ wiki, onOpen, onDelete }) => {
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatFileSize = (bytes) => {
    const sizes = ['Bytes', 'KB', 'MB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="wiki-card">
      <div className="wiki-card-header">
        <h3 className="wiki-title">{wiki.name}</h3>
        <div className="wiki-actions">
          <button 
            className="btn btn-primary"
            onClick={onOpen}
          >
            Open
          </button>
          <button 
            className="btn btn-danger"
            onClick={onDelete}
          >
            Delete
          </button>
        </div>
      </div>
      
      <div className="wiki-card-body">
        <p className="wiki-description">{wiki.description}</p>
        
        <div className="wiki-meta">
          <div className="meta-item">
            <span className="label">Created:</span>
            <span className="value">{formatDate(wiki.created_at)}</span>
          </div>
          <div className="meta-item">
            <span className="label">Last opened:</span>
            <span className="value">{wiki.last_opened ? formatDate(wiki.last_opened) : 'Never'}</span>
          </div>
          <div className="meta-item">
            <span className="label">Size:</span>
            <span className="value">{formatFileSize(wiki.file_size)}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WikiCard;
```

### components/CreateWikiForm.js
```jsx
import React, { useState } from 'react';
import './CreateWikiForm.css';

const CreateWikiForm = ({ onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  });
  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Wiki name is required';
    } else if (formData.name.length > 50) {
      newErrors.name = 'Wiki name must be 50 characters or less';
    }
    
    if (formData.description.length > 200) {
      newErrors.description = 'Description must be 200 characters or less';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validateForm()) {
      onSubmit(formData);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <form onSubmit={handleSubmit} className="create-wiki-form">
          <h2>Create New Wiki</h2>
          
          <div className="form-group">
            <label htmlFor="wiki-name">Wiki Name *</label>
            <input
              id="wiki-name"
              type="text"
              value={formData.name}
              onChange={(e) => handleInputChange('name', e.target.value)}
              placeholder="Enter wiki name"
              className={errors.name ? 'error' : ''}
            />
            {errors.name && <span className="error-text">{errors.name}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="wiki-description">Description</label>
            <textarea
              id="wiki-description"
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              placeholder="Enter wiki description (optional)"
              rows="3"
              className={errors.description ? 'error' : ''}
            />
            {errors.description && <span className="error-text">{errors.description}</span>}
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Create Wiki
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateWikiForm;
```

## Python Backend API Design

### api/wiki_manager.py
```python
import os
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

class WikiManager:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data"
        self.wikis_dir = self.data_dir / "wikis"
        self.metadata_file = self.data_dir / "wikis.json"
        self.base_template = self.base_dir / "assets" / "base.html"
        
        # Ensure directories exist
        self.wikis_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_metadata()

    def _initialize_metadata(self):
        """Initialize metadata file if it doesn't exist"""
        if not self.metadata_file.exists():
            initial_data = {
                "wikis": [],
                "settings": {
                    "last_wiki_id": 0,
                    "default_wiki": None
                }
            }
            self._save_metadata(initial_data)

    def _load_metadata(self):
        """Load wiki metadata from JSON file"""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._initialize_metadata()
            return self._load_metadata()

    def _save_metadata(self, data):
        """Save wiki metadata to JSON file"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _generate_unique_filename(self):
        """Generate unique filename for wiki"""
        return f"wiki_{uuid.uuid4().hex[:8]}.html"

    def _get_file_size(self, filepath):
        """Get file size in bytes"""
        try:
            return os.path.getsize(filepath)
        except OSError:
            return 0

    def create_wiki(self, name: str, description: str = "") -> dict:
        """Create a new wiki from base template"""
        if not self.base_template.exists():
            raise FileNotFoundError(f"Base template not found: {self.base_template}")

        # Generate unique wiki data
        wiki_id = str(uuid.uuid4())
        filename = self._generate_unique_filename()
        wiki_path = self.wikis_dir / filename

        try:
            # Copy base template to new wiki file
            shutil.copy2(self.base_template, wiki_path)
            
            # Create wiki metadata
            wiki_data = {
                "id": wiki_id,
                "name": name.strip(),
                "description": description.strip(),
                "filename": filename,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "last_opened": None,
                "file_size": self._get_file_size(wiki_path)
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
        """Delete a wiki by ID"""
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
            wiki_path = self.wikis_dir / wiki_to_delete["filename"]
            if wiki_path.exists():
                wiki_path.unlink()

            # Remove from metadata
            metadata["wikis"].pop(wiki_index)
            self._save_metadata(metadata)

            return True

        except Exception as e:
            raise Exception(f"Failed to delete wiki: {str(e)}")

    def list_wikis(self) -> list:
        """List all wikis"""
        metadata = self._load_metadata()
        
        # Update file sizes
        for wiki in metadata["wikis"]:
            wiki_path = self.wikis_dir / wiki["filename"]
            wiki["file_size"] = self._get_file_size(wiki_path)
        
        # Save updated metadata
        self._save_metadata(metadata)
        
        return metadata["wikis"]

    def get_wiki(self, wiki_id: str) -> dict:
        """Get wiki by ID"""
        metadata = self._load_metadata()
        
        for wiki in metadata["wikis"]:
            if wiki["id"] == wiki_id:
                # Update file size
                wiki_path = self.wikis_dir / wiki["filename"]
                wiki["file_size"] = self._get_file_size(wiki_path)
                return wiki
        
        raise ValueError(f"Wiki not found: {wiki_id}")

    def get_wiki_path(self, wiki_id: str) -> Path:
        """Get file path for wiki"""
        wiki = self.get_wiki(wiki_id)
        return self.wikis_dir / wiki["filename"]

    def update_last_opened(self, wiki_id: str):
        """Update last opened timestamp for wiki"""
        metadata = self._load_metadata()
        
        for wiki in metadata["wikis"]:
            if wiki["id"] == wiki_id:
                wiki["last_opened"] = datetime.utcnow().isoformat() + "Z"
                self._save_metadata(metadata)
                return
        
        raise ValueError(f"Wiki not found: {wiki_id}")
```

### api/window_manager.py
```python
import webview
from typing import Dict, List, Optional

class WindowManager:
    def __init__(self):
        self.wiki_windows: Dict[str, webview.Window] = {}
        self.main_window: Optional[webview.Window] = None

    def set_main_window(self, window: webview.Window):
        """Set the main application window"""
        self.main_window = window

    def create_wiki_window(self, wiki_id: str, wiki_path: str, wiki_name: str) -> webview.Window:
        """Create a new window for a wiki"""
        if wiki_id in self.wiki_windows:
            # Window already exists, focus it
            existing_window = self.wiki_windows[wiki_id]
            try:
                # Try to focus existing window (platform dependent)
                return existing_window
            except:
                # Window might be closed, remove from tracking
                del self.wiki_windows[wiki_id]

        # Create new window
        window = webview.create_window(
            title=f"TiddlyWiki - {wiki_name}",
            url=f"file://{wiki_path}",
            width=1200,
            height=800,
            resizable=True
        )

        self.wiki_windows[wiki_id] = window
        return window

    def close_wiki_window(self, wiki_id: str) -> bool:
        """Close a wiki window"""
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
        """List currently open wiki windows"""
        return list(self.wiki_windows.keys())

    def cleanup_closed_windows(self):
        """Remove references to closed windows"""
        # This would need to be called periodically or on window events
        # Implementation depends on pywebview capabilities
        pass
```

### Updated main.py
```python
__version__ = "2.0.0"

import webview
import os
from pathlib import Path

from api.wiki_manager import WikiManager
from api.window_manager import WindowManager

class MultiWikiApp:
    def __init__(self):
        # Get the directory where this script is located
        self.base_path = Path(__file__).parent
        self.assets_path = self.base_path / "assets"
        
        # Initialize managers
        self.wiki_manager = WikiManager(self.base_path)
        self.window_manager = WindowManager()

    # API methods exposed to JavaScript
    def create_wiki(self, name: str, description: str = "") -> dict:
        """Create a new wiki"""
        try:
            return self.wiki_manager.create_wiki(name, description)
        except Exception as e:
            print(f"Error creating wiki: {e}")
            raise

    def delete_wiki(self, wiki_id: str) -> bool:
        """Delete a wiki"""
        try:
            return self.wiki_manager.delete_wiki(wiki_id)
        except Exception as e:
            print(f"Error deleting wiki: {e}")
            raise

    def list_wikis(self) -> list:
        """List all wikis"""
        try:
            return self.wiki_manager.list_wikis()
        except Exception as e:
            print(f"Error listing wikis: {e}")
            raise

    def open_wiki(self, wiki_id: str):
        """Open a wiki in a new window"""
        try:
            wiki = self.wiki_manager.get_wiki(wiki_id)
            wiki_path = self.wiki_manager.get_wiki_path(wiki_id)
            
            # Update last opened timestamp
            self.wiki_manager.update_last_opened(wiki_id)
            
            # Create new window (this will be handled after webview.start())
            self._pending_wiki_opens = getattr(self, '_pending_wiki_opens', [])
            self._pending_wiki_opens.append({
                'wiki_id': wiki_id,
                'wiki_path': str(wiki_path),
                'wiki_name': wiki["name"]
            })
            
            return {"status": "success", "wiki_id": wiki_id}
            
        except Exception as e:
            print(f"Error opening wiki: {e}")
            raise

def main():
    app = MultiWikiApp()
    
    # Path to the React app
    react_app_path = app.assets_path / "react-app" / "index.html"
    
    # Create main window with React app
    window = webview.create_window(
        "TiddlyWiki Manager",
        str(react_app_path),
        width=1000,
        height=700,
        resizable=True
    )
    
    app.window_manager.set_main_window(window)
    
    def start_app():
        """Called after webview starts"""
        # Handle any pending wiki opens
        if hasattr(app, '_pending_wiki_opens'):
            for wiki_data in app._pending_wiki_opens:
                app.window_manager.create_wiki_window(
                    wiki_data['wiki_id'],
                    wiki_data['wiki_path'],
                    wiki_data['wiki_name']
                )
            app._pending_wiki_opens.clear()

    # Start the application
    webview.start(start_app, window, ssl=True, debug=True, js_api=app)

if __name__ == "__main__":
    main()
```

## Mobile Compatibility Strategy

### Android Adaptations
1. **Single Window Constraint**: Android typically supports single-window apps
2. **Navigation Pattern**: Use React routing instead of multiple windows
3. **Back Button**: Implement proper back navigation
4. **Touch Optimization**: Larger touch targets, mobile-friendly UI

### Implementation Approach for Mobile
```jsx
// Mobile-specific App component modifications
const App = () => {
  const [currentView, setCurrentView] = useState('manager'); // 'manager' or 'wiki'
  const [currentWikiId, setCurrentWikiId] = useState(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Detect mobile platform
    const checkMobile = async () => {
      try {
        const platform = await window.pywebview.api.get_platform();
        setIsMobile(platform === 'android');
      } catch {
        // Fallback detection
        setIsMobile(/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
      }
    };
    checkMobile();
  }, []);

  const handleOpenWiki = async (wikiId) => {
    if (isMobile) {
      setCurrentWikiId(wikiId);
      setCurrentView('wiki');
    } else {
      await window.pywebview.api.open_wiki(wikiId);
    }
  };

  const handleBackToManager = () => {
    setCurrentView('manager');
    setCurrentWikiId(null);
  };

  if (currentView === 'wiki' && isMobile) {
    return (
      <WikiViewer 
        wikiId={currentWikiId}
        onBack={handleBackToManager}
      />
    );
  }

  return (
    <div className={`app ${isMobile ? 'mobile' : 'desktop'}`}>
      {/* Regular manager interface */}
    </div>
  );
};
```

This comprehensive specification provides the foundation for implementing the multi-wiki TiddlyWiki system with a React frontend and Python backend integration.