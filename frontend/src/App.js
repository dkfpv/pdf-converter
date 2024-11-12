import { useState, useCallback } from 'react';
import { Upload, AlertCircle, FileIcon, Check, Loader2 } from 'lucide-react';
import config from './config';

const App = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [file, setFile] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [margin, setMargin] = useState(-24);

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    setIsDragging(false);
    setErrorMessage('');

    const droppedFile = e.dataTransfer?.files[0];
    if (!droppedFile) {
      setErrorMessage('No file dropped');
      return;
    }

    if (!droppedFile.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Please drop a PDF file');
      return;
    }

    // Check file size (max 10MB)
    if (droppedFile.size > 10 * 1024 * 1024) {
      setErrorMessage('File size must be less than 10MB');
      return;
    }

    setFile(droppedFile);
  }, []);

  const handleFileInput = useCallback((e) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Please select a PDF file');
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setErrorMessage('File size must be less than 10MB');
      return;
    }

    setFile(selectedFile);
    setErrorMessage('');
  }, []);

  const handleSubmit = async () => {
    if (!file || isProcessing) return;

    setIsProcessing(true);
    setErrorMessage('');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('margin_mm', margin.toString());

    try {
      // Ensure clean URL construction
      const baseUrl = config.API_URL.replace(/\/+$/, '');
      const response = await fetch(`${baseUrl}/api/convert`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Conversion failed');
      }

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/pdf')) {
        throw new Error('Invalid response format');
      }

      const blob = await response.blob();
      if (blob.size === 0) {
        throw new Error('Empty response received');
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const fileName = `${file.name.replace('.pdf', '')}_print_${timestamp}.pdf`;

      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();

      // Cleanup
      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }, 100);

      setFile(null);

    } catch (error) {
      console.error('Conversion error:', error);
      setErrorMessage(
        error.message === 'Failed to fetch'
          ? 'Unable to connect to the server. Please try again.'
          : error.message || 'Error processing PDF. Please try again.'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleMarginChange = (e) => {
    const value = Number(e.target.value);
    if (value >= -100 && value <= 100) { // Add reasonable limits
      setMargin(value);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">PDF Label Converter</h1>

          <div className="mb-6 bg-gray-50 p-6 rounded-xl">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Margin (mm):
            </label>
            <input
              type="number"
              value={margin}
              onChange={handleMarginChange}
              min="-100"
              max="100"
              className="w-32 px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-2 text-sm text-gray-500">
              Negative values move right, positive values move left
            </p>
          </div>

          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-xl p-8 text-center
              transition-colors duration-200 ease-in-out
              ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
              ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:border-blue-500 hover:bg-blue-50 cursor-pointer'}
            `}
          >
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileInput}
              className="hidden"
              id="fileInput"
              disabled={isProcessing}
            />
            <label htmlFor="fileInput" className={`cursor-${isProcessing ? 'not-allowed' : 'pointer'}`}>
              <div className="space-y-4">
                {file ? (
                  <div className="flex items-center justify-center space-x-3">
                    <FileIcon className="h-8 w-8 text-blue-500" />
                    <span className="text-gray-700">{file.name}</span>
                  </div>
                ) : (
                  <>
                    <Upload className="h-12 w-12 text-gray-400 mx-auto" />
                    <p className="text-lg font-medium text-gray-700">
                      Drag and drop your PDF here
                    </p>
                    <p className="text-sm text-gray-500">
                      or click to select a file
                    </p>
                    <p className="text-xs text-gray-400 mt-2">
                      Maximum file size: 10MB
                    </p>
                  </>
                )}
              </div>
            </label>
          </div>

          {errorMessage && (
            <div className="mt-4 p-4 bg-red-50 rounded-lg flex items-center text-red-700">
              <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
              <p className="text-sm">{errorMessage}</p>
            </div>
          )}

          {file && !errorMessage && (
            <button
              onClick={handleSubmit}
              disabled={isProcessing}
              className={`
                mt-6 w-full py-3 px-4 rounded-lg text-white font-medium
                flex items-center justify-center space-x-2
                transition-colors duration-200
                ${isProcessing
                  ? 'bg-blue-400 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 active:bg-blue-700'}
              `}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Check className="h-5 w-5" />
                  <span>Convert PDF</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;