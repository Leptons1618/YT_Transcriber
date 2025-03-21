import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';

// Import existing components
import Home from './components/Home';
import Navbar from './components/Navbar';
import TranscriptionView from './components/TranscriptionView';
import JobsList from './components/JobsList';

// Import new authentication components
import Login from './components/Login';
import Register from './components/Register';

function App() {
  // Get theme from localStorage and use 'light' as fallback
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  // Apply theme to document body
  useEffect(() => {
    document.body.className = theme;
  }, [theme]);
  
  // Check if user is already authenticated
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // First try the check_auth endpoint which doesn't require authentication
        const checkResponse = await fetch('http://localhost:5000/api/check_auth', {
          credentials: 'include'
        });
        
        if (checkResponse.ok) {
          const checkData = await checkResponse.json();
          
          if (checkData.authenticated) {
            setIsAuthenticated(true);
            setIsLoading(false);
            return;
          }
        }
        
        // If we get here, we're not authenticated
        setIsAuthenticated(false);
      } catch (error) {
        console.error('Authentication check failed:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    checkAuth();
  }, []);

  if (isLoading) {
    return (
      <div className="App">
        <div className="loading">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }
  
  return (
    <BrowserRouter>
      <div className={`App ${theme}`}>
        <Navbar 
          theme={theme} 
          setTheme={setTheme} 
          isAuthenticated={isAuthenticated} 
          setIsAuthenticated={setIsAuthenticated}
        />
        <div className="content">
          <Routes>
            <Route path="/login" element={
              isAuthenticated ? <Navigate to="/" replace /> : <Login setIsAuthenticated={setIsAuthenticated} />
            } />
            
            <Route path="/register" element={
              <Register />
            } />
            
            <Route path="/" element={
              isAuthenticated ? <Home /> : <Navigate to="/login" replace />
            } />
            
            <Route path="/job/:jobId" element={
              isAuthenticated ? <TranscriptionView /> : <Navigate to="/login" replace />
            } />
            
            <Route path="/jobs" element={
              isAuthenticated ? <JobsList /> : <Navigate to="/login" replace />
            } />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;