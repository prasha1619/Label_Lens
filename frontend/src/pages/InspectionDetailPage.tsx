import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  Download, 
  ShieldCheck, 
  AlertTriangle, 
  Activity, 
  Calendar, 
  FileText, 
  Cpu,
  Layers,
  Sparkles,
  Printer,
  Users,
  Eye,
  CheckCircle2,
  HelpCircle,
  AlertCircle,
  Phone,
  Mail,
  MapPin,
  Clock
} from 'lucide-react';
import { InspectionResponse, ReviewDecision } from '../types/inspection';
import { inspectionService } from '../services/inspectionService';
import { StatusBadge } from '../components/common/StatusBadge';
import { ImageCanvasOverlay } from '../components/inspection/ImageCanvasOverlay';
import { DetectedFieldsTable } from '../components/inspection/DetectedFieldsTable';
import { RawOcrViewer } from '../components/inspection/RawOcrViewer';
import { getCategoryLabel } from '../utils/categoryLabels';
import { ComplianceChecksMatrix } from '../components/inspection/ComplianceChecksMatrix';
import { ViolationsCard } from '../components/inspection/ViolationsCard';
import { LegalDisclaimerBanner } from '../components/common/LegalDisclaimerBanner';
import { ReviewQueueModal } from '../components/inspection/ReviewQueueModal';

interface InspectionDetailPageProps {
  inspectionId: string;
  onBack: () => void;
}

