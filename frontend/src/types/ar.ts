export type ARSystemState =
  | 'IDLE'
  | 'DETECTING'
  | 'SCANNING'
  | 'ANALYZING'
  | 'RESULT'
  | 'REVIEW'
  | 'QUALITY_WARNING'
  | 'OFFLINE';

export type ARFieldStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'N/A';

export interface ARFieldOverlay {
  field_name: string;
  display_name: string;
  raw_text?: string;
  normalized_value?: string;
  unit?: string;
  confidence: number;
  source_panel: string;
  status: ARFieldStatus;
  explanation: string;
  applicable_rule: string;
  has_conflict?: boolean;
  conflict_entry?: {
    field_name: string;
    display_name?: string;
    conflict_summary: string;
    sources: Array<{
      panel_type: string;
      value: string;
      raw_value?: string;
      confidence: number;
      bbox?: number[];
    }>;
  };
  bbox: [number, number, number, number]; // [x1, y1, x2, y2] in pixels
  bbox_normalized: [number, number, number, number]; // [nx1, ny1, nx2, ny2] 0.0 to 1.0
  crop_thumbnail?: string; // base64 JPEG thumbnail
}

export interface ARPackageOverlay {
  package_id: string;
  confidence: number;
  bbox: [number, number, number, number];
  bbox_normalized: [number, number, number, number];
  label: string;
  is_active: boolean;
  overall_status?: 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'UNABLE_TO_VERIFY';
  passed_checks?: number;
  total_checks?: number;
}

export interface ARHudMetrics {
  total_packages: number;
  active_package_id: string;
  active_panel: string;
  pass_count: number;
  fail_count: number;
  review_count: number;
  na_count: number;
  system_state: ARSystemState;
  guidance_message: string;
}

export interface ARFrameResult {
  frame_id: string;
  timestamp: number;
  image_dimensions: { width: number; height: number };
  quality: {
    status: string;
    is_acceptable: boolean;
    blur_score?: number;
    reasons: string[];
  };
  packages: ARPackageOverlay[];
  fields: ARFieldOverlay[];
  conflicts: any[];
  overall_status: string;
  compliance_score?: number;
  hud_metrics: ARHudMetrics;
  processing_time_ms: number;
}
