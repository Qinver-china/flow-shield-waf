<template>
  <div class="login-page">
    <div class="login-brand">
      <div class="brand-inner">
        <app-logo variant="horizontal" class="brand-logo" />
        <h1>{{ BRAND.tagline }}</h1>
        <p>智能流量防护 · CC 攻击识别 · 可视化管理</p>
        <ul class="brand-features">
          <li><check-circle-outlined /> 反向代理型防护</li>
          <li><check-circle-outlined /> 规则热同步，无需 reload</li>
          <li><check-circle-outlined /> 多维日志与 AI 辅助分析</li>
        </ul>
      </div>
    </div>
    <div class="login-panel">
      <a-card class="login-card" :bordered="false">
        <div class="panel-head">
          <app-logo variant="login" class="panel-logo" />
          <h2>登录管理面板</h2>
          <p>请输入管理员账号密码</p>
        </div>
        <a-form layout="vertical" :model="form" @finish="onSubmit">
          <a-form-item label="账号" name="username" :rules="[{ required: true }]">
            <a-input v-model:value="form.username" size="large" placeholder="请输入账号" />
          </a-form-item>
          <a-form-item label="密码" name="password" :rules="[{ required: true }]">
            <a-input-password v-model:value="form.password" size="large" placeholder="请输入密码" />
          </a-form-item>
          <a-button type="primary" size="large" block html-type="submit" :loading="loading">
            登录
          </a-button>
        </a-form>
        <div class="panel-foot">
          <theme-toggle />
        </div>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { CheckCircleOutlined } from "@ant-design/icons-vue";
import AppLogo from "@/components/AppLogo.vue";
import ThemeToggle from "@/components/ThemeToggle.vue";
import { BRAND } from "@/constants/brand";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const form = reactive({ username: "", password: "" });

async function onSubmit() {
  loading.value = true;
  try {
    await auth.login(form.username, form.password);
    message.success("登录成功");
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

.brand-inner {
  max-width: 460px;
}

.brand-logo {
  margin-bottom: 28px;
}

.brand-logo :deep(.app-logo-image) {
  max-height: 72px;
}

.brand-inner h1 {
  margin: 0 0 12px;
  font-size: 32px;
  line-height: 1.2;
}

.brand-inner > p {
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

.panel-logo :deep(.app-logo-image) {
  max-height: 40px;
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
