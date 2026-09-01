export interface RuleRequirement {
  rule_id: string;
  field_name: string;
  title: string;
  legal_reference: string;
  description: string;
  is_mandatory: boolean;
  min_confidence_pass: number;
  min_confidence_warning: number;
  validation_regex?: string;
  severity_if_missing: string;
  recommendation_template: string;
}

export interface ProductCategory {
  category_id: string;
  display_name: string;
  description: string;
  rules: RuleRequirement[];
}

export interface CategorySummary {
  category_id: string;
  display_name: string;
  description: string;
  rule_count: number;
}
