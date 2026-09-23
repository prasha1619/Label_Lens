import React, { useRef, useEffect, useState, useCallback, useRef as _r } from 'react';
import {
  Camera, CameraOff, Pause, Play, RotateCcw, ChevronLeft,
  CheckCircle2, XCircle, AlertTriangle, MinusCircle,
  Zap, Eye, Package, ShieldCheck, AlertCircle, Loader2,
  Radio, Wifi, WifiOff, BarChart3, ClipboardList, Download,
  FileText, X, Printer, TrendingUp, TrendingDown, Activity,
  Calendar, Clock, Layers, BookOpen, ChevronRight, Info, Check
} from 'lucide-react';
import { API_BASE } from '../services/api';

type FieldStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'N_A';
type SystemState = 'IDLE' | 'SCANNING' | 'QUALITY_WARNING' | 'REVIEW' | 'RESULT';
type ActivePanel = 'front' | 'back' | 'side' | 'bottom';
type ProductCategory = 'packaged_commodity' | 'cosmetics_and_toiletries' | 'food_product' | 'pharmaceutical';

interface ARFieldOverlay {
  field_name: string;
  display_name: string;
  raw_text: string | null;
  normalized_value: string | null;
  unit: string | null;
  confidence: number;
  source_panel: string;
  status: FieldStatus;
  explanation: string;
  applicable_rule: string;
  has_conflict: boolean;
  bbox: [number, number, number, number];
  bbox_normalized: [number, number, number, number];
  crop_thumbnail: string | null;
}

interface ARPackage {
  package_id: string;
  confidence: number;
  bbox: number[];
  bbox_normalized: number[];
  label: string;
  is_active: boolean;
}

interface ARFrameResult {
  frame_id: string;
  timestamp: number;
  image_dimensions: { width: number; height: number };
  quality: { status: string; is_acceptable: boolean; blur_score: number; reasons: string[] };
  packages: ARPackage[];
  fields: ARFieldOverlay[];
  conflicts: any[];
  overall_status: string;
  compliance_score: number;
  hud_metrics: {
    total_packages: number;
    active_package_id: string;
    active_panel: string;
    pass_count: number;
    fail_count: number;
    review_count: number;
    na_count: number;
    system_state: SystemState;
    guidance_message: string;
  };
  processing_time_ms: number;
}

const STATUS_COLORS: Record<FieldStatus, { bg: string; border: string; text: string; glow: string }> = {
  PASS:   { bg: 'rgba(16,185,129,0.12)', border: '#10b981', text: '#34d399', glow: '0 0 12px rgba(16,185,129,0.5)' },
  FAIL:   { bg: 'rgba(239,68,68,0.12)',  border: '#ef4444', text: '#f87171', glow: '0 0 12px rgba(239,68,68,0.5)' },
  REVIEW: { bg: 'rgba(245,158,11,0.12)', border: '#f59e0b', text: '#fbbf24', glow: '0 0 12px rgba(245,158,11,0.5)' },
  N_A:    { bg: 'rgba(100,116,139,0.12)', border: '#64748b', text: '#94a3b8', glow: 'none' },
};

const PANEL_OPTIONS: { id: ActivePanel; label: string }[] = [
  { id: 'front',  label: 'Front' },
  { id: 'back',   label: 'Back' },
  { id: 'side',   label: 'Side' },
  { id: 'bottom', label: 'Bottom' },
];

const CATEGORY_OPTIONS: { id: ProductCategory; label: string }[] = [
  { id: 'packaged_commodity',       label: 'Packaged Commodity' },
  { id: 'cosmetics_and_toiletries', label: 'Cosmetics & Toiletries' },
  { id: 'food_product',             label: 'Food Product' },
  { id: 'pharmaceutical',           label: 'Pharmaceutical' },
];

const SCAN_INTERVAL_MS = 1500;

function StatusIcon({ status, size = 14 }: { status: FieldStatus; size?: number }) {
  const s = STATUS_COLORS[status] || STATUS_COLORS.N_A;
  if (status === 'PASS')   return <CheckCircle2  style={{ width: size, height: size, color: s.text }} />;
  if (status === 'FAIL')   return <XCircle       style={{ width: size, height: size, color: s.text }} />;
  if (status === 'REVIEW') return <AlertTriangle style={{ width: size, height: size, color: s.text }} />;
  return <MinusCircle style={{ width: size, height: size, color: s.text }} />;
}

/* ────────────────────────────────────────────────────────────────
   ARLiveReport – interactive full-screen compliance report modal
──────────────────────────────────────────────────────────────── */
interface ARLiveReportProps {
  result: ARFrameResult;
  productCategory: string;
  onClose: () => void;
  isLive: boolean;
  onToggleLive: () => void;
  onSavePdf: () => Promise<void>;
  isSavingPdf: boolean;
  savedInspectionId: string | null;
  accumulatedPanels?: any[];
}

