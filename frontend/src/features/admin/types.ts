export type AssessmentRuleValues = {
  confidence_threshold: number;
  repair_max_percentage: number;
  replacement_min_percentage: number;
};

export type AssessmentRuleConfiguration = {
  values: AssessmentRuleValues;
  updated_by: string | null;
  updated_at: string;
};

export type AssessmentRuleChange = {
  changed_by: string;
  changed_at: string;
  old_values: AssessmentRuleValues;
  new_values: AssessmentRuleValues;
};
