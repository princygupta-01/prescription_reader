'use client';

import { ExtractionResult } from '@/lib/types';
import MedicineTable from './MedicineTable';
import FailureCard from './FailureCard';
import ExportButton from './ExportButton';
import { Calendar, User, UserCheck, Clock } from 'lucide-react';

interface PrescriptionCardProps {
  result: ExtractionResult;
}

export default function PrescriptionCard({ result }: PrescriptionCardProps) {
  const highConfidenceCount = result.medicines.filter(med => med.confidence >= 0.8).length;
  const totalMedicines = result.medicines.length;
  
  const getOcrQualityColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-50';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Failure card if there are extraction failures */}
      {result.extraction_failures.length > 0 && (
        <FailureCard failures={result.extraction_failures} ocr_raw={result.ocr_raw} />
      )}

      {/* Main prescription card */}
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                Digital Prescription Record
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Extracted and validated by AI
              </p>
            </div>
            <ExportButton prescriptionId={result.id} />
          </div>
        </div>

        {/* Patient Information */}
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="text-lg font-medium text-gray-900 mb-4 flex items-center">
            <User className="w-5 h-5 mr-2 text-gray-500" />
            Patient Information
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-500">Patient Name</label>
                <p className="text-base text-gray-900 mt-1">
                  {result.patient_name || '—'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Date</label>
                <p className="text-base text-gray-900 mt-1 flex items-center">
                  <Calendar className="w-4 h-4 mr-2 text-gray-400" />
                  {formatDate(result.date)}
                </p>
              </div>
            </div>
            
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium text-gray-500">Doctor Name</label>
                <p className="text-base text-gray-900 mt-1 flex items-center">
                  <UserCheck className="w-4 h-4 mr-2 text-gray-400" />
                  {result.doctor_name || '—'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Registration No.</label>
                <p className="text-base text-gray-900 mt-1">
                  {result.doctor_reg_no || '—'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Medicines */}
        {result.medicines.length > 0 && (
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Prescribed Medicines ({result.medicines.length})
            </h3>
            <MedicineTable medicines={result.medicines} />
          </div>
        )}

        {/* General Instructions */}
        {result.general_instructions && (
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-lg font-medium text-gray-900 mb-3">
              General Instructions
            </h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-gray-800 leading-relaxed">
                {result.general_instructions}
              </p>
            </div>
          </div>
        )}

        {/* Follow-up Date */}
        {result.followup_date && (
          <div className="px-6 py-4 border-b border-gray-100">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center">
                <Calendar className="w-5 h-5 text-green-600 mr-3" />
                <div>
                  <p className="font-medium text-green-900">Follow-up Appointment</p>
                  <p className="text-green-700 text-sm mt-1">
                    {formatDate(result.followup_date)}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Confidence Summary */}
        <div className="px-6 py-4 bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Extraction Confidence</p>
              <p className="font-medium text-gray-900 mt-1">
                {highConfidenceCount} of {totalMedicines} medicines with high confidence
              </p>
            </div>
            
            <div>
              <p className="text-gray-600">OCR Quality</p>
              <div className="mt-1">
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getOcrQualityColor(result.ocr_confidence)}`}>
                  {Math.round(result.ocr_confidence * 100)}% confidence
                </span>
              </div>
            </div>
            
            <div>
              <p className="text-gray-600">Processing Time</p>
              <p className="font-medium text-gray-900 mt-1 flex items-center">
                <Clock className="w-4 h-4 mr-1 text-gray-400" />
                {(result.processing_time_ms / 1000).toFixed(1)}s
              </p>
            </div>
          </div>
          
          {/* Model Attribution */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              Processed using {result.model_used} • 
              Generated on {new Date().toLocaleDateString('en-IN')} • 
              ID: {result.id.slice(0, 8)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}