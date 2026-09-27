export type AgentCapability = {
  name: string;
  description: string;
  idempotency_supported?: boolean;
};

export type ToolRequirement = {
  name: string;
  description?: string | null;
  schema?: Record<string, unknown> | null;
  required?: boolean;
};

export type AgentInvariants = {
  max_steps: number;
  forbidden_tools: string[];
  approval_required_tools: string[];
};

export type AgentCard = {
  id: string;
  name: string;
  version: string;
  archetype: string;
  capabilities: AgentCapability[];
  tools_required?: ToolRequirement[];
  tools_provided?: ToolRequirement[];
  invariants?: AgentInvariants;
};

export type CandidateTest = {
  id: string;
  capability_id: string;
  persona_id: string;
  name: string;
  user_prompt: string;
  expected_behavior: string;
  coverage_tags: string[];
  mandatory_categories?: string[];
  category: string;
  failure_mode?: string;
  rationale?: string;
  template_id?: string | null;
  execution_cost?: number;
  is_mandatory?: boolean;
};

export type TestPack = {
  agent_id: string;
  version: number;
  tests: CandidateTest[];
  candidate_count: number;
  requirements_fingerprint: string;
};

export type CoverageReport = {
  axes: Record<string, number>;
  covered_tags: string[];
  uncovered_tags: string[];
  critical_uncovered: string[];
  executed_test_ids: string[];
  metadata?: Record<string, unknown>;
};

export type EndpointProbeResult = {
  endpoint_url: string;
  status: "OK" | "UNREACHABLE" | "INVALID_FORMAT" | "AUTH_REQUIRED";
  latency_ms: number;
  response_preview?: string;
  detected_framework?: string;
};

export type SuitePreviewResult = {
  agent_card: AgentCard;
  requirements_fingerprint: string;
  candidate_pool: CandidateTest[];
  optimized_pack: TestPack;
  coverage: CoverageReport;
  endpoint_probe?: EndpointProbeResult | null;
};

export type PreviewResponse = SuitePreviewResult;

export type SuiteGapLoopResult = {
  agent_id: string;
  previous_version: number;
  new_version: number;
  triggered_by_run_id?: string | null;
  targeted_tags: string[];
  added_test_ids: string[];
  remaining_gaps: string[];
  pack_size: number;
  pool_size: number;
  coverage_before: CoverageReport;
  coverage_after: CoverageReport;
  noop: boolean;
};

export type SuiteSyncResult = {
  agent_id: string;
  previous_version: number;
  new_version: number;
  requirements_fingerprint: string;
  removed_capabilities: string[];
  added_capabilities: string[];
  removed_test_ids: string[];
  pool_size: number;
  pack_size: number;
  noop: boolean;
};

export type SuiteInitResult = {
  suite_path: string;
  agent_id: string;
  requirements_fingerprint: string;
  candidate_pool_size: number;
  optimized_pack_size: number;
  coverage: CoverageReport;
  endpoint_stored: boolean;
  agent_card: AgentCard;
  endpoint_probe?: EndpointProbeResult | null;
};

export type SuiteListItem = {
  agent_id: string;
  suite_version: number;
  requirements_fingerprint: string;
  endpoint_profile: string;
  pack_size: number;
  pool_size: number;
  has_latest_run: boolean;
};

export type ObservationBundle = {
  test_id: string;
  user_prompt: string;
  response_text: string;
  http_status: number;
  latency_ms: number;
  raw_json: Record<string, unknown>;
};

export type ExecutionStep = {
  step_id: string;
  kind: string;
  label: string;
  thought?: string;
  action_tool?: string;
  action_args?: Record<string, unknown>;
  observation?: string;
  http_status?: number | null;
  latency_ms?: number | null;
  is_failure?: boolean;
};

export type TestCaseResult = {
  test_id: string;
  verdict: "PASS" | "FAIL" | "UNVERIFIABLE";
  observation: ObservationBundle;
  rationale: string;
  trajectory?: ExecutionStep[];
};

export type VerdictChange = {
  test_id: string;
  previous_verdict: string | null;
  current_verdict: string;
  kind: "STABLE" | "REGRESSED" | "FIXED" | "CHANGED" | "NEW" | "REMOVED";
};

export type SuiteRunDiff = {
  baseline_run_id?: string;
  previous_run_id?: string;
  baseline_suite_version?: number;
  current_run_id: string;
  changes?: VerdictChange[];
  regressions?: string[];
  fixes?: string[];
  new_failures?: string[];
  same_verdict_count?: number;
};

export type AcceptanceCriterionSummary = {
  id: string;
  stable_id: string;
  description: string;
  evidence_kind: string;
  check_kind: string;
};

export type RequirementSummary = {
  stable_id: string;
  statement: string;
  source_kind: string;
  review_status: string;
  criteria: AcceptanceCriterionSummary[];
};

export type SuiteRequirementsResult = {
  agent_id: string;
  suite_version: number;
  requirements: RequirementSummary[];
};

export type CriterionVerdictSummary = {
  criterion_id: string;
  requirement_stable_id: string;
  criterion_stable_id: string;
  test_id: string;
  verdict: "PASS" | "FAIL" | "UNVERIFIABLE" | string;
  verdict_tier: string;
  rationale: string;
  evidence_item_ids: string[];
};

export type SuiteRunReport = {
  agent_id: string;
  run_id: string;
  suite_version: number;
  results: TestCaseResult[];
  passed: number;
  failed: number;
  unverifiable: number;
  coverage_report?: CoverageReport | null;
  run_diff?: SuiteRunDiff | null;
  criterion_verdicts?: CriterionVerdictSummary[];
};

export type SuiteDetailResult = {
  manifest: {
    agent_id: string;
    version: number;
    requirements_fingerprint: string;
    created_at: string;
    endpoint_profile: string;
  };
  optimized_pack: TestPack;
  candidate_pool_size: number;
  requirements_text?: string;
  coverage?: CoverageReport | null;
  latest_run?: SuiteRunReport | null;
  requirements?: SuiteRequirementsResult | null;
};

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  role: "OWNER" | "ADMIN" | "MEMBER";
  isEnterpriseCloud: boolean;
};
