export type OverallStatus = 'COMPLIANT' | 'NON_COMPLIANT' | 'NEEDS_REVIEW' | 'UNABLE_TO_VERIFY' | 'PENDING' | 'PROCESSING' | 'FAILED';

export type CheckStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'N/A' | 'WARNING' | 'NOT_DETECTED' | 'UNCERTAIN' | 'NOT_APPLICABLE' | 'UNABLE_TO_VERIFY';

export interface ImageRecord {
  id: string;
  original_filename: string;
  file_path: string;
  annotated_file_path?: string;
  file_size_bytes: number;
  panel_type?: string;
  image_index?: number;
  package_id?: string;
  bbox?: [number, number, number, number];
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
  source_panel?: string;
  has_conflict?: boolean;
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
  is_applicable?: boolean;
  applicability_reason?: string;
  status: CheckStatus;
  detected_value?: string;
  raw_ocr_value?: string;
  confidence?: number;
  source_panel?: string;
  conflict_detected?: boolean;
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

export interface ConflictItem {
  field_name: string;
  display_name: string;
  conflict_summary: string;
  sources: Array<{
    image_index?: number;
    panel_type: string;
    value?: string;
    raw_value?: string;
    confidence?: number;
    bbox?: [number, number, number, number];
    filename?: string;
  }>;
}

export interface ReviewDecision {
  field_name: string;
  action: string;
  confirmed_value: string;
  source_panel?: string;
  reviewer_name: string;
  reviewer_id?: string;
  note?: string;
  timestamp: string;
  original_ai_value?: string;
  final_verified_value: string;
}

export interface AnomalySignal {
  signal_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  label: string;
  title: string;
  description: string;
  recommended_action: string;
  evidence_sources?: Array<Record<string, any>>;
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
  package_id?: string;
  parent_scan_id?: string;
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
  review_checks_count?: number;
  na_checks_count?: number;
  cv_model_version?: string;
  ocr_version?: string;
  rule_set_version?: string;
  processing_time_ms?: number;
  error_message?: string;
  is_offline_synced?: boolean;
  created_at: string;
  updated_at: string;
  image?: ImageRecord;
  images?: ImageRecord[];
  ocr_summary?: OCRSummary;
  detected_fields: ExtractedField[];
  compliance_checks: RuleCheckResult[];
  violations: ViolationSummary[];
  conflicts?: ConflictItem[];
  review_decisions?: ReviewDecision[];
  anomaly_signals?: AnomalySignal[];
}

export interface MultiPackageScanResponse {
  scan_id: string;
  total_packages: number;
  overall_verdict: string;
  annotated_overview_url?: string;
  packages: InspectionResponse[];
}

export interface InspectionListItem {
  id: string;
  package_id?: string;
  parent_scan_id?: string;
  product_name?: string;
  product_category: string;
  overall_status: OverallStatus;
  compliance_score?: number;
  quality_status?: string;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  has_conflicts?: boolean;
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

