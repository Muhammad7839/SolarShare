// API client helpers for calling SolarShare FastAPI endpoints from Next.js pages/components.
import {
  AssistantChatRequest,
  AssistantChatResponse,
  ContactInquiry,
  DemoRequest,
  LiveComparisonResponse,
  LocationResolveRequest,
  LocationResolveResponse,
  UserRequest
} from "@/lib/types";

const defaultHeaders = { "Content-Type": "application/json" };
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

export async function fetchLiveComparison(payload: UserRequest): Promise<LiveComparisonResponse> {
  const response = await postJson("/live-comparison", payload);

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to fetch live comparison."));
  }

  return response.json() as Promise<LiveComparisonResponse>;
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
