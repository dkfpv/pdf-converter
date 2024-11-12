const config = {
  API_URL: process.env.NODE_ENV === 'production' 
    ? 'https://pdf-converter-production-xxxx.up.railway.app'  // Remove any trailing slash
    : 'http://localhost:8000'
};

export default config;
