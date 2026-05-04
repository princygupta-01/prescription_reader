'use client';

import { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react';

interface FailureCardProps {
  failures: string[];
  ocr_raw?: string;
}

export default function FailureCard({ failures, ocr_raw }: FailureCardProps) {
  const [showOcrText, setShowOcrText] = useState(false);

  if (failures.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
      <div className="flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-amber-800 mb-2">
            Some fields could not be extracted
          </h3>
          
          <div className="space-y-1 mb-3">
            {failures.map((failure, index) => (
              <p key={index} className="text-sm text-amber-700">
                • {failure}
              </p>
            ))}
          </div>
          
          <p className="text-xs text-amber-600 mb-3">
            The AI model read the prescription but could not structure some information clearly. 
            You can review the raw text below and correct manually if needed.
          </p>
          
          {ocr_raw && (
            <div className="border-t border-amber-200 pt-3">
              <button
                onClick={() => setShowOcrText(!showOcrText)}
                className="flex items-center space-x-2 text-sm font-medium text-amber-800 hover:text-amber-900 focus:outline-none"
              >
                {showOcrText ? (
                  <>
                    <EyeOff className="w-4 h-4" />
                    <span>Hide raw OCR text</span>
                    <ChevronUp className="w-4 h-4" />
                  </>
                ) : (
                  <>
                    <Eye className="w-4 h-4" />
                    <span>View raw OCR text</span>
                    <ChevronDown className="w-4 h-4" />
                  </>
                )}
              </button>
              
              {showOcrText && (
                <div className="mt-3 p-3 bg-white border border-amber-200 rounded text-sm">
                  <p className="text-xs text-gray-500 mb-2 font-medium">
                    Raw text extracted by OCR:
                  </p>
                  <div className="text-gray-800 whitespace-pre-wrap font-mono text-xs leading-relaxed max-h-40 overflow-y-auto">
                    {ocr_raw || 'No OCR text available'}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}