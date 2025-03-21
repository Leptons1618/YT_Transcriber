// src/components/Navbar.js
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Navbar.css';
import { FiSun, FiMoon, FiLogOut } from 'react-icons/fi';

const Navbar = ({ theme, setTheme, isAuthenticated, setIsAuthenticated }) => {
  const navigate = useNavigate();
  
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
  };
  
  const handleLogout = async () => {
    try {
      await fetch('http://localhost:5000/api/logout', {
        credentials: 'include'
      });
      setIsAuthenticated(false);
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <Link to={isAuthenticated ? "/" : "/login"}>
            <span className="brand-yt">YouTube</span> Transcriber
          </Link>
        </div>
        
        <div className="navbar-menu">
          {isAuthenticated && (
            <>
              <Link to="/" className="nav-link">Home</Link>
              <Link to="/jobs" className="nav-link">My Jobs</Link>
              <button className="logout-button" onClick={handleLogout} title="Logout">
                <FiLogOut />
              </button>
            </>
          )}
          <button 
            className="theme-toggle" 
            onClick={toggleTheme} 
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <FiSun /> : <FiMoon />}
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;