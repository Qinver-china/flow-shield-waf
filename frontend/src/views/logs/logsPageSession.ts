import { ref } from "vue";

/** Persists logs page UI state across route leave/return (with keep-alive). */
export const logsPageActiveTab = ref<"stats" | "detail">("stats");
