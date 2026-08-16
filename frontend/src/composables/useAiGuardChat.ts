import { Modal, message } from "ant-design-vue";
import dayjs from "dayjs";
import { computed, h, onMounted, onUnmounted, ref, watch } from "vue";
import type { Conversation } from "ant-design-x-vue";
import type { ConversationsProps, PromptProps } from "ant-design-x-vue";
import { api, type ApiResp } from "@/api";
import ChatAssistantContent from "@/components/ai-chat/ChatAssistantContent.vue";
import ChatMarkdownContent from "@/components/ai-chat/ChatMarkdownContent.vue";

export interface ChatStreamStep {
  id: string;
  kind: "thinking" | "tool" | "generating" | "reasoning";
  label: string;
  detail?: string;
  status: "running" | "done" | "error";
  tool?: string;
}

export interface ChatMsg {
  id?: number;
  role: string;
  content: string;
  steps?: ChatStreamStep[];
  pending_action?: Record<string, unknown> | null;
  action_status?: string | null;
}

export interface ChatSessionRow {
  id: number;
  title: string;
  created_at?: string;
}

function formatChatError(err: unknown): string {
  const raw = err instanceof Error ? err.message : String(err);
  if (raw.includes("502") || raw.toLowerCase().includes("upstream")) {
    return "AI 中转站暂时不可用（502），请稍后重试或在 AI 配置中更换模型。";
  }
  if (raw.includes("401")) {
    return "登录已过期，请重新登录。";
  }
  if (raw.includes("连接中断") || raw.toLowerCase().includes("timeout")) {
    return "AI 响应超时或连接中断，请稍后重试。";
  }
  return raw || "发送失败";
}

function markAssistantStreamFailed(assistantMsg: ChatMsg, errText: string) {
  if (!assistantMsg.content?.trim()) {
    assistantMsg.content = errText;
  }
  if (assistantMsg.steps?.length) {
    assistantMsg.steps = assistantMsg.steps.map((step) =>
      step.status === "running" ? { ...step, status: "error" as const } : step,
    );
  }
}

function sessionGroup(createdAt?: string): string {
  if (!createdAt) return "更早";
  return dayjs(createdAt).isSame(dayjs(), "day") ? "今天" : "更早";
}

function unwrapApiData<T>(res: ApiResp<T> | T): T {
  if (res != null && typeof res === "object" && "data" in res && "code" in res) {
    return (res as ApiResp<T>).data;
  }
  return res as T;
}

export interface UseAiGuardChatOptions {
  autoLoadSessions?: boolean;
  /** 打开时自动恢复最近会话（悬浮窗） */
  restoreLatestSession?: boolean;
  getPreferredSessionId?: () => number | null;
  onSessionIdChange?: (id: number | null) => void;
}

/**
 * Shared chat state for the AI Guard page panel and the floating popup.
 * Both UIs must see the same sessions/messages without a page refresh.
 *
 * Options are applied per caller. The first `useAiGuardChat()` (often the
 * always-mounted floating shell with autoLoadSessions=false) must not freeze
 * init behavior for later surfaces.
 */