export const InspectionDetailPage: React.FC<InspectionDetailPageProps> = ({
  inspectionId,
  onBack,
}) => {
  const [inspection, setInspection] = useState<InspectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedField, setSelectedField] = useState<string | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [overrideToast, setOverrideToast] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'inspector' | 'consumer'>('inspector');
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);

  useEffect(() => {
    fetchInspection();
  }, [inspectionId]);

  const fetchInspection = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await inspectionService.getInspection(inspectionId);
      setInspection(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load inspection results.');
    } finally {
      setLoading(false);
    }
  };

  const handleFieldOverride = async (fieldName: string, value: string, unit?: string) => {
    const updated = await inspectionService.overrideField(inspectionId, fieldName, value, unit);
    setInspection(updated);
    setOverrideToast(`"${fieldName.replace(/_/g, ' ')}" manually verified ✓`);
    setTimeout(() => setOverrideToast(null), 3500);
  };

  const handleReviewDecisionSubmit = async (fieldName: string, action: string, finalValue: string, justification: string) => {
    try {
      const updated = await inspectionService.submitReview(
        inspectionId,
        fieldName,
        action as any,
        finalValue,
        justification,
        'Senior Regulatory Inspector'
      );
      setInspection(updated);
      setOverrideToast(`Review decision for "${fieldName}" recorded in audit trail ✓`);
      setTimeout(() => setOverrideToast(null), 3500);
    } catch (err: any) {
      console.error('Review submit error:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
        <p className="text-sm font-medium text-slate-400">Loading statutory audit report...</p>
      </div>
    );
  }

  if (error || !inspection) {
    return (
      <div className="p-8 rounded-3xl bg-slate-900 border border-slate-800 text-center space-y-4 max-w-md mx-auto">
        <AlertTriangle className="w-10 h-10 text-amber-400 mx-auto" />
        <h3 className="text-lg font-bold text-white">Inspection Not Found</h3>
        <p className="text-xs text-slate-400">{error || 'Could not retrieve inspection data.'}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  const imageList = (inspection?.images && inspection.images.length > 0)
    ? inspection.images
    : (inspection?.image ? [inspection.image] : []);

  const activeImage = imageList[selectedImageIndex] || inspection?.image;
  const imageUrl = inspection ? inspectionService.getImageUrl(inspection.id, false, selectedImageIndex, activeImage?.id) : '';
  const pdfDownloadUrl = inspection ? inspectionService.getReportDownloadUrl(inspection.id) : '';

  const getPanelLabel = (panelType?: string, index: number = 0) => {
    if (!panelType || panelType === 'general') {
      return `Panel ${index + 1}`;
    }
    return `${panelType.charAt(0).toUpperCase() + panelType.slice(1)} Panel`;
  };

  const hasReviewItems = (inspection.compliance_checks || []).some(
    (c) => c.status === 'REVIEW' || (inspection.conflicts && inspection.conflicts.length > 0)
  ) || (inspection.conflicts && inspection.conflicts.length > 0) || (inspection.detected_fields || []).some((f) => f.has_conflict);

  const fieldMap: Record<string, any> = {};
  (inspection.detected_fields || []).forEach((f) => {
    fieldMap[f.field_name] = f;
  });

  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <button
          onClick={onBack}
          className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to All Audits</span>
        </button>

        <div className="flex flex-wrap items-center gap-3">
          {/* Mode Switcher */}
          <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setViewMode('inspector')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === 'inspector'
                  ? 'bg-emerald-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Inspector View</span>
            </button>
            <button
              onClick={() => setViewMode('consumer')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                viewMode === 'consumer'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Consumer Awareness</span>
            </button>
          </div>

          {hasReviewItems && (
            <button
              onClick={() => setIsReviewModalOpen(true)}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 hover:bg-amber-500/30 text-xs font-bold transition-all animate-pulse"
            >
              <HelpCircle className="w-4 h-4" />
              <span>Human Review Queue</span>
              {inspection.conflicts && inspection.conflicts.length > 0 && (
                <span className="px-1.5 py-0.5 rounded bg-amber-500 text-slate-950 text-[10px] font-extrabold ml-1">
                  {inspection.conflicts.length} Conflict{inspection.conflicts.length > 1 ? 's' : ''}
                </span>
              )}
            </button>
          )}

          <a
            href={pdfDownloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold text-xs shadow-lg shadow-emerald-600/20 transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Download Official PDF Dossier</span>
          </a>
        </div>
      </div>

      {/* Cross-Panel Conflict Banner */}
      {inspection.conflicts && inspection.conflicts.length > 0 && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-amber-300">Cross-Panel Value Conflict Detected</h4>
              <p className="text-xs text-slate-300 mt-0.5">
                Discrepant statutory declarations found across panels (e.g. Front vs Back panel). Regulatory status held in <strong>REVIEW</strong> until human adjudicator confirmation.
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsReviewModalOpen(true)}
            className="px-3 py-1.5 rounded-xl bg-amber-500 text-slate-950 text-xs font-bold hover:bg-amber-400 shrink-0"
          >
            Resolve in Review Queue
          </button>
        </div>
      )}

      {/* Main Verdict & Audit Summary Banner */}
      <div className="rounded-3xl bg-slate-900/90 border border-slate-800 p-6 sm:p-8 shadow-2xl space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 pb-6 border-b border-slate-800">
          
          {/* Left: Product & ID */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                AUDIT ID: {inspection.id.slice(0, 8).toUpperCase()}
              </span>
              {inspection.package_id && (
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                  PACKAGE #{inspection.package_id}
                </span>
              )}
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                {inspection.execution_mode}
              </span>
              {imageList.length > 1 && (
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                  {imageList.length} PANELS FUSED
                </span>
              )}
            </div>
            <h2 className="text-2xl font-bold text-white">
              {inspection.product_name || 'Packaged Commodity'}
            </h2>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-mono">
              <span className="flex items-center space-x-1">
                <Calendar className="w-3.5 h-3.5 text-slate-500" />
                <span>{new Date(inspection.created_at).toLocaleString()}</span>
              </span>
              <span>Category: <b className="text-slate-200">{getCategoryLabel(inspection.product_category)}</b></span>
              <span>Latency: <b className="text-slate-200">{inspection.processing_time_ms || 0} ms</b></span>
            </div>
          </div>

          {/* Right: Primary Status Verdict Badge & Score */}
          <div className="flex flex-col sm:flex-row lg:flex-col items-start lg:items-end gap-3">
            <div className="text-left lg:text-right">
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400 block mb-1">
                Statutory Compliance Verdict
              </span>
              <StatusBadge status={inspection.overall_status} size="lg" />
            </div>

            {inspection.compliance_score !== null && (
              <div className="text-xs font-mono text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-xl border border-slate-800">
                Confidence / Coverage Index: <b className="text-emerald-400">{inspection.compliance_score}%</b>
              </div>
            )}
          </div>

        </div>

        {/* Quality Assessment & Image Summary Bar */}
        {activeImage && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400 block text-[10px] uppercase">
                {imageList.length > 1 ? `${getPanelLabel(activeImage.panel_type, selectedImageIndex)} Sharpness` : 'Image Sharpness'}
              </span>
              <span className="font-mono font-semibold text-slate-200">
                {activeImage.blur_score ? `${activeImage.blur_score.toFixed(1)} (Laplacian)` : 'N/A'}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400 block text-[10px] uppercase">
                {imageList.length > 1 ? `${getPanelLabel(activeImage.panel_type, selectedImageIndex)} Resolution` : 'Resolution'}
              </span>
              <span className="font-mono font-semibold text-slate-200">
                {activeImage.width || 0} x {activeImage.height || 0} px
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400 block text-[10px] uppercase">Quality Verdict</span>
              <span className={`font-mono font-semibold ${activeImage.quality_status === 'PASS' ? 'text-emerald-400' : 'text-amber-400'}`}>
                {activeImage.quality_status}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400 block text-[10px] uppercase">Mandatory Checks</span>
              <span className="font-mono font-semibold text-emerald-400">
                {inspection.passed_checks} / {inspection.total_checks} PASSED
              </span>
            </div>
          </div>
        )}

      </div>

      {/* CONSUMER AWARENESS VIEW */}
      {viewMode === 'consumer' && (
        <div className="space-y-6 animate-fadeIn">
          <div className="p-5 rounded-3xl bg-blue-950/30 border border-blue-800/40 space-y-2">
            <h3 className="text-base font-bold text-blue-300 flex items-center gap-2">
              <Eye className="w-5 h-5 text-blue-400" />
              <span>Consumer Product Transparency Summary</span>
            </h3>
            <p className="text-xs text-slate-300">
              This label was verified under the <strong>Legal Metrology (Packaged Commodities) Rules, 2011</strong>.
              Below are the key statutory declarations consumers are legally entitled to see before purchasing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400 uppercase font-semibold">Maximum Retail Price (MRP)</span>
              <div className="text-2xl font-black text-emerald-400">
                {fieldMap.mrp?.normalized_value || fieldMap.mrp?.raw_value || 'Not Declared'}
              </div>
              <p className="text-[11px] text-slate-500">Inclusive of all taxes. Retailers cannot charge above this amount.</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400 uppercase font-semibold">Net Quantity</span>
              <div className="text-2xl font-black text-white">
                {fieldMap.net_quantity?.normalized_value || fieldMap.net_quantity?.raw_value || 'Not Declared'}
              </div>
              <p className="text-[11px] text-slate-500">Declared in standard SI units.</p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400 uppercase font-semibold">Manufacturing / Expiry</span>
              <div className="text-base font-bold text-slate-200">
                Mfg: {fieldMap.mfg_date?.raw_value || fieldMap.mfg_date?.normalized_value || '—'}
              </div>
              <div className="text-xs font-semibold text-slate-400">
                Exp: {fieldMap.expiry_date?.raw_value || fieldMap.expiry_date?.normalized_value || 'Not Applicable / Declared'}
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1 lg:col-span-2">
              <span className="text-xs text-slate-400 uppercase font-semibold">Manufacturer & Origin</span>
              <div className="text-sm font-semibold text-slate-200">
                {fieldMap.manufacturer?.raw_value || fieldMap.manufacturer?.normalized_value || 'Manufacturer details unverified'}
              </div>
              <div className="text-xs text-slate-400 pt-1">
                Country of Origin: <b className="text-slate-200">{fieldMap.country_of_origin?.normalized_value || 'India'}</b>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
              <span className="text-xs text-slate-400 uppercase font-semibold">Consumer Care / Grievance</span>
              <div className="text-xs text-slate-300 break-words">
                {fieldMap.consumer_care?.raw_value || fieldMap.consumer_care?.normalized_value || 'Helpline details missing'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* INSPECTOR VIEW */}
      {viewMode === 'inspector' && (
        <>
          {/* Multi-Panel Switcher — thumbnail strip (when > 1 panel) */}
          {imageList.length > 1 && (
            <div className="space-y-2">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-slate-400">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <span>Evidence Panels — click to switch view</span>
                <span className="ml-1 px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-mono text-[10px]">
                  {imageList.length} PHOTOS
                </span>
              </div>
              <div className="flex items-start gap-2 overflow-x-auto pb-1">
                {imageList.map((img, idx) => {
                  const isActive = selectedImageIndex === idx;
                  const thumbUrl = inspectionService.getImageUrl(inspection.id, false, idx, img.id);
                  const label = getPanelLabel(img.panel_type, idx);
                  return (
                    <button
                      key={img.id || idx}
                      onClick={() => { setSelectedImageIndex(idx); setSelectedField(null); }}
                      className={`flex-shrink-0 flex flex-col items-center gap-1 p-1.5 rounded-xl border transition-all duration-200 ${
                        isActive
                          ? 'border-indigo-500 bg-indigo-500/15 shadow-lg shadow-indigo-500/20 scale-[1.04]'
                          : 'border-slate-700 bg-slate-900/60 hover:border-slate-500 hover:scale-[1.02]'
                      }`}
                    >
                      <div className="relative w-16 h-20 rounded-lg overflow-hidden bg-slate-950">
                        <img src={thumbUrl} alt={label} className="w-full h-full object-cover" />
                        {img.quality_status && (
                          <div className={`absolute top-0.5 right-0.5 w-2 h-2 rounded-full ${
                            img.quality_status === 'PASS' ? 'bg-emerald-400' : 'bg-amber-400'
                          }`} />
                        )}
                      </div>
                      <span className={`text-[9px] font-bold uppercase tracking-wide ${
                        isActive ? 'text-indigo-300' : 'text-slate-400'
                      }`}>
                        {label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Interactive Evidence Section (Split Canvas + Table) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            
            {/* Left: Canvas with Bounding Boxes */}
            <div className="sticky top-20">
              <ImageCanvasOverlay
                imageUrl={imageUrl}
                fields={inspection.detected_fields}
                checks={inspection.compliance_checks}
                selectedField={selectedField}
                onSelectField={setSelectedField}
                panelLabel={imageList.length > 1 ? getPanelLabel(activeImage?.panel_type, selectedImageIndex) : undefined}
                activeImageIndex={selectedImageIndex}
              />
            </div>

            {/* Right: Table of Detected Fields */}
            <div className="space-y-6">
              {/* Manual Override Toast */}
              {overrideToast && (
                <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold animate-fadeIn">
                  <ShieldCheck className="w-4 h-4" />
                  {overrideToast}
                </div>
              )}
              <DetectedFieldsTable
                fields={inspection.detected_fields}
                checks={inspection.compliance_checks}
                selectedField={selectedField}
                onSelectField={setSelectedField}
                inspectionId={inspectionId}
                onFieldOverride={handleFieldOverride}
              />

              <ViolationsCard violations={inspection.violations} />
            </div>

          </div>

          {/* Raw OCR vs Normalized Comparison Drawer */}
          <RawOcrViewer
            ocrSummary={inspection.ocr_summary}
            fields={inspection.detected_fields}
          />

          {/* Detailed Legal Rule Checks Matrix */}
          <ComplianceChecksMatrix checks={inspection.compliance_checks} />
        </>
      )}

      {/* Human-in-the-Loop Review Queue Modal */}
      <ReviewQueueModal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        inspection={inspection}
        onReviewCompleted={(updated) => {
          setInspection(updated);
          setOverrideToast('Human review decision recorded and synced in audit trail ✓');
          setTimeout(() => setOverrideToast(null), 3500);
        }}
      />

      {/* Audit Pipeline Metadata Box */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-slate-400">
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-emerald-400" />
          <span>CV Model: <b className="text-slate-200">{inspection.cv_model_version || 'YOLO11-Legal'}</b></span>
        </div>
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-teal-400" />
          <span>OCR Engine: <b className="text-slate-200">{inspection.ocr_version || 'PaddleOCR Multilingual'}</b></span>
        </div>
        <div className="flex items-center space-x-2">
          <FileText className="w-4 h-4 text-blue-400" />
          <span>Rule Set: <b className="text-slate-200">{inspection.rule_set_version || 'LM-2026.1'}</b></span>
        </div>
      </div>

      {/* Statutory Legal Disclaimer */}
      <LegalDisclaimerBanner />

    </div>
  );
};
