import { ref } from "vue";

const STORAGE_KEY = "fs-dashboard-live-refresh";

function readStored(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "1";
  } catch {
    return true;
  }
}

const enabled = ref(readStored());

export function useDashboardLiveRefresh() {
  function setEnabled(value: boolean) {
    enabled.value = value;
    try {
      localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
    } catch {
      /* ignore */
    }
  }

  return { enabled, setEnabled };
}
