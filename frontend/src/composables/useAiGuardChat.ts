import { Modal, message } from "ant-design-vue";
import dayjs from "dayjs";
import { computed, h, onMounted, ref } from "vue";
import type { Conversation } from "ant-design-x-vue";
import type { BubbleDataType } from "ant-design-x-vue";
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

export function useAiGuardChat(options?: { autoLoadSessions?: boolean }) {
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

  const bubbleItems = computed<BubbleDataType[]>(() => {
    const items: BubbleDataType[] = messages.value.map((msg, index) => {
      const key = msg.id != null ? String(msg.id) : `local-${index}`;
      const isStreaming =
        sending.value && streamingAssistantKey.value === key && msg.role === "assistant";
      const hasSteps = Boolean(msg.steps?.length);
      const hasContent = Boolean(msg.content?.trim());
      return {
        key,
        role: msg.role,
        content: msg.content,
        steps: msg.steps,
        loading: isStreaming && !hasSteps && !hasContent,
      };
    });
    return items;
  });

  const renderAssistant = (content: string, steps?: ChatStreamStep[]) =>
    h(ChatAssistantContent, {
      content: String(content || ""),
      steps,
    });

  const renderUser = (content: string) =>
    h(ChatMarkdownContent, { content: String(content || "") });

  const bubbleRoles = (bubbleData: BubbleDataType) => {
    if (bubbleData.role === "assistant") {
      return {
        placement: "start" as const,
        variant: "filled" as const,
        messageRender: (content: string) =>
          renderAssistant(content, bubbleData.steps as ChatStreamStep[] | undefined),
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
          description: "帮我设计一条后台编辑器白名单，避免富文本误拦截",
        },
      ],
    },
  ];

  const senderPrompts: PromptProps[] = [
    { key: "logs", description: "查询拦截日志", icon: undefined },
    { key: "rule", description: "生成防护规则", icon: undefined },
    { key: "cc", description: "CC 限速策略", icon: undefined },
    { key: "help", description: "排查误拦截", icon: undefined },
  ];

  async function loadSessions() {
    sessionsLoading.value = true;
    try {
      const res = await api.get<ChatSessionRow[]>("/api/v1/ai-guard/chat/sessions");
      sessions.value = unwrapApiData(res) || [];
    } finally {
      sessionsLoading.value = false;
    }
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

  function newSession() {
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
      sessionId.value = Number(parsed.session_id);
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
        pendingAction.value = parsed.pending_action as Record<string, unknown>;
        pendingMessageId.value = Number(parsed.message_id);
      } else {
        pendingAction.value = null;
        pendingMessageId.value = null;
      }
    }
  }

  async function send(textOverride?: string) {
    const text = (textOverride ?? input.value).trim();
    if (!text || sending.value) return;

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
      await loadSessions();
      if (sessionId.value != null) {
        await loadMessages(sessionId.value);
      }
    } catch (e: unknown) {
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
      sending.value = false;
      streamingAssistantKey.value = null;
    }
  }

  function onActionDone() {
    pendingAction.value = null;
    if (sessionId.value) void loadMessages(sessionId.value);
    message.success("操作已处理");
  }

  function clearPending() {
    pendingAction.value = null;
    pendingMessageId.value = null;
  }

  function onPromptClick(info: { data: PromptProps }) {
    const text = info.data.description || info.data.label;
    if (typeof text === "string" && text.trim()) {
      void send(text);
    }
  }

  if (options?.autoLoadSessions !== false) {
    onMounted(() => {
      void loadSessions();
    });
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
    onActionDone,
    onPromptClick,
    clearPending,
  };
}
