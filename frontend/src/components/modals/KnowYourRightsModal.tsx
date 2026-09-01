import React from 'react';
import { X, ShieldCheck, Scale, CheckCircle2, AlertCircle } from 'lucide-react';

interface KnowYourRightsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KnowYourRightsModal: React.FC<KnowYourRightsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const statutoryRules = [
    {
      title: 'Rule 6(1)(a) - Name & Address of Manufacturer / Packer / Importer',
      desc: 'Every packaged commodity must clearly declare the complete name and address of the manufacturer, packer, or importer.',
    },
    {
      title: 'Rule 6(1)(b) - Generic Name of the Commodity',
      desc: 'The common or generic name of the commodity contained in the package must be prominently displayed.',
    },
    {
      title: 'Rule 6(1)(c) - Net Quantity Declaration',
      desc: 'The net quantity in terms of standard unit of weight or measure (g, kg, ml, L) or number must be stated with minimum font height rules.',
    },
    {
      title: 'Rule 6(1)(d) - Month and Year of Manufacture / Packaging / Import',
      desc: 'Clear declaration of the month and year in which the commodity is manufactured, packed, or imported.',
    },
    {
      title: 'Rule 6(1)(e) - Maximum Retail Price (MRP) & Unit Sale Price (USP)',
      desc: 'MRP inclusive of all taxes, plus Unit Sale Price (e.g. ₹/g or ₹/ml) for easy consumer price comparison.',
    },
    {
      title: 'Rule 6(1)(n) - Consumer Care Helpline Details',
      desc: 'Name, address, telephone number, and email ID of the grievance officer/consumer care cell.',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-2xl bg-[#0e1533] border border-[#232f58] shadow-2xl p-6 overflow-hidden max-h-[85vh] flex flex-col">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/60 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Scale className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Legal Metrology Act, 2009 & PCR, 2011</h3>
            <p className="text-xs text-slate-400">Consumer Rights & Statutory Label Requirements</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs text-slate-300">
          <p className="text-slate-300 leading-relaxed bg-[#141d3d] p-3 rounded-xl border border-[#202b52]">
            Under the <strong className="text-purple-300">Legal Metrology (Packaged Commodities) Rules, 2011</strong>, 
            every manufacturer, packer, and e-commerce entity is legally mandated to display declarations accurately to prevent fraudulent trade practices.
          </p>

          <div className="space-y-2.5">
            {statutoryRules.map((rule, idx) => (
              <div key={idx} className="p-3 rounded-xl bg-[#121938] border border-[#1e274c]">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold mb-1">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{rule.title}</span>
                </div>
                <p className="text-slate-400 pl-6 leading-relaxed">{rule.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-4 border-t border-[#1d274d] flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold text-xs shadow-lg"
          >
            Understood
          </button>
        </div>
      </div>
    </div>
  );
};
