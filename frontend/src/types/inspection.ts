export type OverallStatus = 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'UNABLE_TO_VERIFY' | 'PENDING' | 'PROCESSING' | 'FAILED';

export type CheckStatus = 'PASS' | 'FAIL' | 'WARNING' | 'NOT_DETECTED' | 'UNCERTAIN' | 'NOT_APPLICABLE' | 'UNABLE_TO_VERIFY';

export interface ImageRecord {
  id: string;
  original_filename: string;
  file_path: string;
  annotated_file_path?: string;
  file_size_bytes: number;
  panel_type?: string;
  image_index?: number;
  width?: number;
  height?: number;
  mime_type: string;
  quality_status: 'PASS' | 'WARNING' | 'FAIL';
  blur_score?: number;
  brightness_score?: number;
  contrast_score?: number;
  glare_score?: number;
  quality_reasons: string[];
}

export interface ExtractedField {
  field_name: string;
  display_name: string;
  raw_value?: string;
  normalized_value?: string;
  unit?: string;
  confidence: number;
  detection_method: string;
  bbox?: [number, number, number, number];
  is_detected: boolean;
  metadata?: Record<string, any>;
}

export interface RuleCheckResult {
  rule_id: string;
  rule_title: string;
  legal_reference: string;
  field_name: string;
  display_name: string;
  is_mandatory: boolean;
  status: CheckStatus;
  detected_value?: string;
  raw_ocr_value?: string;
  confidence?: number;
  explanation: string;
  inspector_recommendation?: string;
  bbox?: [number, number, number, number];
  evidence_available: boolean;
}

export interface ViolationSummary {
  field_name: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | 'ADVISORY';
  rule_id: string;
  legal_reference?: string;
  reason: string;
  recommendation: string;
}

export interface OCRLineInfo {
  line: number;
  text: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface OCRSummary {
  engine: string;
  total_lines: number;
  raw_full_text: string;
  lines: OCRLineInfo[];
}

export interface InspectionResponse {
  id: string;
  product_name?: string;
  product_category: string;
  overall_status: OverallStatus;
  compliance_score?: number;
  is_demo: boolean;
  execution_mode: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  warning_checks: number;
  undetected_checks: number;
  uncertain_checks: number;
  cv_model_version?: string;
  ocr_version?: string;
  rule_set_version?: string;
  processing_time_ms?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
  image?: ImageRecord;
  images?: ImageRecord[];
  ocr_summary?: OCRSummary;
  detected_fields: ExtractedField[];
  compliance_checks: RuleCheckResult[];
  violations: ViolationSummary[];
}

export interface InspectionListItem {
  id: string;
  product_name?: string;
  product_category: string;
  overall_status: OverallStatus;
  compliance_score?: number;
  quality_status?: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  created_at: string;
  original_filename?: string;
  annotated_image_available: boolean;
  image_count?: number;
}

export interface InspectionListResponse {
  total: number;
  page: number;
  limit: number;
  items: InspectionListItem[];
}

export interface DashboardMetrics {
  total_inspections: number;
  compliant_count: number;
  non_compliant_count: number;
  needs_review_count: number;
  unable_to_verify_count: number;
  average_compliance_score: number;
  category_distribution: Record<string, number>;
  recent_inspections: InspectionListItem[];
}

export interface DemoSample {
  key: string;
  title: string;
  category: string;
  filename: string;
  expected_verdict: string;
  description: string;
  scenario: string;
}
