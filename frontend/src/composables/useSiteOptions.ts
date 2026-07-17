import { computed, onMounted, ref } from "vue";
import { api } from "@/api";

export interface SiteOption {
  id: number;
  name: string;
  domain: string;
  enabled: boolean;
}

let cached: SiteOption[] | null = null;
let pending: Promise<SiteOption[]> | null = null;

export function useSiteOptions() {
  const sites = ref<SiteOption[]>(cached ?? []);
  const loading = ref(false);

  const siteMap = computed(() => new Map(sites.value.map((s) => [s.id, s])));

  const selectOptions = computed(() =>
    sites.value.map((s) => ({
      value: s.id,
      label: `${s.name} (${s.domain})`,
      disabled: !s.enabled,
    })),
  );

  async function load() {
    if (cached) {
      sites.value = cached;
      return;
    }
    loading.value = true;
    try {
      if (!pending) {
        pending = api
          .get<SiteOption[]>("/api/v1/sites/options")
          .then((resp) => resp.data);
      }
      cached = await pending;
      sites.value = cached;
    } finally {
      loading.value = false;
    }
  }

  function formatSiteIds(ids?: number[] | null): string {
    if (!ids?.length) return "全局";
    return ids
      .map((id) => {
        const site = siteMap.value.get(id);
        return site ? `${site.name} (${site.domain})` : `#${id}`;
      })
      .join("、");
  }

  function formatSiteId(id?: number | null): string {
    if (id == null) return "全站";
    const site = siteMap.value.get(id);
    return site ? `${site.name} (${site.domain})` : `#${id}`;
  }

  onMounted(load);

  return { sites, loading, siteMap, selectOptions, formatSiteIds, formatSiteId, load };
}

export function siteIdsColumn() {
  return {
    title: "站点",
    key: "site_ids",
    dataIndex: "site_ids",
    width: 180,
    slotCell: true,
  };
}
