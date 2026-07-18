<template>
  <a-layout class="app-layout">
    <a-layout-sider
      v-if="!isMobile"
      v-model:collapsed="collapsed"
      collapsible
      class="app-sider"
      :width="240"
      :collapsed-width="72"
    >
      <div class="logo" :class="{ collapsed }">
        <app-logo variant="sidebar" :collapsed="collapsed" :show-text="!collapsed" />
      </div>
      <a-menu
        theme="dark"
        mode="inline"
        :selected-keys="[selectedKey]"
        :open-keys="openKeys"
        @click="onMenu"
        @open-change="onOpenChange"
      >
        <template v-for="group in menuGroups" :key="group.key">
          <a-menu-item-group v-if="!collapsed" :title="group.label">
            <a-menu-item v-for="item in group.items" :key="item.path">
              <component :is="item.icon" />
              <span>{{ item.label }}</span>
            </a-menu-item>
          </a-menu-item-group>
          <template v-else>
            <a-menu-item v-for="item in group.items" :key="item.path">
              <component :is="item.icon" />
              <span>{{ item.label }}</span>
            </a-menu-item>
          </template>
        </template>
      </a-menu>
    </a-layout-sider>

    <a-drawer
      v-if="isMobile"
      v-model:open="drawerOpen"
      placement="left"
      :width="280"
      :closable="false"
      class="nav-drawer"
      :body-style="{ padding: 0, background: 'var(--fs-bg-sidebar)' }"
    >
      <div class="drawer-head">
        <div class="logo">
          <app-logo variant="sidebar" :show-text="true" />
        </div>
        <a-button type="text" class="drawer-close" @click="drawerOpen = false">
          <close-outlined />
        </a-button>
      </div>
      <a-menu
        theme="dark"
        mode="inline"
        :selected-keys="[selectedKey]"
        @click="onMenu"
      >
        <template v-for="group in menuGroups" :key="group.key">
          <a-menu-item-group :title="group.label">
            <a-menu-item v-for="item in group.items" :key="item.path">
              <component :is="item.icon" />
              <span>{{ item.label }}</span>
            </a-menu-item>
          </a-menu-item-group>
        </template>
      </a-menu>
    </a-drawer>

    <a-layout class="app-main">
      <a-layout-header class="app-header">
        <div class="header-left">
          <a-button
            v-if="isMobile"
            type="text"
            class="menu-trigger"
            @click="drawerOpen = true"
          >
            <menu-outlined />
          </a-button>
          <span class="header-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <theme-toggle />
          <a-dropdown>
            <span class="user-trigger">
              <user-outlined />
              <span class="user-name">{{ auth.username }}</span>
            </span>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="logout">退出登录</a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </a-layout-header>
      <a-layout-content class="app-content">
        <div class="app-page-stage">
          <router-view v-slot="{ Component, route: activeRoute }">
            <transition name="fs-slide" mode="out-in">
              <component :is="Component" :key="activeRoute.path" class="app-page-view" />
            </transition>
          </router-view>
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  BellOutlined,
  CheckCircleOutlined,
  CloseOutlined,
  ClusterOutlined,
  DashboardOutlined,
  DisconnectOutlined,
  FileSearchOutlined,
  GlobalOutlined,
  MenuOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  SettingOutlined,
  StopOutlined,
  UserOutlined,
} from "@ant-design/icons-vue";
import ThemeToggle from "@/components/ThemeToggle.vue";
import AppLogo from "@/components/AppLogo.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useAuthStore } from "@/stores/auth";
import { useAppSettingsStore } from "@/stores/appSettings";

const collapsed = ref(false);
const drawerOpen = ref(false);
const openKeys = ref<string[]>(["overview", "assets", "policy", "observe", "system"]);

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const appSettings = useAppSettingsStore();
const { isMobile } = useBreakpoint();

