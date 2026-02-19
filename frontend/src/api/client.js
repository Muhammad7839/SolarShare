const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL;

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;

  let response;
  try {
    response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch {
    throw new Error(`Network error connecting to backend at ${API_BASE_URL}`);
  }

  const contentType = response.headers.get("content-type") || "";
  const hasJson = contentType.includes("application/json");

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    if (hasJson) {
      try {
        const data = await response.json();
        detail = data?.detail || JSON.stringify(data);
      } catch {}
    } else {
      try {
        detail = await response.text();
      } catch {}
    }
    throw new Error(detail);
  }

  if (hasJson) return response.json();
  return response.text();
}

export function healthCheck() {
  return request("/", { method: "GET" });
}

export function getOptions({ location, monthly_usage_kwh, priority }) {
  return request("/options", {
    method: "POST",
    body: JSON.stringify({ location, monthly_usage_kwh, priority }),
  });
}

export function getRecommendation({ location, monthly_usage_kwh, priority }) {
  return request("/recommendation", {
    method: "POST",
    body: JSON.stringify({ location, monthly_usage_kwh, priority }),
  });
}