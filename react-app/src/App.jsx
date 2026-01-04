import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import WikiList from './components/WikiList';
import CreateWikiForm from './components/CreateWikiForm';
import Footer from './components/Footer';
import './styles/App.css';

function App() {
  const [wikis, setWikis] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState(null);

  useEffect(() => {
    loadWikis();
  }, []);

  const loadWikis = async () => {
    setLoading(true);
    setError(null);
    try {
      // Check if pywebview API is available
      if (window.pywebview && window.pywebview.api) {
        const wikiList = await window.pywebview.api.list_wikis();
        setWikis(wikiList);
      } else {
        // Fallback for development/testing
        console.warn('PyWebView API not available, using mock data');
        setWikis([]);
      }
    } catch (error) {
      console.error('Failed to load wikis:', error);
      setError('Failed to load wikis. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateWiki = async (wikiData) => {
    try {
      setError(null);
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.create_wiki(wikiData.name, wikiData.description);
        await loadWikis(); // Refresh list
        setShowCreateForm(false);
      } else {
        throw new Error('PyWebView API not available');
      }
    } catch (error) {
      console.error('Failed to create wiki:', error);
      setError('Failed to create wiki. Please try again.');
      throw error; // Re-throw to let form handle it
    }
  };

  const handleOpenWiki = async (wikiId) => {
    try {
      setError(null);
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.open_wiki(wikiId);
      } else {
        console.warn('PyWebView API not available');
      }
    } catch (error) {
      console.error('Failed to open wiki:', error);
      setError('Failed to open wiki. Please try again.');
    }
  };

  const handleDeleteWiki = async (wikiId) => {
    if (window.confirm('Are you sure you want to delete this wiki? This action cannot be undone.')) {
      try {
        setError(null);
        if (window.pywebview && window.pywebview.api) {
          await window.pywebview.api.delete_wiki(wikiId);
          await loadWikis(); // Refresh list
        } else {
          throw new Error('PyWebView API not available');
        }
      } catch (error) {
        console.error('Failed to delete wiki:', error);
        setError('Failed to delete wiki. Please try again.');
      }
    }
  };

  const filteredWikis = wikis.filter(wiki =>
    wiki.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (wiki.description && wiki.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="app">
      <Header 
        onCreateNew={() => setShowCreateForm(true)}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
      />
      
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

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
