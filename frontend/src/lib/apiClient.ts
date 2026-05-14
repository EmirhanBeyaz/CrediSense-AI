import { API_BASE_URL } from "./endpoints";
import type { ApiResult } from "@/types";

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
      const message = payload?.error?.message || payload?.detail || "API isteği başarısız oldu.";
      return { data: null, error: message, fromFallback: false };
    }

    return { data: payload as T, error: "", fromFallback: false };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : "API bağlantısı kurulamadı.",
      fromFallback: false,
    };
  }
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
