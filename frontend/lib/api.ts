// API client helpers for calling SolarShare FastAPI endpoints from Next.js pages/components.
import {
  AssistantChatRequest,
  AssistantChatResponse,
  AuthCredentials,
  AuthTokenResponse,
  AuthUser,
  ContactInquiry,
  DashboardDataResponse,
  DemoRequest,
  LiveComparisonResponse,
  LocationResolveRequest,
  LocationResolveResponse,
  UserRequest
} from "@/lib/types";

const defaultHeaders = { "Content-Type": "application/json" };
const AUTH_TOKEN_STORAGE_KEY = "solarshare_auth_token_v1";
const AUTH_USER_STORAGE_KEY = "solarshare_auth_user_v1";
const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim().replace(/\/+$/, "");

function apiUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not set.");
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${normalizedPath}`;
}

function backendUnavailableMessage(): string {
  return "Unable to connect to SolarShare API. Start backend with: cd backend && python main.py";
}

async function postJson(path: string, body: unknown, headers: Record<string, string> = defaultHeaders): Promise<Response> {
  try {
    return await fetch(apiUrl(path), {
      method: "POST",
      headers,
      body: JSON.stringify(body)
    });
  } catch {
    throw new Error(backendUnavailableMessage());
  }
}

async function patchJson(path: string, body: unknown, headers: Record<string, string> = defaultHeaders): Promise<Response> {
  try {
    return await fetch(apiUrl(path), {
      method: "PATCH",
      headers,
      body: JSON.stringify(body)
    });
  } catch {
    throw new Error(backendUnavailableMessage());
  }
}

function mergeHeaders(headers?: Record<string, string>): Record<string, string> {
  return { ...defaultHeaders, ...(headers || {}) };
}

function readStorage(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // No-op when browser storage is unavailable.
  }
}

function removeStorage(key: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(key);
  } catch {
    // No-op when browser storage is unavailable.
  }
}

export function getAuthToken(): string | null {
  return readStorage(AUTH_TOKEN_STORAGE_KEY);
}

export function getAuthUser(): AuthUser | null {
  const raw = readStorage(AUTH_USER_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function getAuthIdentityKey(): string | null {
  return getAuthUser()?.user_identity_key || null;
}

export function clearAuthSession(): void {
  removeStorage(AUTH_TOKEN_STORAGE_KEY);
  removeStorage(AUTH_USER_STORAGE_KEY);
}

function persistAuthSession(payload: AuthTokenResponse): void {
  writeStorage(AUTH_TOKEN_STORAGE_KEY, payload.access_token);
  writeStorage(AUTH_USER_STORAGE_KEY, JSON.stringify(payload.user));
}

function authHeaders(token?: string | null): Record<string, string> {
  const activeToken = (token || getAuthToken() || "").trim();
  if (!activeToken) {
    return mergeHeaders();
  }
  return mergeHeaders({ Authorization: `Bearer ${activeToken}` });
}

export async function fetchLiveComparison(payload: UserRequest): Promise<LiveComparisonResponse> {
  const response = await postJson("/live-comparison", payload);

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to fetch live comparison."));
  }

  return response.json() as Promise<LiveComparisonResponse>;
}

export async function signupCustomer(payload: AuthCredentials): Promise<AuthTokenResponse> {
  const response = await postJson("/auth/signup", payload, mergeHeaders());
  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to create account."));
  }
  const session = (await response.json()) as AuthTokenResponse;
  persistAuthSession(session);
  return session;
}

export async function loginCustomer(payload: AuthCredentials): Promise<AuthTokenResponse> {
  const response = await postJson("/auth/login", payload, mergeHeaders());
  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to sign in."));
  }
  const session = (await response.json()) as AuthTokenResponse;
  persistAuthSession(session);
  return session;
}

export async function fetchCurrentUser(token?: string | null): Promise<AuthUser> {
  let response: Response;
  try {
    response = await fetch(apiUrl("/auth/me"), {
      method: "GET",
      headers: authHeaders(token),
    });
  } catch {
    throw new Error(backendUnavailableMessage());
  }
  if (!response.ok) {
    clearAuthSession();
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to verify session."));
  }
  const user = (await response.json()) as AuthUser;
  writeStorage(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
  return user;
}

export async function submitContactInquiry(payload: ContactInquiry): Promise<{ inquiry_id: string; received: boolean }> {
  return submitContactInquiryWithKey(payload);
}

interface SubmissionOptions {
  idempotencyKey?: string;
}

function withIdempotencyHeaders(options?: SubmissionOptions): Record<string, string> {
  if (!options?.idempotencyKey) {
    return defaultHeaders;
  }
  return {
    ...defaultHeaders,
    "Idempotency-Key": options.idempotencyKey
  };
}

export function createIdempotencyKey(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export async function submitContactInquiryWithKey(
  payload: ContactInquiry,
  options?: SubmissionOptions
): Promise<{ inquiry_id: string; received: boolean }> {
  const response = await postJson("/contact-inquiries", payload, withIdempotencyHeaders(options));

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to submit inquiry."));
  }

  return response.json() as Promise<{ inquiry_id: string; received: boolean }>;
}

export async function submitDemoRequest(
  payload: DemoRequest,
  options?: SubmissionOptions
): Promise<{ lead_id: string; received: boolean }> {
  const response = await postJson("/demo-requests", payload, withIdempotencyHeaders(options));

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to submit demo request."));
  }

  return response.json() as Promise<{ lead_id: string; received: boolean }>;
}

export async function resolveLocation(payload: LocationResolveRequest): Promise<LocationResolveResponse> {
  const response = await postJson("/location-resolve", payload);

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to resolve location."));
  }

  return response.json() as Promise<LocationResolveResponse>;
}

export async function sendAssistantChat(payload: AssistantChatRequest): Promise<AssistantChatResponse> {
  const response = await postJson("/assistant-chat", payload);

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Assistant is temporarily unavailable."));
  }

  return response.json() as Promise<AssistantChatResponse>;
}

export async function fetchDashboardData(userKey: string): Promise<DashboardDataResponse> {
  let response: Response;
  try {
    const query = encodeURIComponent(userKey.trim());
    response = await fetch(apiUrl(`/dashboard-data?user_key=${query}`), { method: "GET" });
  } catch {
    throw new Error(backendUnavailableMessage());
  }

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to load dashboard data."));
  }

  return response.json() as Promise<DashboardDataResponse>;
}

export async function fetchDashboardDataAuthenticated(token?: string | null): Promise<DashboardDataResponse> {
  let response: Response;
  try {
    response = await fetch(apiUrl("/dashboard/me"), {
      method: "GET",
      headers: authHeaders(token),
    });
  } catch {
    throw new Error(backendUnavailableMessage());
  }
  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to load authenticated dashboard data."));
  }
  return response.json() as Promise<DashboardDataResponse>;
}

export async function fetchBillingInvoices(token?: string | null): Promise<NonNullable<DashboardDataResponse["billing_history"]>> {
  let response: Response;
  try {
    response = await fetch(apiUrl("/billing/invoices"), {
      method: "GET",
      headers: authHeaders(token),
    });
  } catch {
    throw new Error(backendUnavailableMessage());
  }
  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to load billing history."));
  }
  const payload = (await response.json()) as { invoices?: NonNullable<DashboardDataResponse["billing_history"]> };
  return payload.invoices || [];
}

export async function updateInvoiceStatus(
  invoiceId: string,
  status: "draft" | "issued" | "paid" | "failed",
  token?: string | null
): Promise<void> {
  const normalizedInvoiceId = encodeURIComponent(invoiceId);
  const response = await patchJson(
    `/billing/invoices/${normalizedInvoiceId}/status`,
    { status },
    authHeaders(token)
  );
  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to update billing status."));
  }
}

export function buildInvoiceDownloadUrl(invoiceId: string): string {
  const normalizedInvoiceId = encodeURIComponent(invoiceId);
  return apiUrl(`/billing/invoices/${normalizedInvoiceId}/download`);
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function resolveErrorMessage(errorBody: unknown, fallback: string): string {
  if (!errorBody || typeof errorBody !== "object") {
    return fallback;
  }

  const detail = (errorBody as { detail?: unknown }).detail;
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const text = detail
      .map((entry) => (entry && typeof entry === "object" ? (entry as { msg?: string }).msg : undefined))
      .filter(Boolean)
      .join(", ");
    return text || fallback;
  }

  return fallback;
}
