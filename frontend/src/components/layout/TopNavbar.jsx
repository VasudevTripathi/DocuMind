import React, { useState } from 'react';
import { Search, Sun, Bell, User, Menu, Zap, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { IconButton } from '../ui/IconButton';
import { useUser } from '../../hooks/useUser';
import './layout.css';

export const TopNavbar = ({ toggleMobileMenu, isMobile }) => {
  const navigate = useNavigate();
  const { userName } = useUser();
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');

  const handleSearchSubmit = (e) => {
    if (e) e.preventDefault();
    if (searchValue.trim()) {
      navigate(`/search?q=${encodeURIComponent(searchValue.trim())}`);
      setMobileSearchOpen(false);
    }
  };

  const userInitial = userName ? userName.trim().charAt(0).toUpperCase() : null;

  return (
    <header className="top-navbar">
      {/* Mobile Search Overlay Bar */}
      {isMobile && mobileSearchOpen ? (
        <form className="mobile-search-overlay" onSubmit={handleSearchSubmit}>
          <Search size={18} className="search-icon" />
          <input
            type="text"
            autoFocus
            placeholder="Search documents, ask anything..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            className="mobile-search-input"
          />
          <button 
            type="button" 
            className="mobile-search-close" 
            onClick={() => setMobileSearchOpen(false)}
            aria-label="Close search"
          >
            <X size={18} />
          </button>
        </form>
      ) : (
        <>
          <div className="navbar-left">
            {isMobile && (
              <button 
                type="button" 
                className="mobile-menu-btn" 
                onClick={toggleMobileMenu}
                aria-label="Toggle navigation menu"
              >
                <Menu size={22} />
              </button>
            )}
            {isMobile && (
              <Link to="/" className="brand mobile-brand">
                <div className="brand-logo">
                  <Zap size={16} className="text-accent-primary" />
                </div>
                <span className="brand-name mobile-brand-name">DocuMind</span>
              </Link>
            )}
          </div>
          
          <div className="navbar-center">
            <div className="search-bar">
              <Search size={18} className="search-icon" />
              <input 
                type="text" 
                placeholder="Search documents, ask anything..." 
                className="search-input"
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSearchSubmit(e);
                }}
              />
              <div className="search-shortcut">⌘ K</div>
            </div>
          </div>

          <div className="navbar-right">
            {isMobile && (
              <button
                type="button"
                className="mobile-search-trigger-btn"
                onClick={() => setMobileSearchOpen(true)}
                aria-label="Open search"
              >
                <Search size={19} />
              </button>
            )}
            <IconButton variant="ghost" className="nav-action desktop-only-action">
              <Sun size={19} />
            </IconButton>
            <IconButton variant="ghost" className="nav-action">
              <Bell size={19} />
            </IconButton>
            <Link 
              to="/dashboard" 
              className="user-profile" 
              title={userName ? `Logged in as ${userName}` : "DocuMind User"}
            >
              <div className="avatar">
                {userInitial ? (
                  <span className="avatar-initial">{userInitial}</span>
                ) : (
                  <User size={18} />
                )}
              </div>
              {userName && (
                <span className="user-nav-name">{userName}</span>
              )}
            </Link>
          </div>
        </>
      )}
    </header>
  );
};
