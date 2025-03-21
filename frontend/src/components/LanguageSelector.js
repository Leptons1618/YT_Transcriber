import React from 'react';
import './LanguageSelector.css';

const LanguageSelector = ({ selectedLanguage, onLanguageChange }) => {
  const languages = [
    { code: '', name: 'Auto Detect', region: null },
    { code: 'en', name: 'English', region: null },
    { code: 'hi', name: 'Hindi', region: 'indic' },
    { code: 'bn', name: 'Bengali', region: 'indic' },
    { code: 'es', name: 'Spanish', region: null },
    { code: 'fr', name: 'French', region: null },
    { code: 'de', name: 'German', region: null },
    { code: 'ja', name: 'Japanese', region: null },
    { code: 'zh', name: 'Chinese', region: null },
    { code: 'ru', name: 'Russian', region: null },
  ];

  // Check if the selected language is one of our specially supported Indic languages
  const isIndicLanguageSelected = selectedLanguage && ['hi', 'bn'].includes(selectedLanguage);

  return (
    <div className="language-selector">
      <label htmlFor="language-select">Video Language:</label>
      <select
        id="language-select"
        value={selectedLanguage}
        onChange={(e) => onLanguageChange(e.target.value)}
      >
        {languages.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.name}
          </option>
        ))}
      </select>
      
      {/* Show the badge for specially supported languages */}
      {isIndicLanguageSelected && (
        <span className="indic-badge">Enhanced Support</span>
      )}
    </div>
  );
};

export default LanguageSelector;
