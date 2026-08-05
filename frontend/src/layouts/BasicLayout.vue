<template>
  <a-layout class="app-layout">
    <a-layout-sider
      v-if="!isMobile"
      v-model:collapsed="collapsed"
      collapsible
      :trigger="null"
      class="app-sider"
      :width="160"
      :collapsed-width="72"
    >
      <div class="logo" :class="{ collapsed }">
        <app-logo variant="sidebar" :collapsed="collapsed" :show-text="!collapsed" />
      </div>
      <div class="sider-menu-wrap">
        <a-menu
          mode="inline"
          class="app-nav-menu"
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
      </div>
      <div class="sider-footer">
        <a-tooltip :title="collapsed ? '展开菜单' : '收起菜单'">
          <a-button
            type="text"
            class="fs-header-icon-btn sider-collapse-btn"
            :aria-label="collapsed ? '展开菜单' : '收起菜单'"
            @click="collapsed = !collapsed"
          >
            <menu-unfold-outlined v-if="collapsed" />
            <menu-fold-outlined v-else />
          </a-button>
        </a-tooltip>
      </div>
    </a-layout-sider>

    <a-drawer
      v-if="isMobile"
      v-model:open="drawerOpen"
      placement="left"
      :width="200"
      :closable="false"
      class="nav-drawer"
      :body-style="{ padding: 0, background: 'transparent' }"
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
        mode="inline"
        class="app-nav-menu"
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
            <a-dropdown placement="bottomRight" :trigger="['click']">
              <a-button type="text" class="fs-header-icon-btn" aria-label="用户菜单">
                <user-outlined />
              </a-button>
              <template #overlay>
                <a-menu :selectable="false">
                  <a-menu-item disabled>
                    <span class="user-menu-name">{{ auth.username }}</span>
                  </a-menu-item>
                  <a-menu-divider />
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
              <keep-alive include="Logs">
                <component :is="Component" :key="activeRoute.path" class="app-page-view" />
              </keep-alive>
            </transition>
          </router-view>
        </div>
      </a-layout-content>
    </a-layout>
    <floating-ai-chat />
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
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  SettingOutlined,
  StopOutlined,
  UserOutlined,
} from "@ant-design/icons-vue";
import ThemeToggle from "@/components/ThemeToggle.vue";
import AppLogo from "@/components/AppLogo.vue";
import FloatingAiChat from "@/components/ai-chat/FloatingAiChat.vue";
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
      { path: "/rules", label: "自定义规则", icon: SafetyOutlined },
      { path: "/ai-guard", label: "AI 防护", icon: RobotOutlined },
    ],
  },
  {
    key: "observe",
    label: "观测",
    items: [
    { path: "/bots", label: "Bot 库管理", icon: RobotOutlined },
    { path: "/ip-groups", label: "IP 组管理", icon: GlobalOutlined },
      { path: "/logs", label: "防护日志", icon: FileSearchOutlined },
      { path: "/alerts", label: "预警通知", icon: BellOutlined },
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
  // Chunk load failures are recovered in router.onError; swallow the rejected push.
  void router.push(key).catch(() => undefined);
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
  background: transparent !important;
}

.app-sider {
  background: transparent !important;
  border-inline-end: none !important;
  position: sticky;
  top: 0;
  align-self: flex-start;
  height: 100vh;
  overflow: hidden;
  flex-shrink: 0;
}

.app-sider :deep(.ant-layout-sider-children) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.sider-menu-wrap {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.sider-footer {
  display: flex;
  justify-content: center;
  flex-shrink: 0;
  padding: 10px 0 14px;
}

.sider-collapse-btn {
  flex-shrink: 0;
}

.app-sider :deep(.ant-layout-sider-trigger) {
  display: none;
}

.app-nav-menu,
.nav-drawer :deep(.app-nav-menu) {
  background: transparent !important;
  border-inline-end: none !important;
}

.app-sider :deep(.app-nav-menu .ant-menu-item),
.app-sider :deep(.app-nav-menu .ant-menu-submenu-title),
.nav-drawer :deep(.app-nav-menu .ant-menu-item),
.nav-drawer :deep(.app-nav-menu .ant-menu-submenu-title) {
  color: var(--fs-text-secondary);
}

.app-sider :deep(.app-nav-menu .ant-menu-item-group-title),
.nav-drawer :deep(.app-nav-menu .ant-menu-item-group-title) {
  color: var(--fs-text-muted);
}

.app-sider :deep(.app-nav-menu .ant-menu-item:not(.ant-menu-item-selected):hover),
.app-sider :deep(.app-nav-menu .ant-menu-submenu-title:hover),
.nav-drawer :deep(.app-nav-menu .ant-menu-item:not(.ant-menu-item-selected):hover),
.nav-drawer :deep(.app-nav-menu .ant-menu-submenu-title:hover) {
  color: var(--fs-text-primary) !important;
  background: var(--fs-bg-muted) !important;
}

.app-sider :deep(.app-nav-menu .ant-menu-item-selected),
.nav-drawer :deep(.app-nav-menu .ant-menu-item-selected) {
  color: #fff !important;
  background: var(--fs-color-primary) !important;
}

.logo {
  display: flex;
  align-items: center;
  min-height: 56px;
  margin: 12px;
  border-radius: var(--fs-radius-md);
  background: transparent;
}

.logo.collapsed {
  justify-content: center;
  padding: 8px 6px;
}

.app-main {
  min-width: 0;
  background: transparent;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 56px;
  line-height: 56px;
  background: transparent;
  border-bottom: none;
}

@media (max-width: 767px) {
  .app-header {
    padding:0 4px;
  }
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
  color: var(--fs-text-secondary);
}

.menu-trigger:hover {
  color: var(--fs-color-primary);
  background: var(--fs-bg-muted);
}

.user-menu-name {
  color: var(--fs-text-primary);
  font-weight: 500;
}

.app-content {
  margin: 0;
  padding: 16px;
  min-height: calc(100vh - 56px);
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 8px 12px 12px;
}

.drawer-close {
  color: var(--fs-text-secondary);
}

.drawer-close:hover {
  color: var(--fs-color-primary);
  background: var(--fs-bg-muted);
}

:deep(.nav-drawer .ant-drawer-content) {
  background: var(--fs-bg-page);
}

@media (max-width: 767px) {
  .app-content {
    padding: 12px;
  }
}
</style>
