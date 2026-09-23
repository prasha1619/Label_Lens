import React, { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  X, 
  ShieldCheck, 
  FileText, 
  Layers, 
  UserCheck, 
  Eye, 
  ArrowRight 
} from 'lucide-react';
import { InspectionResponse, ConflictItem, RuleCheckResult } from '../../types/inspection';
import { inspectionService } from '../../services/inspectionService';

interface ReviewQueueModalProps {
  inspection: InspectionResponse;
  isOpen: boolean;
  onClose: () => void;
  onReviewCompleted: (updated: InspectionResponse) => void;
}

export const ReviewQueueModal: React.FC<ReviewQueueModalProps> = ({
  inspection,
  isOpen,
  onClose,
  onReviewCompleted,
}) => {
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [customValue, setCustomValue] = useState<string>('');
  const [reviewerNote, setReviewerNote] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  // Collect review candidates: conflicts or checks with status REVIEW/WARNING/UNCERTAIN
  const conflicts: ConflictItem[] = inspection.conflicts || [];
  const reviewChecks: RuleCheckResult[] = inspection.compliance_checks.filter(
    (c) => c.status === 'REVIEW' || c.status === 'WARNING' || c.status === 'UNCERTAIN' || c.conflict_detected
  );

  // Group candidate field names
  const candidateFieldNames = Array.from(
    new Set([
      ...conflicts.map((c) => c.field_name),
      ...reviewChecks.map((c) => c.field_name),
    ])
  );

  const activeFieldName = selectedField || candidateFieldNames[0] || 'mrp';
  const activeConflict = conflicts.find((c) => c.field_name === activeFieldName);
  const activeCheck = reviewChecks.find((c) => c.field_name === activeFieldName);
  const activeDetected = inspection.detected_fields.find((f) => f.field_name === activeFieldName);

  const handleConfirmCandidate = async (val: string, sourcePanel: string) => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      const updated = await inspectionService.submitReview(
        inspection.id,
        activeFieldName,
        val,
        'CONFIRM_VALUE',
        sourcePanel,
        'Statutory Inspector',
        reviewerNote || `Confirmed value from ${sourcePanel}`
      );
      onReviewCompleted(updated);
      setCustomValue('');
      setReviewerNote('');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit review resolution.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleMarkUnresolved = async () => {
    try {
      setSubmitting(true);
      setErrorMsg(null);
      const updated = await inspectionService.submitReview(
        inspection.id,
        activeFieldName,
        activeDetected?.normalized_value || '[UNRESOLVED]',
        'MARK_UNRESOLVED',
        'Human Review',
        'Statutory Inspector',
        reviewerNote || 'Marked unresolved by inspector — non-compliant discrepancy.'
      );
      onReviewCompleted(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to mark unresolved.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-3xl bg-[#0b1126] border border-amber-500/30 shadow-2xl overflow-hidden text-slate-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0e1633]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 shadow-inner">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2">
                Human-in-the-Loop Review Queue
                <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  {candidateFieldNames.length} Action Item(s)
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Statutory inspector determination required. AI certainty does not equal legal certainty.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Left Column: Items List */}
          <div className="md:col-span-1 space-y-2 border-r border-slate-800/80 pr-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              Pending Review Items
            </div>
            {candidateFieldNames.map((fname) => {
              const isConflict = conflicts.some((c) => c.field_name === fname);
              const isActive = fname === activeFieldName;
              const fieldTitle = fname.replace(/_/g, ' ').toUpperCase();

              return (
                <button
                  key={fname}
                  onClick={() => { setSelectedField(fname); setCustomValue(''); }}
                  className={`w-full text-left px-4 py-3 rounded-2xl transition-all duration-200 border flex items-center justify-between ${
                    isActive
                      ? 'bg-amber-500/15 border-amber-500/50 text-white shadow-lg'
                      : 'bg-slate-900/60 border-slate-800/60 text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                  }`}
                >
                  <div>
                    <div className="text-xs font-bold">{fieldTitle}</div>
                    <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                      {isConflict ? (
                        <span className="text-rose-400 font-semibold flex items-center gap-1">
                          ⚠ Mismatch Across Panels
                        </span>
                      ) : (
                        <span className="text-amber-400">Requires Verification</span>
                      )}
                    </div>
                  </div>
                  <ArrowRight className={`w-4 h-4 ${isActive ? 'text-amber-400' : 'text-slate-600'}`} />
                </button>
              );
            })}

            {/* Previously Verified Log */}
            {inspection.review_decisions && inspection.review_decisions.length > 0 && (
              <div className="pt-4 mt-4 border-t border-slate-800">
                <div className="text-[11px] font-bold text-emerald-400 mb-2 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Resolved Decisions ({inspection.review_decisions.length})
                </div>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {inspection.review_decisions.map((r, i) => (
                    <div key={i} className="px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-[11px]">
                      <div className="font-semibold text-emerald-300">{r.field_name.replace(/_/g, ' ').toUpperCase()}</div>
                      <div className="text-slate-300">Verified: <b className="text-white">{r.final_verified_value}</b></div>
                      <div className="text-[9px] text-slate-400">{r.timestamp.slice(0, 16)} by {r.reviewer_name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Evidence Comparison & Action Panel */}
          <div className="md:col-span-2 space-y-5">
            
            {/* Active Field Title & Status */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h3 className="text-base font-extrabold text-white">
                  Declaration: {activeFieldName.replace(/_/g, ' ').toUpperCase()}
                </h3>
                <p className="text-xs text-slate-400">
                  {activeCheck?.legal_reference || 'Rule 6, Legal Metrology (PC) Rules 2011'}
                </p>
              </div>
              <span className="px-3 py-1 rounded-xl text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                REVIEW REQUIRED
              </span>
            </div>

            {/* Conflict Alert Banner if applicable */}
            {activeConflict && (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/30 space-y-1.5">
                <div className="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-rose-400" />
                  Cross-Panel Declaration Mismatch Detected
                </div>
                <p className="text-xs text-slate-300">
                  The automated OCR pipeline detected divergent values on different package angles:
                </p>
                <div className="font-mono text-xs text-rose-200 bg-black/40 px-3 py-2 rounded-xl border border-rose-500/20">
                  {activeConflict.conflict_summary}
                </div>
              </div>
            )}

            {/* Side-by-Side Panel Evidence Cards */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Evidence Sources (Click to Confirm Value):
              </label>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {activeConflict?.sources && activeConflict.sources.length > 0 ? (
                  activeConflict.sources.map((src, idx) => (
                    <div
                      key={idx}
                      className="p-4 rounded-2xl bg-[#0e1633] border border-slate-700/60 hover:border-amber-500/60 transition-all flex flex-col justify-between space-y-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="px-2 py-0.5 rounded-lg text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                            {src.panel_type}
                          </span>
                          <span className="text-[10px] text-emerald-400 font-semibold">
                            {Math.round((src.confidence || 0.9) * 100)}% Confidence
                          </span>
                        </div>
                        <div className="text-lg font-extrabold text-white mt-2">
                          {src.value || '—'}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono truncate">
                          Raw OCR: "{src.raw_value || src.value}"
                        </div>
                      </div>

                      <button
                        disabled={submitting}
                        onClick={() => handleConfirmCandidate(src.value || '', src.panel_type)}
                        className="w-full py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-1.5 transition-colors shadow-md disabled:opacity-50"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Confirm {src.value} ({src.panel_type})
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="col-span-2 p-4 rounded-2xl bg-[#0e1633] border border-slate-800 space-y-2">
                    <div className="text-xs text-slate-400">
                      Detected Value:{' '}
                      <b className="text-white text-sm">
                        {activeDetected?.normalized_value || activeCheck?.detected_value || 'None'}
                      </b>
                    </div>
                    <div className="text-xs text-slate-400">
                      Source Panel:{' '}
                      <b className="text-slate-200">
                        {activeDetected?.source_panel || 'Front Panel'}
                      </b>
                    </div>
                    <div className="text-xs text-amber-300/90 bg-amber-500/10 p-2.5 rounded-xl border border-amber-500/20">
                      {activeCheck?.explanation || 'Low confidence or noisy OCR reading.'}
                    </div>
                    {activeDetected?.normalized_value && (
                      <button
                        disabled={submitting}
                        onClick={() => handleConfirmCandidate(activeDetected.normalized_value!, activeDetected.source_panel || 'Front Panel')}
                        className="mt-2 w-full py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Confirm AI Value ({activeDetected.normalized_value})
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Custom Value & Note Input */}
            <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
              <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
                <UserCheck className="w-4 h-4 text-sky-400" />
                Or Enter Inspector-Verified Custom Value:
              </label>

              <div className="flex gap-2">
                <input
                  type="text"
                  value={customValue}
                  onChange={(e) => setCustomValue(e.target.value)}
                  placeholder={`e.g., ₹120 or 500 g`}
                  className="flex-1 px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:outline-none focus:border-sky-500"
                />
                <button
                  disabled={!customValue.trim() || submitting}
                  onClick={() => handleConfirmCandidate(customValue.trim(), 'Manual Physical Verification')}
                  className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold disabled:opacity-50 transition-colors"
                >
                  Verify Custom
                </button>
              </div>

              <input
                type="text"
                value={reviewerNote}
                onChange={(e) => setReviewerNote(e.target.value)}
                placeholder="Auditor Note / Justification (optional)"
                className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-slate-600"
              />
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="p-3 rounded-xl bg-rose-500/20 border border-rose-500/40 text-xs text-rose-300">
                {errorMsg}
              </div>
            )}

            {/* Bottom Actions */}
            <div className="pt-2 flex items-center justify-between">
              <button
                disabled={submitting}
                onClick={handleMarkUnresolved}
                className="px-4 py-2 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center gap-1.5"
              >
                <XCircle className="w-4 h-4" />
                Mark as Non-Compliant / Unresolved
              </button>

              <button
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close Queue
              </button>
            </div>

          </div>

        </div>

      </div>
    </div>
  );
};
