import React from 'react';
import { Search, Sun, Bell, User } from 'lucide-react';
import { IconButton } from '../ui/IconButton';
import './layout.css';

export const TopNavbar = () => {
  return (
    <header className="top-navbar">
      <div className="navbar-left">
        {/* Mobile menu toggle could go here */}
      </div>
      
      <div className="navbar-center">
        <div className="search-bar">
          <Search size={18} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search documents, ask anything..." 
            className="search-input"
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
