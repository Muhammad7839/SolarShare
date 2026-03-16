// API client helpers for calling SolarShare FastAPI endpoints from Next.js pages/components.
import {
  AssistantChatRequest,
  AssistantChatResponse,
  ContactInquiry,
  LiveComparisonResponse,
  LocationResolveRequest,
  LocationResolveResponse,
  UserRequest
} from "@/lib/types";

const configuredApiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();
const defaultApiBase = configuredApiBase.replace(/\/+$/, "");
const defaultHeaders = { "Content-Type": "application/json" };

function runtimeApiBase(): string {
  if (defaultApiBase) {
    return defaultApiBase;
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname === "localhost" ? "127.0.0.1" : window.location.hostname;
    if (window.location.port === "3000" || window.location.port === "3001") {
      return `http://${host}:8000`;
    }
  }
  return "";
}

function apiUrl(path: string): string {
  const base = runtimeApiBase();
  if (!base) {
    return path;
  }
  return `${base}${path}`;
}

export async function fetchLiveComparison(payload: UserRequest): Promise<LiveComparisonResponse> {
  const response = await fetch(apiUrl("/live-comparison"), {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to fetch live comparison."));
  }

  return response.json() as Promise<LiveComparisonResponse>;
}

export async function submitContactInquiry(payload: ContactInquiry): Promise<{ inquiry_id: string; received: boolean }> {
  const response = await fetch(apiUrl("/contact-inquiries"), {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to submit inquiry."));
  }

  return response.json() as Promise<{ inquiry_id: string; received: boolean }>;
}

export async function resolveLocation(payload: LocationResolveRequest): Promise<LocationResolveResponse> {
  const response = await fetch(apiUrl("/location-resolve"), {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw new Error(resolveErrorMessage(errorBody, "Unable to resolve location."));
  }

  return response.json() as Promise<LocationResolveResponse>;
}

export async function sendAssistantChat(payload: AssistantChatRequest): Promise<AssistantChatResponse> {
  const response = await fetch(apiUrl("/assistant-chat"), {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });

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
