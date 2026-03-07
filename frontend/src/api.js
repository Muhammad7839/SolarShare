// src/api.js

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const BASE =
  (import.meta.env.VITE_API_BASE_URL || "").trim() || DEFAULT_BASE_URL;

function joinUrl(base, path) {
  const b = base.endsWith("/") ? base.slice(0, -1) : base;
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

async function readErrorMessage(res) {
  let text = "";
  try {
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      const data = await res.json();
      if (typeof data === "string") return data;
      if (data?.detail) return String(data.detail);
      if (data?.message) return String(data.message);
      if (data?.error) return String(data.error);
      return JSON.stringify(data);
    }
    text = await res.text();
  } catch {
    text = "";
  }
  return text || `Request failed (${res.status})`;
}

async function request(path, options = {}) {
  const url = joinUrl(BASE, path);

  let res;
  try {
    res = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new Error(`Network error connecting to backend at ${BASE}`);
  }

  if (!res.ok) {
    const msg = await readErrorMessage(res);
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export function healthCheck() {
  return request("/", { method: "GET" });
}

export function checkEligibility({ zip }) {
  return request("/api/check-eligibility", {
    method: "POST",
    body: JSON.stringify({ zip }),
  });
}

export function getProjects({ territory_id }) {
  const q = new URLSearchParams({ territory_id: String(territory_id || "") });
  return request(`/api/projects?${q.toString()}`, { method: "GET" });
}

export function estimate({ zip, monthly_usage_kwh, project_id }) {
  return request("/api/estimate", {
    method: "POST",
    body: JSON.stringify({ zip, monthly_usage_kwh, project_id }),
  });
}

export function enroll(payload) {
  return request("/api/enroll", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getEnrollment(enrollment_id) {
  const q = new URLSearchParams({ enrollment_id: String(enrollment_id || "") });
  return request(`/api/enrollment?${q.toString()}`, { method: "GET" });
}