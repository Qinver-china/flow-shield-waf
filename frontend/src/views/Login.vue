<template>
  <div class="login-page">
    <div class="login-brand">
      <div class="brand-inner">
        <app-logo variant="horizontal" class="brand-logo" />
        <h1>{{ BRAND.tagline }}</h1>
        <p>智能流量防护 · CC 攻击识别 · 可视化管理</p>
        <ul class="brand-features">
          <li><check-circle-outlined /> 反向代理接入，流量先过流盾再回源</li>
          <li><check-circle-outlined /> 规则热同步，改配置无需重启引擎</li>
          <li><check-circle-outlined /> 观察 / 拦截 / JS 挑战 / 滑动验证多模式</li>
          <li><check-circle-outlined /> 多维速率防护，精准识别 CC 与自动化攻击</li>
          <li><check-circle-outlined /> ClickHouse 日志可观测，支持预警通知</li>
          <li><check-circle-outlined /> AI 辅助分析日志并生成防护规则</li>
        </ul>
      </div>
    </div>
    <div class="login-panel">
      <a-card class="login-card" :bordered="false">
        <div class="panel-head">
          <div class="panel-header">
            <app-logo variant="login" class="panel-logo" />
            <theme-toggle />
          </div>
          <h2>{{ needsSetup ? "设置管理员账号" : "登录管理面板" }}</h2>
          <p>{{ needsSetup ? "首次使用，请设置管理员用户名和密码" : "请输入管理员账号密码" }}</p>
        </div>
        <a-form v-if="ready" layout="vertical" :model="form" @finish="onSubmit">
          <a-form-item :label="needsSetup ? '管理员用户名' : '账号'" name="username" :rules="[{ required: true }]">
            <a-input
              v-model:value="form.username"
              size="large"
              :placeholder="needsSetup ? '3-64 位，字母、数字、下划线、连字符' : '请输入账号'"
              autocomplete="username"
            />
          </a-form-item>
          <a-form-item label="密码" name="password" :rules="[{ required: true }]">
            <a-input-password
              v-model:value="form.password"
              size="large"
              :placeholder="needsSetup ? '至少 6 位' : '请输入密码'"
              :autocomplete="needsSetup ? 'new-password' : 'current-password'"
            />
          </a-form-item>
          <a-form-item v-if="needsSetup" label="确认密码" name="confirm_password" :rules="[{ required: true }]">
            <a-input-password
              v-model:value="form.confirm_password"
              size="large"
              placeholder="再次输入密码"
              autocomplete="new-password"
            />
          </a-form-item>
          <a-button type="primary" size="large" block html-type="submit" :loading="loading">
            {{ needsSetup ? "保存并进入面板" : "登录" }}
          </a-button>
        </a-form>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { CheckCircleOutlined } from "@ant-design/icons-vue";
import AppLogo from "@/components/AppLogo.vue";
import ThemeToggle from "@/components/ThemeToggle.vue";
import { api } from "@/api";
import { BRAND } from "@/constants/brand";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const ready = ref(false);
const needsSetup = ref(false);
const form = reactive({ username: "", password: "", confirm_password: "" });

onMounted(async () => {
  try {
    const resp = await api.get<{ needs_setup: boolean }>("/api/v1/auth/setup-status");
    needsSetup.value = Boolean(resp.data.needs_setup);
    if (needsSetup.value && auth.isLoggedIn) {
      auth.logout();
    }
  } catch {
    needsSetup.value = false;
  } finally {
    ready.value = true;
  }
});

function validateSetup(): boolean {
  const username = form.username.trim();
  if (!username) {
    message.warning("请输入管理员用户名");
    return false;
  }
  if (username.length < 3 || username.length > 64) {
    message.warning("用户名长度需在 3-64 个字符之间");
    return false;
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
    message.warning("用户名仅允许字母、数字、下划线和连字符");
    return false;
  }
  if (!form.password) {
    message.warning("请输入密码");
    return false;
  }
  if (form.password.length < 6) {
    message.warning("密码至少 6 位");
    return false;
  }
  if (form.password !== form.confirm_password) {
    message.warning("两次输入的密码不一致");
    return false;
  }
  return true;
}

async function onSubmit() {
  if (needsSetup.value && !validateSetup()) return;
  loading.value = true;
  try {
    if (needsSetup.value) {
      await auth.completeInitialSetup(form.username.trim(), form.password);
      message.success("管理员账号已设置");
    } else {
      await auth.login(form.username, form.password);
      message.success("登录成功");
    }
    router.push("/dashboard");
  } catch (err: any) {
    const status = err.response?.status;
    if (status === 401) {
      message.error("账号或密码输入错误");
    } else if (status === 403) {
      message.error("账号已禁用");
    } else if (status === 429) {
      message.error(err.response?.data?.message || "登录尝试过于频繁，请稍后再试");
    }
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: var(--fs-bg-page);
}

.login-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 32px;
  background: linear-gradient(145deg, #0c1f4a 0%, #081a3d 45%, #020617 100%);
  color: #f8fafc;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.brand-inner {
  max-width: 460px;
}

.brand-logo {
  margin-bottom: 28px;
  min-height: 71px;
}

.brand-logo :deep(.app-logo-image) {
  max-height: 72px;
}

.brand-inner h1 {
  margin: 0 0 12px;
  font-size: 32px;
  line-height: 1.2;
}

.brand-inner>p {
  margin: 0 0 28px;
  color: #94a3b8;
  font-size: 15px;
}

.brand-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.brand-features li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #cbd5e1;
  font-size: 14px;
}

.brand-features :deep(.anticon) {
  color: #22c55e;
}

.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  background: var(--fs-bg-body);
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: var(--fs-radius-lg);
  box-shadow: var(--fs-shadow-lg);
  background: var(--fs-bg-surface);
}

.panel-head h2 {
  margin: 16px 0 6px;
  font-size: 22px;
  color: var(--fs-text-primary);
}

.panel-head p {
  margin: 0 0 24px;
  color: var(--fs-text-secondary);
  font-size: 13px;
}

.app-logo.app-logo--login,
.panel-logo :deep(.app-logo-image) {
  max-height: 40px;
  min-height: 40px;
}

.panel-foot {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
  }

  .login-brand {
    padding: 28px 24px 20px;
    min-height: auto;
    text-align: center;
  }

  .brand-logo {
    justify-content: center;
    min-height: 51px;
  }


  .brand-logo :deep(.app-logo-image) {
    max-height: 52px;
  }

  .brand-inner h1 {
    font-size: 22px;
  }

  .brand-features {
    display: none;
  }
}
</style>
