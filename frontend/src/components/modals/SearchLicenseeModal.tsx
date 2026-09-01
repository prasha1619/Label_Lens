import React, { useState } from 'react';
import { X, Search, ShieldCheck, CheckCircle2, AlertCircle, Building, MapPin } from 'lucide-react';

interface SearchLicenseeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SearchLicenseeModal: React.FC<SearchLicenseeModalProps> = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const sampleLicensees = [
    {
      id: 'LIC-2024-9841',
      name: 'Balaji Traders & Agro Packers',
      type: 'Packer / Manufacturer',
      state: 'Rajasthan',
      district: 'Alwar',
      validUntil: '31 Dec 2027',
      status: 'Active',
      commodities: ['Atta', 'Pulses', 'Grains'],
    },
    {
      id: 'LIC-2023-4120',
      name: 'Tata Consumer Products Limited',
      type: 'Manufacturer / Importer',
      state: 'Maharashtra',
      district: 'Mumbai',
      validUntil: '15 Aug 2028',
      status: 'Active',
      commodities: ['Salt', 'Tea', 'Spices'],
    },
    {
      id: 'LIC-2022-7719',
      name: 'Adani Wilmar Limited',
      type: 'Packer / Refiner',
      state: 'Gujarat',
      district: 'Ahmedabad',
      validUntil: '10 Nov 2026',
      status: 'Active',
      commodities: ['Edible Oils', 'Flour', 'Rice'],
    },
    {
      id: 'LIC-2021-3321',
      name: 'Sharma Traders & Suppliers',
      type: 'Retailer / Distributor',
      state: 'Haryana',
      district: 'Gurugram',
      validUntil: '15 Jun 2025',
      status: 'Expiring Soon',
      commodities: ['General Packaged Goods'],
    },
  ];

  const filtered = sampleLicensees.filter(
    (item) =>
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.state.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-2xl rounded-2xl bg-[#0e1533] border border-[#232f58] shadow-2xl p-6 overflow-hidden max-h-[85vh] flex flex-col">
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/60 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
            <Search className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Licensee Registry Search</h3>
            <p className="text-xs text-slate-400">
              Verify manufacturer, packer, or importer Legal Metrology licenses & compliance status
            </p>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative mb-4">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by company name, license number, state..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-[#141d3d] border border-[#263566] rounded-xl text-xs sm:text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:border-emerald-500 transition-all"
            autoFocus
          />
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
          {filtered.map((lic) => (
            <div
              key={lic.id}
              className="p-3.5 rounded-xl bg-[#121a3a] border border-[#202b52] hover:border-emerald-500/40 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-white">{lic.name}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                      lic.status === 'Active'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {lic.status}
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-1">
                  <span className="font-mono text-purple-300">{lic.id}</span>
                  <span>&bull;</span>
                  <span>{lic.type}</span>
                  <span>&bull;</span>
                  <span className="flex items-center">
                    <MapPin className="w-3 h-3 mr-0.5 inline" />
                    {lic.district}, {lic.state}
                  </span>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {lic.commodities.map((c, i) => (
                    <span key={i} className="px-1.5 py-0.5 rounded bg-[#1a254c] text-[10px] text-slate-300">
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              <div className="text-right flex-shrink-0">
                <div className="text-[10px] text-slate-400">Valid Until</div>
                <div className="text-xs font-semibold text-slate-200 font-mono">{lic.validUntil}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
