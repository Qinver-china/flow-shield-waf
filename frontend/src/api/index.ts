import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { message } from "ant-design-vue";

const http: AxiosInstance = axios.create({
  baseURL: "/",
  timeout: 15000,
});

type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string> | null = null;

function getRefreshToken() {
  return localStorage.getItem("waf_refresh_token");
}

function setTokens(accessToken: string, refreshToken?: string) {
  localStorage.setItem("waf_access_token", accessToken);
  if (refreshToken) {
    localStorage.setItem("waf_refresh_token", refreshToken);
  }
}

function clearSession() {
  localStorage.removeItem("waf_access_token");
  localStorage.removeItem("waf_refresh_token");
  localStorage.removeItem("waf_username");
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("missing refresh token");
  }
  const resp = await axios.post("/api/v1/auth/refresh", {
    refresh_token: refreshToken,
  });
  const body = resp.data?.data ?? resp.data;
  const accessToken = body?.access_token;
  const nextRefresh = body?.refresh_token;
  if (!accessToken) {
    throw new Error("refresh failed");
  }
  setTokens(accessToken, nextRefresh);
  return accessToken;
}

function shouldAttemptRefresh(url?: string) {
  if (!url) return false;
  return !url.includes("/api/v1/auth/login") && !url.includes("/api/v1/auth/refresh");
}

function formatErrorMessage(error: any) {
  const status = error.response?.status;
  const payload = error.response?.data;
  const msg = payload?.message || error.message;
  if (status === 422 && Array.isArray(payload?.data)) {
    const detail = payload.data
      .map((item: any) => item?.msg || JSON.stringify(item))
      .filter(Boolean)
      .join("；");
    return detail ? `参数校验失败：${detail}` : "参数校验失败";
  }
  return msg || "请求失败";
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("waf_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (resp) => resp.data,
  async (error) => {
    const status = error.response?.status;
    const config = error.config as RetryConfig | undefined;

    if (status === 401 && config && !config._retry && shouldAttemptRefresh(config.url)) {
      config._retry = true;
      try {
        refreshPromise = refreshPromise ?? refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
        const token = await refreshPromise;
        config.headers = config.headers ?? {};
        config.headers.Authorization = `Bearer ${token}`;
        return http(config);
      } catch {
        clearSession();
        if (location.pathname !== "/login") location.href = "/login";
        return Promise.reject(error);
      }
    }

    if (status === 401 && shouldAttemptRefresh(config?.url)) {
      clearSession();
      if (location.pathname !== "/login") location.href = "/login";
    } else if (status !== 401) {
      message.error(formatErrorMessage(error));
    }
    return Promise.reject(error);
  },
);

export interface ApiResp<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface PageData<T = any> {
  total: number;
  items: T[];
  page: number;
  page_size: number;
}

/** Second argument is the query dict itself — do not nest `{ params: {...} }`. */
export const api = {
  get: <T = any>(url: string, params?: Record<string, unknown>) =>
    http.get(url, { params }) as unknown as Promise<ApiResp<T>>,
  post: <T = any>(url: string, data?: any) =>
    http.post(url, data) as unknown as Promise<ApiResp<T>>,
  put: <T = any>(url: string, data?: any) =>
    http.put(url, data) as unknown as Promise<ApiResp<T>>,
  del: <T = any>(url: string) => http.delete(url) as unknown as Promise<ApiResp<T>>,
  upload: <T = any>(url: string, data: FormData) =>
    http.post(url, data, {
      headers: { "Content-Type": "multipart/form-data" },
    }) as unknown as Promise<ApiResp<T>>,
};

export { clearSession, refreshAccessToken, setTokens };

export default http;
