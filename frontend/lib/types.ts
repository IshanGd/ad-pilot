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
  status: string;
}

export interface RecommendationsResponse {
  account_id: string;
  total_waste_identified: number;
  recommendation_count: number;
  by_severity: Partial<Record<Severity, number>>;
  by_type: Partial<Record<RecommendationType, number>>;
  recommendations: RecommendationOut[];
}

export interface AnalyzeResponse extends RecommendationsResponse {
  analyzed_keywords: number;
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
