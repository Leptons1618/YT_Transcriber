/**
 * Utility to debug session state and authentication issues
 */

export const checkAuthAndSession = async () => {
  console.group('Session Debug Info');
  
  try {
    // Check authentication status
    const authResponse = await fetch('http://localhost:5000/api/check_auth', {
      credentials: 'include'
    });
    
    const authData = await authResponse.json();
    console.log('Authentication Status:', authResponse.status, authData);
    
    // Check cookies
    console.log('Cookies:', document.cookie);
    
    // Check localStorage
    console.log('localStorage:', {
      theme: localStorage.getItem('theme')
      // Add other relevant items
    });
    
    return authData.authenticated;
  } catch (error) {
    console.error('Debug Error:', error);
    return false;
  } finally {
    console.groupEnd();
  }
};

// Call this function in the browser console to debug:
// import('/src/utils/debugSession.js').then(m => m.checkAuthAndSession())
