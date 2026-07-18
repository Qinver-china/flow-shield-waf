import { Modal } from "ant-design-vue";
import { useRouter } from "vue-router";
import { useLogNavigation, type LogNavQuery } from "@/composables/useLogNavigation";

export interface ResourceQuickAction {
  key: string;
  label: string;
  onClick: () => void;
  danger?: boolean;
  divided?: boolean;
  confirm?: string;
}

const LOG_SOURCE_BY_API: Record<string, string> = {
  "/api/v1/rules": "rule",
  "/api/v1/blacklist": "blacklist",
  "/api/v1/ratelimit": "ratelimit",
  "/api/v1/bots": "bot",
};

function hitLogsQuery(apiBase: string, record: Record<string, any>): LogNavQuery | null {
  const id = record.id;
  if (apiBase === "/api/v1/sites" && id) {
    return { tab: "detail", site_id: Number(id) };
  }
  if (apiBase === "/api/v1/bots" && record.name) {
    return { tab: "detail", source: "bot", bot_name: String(record.name) };
  }
  if (apiBase === "/api/v1/bot-categories" && record.value) {
    return { tab: "detail", bot_category: String(record.value) };
  }
  const source = LOG_SOURCE_BY_API[apiBase];
  if (source && id) {
    return { tab: "detail", source, rule_id: Number(id) };
  }
  return null;
}

function statsLogsQuery(apiBase: string, record: Record<string, any>): LogNavQuery | null {
  if (apiBase === "/api/v1/sites") {
    return { tab: "stats", dimension: "site_id" };
  }
  if (apiBase === "/api/v1/bots") {
    return { tab: "stats", dimension: "bot_name" };
  }
  if (apiBase === "/api/v1/bot-categories") {
    return { tab: "stats", dimension: "bot_category" };
  }
  if (LOG_SOURCE_BY_API[apiBase]) {
    return { tab: "stats", dimension: "rule_id" };
  }
  if (apiBase === "/api/v1/ip-groups") {
    return { tab: "stats", dimension: "client_ip" };
  }
  return null;
}

function relatedNavActions(
  apiBase: string,
  record: Record<string, any>,
  router: ReturnType<typeof useRouter>,
): ResourceQuickAction[] {
  const id = record.id;
  if (apiBase !== "/api/v1/sites" || !id) return [];
  const siteId = String(id);
  return [
    {
      key: "goto-rules",
      label: "查看规则",
      onClick: () => router.push({ path: "/rules", query: { site_id: siteId } }),
    },
    {
      key: "goto-ratelimit",
      label: "查看限速",
      onClick: () => router.push({ path: "/ratelimit", query: { site_id: siteId } }),
    },
    {
      key: "goto-blacklist",
      label: "查看黑名单",
      onClick: () => router.push({ path: "/blacklist", query: { site_id: siteId } }),
    },
    {
      key: "goto-whitelist",
      label: "查看白名单",
      onClick: () => router.push({ path: "/whitelist", query: { site_id: siteId } }),
    },
    {
      key: "goto-exceptions",
      label: "查看防护例外",
      onClick: () => router.push({ path: "/exceptions", query: { site_id: siteId } }),
    },
  ];
}

export function useResourceQuickActions() {
  const router = useRouter();
  const { goToLogs } = useLogNavigation();

  function runAction(action: ResourceQuickAction) {
    if (action.confirm) {
      Modal.confirm({
        title: action.confirm,
        okText: "确认",
        cancelText: "取消",
        okButtonProps: action.danger ? { danger: true } : undefined,
        onOk: action.onClick,
      });
      return;
    }
    action.onClick();
  }

  function buildActions(
    apiBase: string,
    record: Record<string, any>,
    handlers: {
      openEdit: () => void;
      openDuplicate?: () => void;
      remove?: () => void;
    },
    opts: { duplicatable?: boolean } = {},
  ): ResourceQuickAction[] {
    const actions: ResourceQuickAction[] = [
      { key: "edit", label: "编辑", onClick: handlers.openEdit },
    ];

    function pushGroup(items: ResourceQuickAction[]) {
      if (!items.length) return;
      if (actions.length > 0) {
        items[0] = { ...items[0], divided: true };
      }
      actions.push(...items);
    }

    if (opts.duplicatable && handlers.openDuplicate) {
      actions.push({ key: "duplicate", label: "复制", onClick: handlers.openDuplicate });
    }

    const logActions: ResourceQuickAction[] = [];
    const hitLogs = hitLogsQuery(apiBase, record);
    if (hitLogs) {
      logActions.push({
        key: "logs-hit",
        label: "查看命中日志",
        onClick: () => goToLogs(hitLogs),
      });
    }
    const statsLogs = statsLogsQuery(apiBase, record);
    if (statsLogs) {
      logActions.push({
        key: "logs-stats",
        label: "查看日志统计",
        onClick: () => goToLogs(statsLogs),
      });
    }
    pushGroup(logActions);
    pushGroup(relatedNavActions(apiBase, record, router));

    if (handlers.remove) {
      pushGroup([
        {
          key: "delete",
          label: "删除",
          danger: true,
          confirm: "确认删除该记录？",
          onClick: handlers.remove,
        },
      ]);
    }

    return actions;
  }

  return { buildActions, runAction };
}
