import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import {
  Home, FileText, BarChart2, CheckSquare, Search, 
  MessageSquare, Calendar, Book, Folder, FolderKanban, 
  User, Settings, ChevronLeft, ChevronRight, HelpCircle, 
  Zap, ArrowRight
} from 'lucide-react';
import './layout.css';

export const Sidebar = ({ isOpen, toggle, isMobile, closeMobileSidebar }) => {
  const navItems = [
    { name: 'Home', icon: Home, path: '/dashboard' },
    { name: 'Documents', icon: FileText, path: '/documents' },
    { name: 'Analytics', icon: BarChart2, path: '/analytics' },
    { name: 'Compare', icon: CheckSquare, path: '/compare' },
    { name: 'AI Playground', icon: MessageSquare, path: '/chat' },
    { name: 'Calendar', icon: Calendar, path: '/calendar' },
    { name: 'Knowledge Base', icon: Book, path: '/knowledge-base' },
  ];

  const projects = [
    { name: 'Research', icon: FolderKanban, path: '/projects/research' },
    { name: 'Academics', icon: FolderKanban, path: '/projects/academics' },
    { name: 'Work', icon: FolderKanban, path: '/projects/work' },
    { name: 'Personal', icon: Folder, path: '/projects/personal' },
  ];

  const handleNavClick = () => {
    if (isMobile && closeMobileSidebar) {
      closeMobileSidebar();
    }
  };

  return (
    <motion.aside 
      className={clsx('sidebar glass-panel', !isOpen && !isMobile && 'collapsed')}
      initial={false}
      animate={{ 
        width: isMobile ? 260 : (isOpen ? 260 : 80),
        x: isMobile ? (isOpen ? 0 : -100 + '%') : 0 // The percentage string x:-100% works better in Framer Motion for full offset
      }}
      style={{ x: isMobile ? (isOpen ? 0 : '-100%') : 0 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
    >
      <div className="sidebar-header">
        <Link 
          to="/" 
          className="brand" 
          onClick={handleNavClick}
          style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}
        >
          <div className="brand-logo">
            <Zap size={20} className="text-accent-primary" />
          </div>
          {(isOpen || isMobile) && <span className="brand-name">DocuMind AI</span>}
        </Link>
        <button className="toggle-btn" onClick={toggle}>
          {isMobile ? <ChevronLeft size={18} /> : (isOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />)}
        </button>
      </div>

      <div className="sidebar-scrollable">
        <nav className="nav-group">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              title={!isOpen && !isMobile ? item.name : undefined}
              className={({ isActive }) => clsx('nav-item', isActive && 'active')}
              onClick={handleNavClick}
            >
              <item.icon size={20} className="nav-icon" />
              {(isOpen || isMobile) && <span className="nav-label">{item.name}</span>}
            </NavLink>
          ))}
        </nav>

        { (isOpen || isMobile) && (
          <div className="nav-group projects-group">
            <h4 className="group-title">Projects</h4>
            {projects.map((project) => (
              <NavLink 
                key={project.name} 
                to={project.path}
                className={({ isActive }) => clsx('nav-item project-item', isActive && 'active')}
                onClick={handleNavClick}
                style={{ textDecoration: 'none' }}
              >
                <project.icon size={18} className="nav-icon" />
                <span className="nav-label">{project.name}</span>
              </NavLink>
            ))}
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        { (isOpen || isMobile) ? (
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
