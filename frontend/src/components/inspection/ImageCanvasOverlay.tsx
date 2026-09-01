import React, { useState, useRef, useEffect } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Layers } from 'lucide-react';
import { ExtractedField, RuleCheckResult } from '../../types/inspection';

interface ImageCanvasOverlayProps {
  imageUrl: string;
  fields: ExtractedField[];
  checks: RuleCheckResult[];
  selectedField: string | null;
  onSelectField: (fieldName: string | null) => void;
  panelLabel?: string;
  activeImageIndex?: number;
}

export const ImageCanvasOverlay: React.FC<ImageCanvasOverlayProps> = ({
  imageUrl,
  fields,
  checks,
  selectedField,
  onSelectField,
  panelLabel,
  activeImageIndex = 0,
}) => {
  const [scale, setScale] = useState(1);
  const [imageDims, setImageDims] = useState<{ width: number; height: number } | null>(null);
  const [hoveredField, setHoveredField] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    setImageDims({ width: img.naturalWidth, height: img.naturalHeight });
  };

  const getColorByStatus = (status: string) => {
    switch (status) {
      case 'PASS':
        return { stroke: '#10b981', fill: 'rgba(16, 185, 129, 0.2)', text: '#10b981' };
      case 'FAIL':
      case 'NOT_DETECTED':
        return { stroke: '#ef4444', fill: 'rgba(239, 68, 68, 0.25)', text: '#ef4444' };
      case 'WARNING':
      case 'UNCERTAIN':
        return { stroke: '#f59e0b', fill: 'rgba(245, 158, 11, 0.25)', text: '#f59e0b' };
      default:
        return { stroke: '#3b82f6', fill: 'rgba(59, 130, 246, 0.2)', text: '#3b82f6' };
    }
  };

  // Build bounding box items — ONLY for the active image panel
  const boxes = fields
    .filter((f) => {
      if (!f.bbox || f.bbox.length !== 4) return false;
      // If field has image_index metadata, only show for the active panel
      const fieldImageIndex = (f as any).image_index ?? (f as any).metadata?.image_index ?? 0;
      return fieldImageIndex === activeImageIndex;
    })
    .map((f) => {
      const check = checks.find((c) => c.field_name === f.field_name);
      const status = check ? check.status : 'PASS';
      return {
        fieldName: f.field_name,
        displayName: f.display_name,
        value: f.normalized_value || f.raw_value || '',
        confidence: f.confidence,
        bbox: f.bbox as [number, number, number, number],
        status,
        color: getColorByStatus(status),
      };
    });

  return (
    <div className="flex flex-col h-full rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950/60 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-slate-300">Visual Evidence Overlay</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {boxes.length} Bounding Boxes
          </span>
          {panelLabel && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider">
              {panelLabel} Panel
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            onClick={() => setScale((s) => Math.max(0.6, s - 0.2))}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-mono text-slate-400 w-10 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(2.5, s + 0.2))}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setScale(1)}
            className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Reset Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Image & SVG Canvas */}
      <div className="relative flex-1 min-h-[380px] p-4 flex items-center justify-center overflow-auto bg-slate-950/40">
        <div 
          className="relative inline-block transition-transform duration-200"
          style={{ transform: `scale(${scale})`, transformOrigin: 'center center' }}
        >
          <img
            ref={imgRef}
            src={imageUrl}
            alt="Product Label Evidence"
            onLoad={handleImageLoad}
            className="max-h-[540px] w-auto rounded-lg shadow-2xl border border-slate-800 pointer-events-none select-none"
          />

          {/* SVG Overlay */}
          {imageDims && (
            <svg
              className="absolute inset-0 w-full h-full cursor-pointer"
              viewBox={`0 0 ${imageDims.width} ${imageDims.height}`}
              preserveAspectRatio="none"
            >
              {boxes.map((box) => {
                const [x1, y1, x2, y2] = box.bbox;
                const width = Math.max(10, x2 - x1);
                const height = Math.max(10, y2 - y1);
                const isSelected = selectedField === box.fieldName;
                const isHovered = hoveredField === box.fieldName;

                const strokeWidth = isSelected || isHovered ? 4 : 2;
                const fill = isSelected || isHovered ? box.color.fill : 'rgba(0,0,0,0.05)';

                return (
                  <g
                    key={box.fieldName}
                    onClick={() => onSelectField(isSelected ? null : box.fieldName)}
                    onMouseEnter={() => setHoveredField(box.fieldName)}
                    onMouseLeave={() => setHoveredField(null)}
                    className="cursor-pointer transition-all duration-150"
                  >
                    {/* Bounding Box Rectangle */}
                    <rect
                      x={x1}
                      y={y1}
                      width={width}
                      height={height}
                      fill={fill}
                      stroke={box.color.stroke}
                      strokeWidth={strokeWidth}
                      rx="4"
                      className="transition-all duration-150"
                    />

                    {/* Tag Header */}
                    <rect
                      x={x1}
                      y={Math.max(0, y1 - 28)}
                      width={Math.max(80, width * 0.9)}
                      height={26}
                      fill={box.color.stroke}
                      rx="3"
                    />

                    <text
                      x={x1 + 6}
                      y={Math.max(16, y1 - 10)}
                      fill="#ffffff"
                      fontSize="14"
                      fontWeight="bold"
                      fontFamily="Inter, sans-serif"
                    >
                      {box.displayName} ({Math.round(box.confidence * 100)}%)
                    </text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>

      {/* Selected Box Footer Tooltip */}
      {selectedField && (
        <div className="px-4 py-2.5 bg-slate-900/90 border-t border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-emerald-400">Highlighted:</span>
            <span className="font-mono text-slate-200">
              {boxes.find((b) => b.fieldName === selectedField)?.displayName || selectedField}
            </span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-300">
              {boxes.find((b) => b.fieldName === selectedField)?.value || 'N/A'}
            </span>
          </div>
          <button
            onClick={() => onSelectField(null)}
            className="text-[11px] text-slate-400 hover:text-white"
          >
            Clear Highlight
          </button>
        </div>
      )}
    </div>
  );
};
