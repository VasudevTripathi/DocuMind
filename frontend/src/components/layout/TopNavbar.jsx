import React from 'react';
import { Search, Sun, Bell, User, Menu, Zap } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { IconButton } from '../ui/IconButton';
import './layout.css';

export const TopNavbar = ({ toggleMobileMenu, isMobile }) => {
  const navigate = useNavigate();

  return (
    <header className="top-navbar">
      <div className="navbar-left" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        {isMobile && (
          <IconButton variant="ghost" onClick={toggleMobileMenu}>
            <Menu size={20} />
          </IconButton>
        )}
        {isMobile && (
          <Link to="/" className="brand" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <div className="brand-logo" style={{ width: '28px', height: '28px', minWidth: '28px' }}>
              <Zap size={16} className="text-accent-primary" />
            </div>
            <span className="brand-name" style={{ fontSize: 'var(--font-size-base)' }}>DocuMind AI</span>
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
            onKeyDown={(e) => {
              if (e.key === 'Enter' && e.target.value.trim()) {
                navigate(`/search?q=${encodeURIComponent(e.target.value.trim())}`);
              }
            }}
          />
          <div className="search-shortcut">⌘ K</div>
        </div>
      </div>

      <div className="navbar-right">
        <IconButton variant="ghost" className="nav-action">
          <Sun size={20} />
        </IconButton>
        <IconButton variant="ghost" className="nav-action">
          <Bell size={20} />
        </IconButton>
        <div className="user-profile">
          <div className="avatar">
            <User size={20} />
          </div>
        </div>
      </div>
    </header>
  );
};
