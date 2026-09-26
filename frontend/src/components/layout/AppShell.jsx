import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import './layout.css';

export const AppShell = () => {
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth <= 768) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="app-shell">
      {isMobile && sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}
      <Sidebar 
        isOpen={sidebarOpen} 
        toggle={() => setSidebarOpen(!sidebarOpen)} 
        closeMobileSidebar={() => setSidebarOpen(false)}
        isMobile={isMobile} 
      />
      <div className={`main-wrapper ${!isMobile && sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <TopNavbar toggleMobileMenu={() => setSidebarOpen(!sidebarOpen)} isMobile={isMobile} />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
