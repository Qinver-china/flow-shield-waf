import { computed, onMounted, ref } from "vue";
import { api } from "@/api";

export interface SiteOption {
  id: number;
  name: string;
  domain: string;
  domains?: string[];
  enabled: boolean;
}

/** Select / table display: site name only. */
function siteSelectLabel(site: SiteOption): string {
  return site.name || site.domain || `#${site.id}`;
}

function siteDisplayName(site: SiteOption): string {
  return siteSelectLabel(site);
}

/** Shared across all useSiteOptions() callers so invalidate refreshes every dropdown. */
const sites = ref<SiteOption[]>([]);
const loading = ref(false);
let cached: SiteOption[] | null = null;
let pending: Promise<SiteOption[]> | null = null;

async function fetchOptions(force = false): Promise<SiteOption[]> {
  if (!force && cached) {
    sites.value = cached;
    return cached;
  }
  if (pending) return pending;

  loading.value = true;
  pending = api
    .get<SiteOption[]>("/api/v1/sites/options")
    .then((resp) => {
      cached = resp.data;
      sites.value = cached;
      return cached;
    })
    .finally(() => {
      pending = null;
      loading.value = false;
    });
  return pending;
}

/** Drop cache and reload so site selects pick up create/edit/delete/toggle. */
export async function invalidateSiteOptions() {
  cached = null;
  pending = null;
  await fetchOptions(true);
}

export function useSiteOptions() {
  const siteMap = computed(() => new Map(sites.value.map((s) => [s.id, s])));

  const selectOptions = computed(() =>
    sites.value.map((s) => ({
      value: s.id,
      label: siteSelectLabel(s),
      disabled: !s.enabled,
    })),
  );

  async function load() {
    await fetchOptions(false);
  }

  function resolveSiteName(id: number): string {
    const site = siteMap.value.get(id);
    return site ? siteDisplayName(site) : `#${id}`;
  }

  function formatSiteIds(ids?: number[] | null): string {
    if (!ids?.length) return "全局";
    return ids.map((id) => resolveSiteName(id)).join("、");
  }

  function formatSiteId(id?: number | null): string {
    if (id == null) return "全站";
    return resolveSiteName(id);
  }

  onMounted(() => {
    void load();
  });

  return {
    sites,
    loading,
    siteMap,
    selectOptions,
    resolveSiteName,
    formatSiteIds,
    formatSiteId,
    load,
    invalidate: invalidateSiteOptions,
  };
}

export function siteIdsColumn() {
  return {
    title: "站点",
    key: "site_ids",
    dataIndex: "site_ids",
    width: 200,
    slotCell: true,
  };
}
