// Create a global fetch interceptor to handle authentication errors

// Store the original fetch function
const originalFetch = window.fetch;

// Replace the global fetch with our interceptor
window.fetch = async (...args) => {
  // Call the original fetch
  const response = await originalFetch(...args);
  
  // Handle 401 Unauthorized responses
  if (response.status === 401) {
    // Only redirect if this is an API call and not already on the login page
    const url = args[0].toString();
    const isApiCall = url.includes('/api/');
    const isLoginPage = window.location.pathname === '/login';
    
    if (isApiCall && !isLoginPage) {
      console.log('Session expired, redirecting to login');
      // For a smoother experience, you might want to store the current page
      // to redirect back after login
      sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
      
      // Redirect to login page
      window.location.href = '/login';
    }
  }
  
  // Return the response
  return response;
};

export default {};
