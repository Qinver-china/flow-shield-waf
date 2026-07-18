import { ref } from "vue";

const STORAGE_KEY = "fs-dashboard-live-refresh";

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
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
