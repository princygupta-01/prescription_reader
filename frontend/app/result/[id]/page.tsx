'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ExtractionResult } from '../../../lib/types';
import { pollResult } from '../../../lib/api';
import PrescriptionCard from '../../../components/PrescriptionCard';
import ProcessingSteps from '../../../components/ProcessingSteps';
import FailureCard from '../../../components/FailureCard';

export default function ResultPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;
  
  const [status, setStatus] = useState<'loading' | 'processing' | 'done' | 'failed'>('loading');
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>('preprocessing');
  const [progress, setProgress] = useState<number>(0);

  useEffect(() => {
    if (!taskId) return;

    const pollInterval = setInterval(async () => {
      try {
        const response = await pollResult(taskId);
        
        setStatus(response.status as any);
        
        if (response.stage) {
          setCurrentStage(response.stage);
        }
        
        if (response.progress !== undefined) {
          setProgress(response.progress);
        }
        
        if (response.status === 'done' && response.result) {
          setResult(response.result);
          clearInterval(pollInterval);
        } else if (response.status === 'failed') {
          setError(response.error || 'Processing failed');
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Polling error:', err);
        setError('Failed to get result');
        setStatus('failed');
        clearInterval(pollInterval);
      }
    }, 1500);

    return () => clearInterval(pollInterval);
  }, [taskId]);

  const handleTryAnother = () => {
    router.push('/');
  };

  if (status === 'loading' || status === 'processing') {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-2xl shadow-sm p-8">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Processing Your Prescription
              </h1>
              <p className="text-gray-600">
                Our AI is reading and structuring your prescription...
              </p>
            </div>
            
            <ProcessingSteps 
              currentStage={currentStage}
              progress={progress}
            />
            
            <div className="mt-8 text-center">
              <p className="text-sm text-gray-500">
                This usually takes 10-15 seconds
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-2xl shadow-sm p-8">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                Processing Failed
              </h1>
              <p className="text-gray-600 mb-6">
                {error || 'We couldn\'t process your prescription. Please try again with a clearer image.'}
              </p>
              
              <button
                onClick={handleTryAnother}
                className="bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 transition-colors"
              >
                Try Another Prescription
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'done' && result) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6">
            <button
              onClick={handleTryAnother}
              className="flex items-center text-blue-600 hover:text-blue-700 font-medium"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Analyze Another Prescription
            </button>
          </div>
          

          
          <PrescriptionCard result={result} />
        </div>
      </div>
    );
  }

  return null;
}