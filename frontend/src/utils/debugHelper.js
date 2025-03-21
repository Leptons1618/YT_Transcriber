// Debug helper functions

// Global debug flag - set to true to enable all debug logging
const DEBUG = true;

/**
 * Enhanced console log with timestamp and optional category
 */
export const debugLog = (message, data = null, category = 'DEBUG') => {
  if (!DEBUG) return;
  
  const timestamp = new Date().toISOString().substring(11, 23); // HH:MM:SS.mmm
  const prefix = `[${timestamp}][${category}]`;
  
  if (data !== null) {
    console.log(prefix, message, data);
  } else {
    console.log(prefix, message);
  }
};

/**
 * Test the authentication status
 */
export const debugAuth = async () => {
  if (!DEBUG) return;
  
  try {
    debugLog('Testing authentication status...', null, 'AUTH');
    
    // Check basic auth
    const authResponse = await fetch('http://localhost:5000/api/check_auth', {
      credentials: 'include'
    });
    
    const authData = await authResponse.json();
    debugLog('Authentication status:', authData, 'AUTH');
    
    // Get detailed session info
    const sessionResponse = await fetch('http://localhost:5000/api/debug_session', {
      credentials: 'include'
    });
    
    if (sessionResponse.ok) {
      const sessionData = await sessionResponse.json();
      debugLog('Session details:', sessionData, 'AUTH');
    } else {
      debugLog('Could not get session details', null, 'AUTH');
    }
    
    return authData.authenticated;
  } catch (error) {
    debugLog('Error checking auth:', error, 'AUTH');
    return false;
  }
};

export default { debugLog, debugAuth };
