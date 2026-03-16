// Shared frontend type definitions for SolarShare API responses and UI models.
export type PriorityMode = "balanced" | "lowest_cost" | "highest_reliability" | "closest_distance";

export interface UserRequest {
  location: string;
  zip_code?: string | null;
  monthly_usage_kwh: number;
  priority: PriorityMode;
}

export interface EnergyOption {
  id: number;
  provider_name: string;
  base_price_per_kwh: number;
  distance_miles: number;
  reliability_score: number;
  time_of_use_modifier: number;
  utility_plan_name: string;
}

export interface ScoredOption {
  option: EnergyOption;
  effective_price: number;
  monthly_cost: number;
  savings_vs_baseline: number;
  badges: string[];
  is_recommended: boolean;
}

export interface RecommendationPayload {
  recommended_option: ScoredOption;
  reason: string;
}

export interface MarketContext {
  resolved_location: string;
  city?: string | null;
  county?: string | null;
  state_code?: string | null;
  postal_code?: string | null;
  country_code?: string | null;
  latitude: number;
  longitude: number;
  utility_price_per_kwh: number;
  utility_rate_period?: string | null;
  avg_shortwave_radiation: number;
  avg_cloud_cover_pct: number;
  data_sources: string[];
  source_urls: string[];
  observed_at_utc: string;
  using_fallback: boolean;
}

export interface LiveComparisonResponse {
  options: ScoredOption[];
  recommendation: RecommendationPayload;
  market_context: MarketContext;
  resolution_confidence?: number;
  fallback_reason?: string | null;
  factor_breakdown?: {
    price: number;
    reliability: number;
    distance: number;
  };
}

export interface LocationResolveRequest {
  location?: string;
  zip_code?: string | null;
}

export interface LocationResolveResponse {
  resolved_location: string;
  city?: string | null;
  county?: string | null;
  state_code?: string | null;
  postal_code?: string | null;
  country_code?: string | null;
  latitude: number;
  longitude: number;
  confidence: number;
  using_fallback: boolean;
  source: string;
}

export interface AssistantChatRequest {
  message: string;
  page?: string;
  context?: Record<string, unknown>;
}

export interface AssistantChatResponse {
  reply: string;
  mode: "ai" | "fallback";
  suggested_actions: string[];
}

export interface ContactInquiry {
  name: string;
  email: string;
  interest: "customer_support" | "methodology_question" | "partnership" | "investor_relations" | "other";
  message: string;
}
