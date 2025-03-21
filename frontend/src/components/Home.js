import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Home.css';
import { FiSettings } from 'react-icons/fi';
import { FaFileAlt, FaChartBar, FaClock, FaSave } from 'react-icons/fa';
import { debugLog, debugAuth } from '../utils/debugHelper';

const Home = () => {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // State for configuration modal and selections
  const [showConfig, setShowConfig] = useState(false);
  const [modelType, setModelType] = useState('whisper');
  const [modelSize, setModelSize] = useState('medium');
  // Set status initially to "no model loaded"
  const [modelLoadStatus, setModelLoadStatus] = useState("no model loaded");
  // Add new state for summarizer model
  const [summarizerModel, setSummarizerModel] = useState('bart-large-cnn');
  const [availableSummarizers, setAvailableSummarizers] = useState({});
  const [summarizerStatus, setSummarizerStatus] = useState("no summarizer loaded");
  const [language, setLanguage] = useState(''); // '' means auto-detect
  const [successMessage, setSuccessMessage] = useState('');

  // Enhanced useEffect to fetch model status and configuration on startup
  useEffect(() => {
    fetch('http://localhost:5000/api/config')
      .then(res => res.json())
      .then(data => {
        // Update model status
        setModelLoadStatus(data.model_status || "no model loaded");
        setSummarizerStatus(data.summarizer_status || "no summarizer loaded");
        
        // Update model type and size from server configuration
        if (data.model_type) {
          setModelType(data.model_type);
        }
        if (data.model_size) {
          setModelSize(data.model_size);
        }
        if (data.summarizer_model) {
          setSummarizerModel(data.summarizer_model);
        }
        
        // Store available summarizers
        if (data.available_summarizers) {
          setAvailableSummarizers(data.available_summarizers);
        }
        
        console.log("Loaded model configuration:", data.model_type, data.model_size, data.summarizer_model);
      })
      .catch(err => console.error("Error loading configuration:", err));
  }, []);

  // Add auth debug on component mount
  useEffect(() => {
    debugLog('Home component mounted');
    debugAuth();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Simplified error logging without localStorage
    const logError = (message, details) => {
      console.error("TRANSCRIPTION ERROR:", { message, details });
      setError(`Error: ${message}`);
    };
    
    if (!youtubeUrl) {
      setError('Please enter a YouTube URL');
      return;
    }
    
    // Simple URL validation
    if (!youtubeUrl.includes('youtube.com/') && !youtubeUrl.includes('youtu.be/')) {
      setError('Please enter a valid YouTube URL');
      return;
    }
    
    // Make sure a model is loaded before submitting
    if (modelLoadStatus !== "loaded") {
      setError("Please load a model first before transcribing");
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      console.log("Sending transcription request with:", {
        youtube_url: youtubeUrl,
        model_type: modelType,
        model_size: modelSize,
        language: language
      });
      
      const response = await fetch('http://localhost:5000/api/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          youtube_url: youtubeUrl,
          model_type: modelType,
          model_size: modelSize,
          language: language
        }),
        credentials: 'include' // Include credentials for auth
      });
      
      console.log("Transcription response status:", response.status);
      
      // Handle unauthorized response specifically
      if (response.status === 401) {
        logError('Authentication error', { status: 401 });
        setError('Your session has expired. Please log in again.');
        setTimeout(() => navigate('/login'), 2000);
        return;
      }
      
      // Get response text first
      const responseText = await response.text();
      console.log("Raw response:", responseText);
      
      let data;
      
      // Try to parse as JSON, but keep the original text if it fails
      try {
        data = JSON.parse(responseText);
        console.log("Transcription response data:", data);
      } catch (parseError) {
        logError('Failed to parse server response', { responseText, parseError: parseError.message });
        throw new Error(`Server returned invalid JSON: ${responseText.substring(0, 100)}...`);
      }
      
      if (response.ok) {
        // Navigate to view page when successful
        navigate(`/job/${data.job_id}`);
      } else {
        logError(data.error || 'Failed to submit transcription request', data);
        setError(data.error || 'Failed to submit transcription request');
      }
    } catch (err) {
      logError('Error connecting to server', { message: err.message, stack: err.stack });
      setError(`Error connecting to server: ${err.message}`);
      console.error("Full error:", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Add useEffect for language-based model recommendation
  useEffect(() => {
    // When language changes, recommend appropriate summarizer model
    if (['hi', 'bn'].includes(language)) {
      // Get the specialized model for this language
      const recommendedModel = language === 'hi' ? 'ai4bharat/IndicBART' : 'google/mt5-base';
      
      // Check if the model is available in our options
      if (availableSummarizers[recommendedModel]) {
        // Show a recommendation notification
        const confirmed = window.confirm(
          `You've selected ${language === 'hi' ? 'Hindi' : 'Bengali'}. Would you like to use the specialized ${
            recommendedModel.split('/')[1]
          } summarization model for better results?`
        );
        
        if (confirmed) {
          setSummarizerModel(recommendedModel);
        }
      }
    }
  }, [language, availableSummarizers]);

  // Updated saveConfig function: close popup immediately, show loading animation,
  // then update status to loaded on success.
  const saveConfig = async () => {
    setShowConfig(false);
    setModelLoadStatus("loading");
    try {
      const response = await fetch('http://localhost:5000/api/load_model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          model_type: modelType, 
          model_size: modelSize,
          summarizer_model: summarizerModel 
        }),
        credentials: 'include'  // Add credentials to the request
      });
      
      // Handle unauthorized response
      if (response.status === 401) {
        console.log("Authentication failed. Redirecting to login...");
        setError('Your session has expired. Please log in again.');
        setTimeout(() => navigate('/login'), 2000);
        setModelLoadStatus("no model loaded");
        return;
      }
      
      const data = await response.json();
      if (response.ok) {
        console.log(data.message);
        setModelLoadStatus("loaded");
        setSummarizerStatus("loaded");
        setSuccessMessage(data.message || 'Model loaded successfully');
        setTimeout(() => setSuccessMessage(''), 5000); // Clear after 5 seconds
      } else {
        setModelLoadStatus("no model loaded");
        setError(data.error || 'Failed to load model configuration');
      }
    } catch (err) {
      console.error("Error in saveConfig:", err);
      setModelLoadStatus("no model loaded");
      setError(err.message || 'Error connecting to server');
    }
  };

  // Enhance the renderModelStatus function to show current model details
  const renderModelStatus = () => {
    if (modelLoadStatus === "loading") {
      return (
        <div className="model-status-container">
          <div className="spinner-container">
            <div className="status-spinner"></div>
          </div>
          <span className="status-text">Loading model: {modelType} ({modelSize})</span>
        </div>
      );
    } else if (modelLoadStatus === "loaded") {
      return (
        <div className="model-status-container">
          <div className="status-icon-success">✓</div>
          <span className="status-text">
            <span className="model-name">{modelType}</span> 
            <span className="model-size">({modelSize})</span>
            {summarizerStatus === "loaded" && (
              <span className="summarizer-info"> + {summarizerModel} summarizer</span>
            )}
            <button 
              onClick={() => setShowConfig(true)}
              className="change-model-btn"
              title="Change model"
            >
              Change
            </button>
          </span>
        </div>
      );
    } else if (modelLoadStatus === "no model loaded") {
      return (
        <div className="model-status-container">
          <div className="status-icon-warning">!</div>
          <span className="status-text">No model loaded. Click <span role="img" aria-label="settings">⚙️</span> to configure.</span>
        </div>
      );
    }
  };

  // New helper to validate YouTube URLs with improved pattern
  const isValidYoutubeUrl = (url) => {
    if (!url || url.trim() === '') return false;
    
    // More comprehensive regex to handle various YouTube URL formats
    const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|v\/|embed\/|shorts\/)|youtu\.be\/)/;
    return pattern.test(url.trim());
  };

  // Add an authentication check function
  // eslint-disable-next-line no-unused-vars
  const checkAuthentication = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/check_auth', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.authenticated;
      }
      return false;
    } catch (error) {
      console.error('Auth check error:', error);
      return false;
    }
  };
  
  // Fetch config when component mounts
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await fetch('http://localhost:5000/api/config', {
          credentials: 'include'
        });
        
        if (response.ok) {
          const config = await response.json();
          setModelType(config.model_type || 'faster-whisper');
          setModelSize(config.model_size || 'base');
          setSummarizerModel(config.summarizer_model || 'bart-large-cnn');
        } else {
          // Handle non-OK response
          if (response.status === 401) {
            // Unauthorized - redirect to login
            navigate('/login');
          } else {
            console.error('Error fetching config:', response.statusText);
          }
        }
      } catch (error) {
        console.error('Failed to fetch config:', error);
      }
    };

    fetchConfig();
  }, [navigate]);

  return (
    <div className="home-container">
      <div className="hero-section">
        <h1 style={{ fontSize: '2rem' }}>YouTube Transcriber Pro</h1>
        <p style={{ fontSize: '1rem' }} className="subtitle">
          Transcribe, analyze, and take notes from any YouTube video
        </p>

        <form onSubmit={handleSubmit} className="url-form">
          <div className="input-group">
            <input
              type="text"
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="Paste YouTube URL here..."
              className="url-input"
              disabled={isSubmitting || modelLoadStatus !== "loaded"}
            />
            <button
              type="submit"
              className="submit-button"
              disabled={isSubmitting || modelLoadStatus !== "loaded" || !isValidYoutubeUrl(youtubeUrl)}
            >
              {isSubmitting ? 'Processing...' : 'Transcribe'}
            </button>
            {/* Replace cog gif with FiSettings icon */}
            <button 
              type="button" 
              className="config-button" 
              onClick={() => setShowConfig(true)}
              disabled={isSubmitting}
              title="Configure Model"
              style={{ marginLeft: '8px', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              <FiSettings className="config-icon" size={24} />
            </button>
          </div>
          {error && (
            <p className="error-message">{error}</p>
          )}
        </form>

        {/* Display loading/loaded model status */}
        {renderModelStatus()}
      </div>

      <div className="features-section">
        <h2 style={{ fontSize: '1.5rem' }}>Advanced Features</h2>
        <div className="features-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          <div className="feature-card">
            {/* Replace emoji with icon */}
            <div className="feature-icon"><FaFileAlt /></div>
            <h3 style={{ fontSize: '1.1rem' }}>Accurate Transcription</h3>
            <p>Powered by OpenAI's Whisper, our system delivers high-quality transcriptions</p>
          </div>
          <div className="feature-card">
            {/* Replace emoji with icon */}
            <div className="feature-icon"><FaChartBar /></div>
            <h3 style={{ fontSize: '1.1rem' }}>Smart Notes</h3>
            <p>AI-generated notes that capture key points and summarize content</p>
          </div>
          <div className="feature-card">
            {/* Replace emoji with icon */}
            <div className="feature-icon"><FaClock /></div>
            <h3 style={{ fontSize: '1.1rem' }}>Time-Stamped</h3>
            <p>Navigate through transcripts with precise time markers</p>
          </div>
          <div className="feature-card">
            {/* Replace emoji with icon */}
            <div className="feature-icon"><FaSave /></div>
            <h3 style={{ fontSize: '1.1rem' }}>Save & Export</h3>
            <p>Download transcripts and notes in multiple formats</p>
          </div>
          {/* New Multilingual Support Card */}
          <div className="feature-card multilingual-card">
            <div className="feature-icon">
              <span role="img" aria-label="Globe">🌐</span>
            </div>
            <h3 style={{ fontSize: '1.1rem' }}>Multilingual Support</h3>
            <p>Enhanced support for Hindi and Bengali with specialized AI models</p>
          </div>
        </div>
      </div>

      {/* About Section - remove the backgroundColor from inline styles */}
      <div
        className="about-section"
        style={{
          padding: '20px',
          textAlign: 'center',
          borderRadius: '12px',
          marginTop: '20px',
          fontSize: '0.8rem' // Reduced overall font size for the about section
        }}
      >
        <h2 style={{ fontSize: '1.1rem' }}>About</h2>
        <p>YT Transcriber Pro is developed by Lept0n5.</p>
        <div
          className="social-links"
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: '20px',
            fontSize: '0.9rem' // Reduced social links font size
          }}
        >
          <a
            href="https://www.linkedin.com/in/anish-giri-a4031723a/"
            target="_blank"
            rel="noopener noreferrer"
          >
            LinkedIn
          </a>
          <a
            href="https://github.com/Leptons1618"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          <a href="mailto:anishgiri163@gmail.com">Email Me</a>
        </div>
      </div>

      {/* Configuration Modal */}
      {showConfig && (
        <div className="config-modal" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0,0,0,0.6)', // darker overlay
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="config-modal-content" style={{
            background: 'white',
            padding: '30px',
            borderRadius: '12px',
            width: '550px',  // Increased from 520px for more horizontal space
            maxHeight: '90vh',  // Increased from 85vh to 90vh for more vertical space
            overflow: 'auto',  // Added scrolling if needed
            boxShadow: '0 8px 24px rgba(0,0,0,0.2)', // Enhanced shadow
            textAlign: 'center'
          }}>
            <h2 style={{ fontSize: '1.3rem', marginBottom: '20px' }}>Model Configuration</h2>
            
            {/* Add a consistent container for all config options */}
            <div className="config-options">
              {/* Model type selection */}
              <div className="config-option">
                <label>Model Type:</label>
                <select 
                  value={modelType} 
                  onChange={(e) => {
                    setModelType(e.target.value);
                    // Don't reset size if same model type or if there's a compatible size
                    if (e.target.value !== modelType) {
                      setModelSize("tiny"); // Reset size only on model type change
                    }
                  }}
                >
                  <option value="whisper">Whisper</option>
                  <option value="faster-whisper">Faster-Whisper</option>
                </select>
              </div>

              {/* Model size selection */}
              <div className="config-option">
                <label>Model Size:</label>
                <select 
                  value={modelSize} 
                  onChange={(e) => setModelSize(e.target.value)}
                >
                  {modelType === 'faster-whisper' ? (
                    <>
                      <option value="tiny">tiny</option>
                      <option value="base">base</option>
                      <option value="small">small</option>
                      <option value="medium">medium</option>
                      <option value="large">large</option>
                      <option value="turbo">turbo</option>
                    </>
                  ) : (
                    <>
                      <option value="tiny">tiny</option>
                      <option value="base">base</option>
                      <option value="small">small</option>
                      <option value="medium">medium</option>
                      <option value="turbo">turbo</option>
                    </>
                  )}
                </select>
              </div>

              {/* Language selection - MOVED FROM OUTSIDE THE MODAL */}
              <div className="config-option">
                <label>Language:</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className={['hi', 'bn'].includes(language) ? 'specialized-language' : ''}
                >
                  <option value="">Auto Detect</option>
                  <option value="en">English</option>
                  <option value="hi" className="specialized-option">Hindi ★</option>
                  <option value="bn" className="specialized-option">Bengali ★</option>
                  <option value="es">Spanish</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="ja">Japanese</option>
                  <option value="zh">Chinese</option>
                  <option value="ru">Russian</option>
                </select>
              </div>

              {/* Summarizer model selection */}
              <div className="config-option">
                <label>Summarizer:</label>
                <select 
                  value={summarizerModel} 
                  onChange={(e) => setSummarizerModel(e.target.value)}
                >
                  {Object.keys(availableSummarizers).map(key => (
                    <option key={key} value={key} className={
                      // Highlight specialized models for current language
                      (language === 'hi' && availableSummarizers[key].languages?.includes('hi')) ||
                      (language === 'bn' && availableSummarizers[key].languages?.includes('bn'))
                        ? 'specialized-option'
                        : ''
                    }>
                      {key.includes('/') ? key.split('/')[1] : key} 
                      {availableSummarizers[key].languages?.includes(language) && ' ★'}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Summarizer model info */}
            {availableSummarizers[summarizerModel] && (
              <div className="model-info">
                {availableSummarizers[summarizerModel].description}
                {availableSummarizers[summarizerModel].languages?.includes(language) && (
                  <div className="language-match">
                    <span role="img" aria-label="Star">⭐</span> Optimized for {language === 'hi' ? 'Hindi' : 'Bengali'}
                  </div>
                )}
              </div>
            )}

            {/* Model comparison table */}
            <div style={{ marginTop: '20px' }}>
              <h3 style={{ fontSize: '1rem' }}>Model Comparison</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem', marginTop: '10px' }}>
                <thead>
                  <tr>
                    <th style={{ borderBottom: '1px solid #ddd', padding: '4px' }}>Size</th>
                    <th style={{ borderBottom: '1px solid #ddd', padding: '4px' }}>Params</th>
                    <th style={{ borderBottom: '1px solid #ddd', padding: '4px' }}>VRAM</th>
                    <th style={{ borderBottom: '1px solid #ddd', padding: '4px' }}>Speed</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ padding: '4px' }}>tiny</td>
                    <td style={{ padding: '4px' }}>39M</td>
                    <td style={{ padding: '4px' }}>~1GB</td>
                    <td style={{ padding: '4px' }}>~10x</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '4px' }}>base</td>
                    <td style={{ padding: '4px' }}>74M</td>
                    <td style={{ padding: '4px' }}>~1GB</td>
                    <td style={{ padding: '4px' }}>~7x</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '4px' }}>small</td>
                    <td style={{ padding: '4px' }}>244M</td>
                    <td style={{ padding: '4px' }}>~2GB</td>
                    <td style={{ padding: '4px' }}>~4x</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '4px' }}>medium</td>
                    <td style={{ padding: '4px' }}>769M</td>
                    <td style={{ padding: '4px' }}>~5GB</td>
                    <td style={{ padding: '4px' }}>~2x</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '4px' }}>turbo</td>
                    <td style={{ padding: '4px' }}>809M</td>
                    <td style={{ padding: '4px' }}>~6GB</td>
                    <td style={{ padding: '4px' }}>~8x</td>
                  </tr>
                  {modelType === 'faster-whisper' && (
                    <tr>
                      <td style={{ padding: '4px' }}>large</td>
                      <td style={{ padding: '4px' }}>1550M</td>
                      <td style={{ padding: '4px' }}>~10GB</td>
                      <td style={{ padding: '4px' }}>~1x</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
              <button 
                onClick={saveConfig}
                className="config-save-button"
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#4f46e5',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                Save Configuration
              </button>
              <button 
                onClick={() => setShowConfig(false)}
                className="config-close-button"
                style={{
                  padding: '10px 20px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.9rem'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success, error, and loading messages */}
      {successMessage && (
        <div className="success-message">
          {successMessage}
        </div>
      )}
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
};

export default Home;