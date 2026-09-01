import React, { useState } from 'react';
import { Table, Eye, AlertOctagon, Pencil, Check, X, RefreshCw } from 'lucide-react';
import { ExtractedField, RuleCheckResult } from '../../types/inspection';
import { StatusBadge } from '../common/StatusBadge';
import { ConfidenceBar } from '../common/ConfidenceBar';

interface DetectedFieldsTableProps {
  fields: ExtractedField[];
  checks: RuleCheckResult[];
  selectedField: string | null;
  onSelectField: (fieldName: string | null) => void;
  inspectionId: string;
  onFieldOverride?: (fieldName: string, value: string, unit?: string) => Promise<void>;
}

export const DetectedFieldsTable: React.FC<DetectedFieldsTableProps> = ({
  fields,
  checks,
  selectedField,
  onSelectField,
  inspectionId,
  onFieldOverride,
}) => {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [editUnit, setEditUnit] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedField, setSavedField] = useState<string | null>(null);

  const handleStartEdit = (fieldName: string, currentValue?: string) => {
    setEditingField(fieldName);
    setEditValue(currentValue || '');
    setEditUnit('');
  };

  const handleCancelEdit = () => {
    setEditingField(null);
    setEditValue('');
    setEditUnit('');
  };

  const handleSaveOverride = async (fieldName: string) => {
    if (!editValue.trim() || !onFieldOverride) return;
    setSaving(true);
    try {
      await onFieldOverride(fieldName, editValue.trim(), editUnit.trim() || undefined);
      setSavedField(fieldName);
      setTimeout(() => setSavedField(null), 2500);
      setEditingField(null);
    } catch (e) {
      // Error handled by parent
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden shadow-xl">
      {/* Table Header Banner */}
      <div className="px-5 py-3.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Table className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-slate-200">Statutory Declarations Matrix</h3>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">Click row to highlight image bounding box</span>
          {onFieldOverride && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 font-medium flex items-center gap-1">
              <Pencil className="w-2.5 h-2.5" />
              Manual verification enabled
            </span>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-800/80 bg-slate-950/40 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <th className="py-3 px-4">Field / Declaration</th>
              <th className="py-3 px-4">Detected Value</th>
              <th className="py-3 px-4">Confidence</th>
              <th className="py-3 px-4">Legal Status</th>
              <th className="py-3 px-3 text-center">Evidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-xs">
            {checks.map((check) => {
              const field = fields.find((f) => f.field_name === check.field_name);
              const isSelected = selectedField === check.field_name;
              const hasBbox = check.bbox && check.bbox.length === 4;
              const isNotDetected = !check.detected_value;
              const isEditing = editingField === check.field_name;
              const wasSaved = savedField === check.field_name;

              return (
                <tr
                  key={check.rule_id}
                  onClick={() => !isEditing && onSelectField(isSelected ? null : check.field_name)}
                  className={`transition-all duration-150 ${
                    isEditing
                      ? 'bg-amber-500/5 border-l-4 border-l-amber-400'
                      : isSelected
                      ? 'bg-emerald-500/10 border-l-4 border-l-emerald-500'
                      : wasSaved
                      ? 'bg-emerald-500/10'
                      : isNotDetected
                      ? 'bg-rose-500/5 hover:bg-rose-500/10 cursor-pointer'
                      : 'hover:bg-slate-800/50 cursor-pointer'
                  }`}
                >
                  {/* Field Name */}
                  <td className="py-3 px-4">
                    <div className="font-semibold text-slate-200">{check.rule_title}</div>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5">{check.legal_reference}</div>
                  </td>

                  {/* Detected Value / Override Input */}
                  <td className="py-3 px-4" onClick={(e) => isEditing && e.stopPropagation()}>
                    {isEditing ? (
                      <div className="flex items-center gap-2 min-w-[200px]">
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveOverride(check.field_name);
                            if (e.key === 'Escape') handleCancelEdit();
                          }}
                          autoFocus
                          placeholder="Enter detected value…"
                          className="flex-1 px-2.5 py-1.5 text-xs bg-slate-800 border border-amber-500/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-400 focus:ring-1 focus:ring-amber-400/20"
                        />
                        <input
                          type="text"
                          value={editUnit}
                          onChange={(e) => setEditUnit(e.target.value)}
                          placeholder="Unit"
                          className="w-16 px-2 py-1.5 text-xs bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-amber-400"
                        />
                        <button
                          onClick={(e) => { e.stopPropagation(); handleSaveOverride(check.field_name); }}
                          disabled={!editValue.trim() || saving}
                          className="p-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white transition-colors"
                          title="Save override"
                        >
                          {saving ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleCancelEdit(); }}
                          className="p-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
                          title="Cancel"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ) : check.detected_value ? (
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-100 font-medium">
                          {check.detected_value}
                          {wasSaved && (
                            <span className="ml-2 text-[10px] text-emerald-400 font-sans font-normal">✓ Saved</span>
                          )}
                        </span>
                        {onFieldOverride && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleStartEdit(check.field_name, check.detected_value || ''); }}
                            className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-500 hover:text-amber-400 transition-all"
                            title="Edit value"
                          >
                            <Pencil className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-rose-400 italic flex items-center space-x-1">
                          <AlertOctagon className="w-3 h-3 text-rose-400/80 shrink-0" />
                          <span>Not Detected</span>
                        </span>
                        {onFieldOverride && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleStartEdit(check.field_name);
                            }}
                            className="ml-1 inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold rounded-md bg-amber-500/15 border border-amber-500/30 text-amber-400 hover:bg-amber-500/25 transition-all"
                            title="Enter value manually"
                          >
                            <Pencil className="w-2.5 h-2.5" />
                            Verify
                          </button>
                        )}
                      </div>
                    )}
                  </td>

                  {/* Confidence */}
                  <td className="py-3 px-4">
                    {check.confidence ? (
                      <ConfidenceBar confidence={check.confidence} />
                    ) : (
                      <span className="text-slate-500 text-xs font-mono">—</span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-3 px-4">
                    <StatusBadge status={check.status} size="sm" />
                  </td>

                  {/* Evidence Indicator */}
                  <td className="py-3 px-3 text-center">
                    {hasBbox ? (
                      <button
                        className={`p-1 rounded-md transition-colors ${
                          isSelected
                            ? 'bg-emerald-500 text-white shadow-sm'
                            : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                        title="Highlight on Image"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <span className="text-slate-600 font-mono text-[10px]">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
