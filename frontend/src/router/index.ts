import { createRouter, createWebHistory, type RouteLocationNormalized } from "vue-router";

/**
 * Browsers cache a rejected dynamic import(); after a brief network blip the same
 * chunk URL keeps failing until a full page load clears that entry.
 */
function isChunkLoadError(error: unknown): boolean {
  const msg = error instanceof Error ? error.message : String(error ?? "");
  return /Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk \d+ failed/i.test(
    msg,
  );
}

/** Hard-navigate to the target route so chunks are fetched with a clean module map. */
function recoverFromChunkLoadError(to: RouteLocationNormalized): void {
  const key = "fs:chunk-reload-at";
  const last = Number(sessionStorage.getItem(key) || "0");
  // Avoid reload loops while the network is still down.
  if (Date.now() - last < 10_000) return;
  sessionStorage.setItem(key, String(Date.now()));

  const base = (import.meta.env.BASE_URL || "/").replace(/\/$/, "");
  const path = to.fullPath.startsWith("/") ? to.fullPath : `/${to.fullPath}`;
  window.location.assign(`${base}${path}`);
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("@/views/Login.vue"), meta: { public: true } },
    {
      path: "/",
      component: () => import("@/layouts/BasicLayout.vue"),
      redirect: "/dashboard",
      children: [
        { path: "dashboard", component: () => import("@/views/Dashboard.vue"), meta: { title: "总览" } },
        { path: "sites", component: () => import("@/views/Sites.vue"), meta: { title: "站点管理" } },
        { path: "certificates", component: () => import("@/views/Certificates.vue"), meta: { title: "证书管理" } },
        { path: "rules", component: () => import("@/views/Rules.vue"), meta: { title: "自定义规则" } },
        { path: "blacklist", component: () => import("@/views/Blacklist.vue"), meta: { title: "黑名单" } },
        { path: "whitelist", component: () => import("@/views/Whitelist.vue"), meta: { title: "白名单" } },
        { path: "ip-groups", component: () => import("@/views/IpGroups.vue"), meta: { title: "IP 组管理" } },
        { path: "exceptions", component: () => import("@/views/Exceptions.vue"), meta: { title: "防护例外" } },
        { path: "ratelimit", component: () => import("@/views/RateLimit.vue"), meta: { title: "速率防护" } },
        { path: "bots", component: () => import("@/views/Bots.vue"), meta: { title: "Bot 库" } },
        { path: "logs", component: () => import("@/views/Logs.vue"), meta: { title: "防护日志" } },
        { path: "alerts", component: () => import("@/views/AlertPolicies.vue"), meta: { title: "预警通知" } },
        { path: "ai-guard", component: () => import("@/views/ai-guard/AiGuard.vue"), meta: { title: "AI 防护" } },
        { path: "settings", component: () => import("@/views/Settings.vue"), meta: { title: "系统设置" } },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("waf_access_token");
  if (!to.meta.public && !token) {
    return "/login";
  }
  if (to.path === "/login" && token) {
    return "/dashboard";
  }
  return true;
});

const preloadChunkErrors = new Set<unknown>();

window.addEventListener("vite:preloadError", (event) => {
  preloadChunkErrors.add(event.payload);
});

window.addEventListener("unhandledrejection", (event) => {
  if (isChunkLoadError(event.reason) || preloadChunkErrors.has(event.reason)) {
    event.preventDefault();
  }
});

router.onError((error, to) => {
  if (isChunkLoadError(error) || preloadChunkErrors.has(error)) {
    preloadChunkErrors.delete(error);
    recoverFromChunkLoadError(to);
  }
});

router.afterEach(() => {
  sessionStorage.removeItem("fs:chunk-reload-at");
});

export default router;
