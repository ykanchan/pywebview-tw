import React from 'react';
import '../styles/WikiCard.css';

const WikiCard = ({ wiki, onOpen, onDelete }) => {
  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 KB';
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="wiki-card">
      <div className="wiki-card-header">
        <h3 className="wiki-title" title={wiki.name}>{wiki.name}</h3>
      </div>
      
      <div className="wiki-card-body">
        {wiki.description && (
          <p className="wiki-description" title={wiki.description}>
            {wiki.description}
          </p>
        )}
        
        <div className="wiki-meta">
          <div className="meta-item">
            <svg className="meta-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M13 2H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1zM5 2v12M2 5h12M2 9h12" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            <span className="label">Created:</span>
            <span className="value">{formatDate(wiki.created_at)}</span>
          </div>
          
          <div className="meta-item">
            <svg className="meta-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M8 4v4l3 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
            <span className="label">Last opened:</span>
            <span className="value">{formatDate(wiki.last_opened)}</span>
          </div>
          
          <div className="meta-item">
            <svg className="meta-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M9 2H4a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V6L9 2z" stroke="currentColor" strokeWidth="1.5"/>
              <path d="M9 2v4h4" stroke="currentColor" strokeWidth="1.5"/>
            </svg>
            <span className="label">Size:</span>
            <span className="value">{formatFileSize(wiki.file_size)}</span>
          </div>
        </div>
      </div>

      <div className="wiki-card-footer">
        <button 
          className="btn btn-primary btn-open"
          onClick={onOpen}
          title="Open wiki"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M1 8s3-5 7-5 7 5 7 5-3 5-7 5-7-5-7-5z" stroke="currentColor" strokeWidth="1.5"/>
            <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5"/>
          </svg>
          Open
        </button>
        <button 
          className="btn btn-danger btn-delete"
          onClick={onDelete}
          title="Delete wiki"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 4h12M5 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1M13 4v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4h10z" stroke="currentColor" strokeWidth="1.5"/>
          </svg>
          Delete
        </button>
      </div>
    </div>
  );
};

export default WikiCard;
