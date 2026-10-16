import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import './layout.css';

export const AppShell = () => {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth <= 768;
    }
    return false;
  });
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth > 768;
    }
    return true;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(max-width: 768px)');
    const handleMediaChange = (e) => {
      const mobile = e.matches;
      setIsMobile(mobile);
      if (mobile) {
        setSidebarOpen(false);
      } else {
        setSidebarOpen(true);
      }
    };

    // Set initial values
    setIsMobile(mediaQuery.matches);
    setSidebarOpen(!mediaQuery.matches);

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleMediaChange);
      return () => mediaQuery.removeEventListener('change', handleMediaChange);
    } else {
      mediaQuery.addListener(handleMediaChange);
      return () => mediaQuery.removeListener(handleMediaChange);
    }
  }, []);

  return (
    <div className="app-shell">
      {isMobile && sidebarOpen && (
        <div 
          className="sidebar-overlay" 
          onClick={() => setSidebarOpen(false)} 
          aria-hidden="true"
        />
      )}
      <Sidebar 
        isOpen={sidebarOpen} 
        toggle={() => setSidebarOpen(!sidebarOpen)} 
        closeMobileSidebar={() => setSidebarOpen(false)}
        isMobile={isMobile} 
      />
      <div className={`main-wrapper ${isMobile ? 'mobile-wrapper' : (sidebarOpen ? 'sidebar-open' : 'sidebar-closed')}`}>
        <TopNavbar 
          toggleMobileMenu={() => setSidebarOpen(!sidebarOpen)} 
          isMobile={isMobile} 
        />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
