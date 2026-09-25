import React from 'react';
import { NavLink } from 'react-router-dom';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import {
  Home, FileText, BarChart2, CheckSquare, Search, 
  MessageSquare, Calendar, Book, Folder, FolderKanban, 
  User, Settings, ChevronLeft, ChevronRight, HelpCircle, 
  Zap, ArrowRight
} from 'lucide-react';
import './layout.css';

export const Sidebar = ({ isOpen, toggle }) => {
  const navItems = [
    { name: 'Home', icon: Home, path: '/dashboard' },
    { name: 'Documents', icon: FileText, path: '/documents' },
    { name: 'Analytics', icon: BarChart2, path: '/analytics' },
    { name: 'Compare', icon: CheckSquare, path: '/compare' },
    { name: 'AI Playground', icon: MessageSquare, path: '/chat' },
    { name: 'Calendar', icon: Calendar, path: '/placeholder/calendar' },
    { name: 'Knowledge Base', icon: Book, path: '/placeholder/kb' },
  ];

  const projects = [
    { name: 'Research', icon: FolderKanban },
    { name: 'Academics', icon: FolderKanban },
    { name: 'Work', icon: FolderKanban },
    { name: 'Personal', icon: Folder },
  ];

  return (
    <motion.aside 
      className={clsx('sidebar glass-panel', !isOpen && 'collapsed')}
      initial={false}
      animate={{ width: isOpen ? 260 : 80 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
    >
      <div className="sidebar-header">
        <div className="brand">
          <div className="brand-logo">
            <Zap size={20} className="text-accent-primary" />
          </div>
          {isOpen && <span className="brand-name">DocuMind AI</span>}
        </div>
        <button className="toggle-btn" onClick={toggle}>
          {isOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
        </button>
      </div>

      <div className="sidebar-scrollable">
        <nav className="nav-group">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) => clsx('nav-item', isActive && 'active')}
            >
              <item.icon size={20} className="nav-icon" />
              {isOpen && <span className="nav-label">{item.name}</span>}
            </NavLink>
          ))}
        </nav>

        {isOpen && (
          <div className="nav-group projects-group">
            <h4 className="group-title">Projects</h4>
            {projects.map((project) => (
              <div key={project.name} className="nav-item project-item">
                <project.icon size={18} className="nav-icon" />
                <span className="nav-label">{project.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        {isOpen ? (
          <div className="storage-widget clay-panel">
            <div className="storage-header">
              <span className="storage-title">Storage</span>
              <span className="storage-icon">⋮</span>
            </div>
            <div className="storage-stats">
              <span className="storage-used">2.4 GB</span>
              <span className="storage-total"> / 10 GB</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: '24%' }}></div>
            </div>
            <button className="upgrade-btn">
              Upgrade <ArrowRight size={14} />
            </button>
          </div>
        ) : (
          <div className="storage-widget-collapsed">
            <div className="progress-circle"></div>
          </div>
        )}
      </div>
    </motion.aside>
  );
};
