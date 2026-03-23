// Shared frontend type definitions for SolarShare API responses and UI models.
export type PriorityMode = "balanced" | "lowest_cost" | "highest_reliability" | "closest_distance";

export interface UserRequest {
  location: string;
  zip_code?: string | null;
  user_key?: string | null;
  assign_project?: boolean;
  subscription_size_kw?: number;
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
  reasons?: string[];
}

export interface MarketContext {
  resolved_location: string;
  city?: string | null;
  county?: string | null;
  state_code?: string | null;
  postal_code?: string | null;
  country_code?: string | null;
  region?: string | null;
  utility?: string | null;
  latitude: number;
  longitude: number;
  utility_price_per_kwh: number;
  utility_rate_period?: string | null;
  rate_source?: string;
  rate_is_estimated?: boolean;
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
  project_status?: string;
  project_status_reason?: string | null;
  waitlist_timeline?: string | null;
  waitlist_position?: number | null;
  matched_project_count?: number;
  project_name?: string | null;
  project_capacity?: number | null;
  remaining_capacity?: number | null;
  factor_breakdown?: {
    price: number;
    reliability: number;
    distance: number;
  };
  financial_breakdown?: {
    credit_value: number;
    user_payment: number;
    user_savings: number;
    annual_savings?: number;
    average_monthly_savings?: number;
    platform_revenue: number;
    platform_margin: number;
    developer_payout: number;
    rate_used: number;
    rate_source: string;
    is_estimated: boolean;
    discount_rate: number;
    system_size_kw?: number;
    subscription_size_kw?: number;
    estimated_credit_value?: number;
    customer_payment?: number;
    savings_percent?: number;
    rollover_credit_balance?: number;
    monthly_breakdown?: Array<{
      month: string;
      production_kwh: number;
      usage_kwh: number;
      credit_kwh: number;
      credit_value: number;
      payment: number;
      savings: number;
      rollover_balance: number;
    }>;
    billing_model?: string | null;
    subscription_start_date?: string | null;
    monthly_generation_share?: number | null;
    billing_explanation: string;
    platform_revenue_explanation: string;
    invoice_preview?: {
      utility_credits: number;
      payment_due: number;
      savings: number;
      explanation: string;
    };
  };
  confidence_score?: number;
  confidence_reason?: string[];
  recommendation_label?: "recommended" | "low_savings" | "not_recommended";
  low_savings_reason?: string | null;
  alternatives?: string[];
  platform_highlights?: string[];
  assumptions?: string[];
  assumptions_used?: string[];
}

export interface DashboardDataResponse {
  user_key?: string | null;
  user_id?: string | null;
  auth_based?: boolean;
  has_subscription: boolean;
  total_savings: number;
  year_to_date_savings?: number;
  rollover_credits: number;
  subscription_size_kw: number;
  subscription_start_date?: string | null;
  monthly_generation_share?: number | null;
  utility?: string | null;
  region?: string | null;
  project_info?: {
    name: string;
    capacity_kw: number;
    remaining_capacity: number;
    billing_model: string;
  } | null;
  monthly_savings: Array<{
    month: string;
    savings: number;
    rollover_balance: number;
  }>;
  billing_history?: Array<{
    invoice_id: string;
    month: string;
    status: "draft" | "issued" | "paid" | "failed";
    billing_status: "draft" | "issued" | "paid" | "failed";
    utility_credits: number;
    payment_due: number;
    savings: number;
    rollover_balance: number;
    explanation: string;
    payment_provider?: string | null;
    payment_transaction_id?: string | null;
    payment_status_message?: string | null;
    created_at: string;
    issued_at?: string | null;
    paid_at?: string | null;
    failed_at?: string | null;
    download_path: string;
  }>;
  status_requests?: Array<{
    id: string;
    invoice_id: string;
    requested_by_user_id: string;
    current_status: "draft" | "issued" | "paid" | "failed";
    requested_status: "draft" | "issued" | "paid" | "failed";
    reason?: string | null;
    state: "pending" | "approved" | "rejected" | "cancelled";
    reviewed_by_user_id?: string | null;
    review_note?: string | null;
    created_at: string;
    reviewed_at?: string | null;
  }>;
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
  region?: string | null;
  utility?: string | null;
  latitude: number;
  longitude: number;
  confidence: number;
  using_fallback: boolean;
  resolution_status?: string;
  suggested_zip_codes?: string[];
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

export interface DemoRequest {
  name: string;
  email: string;
  organization?: string | null;
  message: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface AuthUser {
  id: string;
  email: string;
  role: string;
  user_identity_key: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  refresh_token: string;
  refresh_expires_at: string;
  session: {
    id: string;
    device_name?: string | null;
    user_agent?: string | null;
    ip_address?: string | null;
    created_at: string;
    last_seen_at: string;
    expires_at: string;
    is_active: boolean;
  };
  user: AuthUser;
}

export interface AuthSessionEntry {
  id: string;
  user_id: string;
  device_name?: string | null;
  user_agent?: string | null;
  ip_address?: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  revoked_at?: string | null;
  revoked_reason?: string | null;
  is_active: boolean;
}
