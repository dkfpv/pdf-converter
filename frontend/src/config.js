const config = {
  API_URL: process.env.NODE_ENV === 'production' 
    ? 'https://pdf-label-converter.onrender.com'
    : 'http://localhost:8000'
};

export default config;
