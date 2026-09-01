import React from 'react';
import { ShieldCheck, Scale, AlertCircle, HelpCircle } from 'lucide-react';
import { RuleCheckResult } from '../../types/inspection';
import { StatusBadge } from '../common/StatusBadge';

interface ComplianceChecksMatrixProps {
  checks: RuleCheckResult[];
}

export const ComplianceChecksMatrix: React.FC<ComplianceChecksMatrixProps> = ({ checks }) => {
  return (
    <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-5 shadow-xl space-y-4">
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
        <Scale className="w-5 h-5 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-200">Legal Metrology Compliance Rule Analysis</h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {checks.map((check) => (
          <div
            key={check.rule_id}
            className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-xs font-bold text-slate-100">{check.rule_title}</h4>
                <p className="text-[10px] font-mono text-emerald-400/90 mt-0.5">{check.legal_reference}</p>
              </div>
              <StatusBadge status={check.status} size="sm" />
            </div>

            <div className="text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 leading-relaxed">
              <span className="font-semibold text-slate-400">Explanation: </span>
              {check.explanation}
            </div>

            {check.inspector_recommendation && (
              <div className="text-[11px] text-slate-400 flex items-start space-x-1.5 pt-1">
                <span className="font-semibold text-amber-400 shrink-0">Recommendation:</span>
                <span className="italic">{check.inspector_recommendation}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
