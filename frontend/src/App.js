import { useState, useCallback } from 'react';
import { Upload, AlertCircle, FileIcon, Check, Loader2 } from 'lucide-react';

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
    if (!droppedFile) return;

    if (!droppedFile.name.toLowerCase().endsWith('.pdf')) {
      setErrorMessage('Please drop a PDF file');
      return;
    }

    setFile(droppedFile);
  }, []);

  const handleFileInput = useCallback((e) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;
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
      const response = await fetch('http://localhost:8000/api/convert', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Conversion failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name.replace('.pdf', '_print.pdf');
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setFile(null);

    } catch (error) {
      setErrorMessage('Error processing PDF. Please try again.');
    } finally {
      setIsProcessing(false);
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
              onChange={(e) => setMargin(Number(e.target.value))}
              className="w-32 px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`
              relative border-2 border-dashed rounded-xl p-8 text-center
              transition-colors duration-200 ease-in-out
              ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
              ${isProcessing ? 'opacity-50' : 'hover:border-blue-500 hover:bg-blue-50'}
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
            <label htmlFor="fileInput" className="cursor-pointer">
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
                ${isProcessing
                  ? 'bg-blue-400 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600'}
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