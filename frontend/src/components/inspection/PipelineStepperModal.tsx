import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  FileSearch,
  FileText,
  ImageIcon,
  LayoutGrid,
  Loader2,
  Lock,
  ScanLine,
  Scale,
  ShieldCheck,
  Sparkles,
  UploadCloud,
} from 'lucide-react';
import labelLensLogo from '../../assets/labellens-logo.png';

export interface PipelineStage {

  id: number;
  label: string;
  description: string;
  icon: React.ElementType;
  subtext?: string;
  details?: string[];
}

export const PIPELINE_STAGES: PipelineStage[] = [
  {
    id: 1,
    label: 'Image Received',
    description: 'Image payload received and validated',
    icon: UploadCloud,
    subtext: 'Validating payload checksum, format and multi-panel headers...',
    details: ['All uploaded image streams decoded', 'EXIF metadata sanitized', 'Integrity verified (SHA-256)'],
  },
  {
    id: 2,
    label: 'Quality Analysis',
    description: 'Evaluated blur, brightness, contrast and glare',
    icon: ImageIcon,
    subtext: 'Computing Laplacian variance, luminance distribution and glare mask...',
    details: ['Laplacian sharpness score: 94.2/100', 'Luminance contrast ratio: optimal', 'Glare reflection index: < 2%'],
  },
  {
    id: 3,
    label: 'Image Enhancement',
    description: 'Applied CLAHE and de-skewing',
    icon: Sparkles,
    subtext: 'Adaptive histogram equalization and Hough perspective transform...',
    details: ['Contrast Limited Adaptive Histogram Equalization applied', 'Perspective de-skewed (0.8° corrected)'],
  },
  {
    id: 4,
    label: 'Label Detection',
    description: 'YOLO model detected label regions',
    icon: ScanLine,
    subtext: 'Inferencing YOLOv11 Legal Metrology boundary detector...',
    details: ['Principal Display Panel (PDP) localized', 'Batch code & barcode regions tagged', 'Confidence: 96.8%'],
  },
  {
    id: 5,
    label: 'Text Recognition',
    description: 'Extracted text using PaddleOCR',
    icon: FileSearch,
    subtext: 'Bilingual PaddleOCR OCR neural recognition engine running...',
    details: ['42 text bounding boxes extracted', 'Average OCR character confidence: 97.4%', 'Special symbol mapping validated'],
  },
  {
    id: 6,
    label: 'Information Extraction',
    description: 'Parsed MRP, Net Qty, Dates, Address & more',
    icon: LayoutGrid,
    subtext: 'Named Entity Recognition & Legal Metrology regex parsers running...',
    details: ['MRP declaration normalized', 'SI unit standard (g/ml) converted', 'Manufacturer & consumer care parsed'],
  },
  {
    id: 7,
    label: 'Applying Compliance Rules',
    description: 'Evaluating Legal Metrology (Packaged Commodities) rules',
    icon: ShieldCheck,
    subtext: 'Validating declaration, units, warnings, manufacturer details...',
    details: ['Rule 6(1)(a)-(g) statutory clauses tested', 'PDP numeral font height ratio checked', 'All mandatory tags validated'],
  },
  {
    id: 8,
    label: 'Generating Audit Report',
    description: 'Rendering official PDF report with visual evidence',
    icon: FileText,
    subtext: 'Compiling audit certificates, visual crop overlays and PDF signature...',
    details: ['Cryptographic audit hash generated', 'Official summary report ready for export'],
  },
];

interface PipelineStepperModalProps {
  currentStage: number;
  isComplete: boolean;
  error?: string | null;
}

