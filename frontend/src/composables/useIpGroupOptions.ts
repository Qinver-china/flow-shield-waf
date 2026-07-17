import { ref } from "vue";
import { api } from "@/api";

export interface IpGroupOption {
  id: number;
  name: string;
  entry_count: number;
}

export function useIpGroupOptions() {
  const options = ref<IpGroupOption[]>([]);
  const loading = ref(false);
  const nameMap = ref<Record<string, string>>({});

  async function load() {
    loading.value = true;
    try {
      const resp = await api.get("/api/v1/ip-groups/options");
      options.value = resp.data || [];
      const map: Record<string, string> = {};
      for (const item of options.value) {
        map[String(item.id)] = item.name;
      }
      nameMap.value = map;
    } finally {
      loading.value = false;
    }
  }

  function labelFor(id: string | number) {
    return nameMap.value[String(id)] || `#${id}`;
  }

  return { options, loading, nameMap, load, labelFor };
}
