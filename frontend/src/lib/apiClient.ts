import type { ApiResult } from "@/types";
import { API_BASE_URL } from "./endpoints";

type RequestOptions = {
  method?: string;
  body?: BodyInit | object;
  headers?: HeadersInit;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<ApiResult<T>> {
  const headers = new Headers(options.headers);
  const isFormData = options.body instanceof FormData;
  const token = getAuthToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let body: BodyInit | undefined;
  if (options.body && !isFormData && typeof options.body === "object") {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  } else {
    body = options.body as BodyInit | undefined;
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method || "GET",
      headers,
      body,
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      return {
        data: null,
        error: extractErrorMessage(payload, response.status),
        fromFallback: false,
      };
    }

    return { data: payload as T, error: "", fromFallback: false };
  } catch (error) {
    const message = error instanceof Error ? error.message : "";
    return {
      data: null,
      error: message.includes("Failed to fetch")
        ? "Backend baglantisi kurulamadı. Once backend_baslat.bat dosyasini calistirip FastAPI servisinin acik kaldigindan emin ol."
        : message || "API baglantisi kurulamadi.",
      fromFallback: false,
    };
  }
}

function extractErrorMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object") {
    const body = payload as { error?: { message?: string }; detail?: string };
    return body.error?.message || body.detail || `API istegi basarisiz oldu. HTTP ${status}`;
  }

  if (typeof payload === "string" && payload.trim()) {
    const shortText = payload.replace(/\s+/g, " ").slice(0, 180);
    return `API istegi basarisiz oldu. HTTP ${status}: ${shortText}`;
  }

  return `API istegi basarisiz oldu. HTTP ${status}`;
}

export function setAuthToken(token: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("credisense_access_token", token);
  }
}

export function clearAuthToken() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("credisense_access_token");
  }
}

export function getAuthToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem("credisense_access_token") || "";
}
