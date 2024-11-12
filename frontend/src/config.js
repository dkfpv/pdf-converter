const config = {
  API_URL: process.env.NODE_ENV === 'production' 
    ? 'https://pdf-converter-production-f9b0.up.railway.app/'
    : 'http://localhost:8000'
};

export default config;