const menuGroups = [
  {
    key: "overview",
    label: "概览",
    items: [{ path: "/dashboard", label: "总览", icon: DashboardOutlined }],
  },
  {
    key: "assets",
    label: "资产",
    items: [
      { path: "/sites", label: "站点管理", icon: ClusterOutlined },
      { path: "/certificates", label: "证书管理", icon: SafetyCertificateOutlined },
    ],
  },
  {
    key: "policy",
    label: "策略",
    items: [
      { path: "/whitelist", label: "白名单", icon: CheckCircleOutlined },
      { path: "/blacklist", label: "黑名单", icon: StopOutlined },
      { path: "/exceptions", label: "防护例外", icon: DisconnectOutlined },
      { path: "/ratelimit", label: "速率防护", icon: DashboardOutlined },
      { path: "/bots", label: "Bot 库", icon: RobotOutlined },
      { path: "/rules", label: "自定义规则", icon: SafetyOutlined },
    ],
  },
  {
    key: "observe",
    label: "观测",
    items: [
      { path: "/ip-groups", label: "IP 组管理", icon: GlobalOutlined },
      { path: "/logs", label: "防护日志", icon: FileSearchOutlined },
      { path: "/alerts", label: "预警通知", icon: BellOutlined },
      { path: "/ai-guard", label: "AI 防护", icon: RobotOutlined },
    ],
  },
  {
    key: "system",
    label: "系统",
    items: [{ path: "/settings", label: "系统设置", icon: SettingOutlined }],
  },
];

const selectedKey = computed(() => route.path);
const pageTitle = computed(() => (route.meta.title as string) || "");

function onMenu({ key }: { key: string }) {
  drawerOpen.value = false;
  router.push(key);
}

function onOpenChange(keys: string[]) {
  openKeys.value = keys;
}

function logout() {
  auth.logout();
  router.push("/login");
}

onMounted(() => {
  if (auth.isLoggedIn && !appSettings.loaded) {
    void appSettings.fetch();
  }
});
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.app-sider {
  background: var(--fs-bg-sidebar) !important;
}

.app-sider :deep(.ant-layout-sider-children) {
  display: flex;
  flex-direction: column;
}

.app-sider :deep(.ant-menu-dark),
.nav-drawer :deep(.ant-menu-dark) {
  background: transparent;
}

.app-sider :deep(.ant-menu-dark .ant-menu-item),
.app-sider :deep(.ant-menu-dark .ant-menu-submenu-title),
.nav-drawer :deep(.ant-menu-dark .ant-menu-item),
.nav-drawer :deep(.ant-menu-dark .ant-menu-submenu-title) {
  color: rgba(255, 255, 255, 0.72);
}

.app-sider :deep(.ant-menu-dark .ant-menu-item-group-title),
.nav-drawer :deep(.ant-menu-dark .ant-menu-item-group-title) {
  color: rgba(255, 255, 255, 0.45);
}

.app-sider :deep(.ant-menu-dark .ant-menu-item:not(.ant-menu-item-selected):hover),
.app-sider :deep(.ant-menu-dark .ant-menu-submenu-title:hover),
.nav-drawer :deep(.ant-menu-dark .ant-menu-item:not(.ant-menu-item-selected):hover),
.nav-drawer :deep(.ant-menu-dark .ant-menu-submenu-title:hover) {
  color: #f8fafc !important;
  background: var(--fs-bg-sidebar-hover) !important;
}

.app-sider :deep(.ant-menu-dark .ant-menu-item-selected),
.nav-drawer :deep(.ant-menu-dark .ant-menu-item-selected) {
  color: #fff !important;
  background: var(--fs-color-primary) !important;
}

.logo {
  display: flex;
  align-items: center;
  min-height: 56px;
  margin: 12px;
  padding: 8px 10px;
  border-radius: var(--fs-radius-md);
  background: rgba(255, 255, 255, 0.06);
}

.logo.collapsed {
  justify-content: center;
  padding: 8px 6px;
}

.app-main {
  min-width: 0;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 56px;
  line-height: 56px;
  background: var(--fs-bg-surface);
  border-bottom: 1px solid var(--fs-border);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fs-text-primary);
}

.menu-trigger {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: var(--fs-radius-sm);
  cursor: pointer;
  color: var(--fs-text-secondary);
  transition: background var(--fs-transition);
}

.user-trigger:hover {
  background: var(--fs-bg-muted);
}

.user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-content {
  margin: 0;
  padding: 16px;
  min-height: calc(100vh - 56px);
  background: var(--fs-bg-page);
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 8px 12px 12px;
}

.drawer-close {
  color: #fff;
}

@media (max-width: 767px) {
  .app-content {
    padding: 12px;
  }

  .user-name {
    display: none;
  }
}
</style>
