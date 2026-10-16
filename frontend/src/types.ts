export interface PassageLocation {
  doc_id: string;
  doc_title: string;
  section_heading: string;
  page: number;
  chunk_index: number;
}

export interface PassageRecord {
  passage_id: string;
  text: string;
  score: number;
  location: PassageLocation;
  dense_score?: number;
  bm25_score?: number;
  neighbour_context?: string;
}

export type ClaimType =
  | 'condition'
  | 'exception'
  | 'deadline'
  | 'penalty'
  | 'authority'
  | 'effective_date'
  | 'other';

export type VerificationLabel = 'Verified' | 'Unsupported' | 'Contradicted' | 'Not Applicable';

export interface ClaimVerificationResult {
  claim_id: string;
  claim_text: string;
  label: VerificationLabel;
  type?: ClaimType;
  E_i: number;
  K_i: number;
  evidence_passage_id?: string;
  evidence_text?: string;
  critical: boolean;
  weight: number;
}

export type DecisionReason =
  | 'NONE'
  | 'NO_EVIDENCE'
  | 'CRITICAL_CONTRADICTION'
  | 'RISK_ABOVE_THRESHOLD';

export interface AskResponse {
  run_id: string;
  question: string;
  mode: 'truthguard' | 'plain_rag' | 'answer_level_check';
  answer: string | null;
  abstained: boolean;
  reason_code: DecisionReason;
  reason_explanation: string;
  risk_score: number;
  claims: ClaimVerificationResult[];
  passages: PassageRecord[];
  timings_ms: Record<string, number>;
  token_usage: Record<string, number>;
  model_versions: Record<string, string>;
  parameters: Record<string, any>;
}

export interface RunSummary {
  run_id: string;
  created_at: string;
  question: string;
  mode: string;
  abstained: boolean;
  reason_code: string;
  risk_score: number;
  answer_preview?: string;
}

export interface HealthInfo {
  status: string;
  service: string;
  device: {
    selected_device?: string;
    device?: string;
    mps_available?: boolean;
    cuda_available?: boolean;
    system?: string;
  };
  models: {
    embedding_model: string;
    nli_model: string;
    gemini_model: string;
  };
}

export interface EvalMetricValues {
  coverage: number;
  abstention_precision: number;
  abstention_recall: number;
  leakage_rate: number;
}

export interface EvalModeSummary {
  metrics: EvalMetricValues;
  avg_latency_s: number;
}

export interface MetricDefinition {
  label: string;
  meaning: string;
  target: string;
  formula: string;
}

export interface EvalSummaryResponse {
  modes: Record<string, EvalModeSummary>;
  metric_definitions: Record<string, MetricDefinition>;
  dataset: {
    total: number;
    dev: number;
    test: number;
    answerable: number;
    unanswerable: number;
  };
  live_audit: {
    total_runs: number;
    released_runs: number;
    abstained_runs: number;
  };
  parameters: Record<string, any>;
}

export interface EvalRunRecord {
  question_id: string;
  split: string;
  category: string;
  question: string;
  is_answerable: boolean;
  relevant_clause: string;
  expected_decision: string;
  expected_claims_count: number;
}

export interface EvalErrorCase {
  question_id: string;
  category: string;
  question: string;
  trap_type: string;
  baseline_behavior: string;
  truthguard_behavior: string;
  risk_mitigated: string;
}

export interface PerQueryClaimDetail {
  claim_id: string;
  claim_text: string;
  label: 'VERIFIED' | 'CONTRADICTED' | 'UNSUPPORTED' | string;
  E_i: number;
  K_i: number;
  evidence_text?: string;
  critical?: boolean;
}

export interface PerQueryModeResult {
  abstained: boolean;
  correct_decision: boolean;
  reason_code: string;
  reason_explanation?: string;
  answer?: string;
  risk_score: number;
  claims_count: number;
  claims?: PerQueryClaimDetail[];
  latency_s: number;
}

export interface PerQueryRecord {
  question_id: string;
  question: string;
  split: string;
  category: string;
  is_answerable: boolean;
  relevant_clause: string;
  expected_decision: string;
  expected_claims_count: number;
  modes: Record<string, PerQueryModeResult>;
}

export interface PerQueryResponse {
  total_queries?: number;
  evaluated_count: number;
  modes: string[];
  mode_accuracy: Record<string, { correct: number; total: number; evaluated?: number; accuracy_pct: number }>;
  queries: PerQueryRecord[];
}
