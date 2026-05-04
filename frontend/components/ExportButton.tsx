'use client';

import { useState } from 'react';
import { Download, Loader2 } from 'lucide-react';
import { exportPdf } from '@/lib/api';

interface ExportButtonProps {
  prescriptionId: string;
}

export default function ExportButton({ prescriptionId }: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    if (isExporting) return;

    setIsExporting(true);
    setError(null);

    try {
      await exportPdf(prescriptionId);
      // Success - the download should have started automatically
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'PDF export failed';
      setError(errorMessage);
      console.error('PDF export failed:', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex flex-col items-end space-y-2">
      <button
        onClick={handleExport}
        disabled={isExporting}
        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isExporting ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Generating PDF...
          </>
        ) : (
          <>
            <Download className="w-4 h-4 mr-2" />
            Download PDF
          </>
        )}
      </button>
      
      {error && (
        <p className="text-xs text-red-600 max-w-xs text-right">
          {error}
        </p>
      )}
      
      {!error && (
        <p className="text-xs text-gray-500 max-w-xs text-right">
          For pharmacy/records
        </p>
      )}
    </div>
  );
}