function ARLiveReport({
  result,
  productCategory,
  onClose,
  isLive,
  onToggleLive,
  onSavePdf,
  isSavingPdf,
  savedInspectionId,
  accumulatedPanels = []
}: ARLiveReportProps) {
  const { fields, overall_status, compliance_score, hud_metrics: hud, quality, conflicts, timestamp } = result;
  const printRef = React.useRef<HTMLDivElement>(null);

  const scoreColor = compliance_score >= 80 ? '#10b981' : compliance_score >= 50 ? '#f59e0b' : '#ef4444';
  const scoreLabel = compliance_score >= 80 ? 'COMPLIANT' : compliance_score >= 50 ? 'PARTIAL' : 'NON-COMPLIANT';
  const scoreBg    = compliance_score >= 80 ? 'rgba(16,185,129,0.1)' : compliance_score >= 50 ? 'rgba(245,158,11,0.1)' : 'rgba(239,68,68,0.1)';
  const scoreBorder= compliance_score >= 80 ? '#10b981' : compliance_score >= 50 ? '#f59e0b' : '#ef4444';

  const categoryLabel = ({
    packaged_commodity:       'Packaged Commodity',
    cosmetics_and_toiletries: 'Cosmetics & Toiletries',
    food_product:             'Food Product',
    pharmaceutical:           'Pharmaceutical',
  } as any)[productCategory] || productCategory;

  const handlePrint = () => {
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<!DOCTYPE html><html><head><title>LabelLens AR Compliance Report</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background:#fff; color:#0f172a; margin:0; padding:32px; font-size:12px; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px; }
        .title { font-size: 20px; font-weight: 800; color: #0f172a; margin: 0; }
        .subtitle { font-size: 11px; color: #64748b; margin-top: 4px; }
        .audit-meta { text-align: right; font-size: 11px; color: #475569; }
        .score-banner { display: flex; align-items: center; justify-content: space-between; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; }
        .score-val { font-size: 28px; font-weight: 900; color: ${scoreColor}; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 800; text-transform: uppercase; }
        .badge-pass { background: #dcfce7; color: #15803d; }
        .badge-fail { background: #fee2e2; color: #b91c1c; }
        .badge-review { background: #fef3c7; color: #b45309; }
        .badge-na { background: #f1f5f9; color: #64748b; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th { background: #f1f5f9; text-align: left; padding: 8px 10px; font-size: 11px; font-weight: 700; color: #334155; border-bottom: 1px solid #cbd5e1; }
        td { padding: 8px 10px; font-size: 11px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
        .field-name { font-weight: 700; color: #0f172a; }
        .legal-ref { font-size: 10px; color: #64748b; margin-top: 2px; }
        .note { font-size: 10px; color: #475569; margin-top: 3px; font-style: italic; }
        .disclaimer { font-size: 9.5px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 12px; margin-top: 28px; line-height: 1.4; }
      </style></head><body>
      <div class="header">
        <div>
          <h1 class="title">LabelLens Legal Metrology AR Inspection Report</h1>
          <div class="subtitle">Official Statutory Label Compliance Audit Assessment</div>
        </div>
        <div class="audit-meta">
          <div><strong>Category:</strong> ${categoryLabel}</div>
          <div><strong>Timestamp:</strong> ${new Date(timestamp * 1000).toLocaleString()}</div>
          <div><strong>Active Panel:</strong> ${hud.active_panel}</div>
        </div>
      </div>

      <div class="score-banner">
        <div>
          <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #64748b;">Statutory Verdict</div>
          <div style="font-size: 16px; font-weight: 800; color: ${scoreColor}; margin-top: 2px;">${overall_status.replace(/_/g, ' ')}</div>
        </div>
        <div style="text-align: center;">
          <div style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: #64748b;">Compliance Score</div>
          <div class="score-val">${Math.round(compliance_score)}%</div>
        </div>
        <div style="text-align: right; font-size: 11px;">
          <div><strong style="color: #15803d;">Passed:</strong> ${hud.pass_count}</div>
          <div><strong style="color: #b91c1c;">Failed:</strong> ${hud.fail_count}</div>
          <div><strong style="color: #b45309;">Review:</strong> ${hud.review_count}</div>
        </div>
      </div>

      <h2>Statutory Declarations & Findings</h2>
      <table>
        <thead>
          <tr>
            <th style="width: 22%;">Declaration</th>
            <th style="width: 25%;">Extracted Value</th>
            <th style="width: 14%;">Panel</th>
            <th style="width: 12%;">Status</th>
            <th style="width: 27%;">Legal Reference & Findings</th>
          </tr>
        </thead>
        <tbody>
          ${fields.map(f => {
            const bCls = f.status === 'PASS' ? 'badge-pass' : f.status === 'FAIL' ? 'badge-fail' : f.status === 'REVIEW' ? 'badge-review' : 'badge-na';
            return `<tr>
              <td><div class="field-name">${f.display_name}</div></td>
              <td><code>${f.normalized_value || f.raw_text || '[Not Detected]'}</code></td>
              <td>${f.source_panel}</td>
              <td><span class="badge ${bCls}">${f.status}</span></td>
              <td>
                <div class="legal-ref">${f.applicable_rule}</div>
                <div class="note">${f.explanation}</div>
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>

      ${conflicts.length > 0 ? `
        <h2>Cross-Panel Evidence Discrepancies</h2>
        <table>
          <thead><tr><th>Field</th><th>Discrepancy Details</th></tr></thead>
          <tbody>
            ${conflicts.map((c: any) => `<tr><td><strong>${c.field_name || 'Conflict'}</strong></td><td>${c.description || c.reason || JSON.stringify(c)}</td></tr>`).join('')}
          </tbody>
        </table>
      ` : ''}

      <div class="disclaimer">
        <strong>Statutory Legal Metrology Notice:</strong> This audit report was compiled using the LabelLens Augmented Reality Inspection Pipeline under the Legal Metrology (Packaged Commodities) Rules, 2011. This preliminary assessment serves regulatory compliance verification purposes. Official administrative penalties or enforcement actions are governed by statutory verification by a designated Legal Metrology Officer.
      </div>
      </body></html>`);
    w.document.close();
    w.print();
  };

  const exportReport = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ar_report_${result.frame_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const passFields   = fields.filter(f => f.status === 'PASS');
  const failFields   = fields.filter(f => f.status === 'FAIL');
  const reviewFields = fields.filter(f => f.status === 'REVIEW');
  const naFields     = fields.filter(f => f.status === 'N_A');

  return (
    <div
      className="fixed inset-0 z-[200] flex flex-col"
      style={{ fontFamily: "'Inter','Segoe UI',sans-serif", background: 'rgba(4,8,18,0.97)', backdropFilter: 'blur(20px)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/8 flex-shrink-0 bg-black/40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
            <FileText style={{ width: 20, height: 20, color: '#fff' }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-base font-black text-white tracking-wide">AR Compliance Report</p>
              <button
                onClick={onToggleLive}
                className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border transition-all ${
                  isLive
                    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/25'
                    : 'bg-amber-500/15 text-amber-300 border-amber-500/40 hover:bg-amber-500/25'
                }`}
                title={isLive ? 'Click to freeze current snapshot' : 'Click to resume live report'}
              >
                {isLive ? (
                  <>
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>LIVE FEED</span>
                  </>
                ) : (
                  <>
                    <Pause style={{ width: 10, height: 10 }} />
                    <span>FROZEN SNAPSHOT</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              {categoryLabel} · Scanned {new Date(timestamp * 1000).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onSavePdf}
            disabled={isSavingPdf}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-600/30 transition-all active:scale-95 disabled:opacity-50"
            title="Persist AR scan and download official PDF report"
          >
            {isSavingPdf ? (
              <>
                <Loader2 style={{ width: 14, height: 14 }} className="animate-spin" />
                <span>Generating PDF...</span>
              </>
            ) : (
              <>
                <Download style={{ width: 14, height: 14 }} />
                <span>Official PDF</span>
              </>
            )}
          </button>
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 border border-slate-600/50 text-slate-200 transition-all active:scale-95"
          >
            <Printer style={{ width: 14, height: 14 }} /> Print Report
          </button>
          <button
            onClick={exportReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all active:scale-95"
          >
            <Download style={{ width: 14, height: 14 }} /> Export JSON
          </button>
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 border border-slate-600/50 text-slate-300 transition-all active:scale-95"
          >
            <X style={{ width: 14, height: 14 }} /> Close
          </button>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6" style={{ scrollbarWidth: 'thin', scrollbarColor: '#1e2d4d transparent' }}>

        {/* Persistence feedback alert */}
        {savedInspectionId && (
          <div className="flex items-center justify-between rounded-xl p-3.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs shadow-lg shadow-emerald-500/10">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 style={{ width: 18, height: 18, color: '#34d399', flexShrink: 0 }} />
              <span>
                AR Inspection archived to database with Audit ID: <strong className="font-mono text-white">#{savedInspectionId}</strong>. The official statutory PDF report has been generated.
              </span>
            </div>
            <a
              href={`${API_BASE}/inspections/${savedInspectionId}/report`}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold transition-all shadow"
            >
              Download PDF Again &rarr;
            </a>
          </div>
        )}

        {/* Score Hero Banner */}
        <div className="rounded-2xl border p-6 flex items-center gap-6" style={{ background: scoreBg, borderColor: scoreBorder + '55' }}>
          <div className="text-center flex-shrink-0">
            <div className="text-[9px] text-slate-400 font-bold tracking-widest uppercase mb-1">Compliance Score</div>
            <div className="text-6xl font-black font-mono" style={{ color: scoreColor }}>{Math.round(compliance_score)}%</div>
            <div className="mt-1 px-3 py-1 rounded-full text-[10px] font-black tracking-widest" style={{ background: scoreColor + '22', color: scoreColor, border: '1px solid ' + scoreColor + '44' }}>{scoreLabel}</div>
          </div>
          <div className="flex-1">
            {/* Score bar */}
            <div className="mb-4">
              <div className="h-3 rounded-full bg-slate-800/80 overflow-hidden">
                <div className="h-full rounded-full transition-all duration-700" style={{ width: compliance_score + '%', background: `linear-gradient(90deg, ${scoreColor}88, ${scoreColor})` }} />
              </div>
            </div>
            {/* Stat grid */}
            <div className="grid grid-cols-4 gap-3">
              {[
                { label: 'Passed',  count: hud.pass_count,   color: '#10b981', icon: TrendingUp },
                { label: 'Failed',  count: hud.fail_count,   color: '#ef4444', icon: TrendingDown },
                { label: 'Review',  count: hud.review_count, color: '#f59e0b', icon: AlertTriangle },
                { label: 'N/A',     count: hud.na_count,     color: '#64748b', icon: MinusCircle },
              ].map(m => (
                <div key={m.label} className="rounded-xl p-3 text-center border border-white/5" style={{ background: m.color + '11' }}>
                  <div className="text-2xl font-black" style={{ color: m.color }}>{m.count}</div>
                  <div className="text-[9px] font-bold uppercase tracking-wide" style={{ color: m.color + 'aa' }}>{m.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex-shrink-0 space-y-2 text-[10px] text-slate-400">
            <div className="flex items-center gap-2"><Activity style={{ width: 12, height: 12 }} /><span>Panel: <b className="text-white">{hud.active_panel}</b></span></div>
            <div className="flex items-center gap-2"><Package style={{ width: 12, height: 12 }} /><span>Packages: <b className="text-white">{hud.total_packages}</b></span></div>
            <div className="flex items-center gap-2"><Clock style={{ width: 12, height: 12 }} /><span>Processed in <b className="text-white">{result.processing_time_ms.toFixed(0)}ms</b></span></div>
            <div className="flex items-center gap-2"><Layers style={{ width: 12, height: 12 }} /><span>Fields: <b className="text-white">{fields.length}</b></span></div>
          </div>
        </div>

        {/* Panel Coverage Breakdown */}
        <div className="flex items-center justify-between gap-3 rounded-xl px-4 py-3 bg-slate-900/60 border border-white/5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Layers style={{ width: 14, height: 14, color: '#a78bfa' }} />
            <span>Multi-Panel Audit Coverage:</span>
          </div>
          <div className="flex items-center gap-2">
            {(['front', 'back', 'side', 'bottom'] as const).map(p => {
              const isActive = hud.active_panel.toLowerCase().includes(p);
              const isRecorded = (accumulatedPanels || []).some((ap: any) => ap.panel_type === p);
              const hasData = isActive || isRecorded;
              return (
                <span
                  key={p}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider ${
                    hasData
                      ? 'bg-purple-600/25 text-purple-200 border border-purple-500/40 shadow-sm'
                      : 'bg-slate-800/40 text-slate-500 border border-white/5'
                  }`}
                >
                  {hasData && <Check style={{ width: 11, height: 11, color: '#c084fc' }} />}
                  {p} panel
                </span>
              );
            })}
          </div>
        </div>

        {/* Image quality banner */}
        {!quality.is_acceptable && (
          <div className="flex items-start gap-3 rounded-xl p-4 bg-amber-500/10 border border-amber-500/40">
            <AlertCircle style={{ width: 16, height: 16, color: '#fbbf24', flexShrink: 0, marginTop: 2 }} />
            <div>
              <p className="text-xs font-bold text-amber-300">Image Quality Warning</p>
              <p className="text-[11px] text-amber-200/70 mt-0.5">{quality.reasons.join('; ')} — results may be unreliable. Re-scan with better lighting and steady camera.</p>
            </div>
          </div>
        )}

        {/* Guidance */}
        <div className="flex items-start gap-3 rounded-xl p-4 bg-purple-500/8 border border-purple-500/20">
          <Info style={{ width: 14, height: 14, color: '#a78bfa', flexShrink: 0, marginTop: 1 }} />
          <p className="text-[11px] text-purple-200/80">{hud.guidance_message}</p>
        </div>

        {/* Failed fields – highlighted first */}
        {failFields.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <XCircle style={{ width: 14, height: 14, color: '#f87171' }} />
              <h2 className="text-xs font-black text-red-400 uppercase tracking-widest">Non-Compliant Declarations ({failFields.length})</h2>
            </div>
            <div className="space-y-2">
              {failFields.map(f => <FieldCard key={f.field_name} field={f} />)}
            </div>
          </section>
        )}

        {/* Review fields */}
        {reviewFields.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle style={{ width: 14, height: 14, color: '#fbbf24' }} />
              <h2 className="text-xs font-black text-amber-400 uppercase tracking-widest">Requires Review ({reviewFields.length})</h2>
            </div>
            <div className="space-y-2">
              {reviewFields.map(f => <FieldCard key={f.field_name} field={f} />)}
            </div>
          </section>
        )}

        {/* Passed fields */}
        {passFields.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 style={{ width: 14, height: 14, color: '#34d399' }} />
              <h2 className="text-xs font-black text-emerald-400 uppercase tracking-widest">Compliant Declarations ({passFields.length})</h2>
            </div>
            <div className="space-y-2">
              {passFields.map(f => <FieldCard key={f.field_name} field={f} />)}
            </div>
          </section>
        )}

        {/* N/A fields */}
        {naFields.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <MinusCircle style={{ width: 14, height: 14, color: '#94a3b8' }} />
              <h2 className="text-xs font-black text-slate-400 uppercase tracking-widest">Not Applicable ({naFields.length})</h2>
            </div>
            <div className="space-y-2">
              {naFields.map(f => <FieldCard key={f.field_name} field={f} />)}
            </div>
          </section>
        )}

        {/* Conflicts */}
        {conflicts.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle style={{ width: 14, height: 14, color: '#fb923c' }} />
              <h2 className="text-xs font-black text-orange-400 uppercase tracking-widest">Cross-Panel Conflicts ({conflicts.length})</h2>
            </div>
            <div className="space-y-2">
              {conflicts.map((c: any, i: number) => (
                <div key={i} className="rounded-xl p-4 border border-orange-500/30 bg-orange-500/8">
                  <p className="text-[11px] font-bold text-orange-300">{c.field_name || 'Conflict'}</p>
                  <p className="text-[10px] text-slate-400 mt-1">{c.description || c.reason || JSON.stringify(c)}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Legal disclaimer */}
        <div className="rounded-xl p-4 bg-slate-800/40 border border-slate-700/40">
          <div className="flex items-start gap-2">
            <BookOpen style={{ width: 13, height: 13, color: '#64748b', flexShrink: 0, marginTop: 2 }} />
            <p className="text-[10px] text-slate-500 leading-relaxed">
              <span className="font-bold text-slate-400">Legal Disclaimer:</span> This report is generated by an AI-assisted preliminary compliance scanner under the Legal Metrology (Packaged Commodities) Rules, 2011. It is intended as a screening tool only. Official enforcement actions, recalls, or regulatory decisions must be taken by a Licensed Legal Metrology Inspector following physical verification of the packaged commodity.
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}

/* FieldCard sub-component for the report */
function FieldCard({ field }: { field: ARFieldOverlay }) {
  const [expanded, setExpanded] = useState(false);
  const sc = STATUS_COLORS[field.status] || STATUS_COLORS.N_A;
  return (
    <div
      className="rounded-xl border overflow-hidden transition-all"
      style={{ background: sc.bg, borderColor: sc.border + '55' }}
    >
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2.5">
          <StatusIcon status={field.status} size={14} />
          <span className="text-xs font-bold text-white">{field.display_name}</span>
          {field.has_conflict && (
            <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-black">CONFLICT</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-300 max-w-[160px] truncate">
            {field.normalized_value || field.raw_text || '—'}
          </span>
          <span className="text-[9px] px-2 py-0.5 rounded font-black" style={{ background: sc.border + '22', color: sc.text, border: '1px solid ' + sc.border + '44' }}>{field.status}</span>
          <ChevronRight style={{ width: 12, height: 12, color: '#64748b', transform: expanded ? 'rotate(90deg)' : 'none', transition: 'transform 0.2s' }} />
        </div>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t" style={{ borderColor: sc.border + '33' }}>
          {/* Row: value / raw / unit */}
          <div className="grid grid-cols-3 gap-3 pt-3">
            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wide font-bold mb-0.5">Normalised Value</p>
              <p className="text-[11px] text-white font-mono">{field.normalized_value || '—'}</p>
            </div>
            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wide font-bold mb-0.5">Raw OCR Text</p>
              <p className="text-[11px] text-slate-300 font-mono">{field.raw_text || '—'}</p>
            </div>
            <div>
              <p className="text-[9px] text-slate-500 uppercase tracking-wide font-bold mb-0.5">Unit</p>
              <p className="text-[11px] text-slate-300">{field.unit || '—'}</p>
            </div>
          </div>
          {/* Confidence */}
          <div>
            <div className="flex justify-between text-[9px] text-slate-500 mb-1">
              <span>OCR Confidence</span>
              <span className="font-bold" style={{ color: field.confidence >= 0.8 ? '#10b981' : field.confidence >= 0.5 ? '#f59e0b' : '#ef4444' }}>{Math.round(field.confidence * 100)}%</span>
            </div>
            <div className="h-1 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full" style={{ width: (field.confidence * 100) + '%', background: field.confidence >= 0.8 ? '#10b981' : field.confidence >= 0.5 ? '#f59e0b' : '#ef4444' }} />
            </div>
          </div>
          {/* Explanation */}
          <div className="rounded-lg p-3 bg-black/30 border border-white/5">
            <p className="text-[9px] text-slate-500 uppercase tracking-wide font-bold mb-1">Inspector Note</p>
            <p className="text-[11px] text-slate-200 leading-relaxed">{field.explanation}</p>
          </div>
          {/* Legal ref */}
          <div className="flex items-start gap-2">
            <BookOpen style={{ width: 11, height: 11, color: '#a78bfa', flexShrink: 0, marginTop: 2 }} />
            <p className="text-[10px] text-purple-300">{field.applicable_rule}</p>
          </div>
          {/* Source + thumbnail */}
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <p className="text-[9px] text-slate-500 uppercase tracking-wide font-bold mb-0.5">Source Panel</p>
              <p className="text-[10px] text-slate-300">{field.source_panel}</p>
            </div>
            {field.crop_thumbnail && (
              <div>
                <p className="text-[9px] text-slate-500 uppercase tracking-wide font-bold mb-1">OCR Region</p>
                <img src={field.crop_thumbnail} alt="crop" className="rounded-lg border border-white/10 max-h-14 object-contain" style={{ maxWidth: 120 }} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

interface ARInspectionPageProps { onBack: () => void; }

export const ARInspectionPage: React.FC<ARInspectionPageProps> = ({ onBack }) => {
  const videoRef    = useRef<HTMLVideoElement>(null);
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const overlayRef  = useRef<HTMLCanvasElement>(null);
  const streamRef   = useRef<MediaStream | null>(null);
  const intervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const accPanelsRef = useRef<any[]>([]);
  const isAnalyzingRef = useRef(false);

  const [cameraActive, setCameraActive]       = useState(false);
  const [paused, setPaused]                   = useState(false);
  const [isAnalyzing, setIsAnalyzing]         = useState(false);
  const [cameraError, setCameraError]         = useState<string | null>(null);
  const [lastError, setLastError]             = useState<string | null>(null);
  const [activePanel, setActivePanel]         = useState<ActivePanel>('front');
  const [productCategory, setProductCategory] = useState<ProductCategory>('packaged_commodity');
  const [lastResult, setLastResult]           = useState<ARFrameResult | null>(null);
  const [frameCount, setFrameCount]           = useState(0);
  const [isConnected, setIsConnected]         = useState(true);
  const [selectedField, setSelectedField]     = useState<ARFieldOverlay | null>(null);
  const [showSidebar, setShowSidebar]         = useState(true);
  const [sessionLog, setSessionLog]           = useState<ARFrameResult[]>([]);
  const [showReport, setShowReport]           = useState(false);
  const [reportFrozenResult, setReportFrozenResult] = useState<ARFrameResult | null>(null);
  const [isLiveReport, setIsLiveReport]       = useState(true);
  const [isSavingPdf, setIsSavingPdf]         = useState(false);
  const [savedInspectionId, setSavedInspectionId] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const isSavingPdfRef                        = useRef(false);

  const startCamera = useCallback(async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); }
      setCameraActive(true);
    } catch (err: any) {
      setCameraError(err.message || 'Camera access denied.');
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (intervalRef.current) clearTimeout(intervalRef.current);
    intervalRef.current = null;
    isAnalyzingRef.current = false;
    setIsAnalyzing(false);
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setCameraActive(false);
    setPaused(false);
    setLastResult(null);
    setLastError(null);
    accPanelsRef.current = [];
  }, []);

  const drawOverlay = useCallback((result: ARFrameResult, W: number, H: number) => {
    const ov = overlayRef.current;
    if (!ov) return;
    ov.width = W; ov.height = H;
    const ctx = ov.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, W, H);

    result.packages.forEach(pkg => {
      const n = pkg.bbox_normalized;
      const x1 = n[0]*W, y1 = n[1]*H, x2 = n[2]*W, y2 = n[3]*H;
      ctx.strokeStyle = pkg.is_active ? '#8b5cf6' : '#4b5563';
      ctx.lineWidth = 2; ctx.setLineDash([8,4]);
      ctx.strokeRect(x1, y1, x2-x1, y2-y1);
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(139,92,246,0.85)';
      ctx.fillRect(x1, Math.max(0, y1-20), Math.min(180, x2-x1), 20);
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px Inter,sans-serif';
      ctx.fillText(`${pkg.label} ${Math.round(pkg.confidence*100)}%`, x1+4, Math.max(14, y1-5));
    });

    result.fields.forEach(field => {
      const sc = STATUS_COLORS[field.status] || STATUS_COLORS.N_A;
      const n = field.bbox_normalized;
      const x1=n[0]*W, y1=n[1]*H, x2=n[2]*W, y2=n[3]*H;
      const bw=x2-x1, bh=y2-y1;
      if (bw<5||bh<5) return;
      ctx.fillStyle = sc.bg; ctx.fillRect(x1,y1,bw,bh);
      ctx.strokeStyle = sc.border; ctx.lineWidth=1.5;
      ctx.strokeRect(x1,y1,bw,bh);
      const cs=8; ctx.lineWidth=2;
      ([[x1,y1,1,1],[x2,y1,-1,1],[x1,y2,1,-1],[x2,y2,-1,-1]] as [number,number,number,number][]).forEach(([cx,cy,dx,dy]) => {
        ctx.beginPath(); ctx.moveTo(cx, cy+dy*cs); ctx.lineTo(cx,cy); ctx.lineTo(cx+dx*cs,cy);
        ctx.strokeStyle=sc.border; ctx.stroke();
      });
      const lbl = field.display_name.substring(0,16);
      const pw=Math.min(110,bw), ph=15, px=x1, py=Math.max(0,y1-ph);
      ctx.fillStyle=sc.border;
      ctx.beginPath(); (ctx as any).roundRect(px,py,pw,ph,3); ctx.fill();
      ctx.fillStyle='#000'; ctx.font='bold 9px Inter,sans-serif';
      ctx.fillText(lbl, px+3, py+10);
    });
  }, []);

  const captureAndAnalyze = useCallback(async () => {
    if (isAnalyzingRef.current || !videoRef.current || !canvasRef.current || paused) return;
    const video = videoRef.current;
    if (video.readyState < 2 || !video.videoWidth || !video.videoHeight) return;

    isAnalyzingRef.current = true;
    setIsAnalyzing(true);

    const canvas = canvasRef.current;
    const maxDim = 960;
    let w = video.videoWidth;
    let h = video.videoHeight;
    if (Math.max(w, h) > maxDim) {
      const scale = maxDim / Math.max(w, h);
      w = Math.round(w * scale);
      h = Math.round(h * scale);
    }
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      isAnalyzingRef.current = false;
      setIsAnalyzing(false);
      return;
    }
    ctx.drawImage(video, 0, 0, w, h);

    return new Promise<void>((resolve) => {
      canvas.toBlob(async (blob) => {
        if (!blob) {
          isAnalyzingRef.current = false;
          setIsAnalyzing(false);
          resolve();
          return;
        }
        const fd = new FormData();
        fd.append('file', blob, 'frame.jpg');
        fd.append('active_panel', activePanel);
        fd.append('package_id', 'Package #1');
        fd.append('product_category', productCategory);
        fd.append('accumulated_panels_json', JSON.stringify(accPanelsRef.current.slice(-3)));
        fd.append('is_demo', 'false');
        try {
          const res = await fetch(`${API_BASE}/inspections/ar-frame`, { method: 'POST', body: fd, credentials: 'include' });
          if (!res.ok) {
            setIsConnected(false);
            setLastError(`Backend responded with HTTP ${res.status}: ${res.statusText}`);
            return;
          }
          setIsConnected(true);
          setLastError(null);
          const data: ARFrameResult = await res.json();
          setLastResult(data);
          setFrameCount(c => c + 1);
          setSessionLog(prev => [data, ...prev].slice(0, 50));
          if (data.fields.length > 0) {
            const fm: Record<string, any> = {};
            data.fields.forEach(f => { fm[f.field_name] = f; });
            accPanelsRef.current = [
              ...accPanelsRef.current.filter(p => p.panel_type !== activePanel),
              { panel_type: activePanel, fields: fm }
            ].slice(-4);
          }
          drawOverlay(data, canvas.width, canvas.height);
        } catch (err: any) {
          setIsConnected(false);
          setLastError(err.message || 'Unable to connect to backend server');
        } finally {
          isAnalyzingRef.current = false;
          setIsAnalyzing(false);
          resolve();
        }
      }, 'image/jpeg', 0.85);
    });
  }, [paused, activePanel, productCategory, drawOverlay]);

  useEffect(() => {
    let timer: any = null;
    let isSubscribed = true;

    const scheduleNext = async () => {
      if (!isSubscribed) return;
      if (cameraActive && !paused) {
        await captureAndAnalyze();
      }
      if (isSubscribed && cameraActive && !paused) {
        timer = setTimeout(scheduleNext, SCAN_INTERVAL_MS);
      }
    };

    if (cameraActive && !paused) {
      scheduleNext();
    }

    return () => {
      isSubscribed = false;
      if (timer) clearTimeout(timer);
    };
  }, [cameraActive, paused, captureAndAnalyze]);

  useEffect(() => () => stopCamera(), [stopCamera]);
  useEffect(() => { accPanelsRef.current = []; }, [activePanel]);

  const exportLog = () => {
    const blob = new Blob([JSON.stringify(sessionLog, null, 2)], { type:'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href=url; a.download=`ar_session_${Date.now()}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const handleOpenReport = useCallback(async () => {
    if (lastResult) {
      setReportFrozenResult(lastResult);
      setShowReport(true);
      return;
    }

    if (!cameraActive) {
      await startCamera();
    }

    setIsGeneratingReport(true);
    try {
      await captureAndAnalyze();
      setShowReport(true);
    } catch (err) {
      console.error('Failed to capture frame for report:', err);
    } finally {
      setIsGeneratingReport(false);
    }
  }, [lastResult, cameraActive, startCamera, captureAndAnalyze]);

  const handleSavePdf = useCallback(async () => {
    if (isSavingPdfRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    setIsSavingPdf(true);
    isSavingPdfRef.current = true;

    try {
      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', 0.9);
      });

      if (!blob) {
        throw new Error('No frame available to save inspection.');
      }

      const fd = new FormData();
      fd.append('file', blob, 'ar_scan_frame.jpg');
      fd.append('active_panel', activePanel);
      fd.append('package_id', 'Package #1');
      fd.append('product_category', productCategory);
      fd.append('accumulated_panels_json', JSON.stringify(accPanelsRef.current));
      fd.append('is_demo', 'false');

      const res = await fetch(`${API_BASE}/inspections/ar-save`, {
        method: 'POST',
        body: fd,
        credentials: 'include'
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Failed to save AR inspection (${res.status}): ${errText}`);
      }

      const data = await res.json();
      setSavedInspectionId(data.id);

      // Trigger automatic PDF report download
      const reportRes = await fetch(`${API_BASE}/inspections/${data.id}/report`, {
        credentials: 'include'
      });
      if (reportRes.ok) {
        const pdfBlob = await reportRes.blob();
        const pdfUrl = URL.createObjectURL(pdfBlob);
        const link = document.createElement('a');
        link.href = pdfUrl;
        link.download = `LabelLens_AR_Report_${data.id.substring(0, 8)}.pdf`;
        link.click();
        URL.revokeObjectURL(pdfUrl);
      } else {
        window.open(`${API_BASE}/inspections/${data.id}/report`, '_blank');
      }
    } catch (err: any) {
      console.error('Error saving AR report:', err);
      alert(err.message || 'Failed to download official PDF report.');
    } finally {
      setIsSavingPdf(false);
      isSavingPdfRef.current = false;
    }
  }, [activePanel, productCategory]);

  const hud = lastResult?.hud_metrics;
  const quality = lastResult?.quality;
  const overallStatus = lastResult?.overall_status || 'UNKNOWN';
  const complianceScore = lastResult?.compliance_score ?? null;
  const fields = lastResult?.fields || [];

  const statusBorderClass: Record<string,string> = {
    COMPLIANT:     'border-emerald-500/50 text-emerald-300',
    NON_COMPLIANT: 'border-red-500/50 text-red-300',
    REVIEW:        'border-amber-500/50 text-amber-300',
    UNKNOWN:       'border-purple-500/30 text-purple-300',
  };
  const borderCls = statusBorderClass[overallStatus] || statusBorderClass.UNKNOWN;
  const scoreColor = complianceScore !== null
    ? (complianceScore>=80 ? '#10b981' : complianceScore>=50 ? '#f59e0b' : '#ef4444')
    : '#94a3b8';

  return (
    <div className="fixed inset-0 bg-[#040812] text-white flex flex-col z-[100] overflow-hidden" style={{fontFamily:"'Inter','Segoe UI',sans-serif"}}>

      {/* Top HUD */}
      <div className="flex items-center justify-between px-4 py-2 bg-black/60 backdrop-blur-md border-b border-white/5 z-20 flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="flex items-center gap-1 text-xs font-semibold text-purple-400 hover:text-purple-200 px-2 py-1 rounded-lg hover:bg-purple-500/10 transition-colors">
            <ChevronLeft style={{width:16,height:16}} /> Back
          </button>
          <div className="w-px h-5 bg-white/10"/>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-purple-500/30">
              <Eye style={{width:14,height:14,color:'#fff'}}/>
            </div>
            <div>
              <p className="text-xs font-bold text-white tracking-wide">AR Inspection Mode</p>
              <p className="text-[10px] text-slate-400">Real-time compliance overlay</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {cameraActive && (
            <>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"/>
                <span className="text-[10px] font-bold text-red-400 tracking-widest">LIVE</span>
              </span>
              <span className="text-[10px] text-slate-400 font-mono">{frameCount} frames</span>
              {isAnalyzing && (
                <span className="flex items-center gap-1 text-[10px] text-cyan-400 font-mono animate-pulse">
                  <Loader2 style={{width: 10, height: 10}} className="animate-spin"/> Scanning...
                </span>
              )}
              {isConnected
                ? <span title="Backend connected"><Wifi style={{width:12,height:12,color:'#34d399'}}/></span>
                : <span title="Backend disconnected"><WifiOff style={{width:12,height:12,color:'#f87171'}}/></span>}
              {lastResult && <span className="text-[10px] text-slate-400 font-mono">{lastResult.processing_time_ms.toFixed(0)}ms</span>}
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleOpenReport}
            disabled={isGeneratingReport}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white shadow-md shadow-purple-600/30 transition-all active:scale-95 disabled:opacity-50"
            title="View Compliance Report"
          >
            {isGeneratingReport ? (
              <Loader2 style={{ width: 12, height: 12 }} className="animate-spin" />
            ) : (
              <FileText style={{ width: 12, height: 12 }} />
            )}
            <span>Report</span>
            {lastResult && (
              <span className="px-1.5 py-0.2 rounded text-[9px] font-black bg-black/40 text-purple-200">
                {Math.round(lastResult.compliance_score)}%
              </span>
            )}
          </button>
          {sessionLog.length > 0 && (
            <button onClick={exportLog} className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-600/50 text-slate-300 transition-all">
              <Download style={{width:12,height:12}}/> Export
            </button>
          )}
          <button onClick={() => setShowSidebar(s => !s)} className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 border border-slate-600/50 text-slate-300 transition-all">
            <BarChart3 style={{width:12,height:12}}/> {showSidebar ? 'Hide' : 'Show'} Panel
          </button>
        </div>
      </div>

      {/* Main */}
      <div className="flex flex-1 overflow-hidden">

        {/* Camera Area */}
        <div className="relative flex-1 bg-black overflow-hidden">
          <video ref={videoRef} autoPlay playsInline muted
            className={`absolute inset-0 w-full h-full object-cover transition-opacity ${cameraActive ? 'opacity-100' : 'opacity-0'}`}/>
          <canvas ref={canvasRef} className="hidden"/>
          <canvas ref={overlayRef}
            className={`absolute inset-0 w-full h-full pointer-events-none ${cameraActive ? 'opacity-100' : 'opacity-0'}`}
            style={{objectFit:'cover'}}/>

          {!cameraActive && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 bg-gradient-to-b from-[#060c24] to-[#030611]">
              <div className="absolute inset-0 opacity-[0.04]" style={{backgroundImage:'linear-gradient(rgba(139,92,246,0.5) 1px,transparent 1px),linear-gradient(90deg,rgba(139,92,246,0.5) 1px,transparent 1px)',backgroundSize:'40px 40px'}}/>
              <div className="relative z-10 flex flex-col items-center gap-5 max-w-xs text-center">
                <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-purple-600/30 to-cyan-600/20 border border-purple-500/30 flex items-center justify-center shadow-2xl shadow-purple-500/20">
                  <Camera style={{width:40,height:40,color:'#a78bfa'}}/>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white mb-1">AR Inspection Mode</h2>
                  <p className="text-sm text-slate-400">Point your camera at a packaged commodity. LabelLens will detect the package, run bilingual OCR, and overlay real-time compliance status.</p>
                </div>
                {cameraError && (
                  <div className="flex items-center gap-2 bg-red-900/30 border border-red-500/40 rounded-xl px-4 py-2.5 text-sm text-red-300">
                    <CameraOff style={{width:16,height:16,flexShrink:0}}/> <span>{cameraError}</span>
                  </div>
                )}
                <button onClick={startCamera} className="flex items-center gap-2 px-8 py-3.5 rounded-2xl bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-bold shadow-xl shadow-purple-600/40 transition-all duration-200 hover:scale-105 text-sm">
                  <Camera style={{width:20,height:20}}/> Start AR Inspection
                </button>
                <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
                  <ShieldCheck style={{width:12,height:12,color:'#10b981'}}/> Camera feed processed locally
                </p>
              </div>
            </div>
          )}

          {cameraActive && (
            <>
              {/* Corner brackets */}
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-4 left-4 w-8 h-8 border-t-2 border-l-2 border-purple-400/60 rounded-tl-sm"/>
                <div className="absolute top-4 right-4 w-8 h-8 border-t-2 border-r-2 border-purple-400/60 rounded-tr-sm"/>
                <div className="absolute bottom-[104px] left-4 w-8 h-8 border-b-2 border-l-2 border-purple-400/60 rounded-bl-sm"/>
                <div className="absolute bottom-[104px] right-4 w-8 h-8 border-b-2 border-r-2 border-purple-400/60 rounded-br-sm"/>
              </div>

              {/* Score badge */}
              {complianceScore !== null && (
                <div
                  onClick={handleOpenReport}
                  title="Click to view full compliance report"
                  className={`absolute top-4 left-4 z-10 cursor-pointer pointer-events-auto rounded-2xl px-3 py-2 backdrop-blur-md border bg-black/70 shadow-lg hover:scale-105 active:scale-95 transition-all ${borderCls}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[9px] text-slate-400 font-medium tracking-widest uppercase">Score</span>
                    <span className="text-[8px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30">
                      Report &rarr;
                    </span>
                  </div>
                  <div className="text-2xl font-black font-mono" style={{color:scoreColor}}>{Math.round(complianceScore)}%</div>
                  <div className="text-[9px] font-bold" style={{color:scoreColor}}>{overallStatus.replace('_',' ')}</div>
                </div>
              )}

              {/* Quality warning */}
              {quality && !quality.is_acceptable && (
                <div className="absolute top-4 right-4 z-10 pointer-events-none flex items-center gap-1.5 bg-amber-900/50 border border-amber-500/50 rounded-xl px-3 py-1.5 backdrop-blur-md">
                  <AlertCircle style={{width:14,height:14,color:'#fbbf24'}}/>
                  <span className="text-[10px] text-amber-300 font-medium">{quality.reasons[0] || 'Low quality'}</span>
                </div>
              )}

              {/* Bottom controls */}
              <div className="absolute bottom-0 left-0 right-0 z-10">
                {hud && (
                  <div className="mx-4 mb-2">
                    <div className={`rounded-xl px-4 py-2 text-center text-xs font-medium backdrop-blur-md border bg-black/50 ${borderCls}`}>
                      {hud.guidance_message}
                    </div>
                  </div>
                )}
                <div className="bg-black/70 backdrop-blur-md border-t border-white/5 px-6 py-3 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-[10px] text-slate-400 font-medium mr-1">Panel:</span>
                    {PANEL_OPTIONS.map(p => (
                      <button key={p.id} onClick={() => setActivePanel(p.id)}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all duration-150 ${activePanel===p.id ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30' : 'bg-slate-800/70 text-slate-400 hover:text-white hover:bg-slate-700'}`}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button onClick={() => captureAndAnalyze()} disabled={isAnalyzing || paused}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all disabled:opacity-50">
                      {isAnalyzing ? <Loader2 style={{width:14,height:14}} className="animate-spin"/> : <Zap style={{width:14,height:14}}/>}
                      Scan Now
                    </button>
                    <button
                      onClick={handleOpenReport}
                      disabled={isGeneratingReport}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-600/30 transition-all active:scale-95 disabled:opacity-50"
                      title="Generate and view live compliance report"
                    >
                      {isGeneratingReport ? (
                        <Loader2 style={{width:14,height:14}} className="animate-spin" />
                      ) : (
                        <FileText style={{width:14,height:14}} />
                      )}
                      Get Report
                    </button>
                    <button onClick={() => setPaused(p => !p)} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${paused ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/40' : 'bg-amber-500/10 text-amber-300 border-amber-500/40'}`}>
                      {paused ? <Play style={{width:14,height:14}}/> : <Pause style={{width:14,height:14}}/>}
                      {paused ? 'Resume' : 'Pause'}
                    </button>
                    <button onClick={() => { accPanelsRef.current=[]; setLastResult(null); setFrameCount(0); }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-700/60 text-slate-300 border border-slate-600/50 hover:bg-slate-600/80 transition-all">
                      <RotateCcw style={{width:14,height:14}}/> Reset
                    </button>
                    <button onClick={stopCamera} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold bg-red-500/10 text-red-300 border border-red-500/30 hover:bg-red-500/20 transition-all">
                      <CameraOff style={{width:14,height:14}}/> Stop
                    </button>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-[10px] text-slate-400 font-medium">Category:</span>
                    <select value={productCategory} onChange={e => setProductCategory(e.target.value as ProductCategory)} className="bg-slate-800/80 border border-slate-600/50 text-slate-200 text-[10px] rounded-lg px-2 py-1 outline-none focus:border-purple-500">
                      {CATEGORY_OPTIONS.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
                    </select>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Sidebar */}
        {showSidebar && (
          <div className="w-80 flex-shrink-0 bg-[#080e20] border-l border-white/5 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between flex-shrink-0">
              <div
                className="flex items-center gap-2 cursor-pointer hover:opacity-85 transition-opacity"
                onClick={handleOpenReport}
                title="Click to view full compliance report"
              >
                <ClipboardList style={{width:16,height:16,color:'#a78bfa'}}/>
                <span className="text-xs font-bold text-white">Compliance Report</span>
              </div>
              <div className="flex items-center gap-1.5">
                {cameraActive && hud && (
                  <div className="flex items-center gap-1">
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">{hud.pass_count}P</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 font-bold">{hud.fail_count}F</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">{hud.review_count}R</span>
                  </div>
                )}
                <button
                  onClick={handleOpenReport}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all"
                  title="Expand Full Compliance Report"
                >
                  <FileText style={{width: 13, height: 13}} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto" style={{scrollbarWidth:'thin',scrollbarColor:'#1e2d4d transparent'}}>
              {!cameraActive && (
                <div className="flex flex-col items-center justify-center h-full gap-4 p-6 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center">
                    <Radio style={{width:24,height:24,color:'#475569'}}/>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-300">Awaiting Camera</p>
                    <p className="text-[11px] text-slate-500 mt-1">Start AR inspection to see real-time compliance results.</p>
                  </div>
                </div>
              )}
              {cameraActive && (!isConnected || lastError) && (
                <div className="flex flex-col items-center justify-center h-full gap-4 p-6 text-center">
                  <div className="w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
                    <WifiOff style={{width:28,height:28}}/>
                  </div>
                  <div>
                    <p className="text-sm font-bold text-red-400">Backend Disconnected</p>
                    <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                      {lastError || 'Cannot reach API backend at http://127.0.0.1:8000.'}
                    </p>
                    <div className="mt-3 p-2 rounded-lg bg-black/40 border border-white/5 text-[10px] text-slate-400 font-mono text-left">
                      Run in terminal:<br/>
                      <span className="text-purple-300">uvicorn app.main:app --port 8000</span>
                    </div>
                  </div>
                  <button onClick={() => captureAndAnalyze()} disabled={isAnalyzing}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 transition-all">
                    {isAnalyzing ? <Loader2 style={{width:13,height:13}} className="animate-spin"/> : <RotateCcw style={{width:13,height:13}}/>}
                    Retry Inspection
                  </button>
                </div>
              )}
              {cameraActive && isConnected && !lastError && fields.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full gap-4 p-6 text-center">
                  <Loader2 style={{width:32,height:32,color:'#a78bfa'}} className="animate-spin"/>
                  <div>
                    <p className="text-sm font-semibold text-slate-300">
                      {isAnalyzing ? 'Analyzing frame...' : 'Scanning...'}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">Point camera steadily at label declarations.</p>
                  </div>
                  <button onClick={() => captureAndAnalyze()} disabled={isAnalyzing}
                    className="mt-2 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-600/30 text-purple-200 border border-purple-500/40 hover:bg-purple-600/50 transition-all">
                    <Zap style={{width:12,height:12}}/> Scan Now
                  </button>
                </div>
              )}
              {cameraActive && fields.length > 0 && (
                <div className="p-3 space-y-2">
                  {fields.map(field => {
                    const sc = STATUS_COLORS[field.status] || STATUS_COLORS.N_A;
                    const isSel = selectedField?.field_name === field.field_name;
                    return (
                      <button key={field.field_name} onClick={() => setSelectedField(isSel ? null : field)}
                        className="w-full text-left rounded-xl border overflow-hidden transition-all duration-150"
                        style={{background:sc.bg, borderColor: isSel ? sc.border : 'rgba(255,255,255,0.06)', boxShadow: isSel ? sc.glow : 'none'}}>
                        <div className="px-3 py-2.5">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-1.5">
                              <StatusIcon status={field.status} size={13}/>
                              <span className="text-[11px] font-bold text-white">{field.display_name}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              {field.has_conflict && <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold">CONFLICT</span>}
                              <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{background:sc.border+'22',color:sc.text,border:'1px solid '+sc.border+'44'}}>{field.status}</span>
                            </div>
                          </div>
                          <div className="text-[10px] text-slate-300 font-mono truncate">{field.normalized_value || field.raw_text || '\u2014'}</div>
                          <div className="text-[9px] text-slate-500 mt-0.5">{field.source_panel} \u00b7 {Math.round(field.confidence*100)}% conf</div>
                        </div>
                        {isSel && (
                          <div className="border-t px-3 py-2.5 space-y-2" style={{borderColor:sc.border+'33'}}>
                            <div>
                              <p className="text-[9px] text-slate-400 uppercase tracking-wide font-bold mb-0.5">Explanation</p>
                              <p className="text-[10px] text-slate-200">{field.explanation}</p>
                            </div>
                            <div>
                              <p className="text-[9px] text-slate-400 uppercase tracking-wide font-bold mb-0.5">Legal Reference</p>
                              <p className="text-[10px] text-purple-300">{field.applicable_rule}</p>
                            </div>
                            {field.crop_thumbnail && (
                              <div>
                                <p className="text-[9px] text-slate-400 uppercase tracking-wide font-bold mb-1">OCR Region</p>
                                <img src={field.crop_thumbnail} alt="OCR crop" className="rounded-lg border border-white/10 max-h-16 object-contain w-full"/>
                              </div>
                            )}
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {cameraActive && hud && (
              <div className="border-t border-white/5 px-4 py-3 flex-shrink-0">
                <div className="grid grid-cols-4 gap-2 mb-2.5">
                  {[
                    {label:'Pass',count:hud.pass_count,color:'#10b981'},
                    {label:'Fail',count:hud.fail_count,color:'#ef4444'},
                    {label:'Review',count:hud.review_count,color:'#f59e0b'},
                    {label:'N/A',count:hud.na_count,color:'#64748b'},
                  ].map(m => (
                    <div key={m.label} className="text-center rounded-xl py-2 border border-white/5" style={{background:'rgba(255,255,255,0.02)'}}>
                      <div className="text-base font-black" style={{color:m.color}}>{m.count}</div>
                      <div className="text-[8px] text-slate-400 font-medium">{m.label}</div>
                    </div>
                  ))}
                </div>
                {complianceScore !== null && (
                  <div className="mb-2.5">
                    <div className="flex justify-between text-[9px] text-slate-400 mb-1">
                      <span>Compliance Score</span>
                      <span className="font-bold" style={{color:scoreColor}}>{Math.round(complianceScore)}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500" style={{width:complianceScore+'%',background:scoreColor}}/>
                    </div>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-[9px] text-slate-400">
                    <Package style={{width:12,height:12}}/> {hud.total_packages} pkg · {hud.active_panel}
                  </div>
                  <div className="flex items-center gap-1 text-[9px] text-slate-400">
                    <Zap style={{width:12,height:12,color:'#a78bfa'}}/>
                    <span className="font-mono">{lastResult?.processing_time_ms.toFixed(0)}ms</span>
                  </div>
                </div>
                <button
                  onClick={handleOpenReport}
                  className="w-full mt-2.5 flex items-center justify-center gap-2 py-2 px-3 rounded-xl text-xs font-bold bg-gradient-to-r from-purple-600 via-indigo-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white shadow-lg shadow-purple-600/25 transition-all active:scale-95"
                >
                  <FileText style={{ width: 14, height: 14 }} />
                  <span>View Full Report</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Live / Frozen Fullscreen Report Modal */}
      {showReport && (lastResult || reportFrozenResult) && (
        <ARLiveReport
          result={isLiveReport ? (lastResult || reportFrozenResult!) : (reportFrozenResult || lastResult!)}
          productCategory={productCategory}
          onClose={() => setShowReport(false)}
          isLive={isLiveReport}
          onToggleLive={() => {
            setIsLiveReport(prev => {
              if (prev && lastResult) {
                setReportFrozenResult(lastResult);
              }
              return !prev;
            });
          }}
          onSavePdf={handleSavePdf}
          isSavingPdf={isSavingPdf}
          savedInspectionId={savedInspectionId}
          accumulatedPanels={accPanelsRef.current}
        />
      )}
    </div>
  );
};

export default ARInspectionPage;