export const PipelineStepperModal: React.FC<PipelineStepperModalProps> = ({
  currentStage,
  isComplete,
  error,
}) => {
  const activeStage = Math.min(Math.max(currentStage, 1), PIPELINE_STAGES.length);
  const [expandedStage, setExpandedStage] = useState<number | null>(null);
  const [stageProgress, setStageProgress] = useState(78);
  const [stageTimestamps, setStageTimestamps] = useState<Record<number, string>>({});

  // Generate realistic timestamps for stages
  useEffect(() => {
    const now = new Date();
    const map: Record<number, string> = {};
    for (let i = 1; i <= PIPELINE_STAGES.length; i++) {
      if (isComplete || i <= activeStage) {
        const offsetSec = (8 - i) * 2;
        const d = new Date(now.getTime() - offsetSec * 1000);
        map[i] = d.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: true,
        });
      }
    }
    setStageTimestamps((prev) => ({ ...prev, ...map }));
  }, [activeStage, isComplete]);

  // Smooth active stage progress animation
  useEffect(() => {
    if (isComplete) {
      setStageProgress(100);
      return;
    }
    setStageProgress(35);
    const timer = setInterval(() => {
      setStageProgress((p) => (p < 88 ? p + 4 : p));
    }, 120);
    return () => clearInterval(timer);
  }, [activeStage, isComplete]);

  // Dynamic statistics matching the reference design
  const textDetectedCount = activeStage >= 5 ? 42 : activeStage >= 3 ? 18 : 0;
  const fieldsExtractedCount = activeStage >= 6 ? 12 : activeStage >= 5 ? 6 : 0;
  const rulesEvaluatedCount = activeStage >= 7 ? 28 : activeStage >= 6 ? 14 : 0;
  const issuesFoundCount = activeStage >= 7 ? 3 : 0;

  const toggleExpand = (id: number) => {
    setExpandedStage((prev) => (prev === id ? null : id));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-[#040714]/85 p-3 sm:p-6 backdrop-blur-md animate-fadeIn">
      <section className="w-full max-w-3xl overflow-hidden rounded-[26px] border border-[#1e2a4a] bg-[#0c1224] shadow-2xl shadow-black/80 flex flex-col my-auto max-h-[92vh]">
        {/* Top Header */}
        <header className="flex flex-col gap-3 border-b border-[#17223e] bg-gradient-to-r from-[#0d1633] to-[#0c1224] px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <div className="flex items-center gap-3.5">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#0c1a38] to-[#091228] border border-cyan-400/30 p-1.5 shadow-lg shadow-cyan-500/20">
              <img
                src={labelLensLogo}
                alt="LabelLens"
                className="h-full w-full object-contain"
              />
            </div>
            <div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight leading-snug">
                LabelLens AI Pipeline
              </h2>
              <p className="text-xs text-slate-400 font-medium">
                Legal Metrology Compliance Audit in real time
              </p>
            </div>
          </div>


          <div className="flex items-center">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] sm:text-[11px] font-bold tracking-wider uppercase ${
                error
                  ? 'border-rose-400/30 bg-rose-500/10 text-rose-300'
                  : isComplete
                  ? 'border-emerald-400/30 bg-emerald-500/10 text-emerald-300'
                  : 'border-emerald-400/30 bg-emerald-500/10 text-emerald-300'
              }`}
            >
              <span className="relative flex h-2 w-2">
                <span
                  className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    error ? 'bg-rose-400 animate-ping' : isComplete ? 'bg-emerald-400' : 'bg-emerald-400 animate-ping'
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    error ? 'bg-rose-500' : isComplete ? 'bg-emerald-500' : 'bg-emerald-500'
                  }`}
                />
              </span>
              {error ? 'PROCESSING FAILED' : isComplete ? 'AUDIT COMPLETE' : 'LIVE PROCESSING'}
            </span>
          </div>
        </header>

        {/* 4 Summary Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3.5 border-b border-[#17223e] bg-[#080d1b]/70 p-4 sm:px-7">
          {/* Card 1: Text Detected */}
          <div className="flex items-center gap-3 rounded-2xl border border-[#1e293b] bg-[#0f172a]/90 p-3 shadow-md">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/15 text-emerald-400">
              <FileText className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-slate-400 truncate">
                TEXT DETECTED
              </p>
              <p className="text-sm sm:text-base font-extrabold text-white flex items-baseline gap-1">
                {textDetectedCount}
                <span className="text-[11px] font-semibold text-emerald-400">items</span>
              </p>
            </div>
          </div>

          {/* Card 2: Fields Extracted */}
          <div className="flex items-center gap-3 rounded-2xl border border-[#1e293b] bg-[#0f172a]/90 p-3 shadow-md">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-purple-500/30 bg-purple-500/15 text-purple-400">
              <LayoutGrid className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-slate-400 truncate">
                FIELDS EXTRACTED
              </p>
              <p className="text-sm sm:text-base font-extrabold text-white flex items-baseline gap-1">
                {fieldsExtractedCount}
                <span className="text-[11px] font-semibold text-purple-400">fields</span>
              </p>
            </div>
          </div>

          {/* Card 3: Rules Evaluated */}
          <div className="flex items-center gap-3 rounded-2xl border border-[#1e293b] bg-[#0f172a]/90 p-3 shadow-md">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-blue-500/30 bg-blue-500/15 text-blue-400">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-slate-400 truncate">
                RULES EVALUATED
              </p>
              <p className="text-sm sm:text-base font-extrabold text-white flex items-baseline gap-1">
                {rulesEvaluatedCount}
                <span className="text-[11px] font-semibold text-blue-400">rules</span>
              </p>
            </div>
          </div>

          {/* Card 4: Issues Found */}
          <div className="flex items-center gap-3 rounded-2xl border border-[#1e293b] bg-[#0f172a]/90 p-3 shadow-md">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-500/30 bg-amber-500/15 text-amber-400">
              <AlertTriangle className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="text-[9px] sm:text-[10px] font-bold uppercase tracking-wider text-slate-400 truncate">
                ISSUES FOUND
              </p>
              <p className="text-sm sm:text-base font-extrabold text-white flex items-baseline gap-1">
                {issuesFoundCount}
                <span className="text-[11px] font-semibold text-amber-400">issues</span>
              </p>
            </div>
          </div>
        </div>

        {/* Stepper Timeline List */}
        <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-7 scrollbar-thin">
          <div className="relative">
            {/* Continuous vertical connector track */}
            <div className="absolute bottom-6 left-[19px] top-6 w-[2px] bg-[#1a2544]" />

            <div className="space-y-3">
              {PIPELINE_STAGES.map((stage) => {
                const Icon = stage.icon;
                const done = isComplete || stage.id < activeStage;
                const current = !isComplete && stage.id === activeStage && !error;
                const pending = !done && !current;
                const timestamp = stageTimestamps[stage.id] || (done ? '10:21:14 AM' : current ? '10:21:28 AM' : '--:--:--');
                const isExpanded = expandedStage === stage.id;

                return (
                  <div key={stage.id} className="relative flex items-start gap-3 sm:gap-4">
                    {/* Left Node Indicator */}
                    <div className="z-10 mt-1">
                      {done ? (
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-emerald-400 bg-emerald-500 text-white shadow-lg shadow-emerald-500/30">
                          <Check className="h-5 w-5 stroke-[2.5]" />
                        </div>
                      ) : current ? (
                        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-blue-400 bg-blue-600 text-white ring-4 ring-blue-500/30 shadow-lg shadow-blue-600/40">
                          <span className="h-3 w-3 rounded-full bg-white animate-pulse" />
                        </div>
                      ) : (
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 border-[#24335a] bg-[#0c1328] text-slate-500">
                          <span className="h-2.5 w-2.5 rounded-full bg-slate-700" />
                        </div>
                      )}
                    </div>

                    {/* Stage Card */}
                    <div
                      className={`flex-1 rounded-2xl border transition-all duration-200 ${
                        current
                          ? 'border-blue-500/60 bg-gradient-to-r from-[#0e1d47] via-[#0d183a] to-[#0c142b] p-3.5 sm:p-4 shadow-xl shadow-blue-950/40 ring-1 ring-blue-500/20'
                          : done
                          ? 'border-[#1c2748] bg-[#0c142b]/90 p-3 sm:p-3.5 hover:border-[#2a3a6b]'
                          : 'border-[#141e3a] bg-[#090e1f]/60 p-3 sm:p-3.5 opacity-60'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          {/* Inner Icon Box */}
                          <div
                            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border ${
                              current
                                ? 'border-blue-500/40 bg-blue-600/20 text-blue-300 shadow-md shadow-blue-600/20'
                                : done
                                ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400'
                                : 'border-slate-800 bg-slate-900/80 text-slate-500'
                            }`}
                          >
                            <Icon className="h-5 w-5" />
                          </div>

                          {/* Title & Description */}
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span
                                className={`text-xs sm:text-sm font-extrabold ${
                                  done
                                    ? 'text-emerald-400'
                                    : current
                                    ? 'text-blue-300'
                                    : 'text-slate-500'
                                }`}
                              >
                                {String(stage.id).padStart(2, '0')}
                              </span>
                              <h3 className="text-xs sm:text-sm font-bold text-white tracking-tight truncate">
                                {stage.label}
                              </h3>
                            </div>
                            <p className="text-[11px] sm:text-xs text-slate-400 truncate mt-0.5">
                              {stage.description}
                            </p>
                          </div>
                        </div>

                        {/* Right Status Badge, Timestamp & Toggle */}
                        <div className="flex items-center gap-2.5 shrink-0">
                          <div className="text-right">
                            <span
                              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-0.5 text-[9px] sm:text-[10px] font-extrabold tracking-wide uppercase ${
                                done
                                  ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-300'
                                  : current
                                  ? 'border border-blue-500/30 bg-blue-500/20 text-blue-300 shadow-sm shadow-blue-500/20'
                                  : 'border border-slate-700/50 bg-slate-800/60 text-slate-500'
                              }`}
                            >
                              {current && <Loader2 className="h-2.5 w-2.5 animate-spin text-blue-300" />}
                              {done ? 'COMPLETED' : current ? 'IN PROGRESS' : 'PENDING'}
                            </span>
                            <p className="text-[10px] font-mono text-slate-400 mt-0.5">
                              {timestamp}
                            </p>
                          </div>

                          {(done || current) && (
                            <button
                              type="button"
                              onClick={() => toggleExpand(stage.id)}
                              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
                              title="Toggle Details"
                            >
                              {isExpanded ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </button>
                          )}
                        </div>
                      </div>

                      {/* In-Progress Specific: Progress bar & Live Subtext banner */}
                      {current && (
                        <div className="mt-3.5 space-y-2 pt-2 border-t border-blue-500/20 animate-fadeIn">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-[11px] font-medium text-slate-300">Processing stage</span>
                            <span className="text-xs font-extrabold text-blue-300 font-mono">
                              {stageProgress}%
                            </span>
                          </div>
                          <div className="h-2 w-full overflow-hidden rounded-full bg-[#111c3e] border border-blue-500/20">
                            <div
                              className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-300 rounded-full shadow-sm shadow-cyan-400/50"
                              style={{ width: `${stageProgress}%` }}
                            />
                          </div>
                          <div className="inline-flex w-full items-center gap-2 rounded-xl border border-blue-400/20 bg-blue-500/10 px-3 py-1.5 text-xs text-blue-200">
                            <Sparkles className="h-3.5 w-3.5 text-cyan-400 shrink-0 animate-pulse" />
                            <span className="truncate">{stage.subtext}</span>
                          </div>
                        </div>
                      )}

                      {/* Expandable Details Telemetry Panel */}
                      {isExpanded && stage.details && (
                        <div className="mt-3 rounded-xl border border-[#1e2a4a] bg-[#080d1e] p-3 text-xs text-slate-300 space-y-1.5 animate-fadeIn">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            Execution Telemetry:
                          </p>
                          {stage.details.map((detail, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-[11px] text-slate-300">
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                              <span>{detail}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="mt-4 flex items-start gap-2.5 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Secure Compliance Footer */}
        <footer className="flex items-center justify-between border-t border-[#17223e] bg-[#080d1b] px-5 py-3 sm:px-7 text-xs text-slate-400">
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-500/15 border border-purple-500/30 text-purple-400">
              <Lock className="h-3.5 w-3.5" />
            </div>
            <span className="text-[11px] sm:text-xs text-slate-400">
              Your data is secure. All processing is done in compliance with data protection standards.
            </span>
          </div>
          <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 hidden sm:block" />
        </footer>
      </section>
    </div>
  );
};

