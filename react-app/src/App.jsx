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
    // Wait for PyWebView API to be fully ready before loading wikis
    const waitForApi = () => {
      if (window.pywebview && window.pywebview.api) {
        // Check if list_wikis method is actually callable
        try {
          const apiType = typeof window.pywebview.api.list_wikis;
          console.log('[React] PyWebView API found, list_wikis type:', apiType);
          console.log('[React] API object:', window.pywebview.api);
          
          if (apiType === 'function') {
            console.log('[React] list_wikis is ready, loading wikis...');
            loadWikis();
          } else {
            console.log('[React] list_wikis not ready yet, waiting...');
            setTimeout(waitForApi, 100);
          }
        } catch (e) {
          console.log('[React] Error checking API:', e);
          setTimeout(waitForApi, 100);
        }
      } else {
        console.log('[React] Waiting for PyWebView API...');
        setTimeout(waitForApi, 100);
      }
    };
    waitForApi();
  }, []);

  const loadWikis = async () => {
    console.log('[React] loadWikis called');
    setLoading(true);
    setError(null);
    try {
      // Call list_wikis directly - PyWebView Proxy doesn't enumerate methods properly
      const wikiList = await window.pywebview.api.list_wikis();
      console.log('[React] Received wiki list:', wikiList);
      setWikis(wikiList);
    } catch (error) {
      console.error('[React] Failed to load wikis:', error);
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
        const result = await window.pywebview.api.open_wiki(wikiId);
        
        // On mobile, navigate to the wiki URL
        if (result.is_mobile && result.wiki_url) {
          console.log('[React] Mobile platform, navigating to wiki:', result.wiki_url);
          window.location.href = result.wiki_url;
        } else {
          console.log('[React] Desktop platform, wiki opened in new window');
        }
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
