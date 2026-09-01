import React from 'react';
import { Scale, Info } from 'lucide-react';

export const LegalDisclaimerBanner: React.FC = () => {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="flex items-start space-x-3">
        <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0 mt-0.5">
          <Scale className="w-4 h-4" />
        </div>
        <div className="text-xs leading-relaxed text-slate-300">
          <span className="font-semibold text-amber-300">Statutory Legal Metrology Disclaimer: </span>
          AI-assisted screening result. Final legal determination requires verification by an authorized inspector/competent authority 
          under the <span className="text-slate-100 font-medium">Legal Metrology Act, 2009</span> and <span className="text-slate-100 font-medium">Legal Metrology (Packaged Commodities) Rules, 2011</span>, and depends on the applicable statutory rules and the quality/completeness of the submitted evidence.
        </div>
      </div>
    </div>
  );
};
