'use client';

import { useEffect, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { PROCESSING_STAGES, ProcessingStage } from '@/lib/types';

interface ProcessingStepsProps {
  currentStage: string;
  progress: number;
}

export default function ProcessingSteps({ currentStage, progress }: ProcessingStepsProps) {
  const [elapsedTime, setElapsedTime] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const getCurrentStageIndex = () => {
    return PROCESSING_STAGES.findIndex(stage => stage.name === currentStage);
  };

  const getStageStatus = (index: number) => {
    const currentIndex = getCurrentStageIndex();
    
    if (currentIndex === -1) return 'pending';
    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'active';
    return 'pending';
  };

  const getEstimatedTimeRemaining = () => {
    const currentIndex = getCurrentStageIndex();
    if (currentIndex === -1) return 0;
    
    let remaining = 0;
    for (let i = currentIndex; i < PROCESSING_STAGES.length; i++) {
      remaining += PROCESSING_STAGES[i].estimatedTime;
    }
    
    // Adjust based on current progress within stage
    if (currentIndex >= 0) {
      const currentStageTime = PROCESSING_STAGES[currentIndex].estimatedTime;
      const stageProgress = Math.max(0, Math.min(1, (progress - currentIndex / PROCESSING_STAGES.length) * PROCESSING_STAGES.length));
      remaining -= currentStageTime * stageProgress;
    }
    
    return Math.max(0, Math.ceil(remaining));
  };

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-gray-200 p-6">
      <div className="text-center mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          Processing Prescription
        </h3>
        <div className="flex items-center justify-center space-x-4 text-sm text-gray-500">
          <span>Elapsed: {formatTime(elapsedTime)}</span>
          <span>•</span>
          <span>Est. remaining: {formatTime(getEstimatedTimeRemaining())}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs text-gray-500 mb-2">
          <span>Progress</span>
          <span>{Math.round(progress * 100)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      </div>

      {/* Processing stages */}
      <div className="space-y-4">
        {PROCESSING_STAGES.map((stage, index) => {
          const status = getStageStatus(index);
          
          return (
            <div key={stage.name} className="flex items-center space-x-3">
              <div className={`
                flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                ${status === 'completed' 
                  ? 'bg-green-100 text-green-600' 
                  : status === 'active'
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-gray-100 text-gray-400'
                }
              `}>
                {status === 'completed' ? (
                  <Check className="w-4 h-4" />
                ) : status === 'active' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <div className="w-2 h-2 bg-current rounded-full" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <p className={`
                  text-sm font-medium
                  ${status === 'active' 
                    ? 'text-blue-900' 
                    : status === 'completed'
                    ? 'text-green-900'
                    : 'text-gray-500'
                  }
                `}>
                  {stage.label}
                </p>
                <p className="text-xs text-gray-400">
                  ~{stage.estimatedTime}s
                  {status === 'active' && ' (in progress)'}
                  {status === 'completed' && ' (done)'}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Current stage details */}
      {currentStage && (
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
            <span className="text-sm font-medium text-blue-900">
              {PROCESSING_STAGES.find(s => s.name === currentStage)?.label || 'Processing...'}
            </span>
          </div>
          <p className="text-xs text-blue-700 mt-1">
            Using AI models to analyze your prescription image
          </p>
        </div>
      )}
    </div>
  );
}