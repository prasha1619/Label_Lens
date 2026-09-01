import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileCode, ArrowRight, Copy, Check } from 'lucide-react';
import { OCRSummary, ExtractedField } from '../../types/inspection';

interface RawOcrViewerProps {
  ocrSummary?: OCRSummary;
  fields: ExtractedField[];
}

export const RawOcrViewer: React.FC<RawOcrViewerProps> = ({ ocrSummary, fields }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyRaw = () => {
    if (ocrSummary?.raw_full_text) {
      navigator.clipboard.writeText(ocrSummary.raw_full_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
      {/* Header Accordion Toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-4 bg-slate-950/60 flex items-center justify-between hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center space-x-2.5">
          <FileCode className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-semibold text-slate-200">Raw OCR Text vs Normalized Extraction</span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
            {ocrSummary?.engine || 'PaddleOCR'} ({ocrSummary?.total_lines || 0} lines)
          </span>
        </div>
        <div className="flex items-center space-x-2 text-slate-400 text-xs">
          <span>{isOpen ? 'Collapse' : 'Expand Raw Output'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="p-5 border-t border-slate-800 grid grid-cols-1 lg:grid-cols-2 gap-6 bg-slate-950/30">
          
          {/* Left Column: Raw OCR Lines */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Raw Unmodified OCR Output
              </span>
              <button
                onClick={handleCopyRaw}
                className="flex items-center space-x-1 text-[11px] text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800/60"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copied ? 'Copied' : 'Copy Text'}</span>
              </button>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 font-mono text-xs text-slate-300 max-h-72 overflow-y-auto border border-slate-800/80 space-y-1.5 leading-relaxed">
              {ocrSummary?.lines && ocrSummary.lines.length > 0 ? (
                ocrSummary.lines.map((line, idx) => (
                  <div key={idx} className="flex items-baseline space-x-3 hover:bg-slate-900/60 px-1 py-0.5 rounded">
                    <span className="text-slate-600 text-[10px] w-6 shrink-0">{line.line}</span>
                    <span className="flex-1 text-slate-200">{line.text}</span>
                    <span className="text-[10px] text-slate-500">{Math.round(line.confidence * 100)}%</span>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic">No OCR text lines captured.</div>
              )}
            </div>
          </div>

          {/* Right Column: Normalized Mapping */}
          <div className="space-y-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Extracted & Normalized Mapping
            </span>

            <div className="p-3.5 rounded-xl bg-slate-950 font-mono text-xs text-slate-300 max-h-72 overflow-y-auto border border-slate-800/80 space-y-2">
              {fields.length > 0 ? (
                fields.map((f) => (
                  <div key={f.field_name} className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/60 space-y-1">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-sans font-semibold text-emerald-400">{f.display_name}</span>
                      <span className="text-[10px] text-slate-400">{f.detection_method}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                      <span className="text-slate-500 truncate max-w-[140px]">{f.raw_value || '—'}</span>
                      <ArrowRight className="w-3 h-3 text-slate-600 shrink-0" />
                      <span className="text-slate-100 font-semibold truncate">{f.normalized_value}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic">No structured fields extracted.</div>
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
};
