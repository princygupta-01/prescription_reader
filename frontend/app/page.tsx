'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { uploadPrescription } from '@/lib/api';
import UploadZone from '@/components/UploadZone';
import { Loader2, AlertCircle } from 'lucide-react';

export default function Home() {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadPrescription(selectedFile);
      if (response.task_id) {
        // Navigate to the result page which handles polling
        router.push(`/result/${response.task_id}`);
      } else {
        throw new Error('No task ID received from server');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Failed to upload prescription');
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Digitize Handwritten Prescriptions
          </h1>
          <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
            Upload a photo of any handwritten doctor's prescription. Our AI will read it, 
            structure the data, and validate the medicines instantly.
          </p>
        </div>

        <div className="mt-8">
          <UploadZone 
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            onUpload={handleUpload}
            disabled={isUploading}
          />
        </div>

        {isUploading && (
          <div className="max-w-md mx-auto bg-white p-6 rounded-2xl shadow-sm border border-gray-200 text-center mt-4">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">Uploading Prescription</h3>
            <p className="text-sm text-gray-500 mt-2">
              Please wait while we upload your image...
            </p>
          </div>
        )}

        {error && (
          <div className="max-w-md mx-auto bg-red-50 p-4 rounded-xl border border-red-200 flex items-start space-x-3 mt-4">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-medium text-red-800">Upload Failed</h4>
              <p className="text-sm text-red-700 mt-1">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-sm text-red-600 font-medium hover:text-red-800 mt-2"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        <div className="max-w-3xl mx-auto mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-center px-4">
          <div>
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-blue-600 font-bold text-xl">1</span>
            </div>
            <h3 className="font-medium text-gray-900 mb-2">Upload Photo</h3>
            <p className="text-sm text-gray-500">Take a clear photo of the prescription or upload an existing one.</p>
          </div>
          <div>
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-blue-600 font-bold text-xl">2</span>
            </div>
            <h3 className="font-medium text-gray-900 mb-2">AI Processing</h3>
            <p className="text-sm text-gray-500">Our TrOCR model reads the handwriting while Llama 3.2 structures it.</p>
          </div>
          <div>
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <span className="text-blue-600 font-bold text-xl">3</span>
            </div>
            <h3 className="font-medium text-gray-900 mb-2">Get Results</h3>
            <p className="text-sm text-gray-500">Review the validated medicines and download a clean PDF record.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
