import React from 'react';
import WikiCard from './WikiCard';
import '../styles/WikiList.css';

const WikiList = ({ wikis, onOpenWiki, onDeleteWiki, loading }) => {
  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <p>Loading wikis...</p>
      </div>
    );
  }

  if (wikis.length === 0) {
    return (
      <div className="empty-state">
        <svg className="empty-icon" width="64" height="64" viewBox="0 0 64 64" fill="none">
          <path d="M32 8v48M8 32h48" stroke="currentColor" strokeWidth="4" strokeLinecap="round"/>
          <circle cx="32" cy="32" r="28" stroke="currentColor" strokeWidth="4"/>
        </svg>
        <h2>No wikis found</h2>
        <p>Create your first wiki to get started!</p>
      </div>
    );
  }

  return (
    <div className="wiki-list">
      <div className="wiki-count">
        {wikis.length} {wikis.length === 1 ? 'wiki' : 'wikis'}
      </div>
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