function createAiGuardChat() {
  const sessions = ref<ChatSessionRow[]>([]);
  const sessionsLoading = ref(false);
  const sessionId = ref<number | null>(null);
  const messages = ref<ChatMsg[]>([]);
  const input = ref("");
  const sending = ref(false);
  const pendingAction = ref<Record<string, unknown> | null>(null);
  const pendingMessageId = ref<number | null>(null);
  const streamingAssistantKey = ref<string | null>(null);
  const messageListKey = ref(0);
  let streamAbort: AbortController | null = null;
  let stayOnNewSession = false;
  let surfaceCount = 0;
  let inflightLoad: Promise<void> | null = null;
  const hooks: {
    getPreferredSessionId?: () => number | null;
    onSessionIdChange?: (id: number | null) => void;
  } = {};

  function applyOptions(options?: UseAiGuardChatOptions) {
    if (!options) return;
    if (options.getPreferredSessionId) {
      hooks.getPreferredSessionId = options.getPreferredSessionId;
    }
    if (options.onSessionIdChange) {
      hooks.onSessionIdChange = options.onSessionIdChange;
      options.onSessionIdChange(sessionId.value);
    }
  }

  function retain() {
    surfaceCount += 1;
  }

  function release() {
    surfaceCount = Math.max(0, surfaceCount - 1);
    if (surfaceCount === 0) {
      stopGeneration();
    }
  }

  function currentSessionTitle() {
    const text = messages.value.find((m) => m.role === "user")?.content?.trim();
    return text ? text.slice(0, 40) : "新对话";
  }

  function upsertSession(row: ChatSessionRow) {
    const rest = sessions.value.filter((s) => s.id !== row.id);
    sessions.value = [row, ...rest];
  }

  function stopGeneration() {
    if (!streamAbort) {
      sending.value = false;
      streamingAssistantKey.value = null;
      return;
    }
    streamAbort.abort();
    streamAbort = null;
    sending.value = false;
    streamingAssistantKey.value = null;
  }

  const conversationItems = computed<Conversation[]>(() =>
    sessions.value.map((s) => ({
      key: String(s.id),
      label: s.title,
      group: sessionGroup(s.created_at),
    })),
  );

  const activeConversationKey = computed(() =>
    sessionId.value == null ? undefined : String(sessionId.value),
  );

  const bubbleItems = computed(() =>
    messages.value.map((msg, index) => {
      const key = msg.id != null ? String(msg.id) : `local-${index}`;
      const isStreaming =
        sending.value && streamingAssistantKey.value === key && msg.role === "assistant";
      const hasSteps = Boolean(msg.steps?.length);
      const hasContent = Boolean(msg.content?.trim());
      return {
        key,
        messageId: msg.id ?? null,
        role: msg.role,
        content: msg.content,
        steps: msg.steps,
        pending_action: msg.pending_action ?? null,
        action_status: msg.action_status ?? null,
        loading: isStreaming && !hasSteps && !hasContent,
      };
    }),
  );

  const renderAssistant = (content: string, steps?: ChatStreamStep[]) =>
    h(ChatAssistantContent, {
      content: String(content || ""),
      steps,
    });

  const renderUser = (content: string) =>
    h(ChatMarkdownContent, { content: String(content || "") });

  const bubbleRoles = (bubbleData: { role?: string; steps?: ChatStreamStep[] }) => {
    if (bubbleData.role === "assistant") {
      return {
        placement: "start" as const,
        variant: "filled" as const,
        messageRender: (content: string) =>
          renderAssistant(content, bubbleData.steps),
      };
    }
    return {
      placement: "end" as const,
      variant: "shadow" as const,
      messageRender: renderUser,
    };
  };

  const resolvedBubbles = computed(() =>
    bubbleItems.value.map((item) => {
      const roleProps = bubbleRoles(item);
      return {
        key: item.key,
        content: item.content ?? "",
        loading: item.loading,
        placement: roleProps.placement,
        variant: roleProps.variant,
        messageRender: roleProps.messageRender,
        typing: false as const,
      };
    }),
  );

  const welcomePrompts: PromptProps[] = [
    {
      key: "hot",
      label: "常用场景",
      children: [
        {
          key: "xss",
          description: "生成防 XSS 的观察规则，尽量避免误伤正常请求",
        },
        {
          key: "sqli",
          description: "分析最近 24 小时拦截日志，找出 SQL 注入攻击特征",
        },
        {
          key: "cc",
          description: "为动态页面创建一条 CC 限速策略，排除静态资源",
        },
      ],
    },
    {
      key: "ops",
      label: "运维助手",
      children: [
        {
          key: "stats",
          description: "查看最近 24 小时 WAF 拦截统计概览",
        },
        {
          key: "bot",
          description: "列出当前所有自定义防护规则",
        },
        {
          key: "whitelist",
          description: "帮我创建一条办公网白名单，放行内网 IP",
        },
        {
          key: "exception",
          description: "为后台编辑器创建防护例外，避免富文本误拦截",
        },
      ],
    },
  ];

  const senderPrompts: PromptProps[] = [
    { key: "logs", description: "查询拦截日志", icon: undefined },
    { key: "blacklist", description: "创建黑名单", icon: undefined },
    { key: "rule", description: "生成自定义规则", icon: undefined },
    { key: "cc", description: "CC 限速策略", icon: undefined },
  ];

  async function loadSessions() {
    if (inflightLoad) return inflightLoad;
    sessionsLoading.value = true;
    inflightLoad = (async () => {
      try {
        const res = await api.get<ChatSessionRow[]>("/api/v1/ai-guard/chat/sessions");
        const fetched = unwrapApiData(res);
        const rows = Array.isArray(fetched) ? [...fetched] : [];
        if (
          sessionId.value != null &&
          !rows.some((s) => s.id === sessionId.value)
        ) {
          const existing = sessions.value.find((s) => s.id === sessionId.value);
          rows.unshift(
            existing ?? {
              id: sessionId.value,
              title: currentSessionTitle(),
              created_at: new Date().toISOString(),
            },
          );
        }
        sessions.value = rows;
      } finally {
        sessionsLoading.value = false;
        inflightLoad = null;
      }
    })();
    return inflightLoad;
  }

  async function loadMessages(id: number) {
    const res = await api.get<ChatMsg[]>(`/api/v1/ai-guard/chat/sessions/${id}/messages`);
    const rows = unwrapApiData(res) || [];
    messages.value = rows.map((m) => ({
      ...m,
      content: m.content ?? "",
      role: m.role || "user",
    }));
    messageListKey.value += 1;
    const pending = [...messages.value].reverse().find(
      (m) => m.pending_action && m.action_status === "pending",
    );
    pendingAction.value = pending?.pending_action || null;
    pendingMessageId.value = pending?.id ?? null;
  }

  async function restorePreferredSession() {
    if (stayOnNewSession || sessionId.value != null || sending.value) return;
    const preferred = hooks.getPreferredSessionId?.() ?? null;
    const target =
      preferred != null && sessions.value.some((s) => s.id === preferred)
        ? preferred
        : (sessions.value[0]?.id ?? null);
    if (target != null) {
      await openSession(target);
    }
  }

  function newSession() {
    stayOnNewSession = true;
    sessionId.value = null;
    messages.value = [];
    input.value = "";
    pendingAction.value = null;
    pendingMessageId.value = null;
    streamingAssistantKey.value = null;
  }

  async function openSession(id: number) {
    if (sending.value) {
      message.warning("请等待当前回复完成");
      return;
    }
    stayOnNewSession = false;
    sessionId.value = id;
    await loadMessages(id);
  }

  async function deleteSession(id: number) {
    if (sending.value) {
      message.warning("请等待当前回复完成");
      return;
    }
    try {
      await api.delete(`/api/v1/ai-guard/chat/sessions/${id}`);
      if (sessionId.value === id) {
        newSession();
      }
      await loadSessions();
      message.success("会话已删除");
    } catch (e: unknown) {
      message.error(formatChatError(e));
    }
  }

  function confirmDeleteSession(id: number) {
    Modal.confirm({
      title: "删除会话",
      content: "删除后无法恢复，确定要删除这条会话吗？",
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: () => deleteSession(id),
    });
  }

  async function clearAllSessions() {
    if (sending.value) {
      message.warning("请等待当前回复完成");
      return;
    }
    Modal.confirm({
      title: "清空所有对话",
      content: "将删除全部会话记录，且无法恢复，确定继续吗？",
      okText: "清空",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          await api.del("/api/v1/ai-guard/chat/sessions");
          newSession();
          await loadSessions();
          message.success("已清空所有对话");
        } catch (e: unknown) {
          message.error(formatChatError(e));
        }
      },
    });
  }

  const conversationMenu: ConversationsProps["menu"] = (conversation) => ({
    items: [{ key: "delete", label: "删除", danger: true }],
    onClick: ({ key }) => {
      if (key === "delete") {
        const id = Number(conversation.key);
        if (Number.isFinite(id)) confirmDeleteSession(id);
      }
    },
  });

  function onConversationChange(key: string) {
    const id = Number(key);
    if (!Number.isFinite(id)) return;
    void openSession(id);
  }

  function upsertStreamStep(msg: ChatMsg, step: ChatStreamStep) {
    if (!msg.steps) msg.steps = [];
    const idx = msg.steps.findIndex((s) => s.id === step.id);
    if (idx >= 0) {
      msg.steps[idx] = { ...msg.steps[idx], ...step };
    } else {
      msg.steps.push(step);
    }
    msg.steps = [...msg.steps];
  }

  function handleStreamEvent(parsed: Record<string, unknown>, assistantMsg: ChatMsg) {
    if (parsed.type === "session") {
      const id = Number(parsed.session_id);
      if (!Number.isFinite(id)) return;
      stayOnNewSession = false;
      sessionId.value = id;
      upsertSession({
        id,
        title: currentSessionTitle(),
        created_at: new Date().toISOString(),
      });
      return;
    }
    if (parsed.type === "step") {
      upsertStreamStep(assistantMsg, {
        id: String(parsed.id),
        kind: (parsed.kind as ChatStreamStep["kind"]) || "thinking",
        label: String(parsed.label || ""),
        detail: parsed.detail != null ? String(parsed.detail) : undefined,
        status: (parsed.status as ChatStreamStep["status"]) || "running",
        tool: parsed.tool != null ? String(parsed.tool) : undefined,
      });
      return;
    }
    if (parsed.type === "delta") {
      assistantMsg.content += String(parsed.delta || "");
      return;
    }
    if (parsed.type === "done") {
      assistantMsg.id = Number(parsed.message_id);
      streamingAssistantKey.value = String(parsed.message_id);
      if (parsed.pending_action) {
        const action = parsed.pending_action as Record<string, unknown>;
        assistantMsg.pending_action = action;
        assistantMsg.action_status = "pending";
        pendingAction.value = action;
        pendingMessageId.value = Number(parsed.message_id);
      } else {
        assistantMsg.pending_action = null;
        assistantMsg.action_status = null;
        pendingAction.value = null;
        pendingMessageId.value = null;
      }
    }
  }

  async function send(textOverride?: string) {
    const text = (textOverride ?? input.value).trim();
    if (!text || sending.value) return;

    stopGeneration();
    streamAbort = new AbortController();
    const signal = streamAbort.signal;

    sending.value = true;
    messages.value.push({ role: "user", content: text });
    input.value = "";

    const assistantIdx = messages.value.length;
    const assistantKey = `local-${assistantIdx}`;
    streamingAssistantKey.value = assistantKey;
    messages.value.push({ role: "assistant", content: "", steps: [] });
    const assistantMsg = messages.value[assistantIdx]!;

    try {
      const token = localStorage.getItem("waf_access_token");
      const resp = await fetch("/api/v1/ai-guard/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ session_id: sessionId.value, message: text }),
        signal,
      });

      if (!resp.ok) {
        if (resp.status === 401) {
          localStorage.removeItem("waf_access_token");
          location.href = "/login";
          return;
        }
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.message || "请求失败");
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("无法读取响应流");

      const decoder = new TextDecoder();
      let buffer = "";
      let streamFinished = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") {
            streamFinished = true;
            continue;
          }
          let parsed: Record<string, unknown>;
          try {
            parsed = JSON.parse(raw);
          } catch {
            continue;
          }
          if (parsed.type === "error") throw new Error(String(parsed.message || "请求失败"));
          handleStreamEvent(parsed, assistantMsg);
          if (parsed.type === "done") streamFinished = true;
        }
      }
      if (!streamFinished) {
        throw new Error("连接中断，AI 响应未完成");
      }
      if (sessionId.value != null) {
        await loadMessages(sessionId.value);
      }
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === "AbortError") {
        if (!assistantMsg.content?.trim()) {
          assistantMsg.content = "（已停止生成）";
        }
        return;
      }
      const errText = formatChatError(e);
      if (sessionId.value != null) {
        try {
          await loadMessages(sessionId.value);
        } catch {
          markAssistantStreamFailed(assistantMsg, errText);
        }
      } else {
        markAssistantStreamFailed(assistantMsg, errText);
      }
      const hasAssistant = messages.value.some((m) => m.role === "assistant");
      if (!hasAssistant) {
        messages.value.push({ role: "assistant", content: errText });
        messageListKey.value += 1;
      }
      message.error(errText);
    } finally {
      if (streamAbort?.signal === signal) {
        streamAbort = null;
      }
      sending.value = false;
      streamingAssistantKey.value = null;
      try {
        await loadSessions();
      } catch {
        // list refresh is best-effort; stream errors are already surfaced
      }
    }
  }

  async function onActionDone() {
    await resolvePendingAction(true);
  }

  async function clearPending() {
    await resolvePendingAction(false);
  }

  async function resolvePendingAction(approved: boolean) {
    pendingAction.value = null;
    pendingMessageId.value = null;
    if (sessionId.value != null) {
      await loadMessages(sessionId.value);
    }
    message.success(approved ? "已确认执行" : "已取消执行");
  }

  function onPromptClick(info: { data: PromptProps }) {
    const text = info.data.description || info.data.label;
    if (typeof text === "string" && text.trim()) {
      void send(text);
    }
  }

  watch(sessionId, (id) => hooks.onSessionIdChange?.(id));

  async function ensureInitialized(callOptions?: UseAiGuardChatOptions) {
    if (callOptions?.autoLoadSessions === false) return;
    await loadSessions();
    if (callOptions?.restoreLatestSession) {
      await restorePreferredSession();
    }
  }

  return {
    sessions,
    sessionsLoading,
    sessionId,
    messages,
    input,
    sending,
    pendingAction,
    pendingMessageId,
    conversationItems,
    activeConversationKey,
    bubbleItems,
    resolvedBubbles,
    messageListKey,
    bubbleRoles,
    welcomePrompts,
    senderPrompts,
    conversationMenu,
    loadSessions,
    loadMessages,
    newSession,
    openSession,
    deleteSession,
    clearAllSessions,
    onConversationChange,
    send,
    stopGeneration,
    onActionDone,
    onPromptClick,
    clearPending,
    ensureInitialized,
    applyOptions,
    retain,
    release,
  };
}

let sharedChat: ReturnType<typeof createAiGuardChat> | null = null;

/** Returns the app-wide AI chat instance (page + floating popup share one state). */
export function useAiGuardChat(options?: UseAiGuardChatOptions) {
  if (!sharedChat) {
    sharedChat = createAiGuardChat();
  }
  sharedChat.applyOptions(options);
  onMounted(() => {
    sharedChat?.retain();
    void sharedChat?.ensureInitialized(options);
  });
  onUnmounted(() => {
    // Abort in-flight stream only when no chat surface remains mounted.
    sharedChat?.release();
  });
  return sharedChat;
}
