import React from 'react';
import '../styles/Header.css';

const Header = ({ onCreateNew, searchTerm, onSearchChange }) => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <h1 className="app-title">TiddlyWiki Manager</h1>
          <p className="app-subtitle">Manage your personal wikis</p>
        </div>
        
        <div className="header-right">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search wikis..."
              value={searchTerm}
              onChange={(e) => onSearchChange(e.target.value)}
              className="search-input"
            />
            <svg className="search-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M9 17A8 8 0 1 0 9 1a8 8 0 0 0 0 16zM19 19l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          
          <button className="btn btn-primary" onClick={onCreateNew}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            New Wiki
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
