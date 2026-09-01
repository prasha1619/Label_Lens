import React from 'react';
import { AlertOctagon, ArrowRight, ShieldAlert } from 'lucide-react';
import { ViolationSummary } from '../../types/inspection';

interface ViolationsCardProps {
  violations: ViolationSummary[];
}

export const ViolationsCard: React.FC<ViolationsCardProps> = ({ violations }) => {
  if (!violations || violations.length === 0) {
    return (
      <div className="rounded-2xl bg-emerald-500/5 border border-emerald-500/20 p-5 flex items-center space-x-3">
        <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-emerald-300">No Statutory Deficiencies Identified</h4>
          <p className="text-xs text-slate-400 mt-0.5">All mandatory declarations meet standard Legal Metrology (Packaged Commodities) requirements.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-rose-950/20 border border-rose-500/30 p-5 shadow-xl space-y-4">
      <div className="flex items-center space-x-2 border-b border-rose-500/20 pb-3">
        <AlertOctagon className="w-5 h-5 text-rose-400" />
        <h3 className="text-sm font-bold text-rose-200">
          Potential Deficiencies & Violations ({violations.length})
        </h3>
      </div>

      <div className="space-y-3">
        {violations.map((v, idx) => {
          const sevColor = v.severity === 'HIGH' 
            ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' 
            : 'bg-amber-500/20 text-amber-300 border-amber-500/40';

          return (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2.5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-100 uppercase tracking-wide">
                    {v.field_name.replace(/_/g, ' ')}
                  </span>
                  {v.legal_reference && (
                    <p className="text-[10px] font-mono text-slate-400 mt-0.5">{v.legal_reference}</p>
                  )}
                </div>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${sevColor}`}>
                  {v.severity} SEVERITY
                </span>
              </div>

              <div className="text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
                <span className="font-semibold text-slate-400">Issue: </span>
                {v.reason}
              </div>

              <div className="text-xs text-slate-300 flex items-start space-x-2 bg-emerald-500/5 p-2.5 rounded-lg border border-emerald-500/20">
                <ArrowRight className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-emerald-400">Inspector Recommendation: </span>
                  {v.recommendation}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
