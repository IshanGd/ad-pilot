// Mirrors the Pydantic response models in backend/app/schemas.py.

export type Severity = "HIGH" | "MEDIUM" | "LOW";

export type RecommendationType =
  | "PAUSE_KEYWORD"
  | "INCREASE_BUDGET"
  | "ADD_NEGATIVE"
  | "REVIEW_LOW_CTR";

export interface RecommendationOut {
  id: string;
  campaign_id: string;
  campaign_name: string;
  keyword_id: string | null;
  label: string;
  type: RecommendationType;
  severity: Severity;
  confidence: number | null;
  estimated_impact: number | null;
  explanation: string | null;
  explanation_source?: "llm" | "template" | "stored" | null;
  status: string;
}

export interface RecommendationsResponse {
  account_id: string;
  language: "en" | "hi";
  total_waste_identified: number;
  recommendation_count: number;
  by_severity: Partial<Record<Severity, number>>;
  by_type: Partial<Record<RecommendationType, number>>;
  recommendations: RecommendationOut[];
}

export interface AnalyzeResponse extends RecommendationsResponse {
  analyzed_keywords: number;
  llm_explanations: number;
}

export interface CampaignSummary {
  id: string;
  name: string;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  conversion_value: number;
  keyword_count: number;
}

export interface CampaignAllocation {
  campaign_id: string;
  name: string;
  current_spend: number;
  current_share: number;
  suggested_budget: number;
  suggested_share: number;
  delta: number;
  cpa: number | null;
  reason_code: "PAUSE" | "SCALE_UP" | "TRIM" | "AVERAGE";
  reason: string;
}

export interface BudgetOptimizeResponse {
  account_id: string;
  total_budget: number;
  current_total_spend: number;
  allocations: CampaignAllocation[];
}

export interface SimulationResponse {
  account_id: string;
  current_spend: number;
  current_conversions: number;
  current_cpa: number | null;
  projected_spend: number;
  projected_conversions: number;
  projected_cpa: number | null;
  monthly_saving: number;
  extra_sales: number;
  reinvested: boolean;
  assumptions: string[];
}

export interface UploadResponse {
  account_id: string;
  campaigns: number;
  keywords: number;
  rows_ingested: number;
  totals: {
    spend: number;
    impressions: number;
    clicks: number;
    conversions: number;
    conversion_value: number;
  };
  account_averages: Record<string, number | null>;
  campaign_breakdown: CampaignSummary[];
}
