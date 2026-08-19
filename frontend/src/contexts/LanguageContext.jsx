import React, { createContext, useState, useContext, useEffect } from 'react';
import en from '../locales/en.json';
import ar from '../locales/ar.json';

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('language') || 'ar');
  
  const toggleLanguage = () => {
    setLanguage(prev => prev === 'ar' ? 'en' : 'ar');
  };

  useEffect(() => {
    localStorage.setItem('language', language);
    document.dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language]);

  const t = (key) => {
    const dict = language === 'ar' ? ar : en;
    return dict[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
