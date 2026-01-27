/**
 * Centralized API utility for making requests to the backend.
 * Handles CORS, base URL configuration, and common headers.
 */

// Get backend URL from environment or default to empty (for local dev with rewrites)
export const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";

/**
 * Build the full API URL for a given path.
 * If NEXT_PUBLIC_BACKEND_URL is set, use it as base.
 * Otherwise, use relative paths (for local dev with Next.js rewrites).
 */
export function getApiUrl(path: string): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  
  // If we have a backend URL, use it
  if (API_BASE_URL) {
    // Remove trailing slash from base URL if present
    const baseUrl = API_BASE_URL.replace(/\/$/, "");
    return `${baseUrl}${normalizedPath}`;
  }
  
  // Otherwise, use relative path (for local development with Next.js rewrites)
  return normalizedPath;
}

/**
 * Common fetch options for API requests.
 * Includes CORS mode and credentials.
 */
export const defaultFetchOptions: RequestInit = {
  mode: "cors",
  credentials: "include",
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json",
  },
};

/**
 * Make a GET request to the API.
 */
export async function apiGet<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(path);
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    method: "GET",
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorData.message || response.statusText, errorData);
  }
  
  return response.json();
}

/**
 * Make a POST request to the API.
 */
export async function apiPost<T = unknown>(
  path: string,
  body?: unknown,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(path);
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    method: "POST",
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorData.message || response.statusText, errorData);
  }
  
  return response.json();
}

/**
 * Make a PUT request to the API.
 */
export async function apiPut<T = unknown>(
  path: string,
  body?: unknown,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(path);
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    method: "PUT",
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorData.message || response.statusText, errorData);
  }
  
  return response.json();
}

/**
 * Make a DELETE request to the API.
 */
export async function apiDelete<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = getApiUrl(path);
  const response = await fetch(url, {
    ...defaultFetchOptions,
    ...options,
    method: "DELETE",
    headers: {
      ...defaultFetchOptions.headers,
      ...options.headers,
    },
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorData.message || response.statusText, errorData);
  }
  
  return response.json();
}

/**
 * Make a raw fetch request with full control.
 * Use this for file uploads, streaming, etc.
 */
export async function apiFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = getApiUrl(path);
  return fetch(url, {
    mode: "cors",
    credentials: "include",
    ...options,
  });
}

/**
 * Custom API error class for better error handling.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}
