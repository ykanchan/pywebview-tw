import React from 'react';
import '../styles/Footer.css';

const Footer = () => {
  return (
    <footer className="footer">
      <div className="footer-content">
        <p className="footer-text">
          TiddlyWiki Manager v2.0.0
        </p>
        <p className="footer-links">
          <a href="https://tiddlywiki.com" target="_blank" rel="noopener noreferrer">
            About TiddlyWiki
          </a>
        </p>
      </div>
    </footer>
  );
};

export default Footer;
