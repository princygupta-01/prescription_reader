'use client';

import { MedicineItem } from '@/lib/types';
import { Shield, ShieldCheck, AlertTriangle } from 'lucide-react';

interface MedicineTableProps {
  medicines: MedicineItem[];
}

export default function MedicineTable({ medicines }: MedicineTableProps) {
  const getRowBorderColor = (medicine: MedicineItem) => {
    if (medicine.fda_verified) return 'border-l-green-500';
    if (medicine.india_db_verified) return 'border-l-yellow-500';
    if (medicine.confidence < 0.4) return 'border-l-red-500';
    return 'border-l-gray-200';
  };

  const getRowBackgroundColor = (medicine: MedicineItem) => {
    if (medicine.fda_verified) return 'bg-green-50';
    if (medicine.india_db_verified) return 'bg-yellow-50';
    if (medicine.confidence < 0.4) return 'bg-red-50';
    return 'bg-white';
  };

  const getConfidenceBadgeColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const renderVerificationBadges = (medicine: MedicineItem) => {
    const badges = [];
    
    if (medicine.fda_verified) {
      badges.push(
        <span key="fda" className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <ShieldCheck className="w-3 h-3 mr-1" />
          FDA
        </span>
      );
    }
    
    if (medicine.india_db_verified) {
      badges.push(
        <span key="india" className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          <Shield className="w-3 h-3 mr-1" />
          India DB
        </span>
      );
    }
    
    if (!medicine.fda_verified && !medicine.india_db_verified) {
      badges.push(
        <span key="unverified" className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Unverified
        </span>
      );
    }
    
    return badges;
  };

  const renderCellValue = (value: string | null) => {
    return value ? (
      <span className="text-gray-900">{value}</span>
    ) : (
      <span className="text-gray-400">—</span>
    );
  };

  return (
    <div className="overflow-hidden">
      {/* Desktop Table */}
      <div className="hidden md:block">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Medicine
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Dosage
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Frequency
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Instructions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {medicines.map((medicine, index) => (
                <tr
                  key={index}
                  className={`border-l-4 ${getRowBorderColor(medicine)} ${getRowBackgroundColor(medicine)}`}
                >
                  <td className="px-4 py-4">
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-900">
                          {medicine.name}
                        </span>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getConfidenceBadgeColor(medicine.confidence)}`}>
                          {Math.round(medicine.confidence * 100)}%
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {renderVerificationBadges(medicine)}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm">
                    {renderCellValue(medicine.dosage)}
                  </td>
                  <td className="px-4 py-4 text-sm">
                    {renderCellValue(medicine.frequency)}
                  </td>
                  <td className="px-4 py-4 text-sm">
                    {renderCellValue(medicine.duration)}
                  </td>
                  <td className="px-4 py-4 text-sm">
                    {renderCellValue(medicine.instructions)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-4">
        {medicines.map((medicine, index) => (
          <div
            key={index}
            className={`border-l-4 ${getRowBorderColor(medicine)} ${getRowBackgroundColor(medicine)} rounded-r-lg p-4 border border-gray-200`}
          >
            {/* Medicine name and confidence */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 mb-2">
                  {medicine.name}
                </h4>
                <div className="flex flex-wrap gap-1">
                  {renderVerificationBadges(medicine)}
                </div>
              </div>
              <span className={`ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getConfidenceBadgeColor(medicine.confidence)}`}>
                {Math.round(medicine.confidence * 100)}%
              </span>
            </div>

            {/* Medicine details */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Dosage:</span>
                {renderCellValue(medicine.dosage)}
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Frequency:</span>
                {renderCellValue(medicine.frequency)}
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Duration:</span>
                {renderCellValue(medicine.duration)}
              </div>
              {medicine.instructions && (
                <div className="pt-2 border-t border-gray-200">
                  <span className="text-gray-500 text-xs">Instructions:</span>
                  <p className="text-gray-900 mt-1">{medicine.instructions}</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Legend</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-gray-600">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-green-500 rounded"></div>
            <span>Green border = FDA Verified</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-yellow-500 rounded"></div>
            <span>Yellow border = India DB Verified</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-gray-300 rounded"></div>
            <span>Gray border = Unverified</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-red-500 rounded"></div>
            <span>Red border = Low Confidence (&lt;40%)</span>
          </div>
        </div>
      </div>
    </div>
  );
}