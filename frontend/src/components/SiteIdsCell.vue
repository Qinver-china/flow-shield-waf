<template>
  <span class="site-ids-cell">
    <a-tag v-if="!siteIds?.length" class="site-tag site-tag--global">全局</a-tag>
    <template v-else>
      <fs-hover-dropdown
        v-for="id in siteIds"
        :key="id"
        :arrow="true"
        placement="bottomLeft"
      >
        <span class="site-tag-trigger">
          <a-tag class="site-tag" :title="resolveSiteName(id)">{{ resolveSiteName(id) }}</a-tag>
        </span>
        <template #overlay>
          <a-menu class="site-tag-menu" :selectable="false">
            <a-menu-item @click="viewSite(id)">查看</a-menu-item>
            <a-menu-item @click="goStats(id)">统计</a-menu-item>
            <a-menu-item @click="goLogs(id)">日志</a-menu-item>
          </a-menu>
        </template>
      </fs-hover-dropdown>
    </template>
  </span>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import FsHoverDropdown from "@/components/FsHoverDropdown.vue";
import { useLogNavigation } from "@/composables/useLogNavigation";
import { useSiteOptions } from "@/composables/useSiteOptions";

defineProps<{ siteIds?: number[] | null }>();

const router = useRouter();
const { resolveSiteName } = useSiteOptions();
const { goToLogs } = useLogNavigation("24h");

function viewSite(id: number) {
  router.push({ path: "/sites", query: { id: String(id), drawer: "view" } });
}

function goStats(id: number) {
  goToLogs({ tab: "stats", preset: "24h", site_id: id });
}

function goLogs(id: number) {
  goToLogs({ tab: "detail", preset: "24h", site_id: id });
}
</script>

<style scoped>
.site-ids-cell {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  max-width: 100%;
}

.site-tag-trigger {
  display: inline-flex;
  max-width: 100%;
}

.site-tag {
  margin-inline-end: 0 !important;
  cursor: pointer;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.site-tag--global {
  cursor: default;
}

.site-tag-menu {
  min-width: 120px;
}
</style>
