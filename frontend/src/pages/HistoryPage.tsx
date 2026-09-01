import React, { useState, useEffect } from 'react';
import { 
  History, 
  Search, 
  Filter, 
  Download, 
  ArrowRight, 
  Trash2,
  Calendar,
  AlertTriangle,
  RefreshCw
} from 'lucide-react';
import { InspectionListItem } from '../types/inspection';
import { inspectionService } from '../services/inspectionService';
import { StatusBadge } from '../components/common/StatusBadge';
import { LegalDisclaimerBanner } from '../components/common/LegalDisclaimerBanner';

interface HistoryPageProps {
  onSelectInspection: (id: string) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({ onSelectInspection }) => {
  const [inspections, setInspections] = useState<InspectionListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    fetchHistory();
  }, [page, categoryFilter, statusFilter]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const res = await inspectionService.listInspections({
        page,
        limit,
        category: categoryFilter || undefined,
        statusFilter: statusFilter || undefined,
        search: search || undefined,
      });
      setInspections(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error('Failed to load history:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this inspection audit record?')) {
      try {
        await inspectionService.deleteInspection(id);
        fetchHistory();
      } catch (err) {
        alert('Failed to delete inspection.');
      }
    }
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <History className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Inspection Audit History</h1>
          </div>
          <p className="text-xs text-slate-400">
            Immutable inspection log containing statutory verdicts, rule checks, confidence scores, and PDF reports.
          </p>
        </div>

        <button
          onClick={fetchHistory}
          className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold self-start transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row gap-4 items-center justify-between shadow-lg">
        
        {/* Search form */}
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search product name..."
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </form>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <select
            value={categoryFilter}
            onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Categories</option>
            <option value="packaged_commodity">Packaged Commodities</option>
            <option value="food_and_beverages">Food & Beverages</option>
            <option value="cosmetics_and_toiletries">Cosmetics</option>
            <option value="electronics_and_appliances">Electronics</option>
            <option value="pharmaceuticals">Pharmaceuticals</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
          >
            <option value="">All Verdicts</option>
            <option value="COMPLIANT">COMPLIANT</option>
            <option value="NON_COMPLIANT">NON-COMPLIANT</option>
            <option value="NEEDS_REVIEW">NEEDS REVIEW</option>
            <option value="UNABLE_TO_VERIFY">UNABLE TO VERIFY</option>
          </select>
        </div>

      </div>

      {/* History Table */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold uppercase text-slate-400">
                <th className="py-3 px-4">Audit ID / Date</th>
                <th className="py-3 px-4">Product Name</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Legal Verdict</th>
                <th className="py-3 px-4">Checks Passed</th>
                <th className="py-3 px-4">Coverage Index</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <div className="flex justify-center items-center space-x-2">
                      <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                      <span>Loading records...</span>
                    </div>
                  </td>
                </tr>
              ) : inspections.length > 0 ? (
                inspections.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => onSelectInspection(item.id)}
                    className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                  >
                    {/* ID & Date */}
                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-slate-200 font-semibold">{item.id.slice(0, 8).toUpperCase()}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>

                    {/* Product Name */}
                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      {item.product_name || item.original_filename || 'Packaged Commodity'}
                    </td>

                    {/* Category */}
                    <td className="py-3.5 px-4 text-slate-400 capitalize">
                      {item.product_category.replace(/_/g, ' ')}
                    </td>

                    {/* Verdict */}
                    <td className="py-3.5 px-4">
                      <StatusBadge status={item.overall_status} size="sm" />
                    </td>

                    {/* Passed Checks */}
                    <td className="py-3.5 px-4 font-mono">
                      <span className="text-emerald-400 font-semibold">{item.passed_checks}</span>
                      <span className="text-slate-500"> / {item.total_checks}</span>
                    </td>

                    {/* Coverage Index */}
                    <td className="py-3.5 px-4 font-mono font-semibold text-slate-300">
                      {item.compliance_score !== null && item.compliance_score !== undefined
                        ? `${item.compliance_score}%`
                        : '—'}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        <a
                          href={inspectionService.getReportDownloadUrl(item.id)}
                          onClick={(e) => e.stopPropagation()}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                          title="Download PDF Report"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                        <button
                          onClick={(e) => handleDelete(e, item.id)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-colors"
                          title="Delete Record"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-500 italic">
                    No inspection audit records found matching your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="px-5 py-3 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <span>Showing {((page - 1) * limit) + 1} - {Math.min(page * limit, total)} of {total} inspections</span>
            <div className="flex items-center space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1 rounded bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700"
              >
                Previous
              </button>
              <span className="font-mono text-slate-200">Page {page} of {totalPages}</span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1 rounded bg-slate-800 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-700"
              >
                Next
              </button>
            </div>
          </div>
        )}

      </div>

      <LegalDisclaimerBanner />

    </div>
  );
};
