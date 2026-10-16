import { useState, useEffect, useCallback } from 'react';

const USER_NAME_KEY = 'documind_user_name';

/**
 * Hook to manage user profile name with localStorage persistence
 * and cross-component reactive synchronization.
 */
export const useUser = () => {
  const [userName, setUserNameState] = useState(() => {
    try {
      return localStorage.getItem(USER_NAME_KEY) || '';
    } catch {
      return '';
    }
  });

  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === USER_NAME_KEY) {
        setUserNameState(e.newValue || '');
      }
    };

    const handleCustomChange = (e) => {
      setUserNameState(e.detail || '');
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('documind_user_updated', handleCustomChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('documind_user_updated', handleCustomChange);
    };
  }, []);

  const setUserName = useCallback((name) => {
    const cleanName = (name || '').trim();
    try {
      if (cleanName) {
        localStorage.setItem(USER_NAME_KEY, cleanName);
      } else {
        localStorage.removeItem(USER_NAME_KEY);
      }
    } catch (e) {
      console.warn('LocalStorage access error:', e);
    }
    setUserNameState(cleanName);
    window.dispatchEvent(new CustomEvent('documind_user_updated', { detail: cleanName }));
  }, []);

  const clearUserName = useCallback(() => {
    try {
      localStorage.removeItem(USER_NAME_KEY);
    } catch (e) {
      console.warn('LocalStorage access error:', e);
    }
    setUserNameState('');
    window.dispatchEvent(new CustomEvent('documind_user_updated', { detail: '' }));
  }, []);

  const getGreeting = useCallback(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }, []);

  return {
    userName,
    setUserName,
    clearUserName,
    getGreeting
  };
};
