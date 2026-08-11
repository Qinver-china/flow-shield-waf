<template>
  <a-layout class="app-layout">
    <a-layout-sider v-if="!isMobile" class="app-sider" :width="160">
      <div class="logo">
        <app-logo variant="sidebar" />
      </div>
      <div class="sider-menu-wrap">
        <a-menu mode="inline" class="app-nav-menu" :selected-keys="[selectedKey]" :open-keys="openKeys" @click="onMenu"
          @open-change="onOpenChange">
          <template v-for="group in menuGroups" :key="group.key">
            <a-menu-item-group :title="group.label">
              <a-menu-item v-for="item in group.items" :key="item.path">
                <component :is="item.icon" />
                <span>{{ item.label }}</span>
              </a-menu-item>
            </a-menu-item-group>
          </template>
        </a-menu>
      </div>
      <div class="sider-footer">
        <a class="sider-footer-link" :href="changelogUrl" target="_blank" rel="noopener noreferrer">
          <tag-outlined />
          <span>v{{ appVersion }}</span>
        </a>
        <a class="sider-footer-link" :href="docsUrl" target="_blank" rel="noopener noreferrer">
          <book-outlined />
          <span>教程文档</span>
        </a>
      </div>
    </a-layout-sider>

    <a-drawer v-if="isMobile" v-model:open="drawerOpen" placement="left" :width="200" :closable="false"
      class="nav-drawer" :body-style="{ padding: 0, background: 'transparent' }">
      <div class="drawer-body">
        <div class="drawer-head">
          <div class="logo">
            <app-logo variant="sidebar" />
          </div>
        </div>
        <div class="drawer-menu-wrap">
          <a-menu mode="inline" class="app-nav-menu" :selected-keys="[selectedKey]" @click="onMenu">
            <template v-for="group in menuGroups" :key="group.key">
              <a-menu-item-group :title="group.label">
                <a-menu-item v-for="item in group.items" :key="item.path">
                  <component :is="item.icon" />
                  <span>{{ item.label }}</span>
                </a-menu-item>
              </a-menu-item-group>
            </template>
          </a-menu>
        </div>
        <div class="sider-footer">
          <a class="sider-footer-link" :href="changelogUrl" target="_blank" rel="noopener noreferrer">
            <tag-outlined />
            <span>v{{ appVersion }}</span>
          </a>
          <a class="sider-footer-link" :href="docsUrl" target="_blank" rel="noopener noreferrer">
            <book-outlined />
            <span>教程文档</span>
          </a>
        </div>
      </div>
    </a-drawer>

    <a-layout class="app-main">
      <a-layout-header class="app-header">
        <div class="header-left">
          <a-button v-if="isMobile" type="text" class="menu-trigger" @click="drawerOpen = true">
            <menu-outlined />
          </a-button>
          <span class="header-title">{{ pageTitle }}</span>
        </div>
        <div class="header-right">
          <theme-toggle />
          <a-dropdown placement="bottomRight" :trigger="['click']" :arrow="true">
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
  BookOutlined,
  CheckCircleOutlined,
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
  TagOutlined,
  UserOutlined,
} from "@ant-design/icons-vue";
import ThemeToggle from "@/components/ThemeToggle.vue";
import AppLogo from "@/components/AppLogo.vue";
import FloatingAiChat from "@/components/ai-chat/FloatingAiChat.vue";
import { useBreakpoint } from "@/composables/useBreakpoint";
import { useAuthStore } from "@/stores/auth";
import { useAppSettingsStore } from "@/stores/appSettings";
import { version as appVersion } from "../../package.json";

const drawerOpen = ref(false);
const openKeys = ref<string[]>(["overview", "assets", "policy", "observe", "system"]);
const changelogUrl = "https://fswaf.top/changelog";
const docsUrl = "https://fswaf.top/guide/dashboard";

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

.sider-menu-wrap,
.drawer-menu-wrap {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.sider-footer {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  gap: 0;
  padding: 4px 10px 8px;
}

.sider-footer-link {
  display: inline-flex;
  align-items: center;
  gap: 13px;
  padding: 5px 18px;
  border-radius: var(--fs-radius-sm, 4px);
  color:
    color-mix(in srgb, var(--fs-text-secondary) 80%, transparent);
  font-size: 12px;
  line-height: 1.4;
  text-decoration: none;
  transition: color .15s ease, background .15s ease;
}

.sider-footer-link :deep(.anticon) {
  font-size: 12px;
}

.sider-footer-link:hover {
  color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 5%, transparent);
}

.app-nav-menu,
.nav-drawer :deep(.app-nav-menu) {
  background: transparent !important;
  border-inline-end: none !important;
  --ant-menu-item-height: 36px;
  --ant-menu-item-margin-block: 2px;
}

.app-sider :deep(.app-nav-menu .ant-menu-item),
.app-sider :deep(.app-nav-menu .ant-menu-submenu-title),
.nav-drawer :deep(.app-nav-menu .ant-menu-item),
.nav-drawer :deep(.app-nav-menu .ant-menu-submenu-title) {
  color: var(--fs-text-secondary);
  height: 36px;
  line-height: 36px;
  margin-block: 2px;
}

.app-sider :deep(.app-nav-menu .ant-menu-item-group-title),
.nav-drawer :deep(.app-nav-menu .ant-menu-item-group-title) {
  color: var(--fs-text-muted);
  padding: 8px 16px 4px;
  line-height: 1.4;
  font-size: 12px;
}

.app-sider :deep(.app-nav-menu .ant-menu-item:not(.ant-menu-item-selected):hover),
.app-sider :deep(.app-nav-menu .ant-menu-submenu-title:hover),
.nav-drawer :deep(.app-nav-menu .ant-menu-item:not(.ant-menu-item-selected):hover),
.nav-drawer :deep(.app-nav-menu .ant-menu-submenu-title:hover) {
  background: color-mix(in srgb, var(--fs-color-primary) 10%, transparent) !important;
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
  margin: 12px 6px;
  border-radius: var(--fs-radius-md);
  background: transparent;
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
    padding: 0 4px;
  }

  .logo {
    margin: 0;
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

.drawer-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
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
