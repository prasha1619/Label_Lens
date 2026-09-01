import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  MinusCircle, 
  AlertOctagon 
} from 'lucide-react';
import { CheckStatus, OverallStatus } from '../../types/inspection';

interface StatusBadgeProps {
  status: CheckStatus | OverallStatus | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  status, 
  size = 'md', 
  showIcon = true 
}) => {
  const normStatus = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
  let Icon = HelpCircle;
  let label = normStatus.replace(/_/g, ' ');

  switch (normStatus) {
    case 'PASS':
    case 'COMPLIANT':
      colorClasses = 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      Icon = CheckCircle2;
      break;
    case 'FAIL':
    case 'NON_COMPLIANT':
      colorClasses = 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      Icon = XCircle;
      break;
    case 'WARNING':
    case 'NEEDS_REVIEW':
      colorClasses = 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      Icon = AlertTriangle;
      break;
    case 'NOT_DETECTED':
      colorClasses = 'bg-red-500/10 text-red-300 border-red-500/20';
      Icon = AlertOctagon;
      label = 'NOT DETECTED';
      break;
    case 'UNCERTAIN':
      colorClasses = 'bg-yellow-500/10 text-yellow-300 border-yellow-500/20';
      Icon = AlertTriangle;
      break;
    case 'UNABLE_TO_VERIFY':
      colorClasses = 'bg-slate-700/40 text-slate-300 border-slate-600/40';
      Icon = HelpCircle;
      label = 'UNABLE TO VERIFY';
      break;
    case 'NOT_APPLICABLE':
      colorClasses = 'bg-slate-800 text-slate-400 border-slate-700';
      Icon = MinusCircle;
      label = 'N/A';
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[11px] font-medium space-x-1',
    md: 'px-2.5 py-1 text-xs font-semibold space-x-1.5',
    lg: 'px-3.5 py-1.5 text-sm font-bold space-x-2'
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4'
  }[size];

  return (
    <span className={`inline-flex items-center rounded-md border font-mono uppercase tracking-wider ${colorClasses} ${sizeClasses}`}>
      {showIcon && <Icon className={iconSizes} />}
      <span>{label}</span>
    </span>
  );
};
