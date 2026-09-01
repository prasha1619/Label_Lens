import React, { useState } from 'react';
import { X, AlertTriangle, CheckCircle2, Upload, Building2, MapPin } from 'lucide-react';

interface RegisterComplaintModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RegisterComplaintModal: React.FC<RegisterComplaintModalProps> = ({ isOpen, onClose }) => {
  const [submitted, setSubmitted] = useState(false);
  const [complaintType, setComplaintType] = useState('Net Quantity Mismatch');
  const [productName, setProductName] = useState('');
  const [brandName, setBrandName] = useState('');
  const [storeLocation, setStoreLocation] = useState('');
  const [details, setDetails] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      // Auto close after 2 seconds
    }, 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#0e1533] border border-[#232f58] shadow-2xl p-6 overflow-hidden">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/60 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {submitted ? (
          <div className="py-8 text-center space-y-3">
            <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-white">Complaint Registered Successfully</h3>
            <p className="text-xs text-slate-300 max-w-sm mx-auto">
              Docket ID: <span className="font-mono text-purple-300 font-bold">LM-CMP-2026-{Math.floor(1000 + Math.random() * 9000)}</span>.
              The Legal Metrology enforcement wing has been notified for inspection.
            </p>
            <button
              onClick={() => { setSubmitted(false); onClose(); }}
              className="mt-4 px-5 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-xl text-white text-xs font-semibold"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-pink-500/20 border border-pink-500/30 flex items-center justify-center text-pink-400">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Register Legal Metrology Complaint</h3>
                <p className="text-xs text-slate-400">Report deceptive packaging, missing MRP, or incorrect weights</p>
              </div>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Violation Category</label>
                <select
                  value={complaintType}
                  onChange={(e) => setComplaintType(e.target.value)}
                  className="w-full px-3 py-2 bg-[#141d3d] border border-[#263566] rounded-xl text-slate-200 focus:outline-none focus:border-purple-500"
                >
                  <option>Net Quantity Mismatch / Underweight</option>
                  <option>Overcharging Above MRP</option>
                  <option>Missing Mandatory Declarations</option>
                  <option>Smudged / Overwritten Date of Packaging</option>
                  <option>Non-Standard Packaging Size</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Product Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Premium Basmati Rice"
                    value={productName}
                    onChange={(e) => setProductName(e.target.value)}
                    className="w-full px-3 py-2 bg-[#141d3d] border border-[#263566] rounded-xl text-slate-200 focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Brand / Manufacturer</label>
                  <input
                    type="text"
                    placeholder="e.g. Royal Foods Ltd"
                    value={brandName}
                    onChange={(e) => setBrandName(e.target.value)}
                    className="w-full px-3 py-2 bg-[#141d3d] border border-[#263566] rounded-xl text-slate-200 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Store / Location Found</label>
                <div className="relative">
                  <MapPin className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="e.g. Supermarket, Sector 15, Bhiwadi"
                    value={storeLocation}
                    onChange={(e) => setStoreLocation(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 bg-[#141d3d] border border-[#263566] rounded-xl text-slate-200 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Details & Evidence Description</label>
                <textarea
                  rows={3}
                  placeholder="Provide batch number, declared vs actual weight, or specific missing fields..."
                  value={details}
                  onChange={(e) => setDetails(e.target.value)}
                  className="w-full px-3 py-2 bg-[#141d3d] border border-[#263566] rounded-xl text-slate-200 focus:outline-none focus:border-purple-500 resize-none"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-pink-600 to-rose-600 hover:from-pink-500 hover:to-rose-500 text-white text-xs font-bold shadow-lg shadow-pink-900/30 transition-all"
              >
                Submit Official Complaint
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
