import React from 'react';

interface ConfidenceBarProps {
  confidence: number; // 0.0 to 1.0 or 0 to 100
  showLabel?: boolean;
}

export const ConfidenceBar: React.FC<ConfidenceBarProps> = ({ confidence, showLabel = true }) => {
  const normalized = confidence > 1.0 ? confidence : confidence * 100;
  const pct = Math.min(100, Math.max(0, Math.round(normalized)));

  let colorClass = 'bg-emerald-500';
  let textClass = 'text-emerald-400';

  if (pct < 50) {
    colorClass = 'bg-rose-500';
    textClass = 'text-rose-400';
  } else if (pct < 70) {
    colorClass = 'bg-amber-500';
    textClass = 'text-amber-400';
  }

  return (
    <div className="flex items-center space-x-2">
      <div className="flex-1 w-20 bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span className={`text-xs font-mono font-semibold ${textClass}`}>
          {pct}%
        </span>
      )}
    </div>
  );
};
