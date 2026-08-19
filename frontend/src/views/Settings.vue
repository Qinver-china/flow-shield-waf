<template>
  <page-shell title="系统设置" description="管理账户、引擎防护、访客页面、日志采样、面板通道与配置备份">
    <div class="settings-layout">
      <settings-nav :model-value="activeGroup" :items="navItems" @update:model-value="onGroupChange" />

      <div class="settings-main">
        <fs-slide-transition :transition-key="activeGroup">
          <!-- 账户与显示 -->
          <div v-if="activeGroup === 'account-display'" class="settings-group">
            <a-row :gutter="[16, 16]">
              <a-col :xs="24" :xl="12">
                <a-card class="settings-panel" :bordered="false">
                  <div class="section-head">
                    <div class="section-title">修改用户名</div>
                    <div class="section-desc">修改后需使用新用户名登录，系统会自动刷新当前会话凭证。</div>
                  </div>
                  <a-form layout="vertical" class="section-form">
                    <a-form-item label="当前用户名">
                      <div class="readonly-value">{{ accountProfile.username }}</div>
                    </a-form-item>
                    <a-form-item label="新用户名" required>
                      <a-input v-model:value="usernameForm.new_username" placeholder="3-64 位，支持字母、数字、下划线、连字符"
                        autocomplete="username" :maxlength="64" />
                    </a-form-item>
                    <a-form-item label="当前密码" required>
                      <a-input-password v-model:value="usernameForm.current_password" placeholder="验证身份"
                        autocomplete="current-password" />
                    </a-form-item>
                    <a-button type="primary" :loading="usernameSaving" @click="saveUsername">
                      保存用户名
                    </a-button>
                  </a-form>
                </a-card>
              </a-col>
              <a-col :xs="24" :xl="12">
                <a-card class="settings-panel" :bordered="false">
                  <div class="section-head">
                    <div class="section-title">修改密码</div>
                    <div class="section-desc">保存后当前会话仍有效，下次登录请使用新密码。</div>
                  </div>
                  <a-form layout="vertical" class="section-form">
                    <a-form-item label="当前密码" required>
                      <a-input-password v-model:value="passwordForm.current_password" placeholder="请输入当前密码"
                        autocomplete="current-password" />
                    </a-form-item>
                    <a-form-item label="新密码" required>
                      <a-input-password v-model:value="passwordForm.new_password" placeholder="至少 6 位"
                        autocomplete="new-password" />
                    </a-form-item>
                    <a-form-item label="确认新密码" required>
                      <a-input-password v-model:value="passwordForm.confirm_password" placeholder="再次输入新密码"
                        autocomplete="new-password" />
                    </a-form-item>
                    <a-button type="primary" :loading="passwordSaving" @click="savePassword">
                      保存密码
                    </a-button>
                  </a-form>
                </a-card>
              </a-col>
            </a-row>

            <a-card class="settings-panel" :bordered="false">
              <div class="section-head">
                <div class="section-title">显示与联系</div>
                <div class="section-desc">时区、外网面板地址与证书申请联系邮箱。</div>
              </div>
              <a-form layout="vertical" class="section-form wide">
                <a-form-item label="显示时区">
                  <a-select v-model:value="displayForm.timezone" show-search option-filter-prop="label" :virtual="true"
                    :popup-match-select-width="true" style="width: 100%">
                    <a-select-option v-for="opt in displayForm.timezone_options" :key="opt.value" :value="opt.value"
                      :label="opt.label">
                      {{ opt.label }}
                    </a-select-option>
                  </a-select>
                  <div class="hint">
                    后台列表、日志、仪表盘等时间将按此时区显示。默认使用中国标准时间（上海，UTC+8）。
                  </div>
                </a-form-item>
                <a-form-item label="外网可访问面板地址" required>
                  <a-input v-model:value="displayForm.panel_public_url" type="url" inputmode="url" autocomplete="url"
                    placeholder="https://waf.example.com:9000" @blur="trimPanelUrl" />
                  <div class="hint">
                    用于 AI 分析邮件中的「应用规则 / 忽略」链接，请勿带尾部斜杠。首次打开本页时会根据当前访问地址自动填入，可手动修改。
                  </div>
                </a-form-item>
                <a-form-item label="ACME 账户邮箱">
                  <a-input v-model:value="displayForm.acme_account_email" type="email" inputmode="email"
                    autocomplete="email" placeholder="可选，未填时申请免费证书会自动生成" />
                  <div class="hint">
                    用于向 Let's Encrypt、ZeroSSL 注册 ACME 账户（协议要求）。未填写时，申请或自动续期会自动生成一个默认邮箱并写入此处。产品内的申请/续期通知仍走「通知通道」。
                  </div>
                </a-form-item>
              </a-form>
            </a-card>

            <settings-save-bar :dirty="displayDirty" :loading="displaySaving" label="保存" @save="saveDisplayGroup" />
          </div>

          <!-- 引擎与防护 -->
          <div v-else-if="activeGroup === 'engine-protection'" class="settings-group">
            <a-card class="settings-panel" :bordered="false">
              <div class="section-head">
                <div class="section-title">引擎代理</div>
                <div class="section-desc">控制流盾转发到源站时的请求体上限与等待源站响应的时间，保存后会重载引擎。</div>
              </div>
              <a-form layout="vertical" class="section-form wide">
                <a-form-item label="文件上传大小限制" required>
                  <preset-number-field v-model="engineForm.max_upload_size_mb" :presets="uploadPresets" :min="1"
                    :max="2048" :step="1" unit="MB" show-slider />
                  <div class="hint">
                    最大文件上传限制：普通图文/文档站点 <strong>50–100 MB</strong>；音视频或网盘类可提到
                    <strong>256–512 MB</strong>
                  </div>
                  <div class="hint hint-warn">
                    设置过大时，超大请求体会在引擎侧完整缓冲，占用磁盘临时文件与 worker
                    时间，并放大慢速上传占满连接的风险。请同时确认源站（如 PHP
                    <code>upload_max_filesize</code>）允许同等大小，避免只放宽流盾一侧。
                  </div>
                </a-form-item>
                <a-form-item label="源站响应超时" required>
                  <preset-number-field v-model="engineForm.origin_read_timeout_sec" :presets="timeoutPresets" :min="5"
                    :max="600" :step="5" unit="秒" show-slider />
                  <div class="hint">
                    等待源站返回响应的最长时间，默认 <strong>60 秒</strong>（与 Nginx
                    <code>proxy_read_timeout</code> 一致）。慢接口或大文件下载可提到
                    <strong>120–300 秒</strong>。
                  </div>
                  <div class="hint hint-warn">
                    设置过长时，源站卡死或极慢会长时间占用引擎连接与 worker；过短则容易对正常慢请求返回 504。
                  </div>
                </a-form-item>
              </a-form>
            </a-card>

            <a-card class="settings-panel" :bordered="false">
              <div class="section-head">
                <div class="section-title">挑战验证</div>
                <div class="section-desc">控制 JS 挑战与人机验证通过后的免验时长与指纹维度。</div>
              </div>
              <a-form layout="vertical" class="section-form wide">
                <a-row :gutter="16">
                  <a-col :xs="24" :md="12">
                    <a-form-item label="JS 挑战免验时间">
                      <duration-field v-model="form.js_challenge_ttl" :quick-presets="challengePresets"
                        :units="challengeDurationUnits" />
                      <div class="hint">
                        通过 JS 挑战后，仅对<strong>触发该次挑战的那条规则</strong>及其维度加白。
                      </div>
                    </a-form-item>
                  </a-col>
                  <a-col :xs="24" :md="12">
                    <a-form-item label="数学/滑动验证免验时间">
                      <duration-field v-model="form.captcha_ttl" :quick-presets="challengePresets"
                        :units="challengeDurationUnits" />
                      <div class="hint">
                        通过数学计算或滑动验证后，仅对<strong>触发该次验证的那条规则</strong>加白。
                      </div>
                    </a-form-item>
                  </a-col>
                </a-row>

                <a-form-item label="免验指纹维度">
                  <div class="dim-group">
                    <button v-for="opt in dimensionOptions" :key="opt.key" type="button" class="dim-card" :class="{
                      'is-on': form.clearance_fingerprint_dims.includes(opt.key),
                      'is-locked': opt.required,
                    }" :disabled="opt.required" @click="toggleDimension(opt.key, opt.required)">
                      <a-checkbox :checked="form.clearance_fingerprint_dims.includes(opt.key)" :disabled="opt.required"
                        @click.stop>
                        {{ opt.label }}
                        <a-tag v-if="opt.required" color="blue" class="dim-required">必选</a-tag>
                      </a-checkbox>
                      <div class="dim-desc">{{ opt.description }}</div>
                    </button>
                  </div>
                  <div class="hint">
                    用于自定义防护规则触发 JS 挑战 / 数学计算 / 滑动验证时的访客识别；限速规则使用其统计维度，不受此项影响。
                  </div>
                </a-form-item>
              </a-form>

              <a-alert type="info" show-icon class="tab-notes">
                <template #message>挑战验证说明</template>
                <template #description>
                  <ul class="notes">
                    <li>免验记录按<strong>规则 + 维度</strong>保存，通过 A 规则不会豁免 B 规则。</li>
                    <li>JS 挑战与验证类规则（数学计算、滑动）的免验时间彼此独立。</li>
                    <li>修改后立即同步到引擎；引擎重启后免验记录会清空。</li>
                  </ul>
                </template>
              </a-alert>
            </a-card>

            <a-card class="settings-panel" :bordered="false">
              <div class="section-head">
                <div class="section-title">诊断开关</div>
                <div class="section-desc">调试响应头与限速异常时的放行策略。</div>
              </div>
              <div class="switch-stack">
                <settings-switch-row v-model:checked="debugForm.debug_mode" title="开启调试模式"
                  description="开启后，命中防护规则时响应头会附带调试信息，便于在浏览器开发者工具中排查。生产环境可能暴露规则信息，建议仅在测试环境使用。" warning />
                <settings-switch-row v-model:checked="debugForm.ratelimit_fail_open" title="限速异常时放行"
                  description="开启后，限速计数器异常（如共享内存不足）时放行请求，避免误拦全站。生产环境建议保持开启；关闭后异常情况下可能批量拦截合法流量。" />
              </div>
              <div class="debug-headers">
                <div class="debug-headers-title">响应头字段</div>
                <ul>
                  <li><code>X-WAF-Debug</code>：固定为 <code>1</code></li>
                  <li><code>X-WAF-Request-Id</code>：请求 ID（无论是否开启调试，都会写入转发源站的请求头与返回客户端的响应头）</li>
                  <li><code>X-WAF-Rule-Id</code>：命中规则 ID</li>
                  <li><code>X-WAF-Rule-Name</code>：命中规则名称（含中文时为 <code>UTF-8''</code> 百分号编码，可用
                    <code>decodeURIComponent(value.slice(7))</code> 解码）
                  </li>
                  <li><code>X-WAF-Rule-Source</code>：来源（rule / ratelimit / blacklist）</li>
                  <li><code>X-WAF-Mode</code>：防护方式（observe / block / captcha / js_challenge / slide_captcha）</li>
                </ul>
              </div>
            </a-card>

            <settings-save-bar :dirty="engineGroupDirty" :loading="engineGroupSaving" :label="engineSaveLabel"
              @save="saveEngineGroup" />
          </div>

          <!-- 访客页面 -->
          <div v-else-if="activeGroup === 'visitor-pages'" class="settings-group">
            <div class="settings-stack">
              <a-card class="settings-panel" :bordered="false">
                <div class="section-head">
                  <div class="section-title">全局拦截页面</div>
                  <div class="section-desc">
                    命中拦截动作时返回的完整 HTML 页面，支持变量占位。保存后立即下发到引擎。
                  </div>
                </div>
                <a-form layout="vertical" class="section-form wide">
                  <a-form-item label="响应状态码">
                    <a-segmented v-model:value="blockPageForm.status_code" :options="blockStatusOptions"
                      class="status-segmented" />
                  </a-form-item>
                  <a-form-item label="HTML 内容">
                    <a-textarea ref="blockPageTextareaRef" v-model:value="blockPageForm.html"
                      :auto-size="{ minRows: 8, maxRows: 20 }" placeholder="输入完整 HTML 页面代码" class="code-textarea"
                      spellcheck="false" autocapitalize="off" />
                    <page-template-hints :variables="blockPageForm.template_variables" hint="点击变量标签可插入到光标位置"
                      @insert="(key) => insertVariable(blockPageTextareaRef, blockPageForm, 'html', key)" />
                  </a-form-item>
                </a-form>
              </a-card>

              <a-card class="settings-panel" :bordered="false">
                <div class="section-head">
                  <div class="section-title">全局验证页页脚</div>
                  <div class="section-desc">
                    替换数学计算验证、滑动验证页面底部的品牌说明区域，不影响验证码表单主体。
                  </div>
                </div>
                <a-form layout="vertical" class="section-form wide">
                  <a-form-item label="页脚 HTML">
                    <a-textarea ref="captchaFooterTextareaRef" v-model:value="captchaFooterForm.html"
                      :auto-size="{ minRows: 3, maxRows: 8 }" placeholder="例如：由贵站品牌提供安全防护" class="code-textarea"
                      spellcheck="false" autocapitalize="off" />
                    <page-template-hints :variables="captchaFooterForm.template_variables"
                      hint="页脚内容会渲染在 .brand 容器内，可包含简单 HTML 标签"
                      @insert="(key) => insertVariable(captchaFooterTextareaRef, captchaFooterForm, 'html', key)" />
                  </a-form-item>
                </a-form>
              </a-card>
            </div>

            <settings-save-bar :dirty="visitorPagesDirty" :loading="visitorPagesSaving" label="保存"
              @save="saveVisitorPagesGroup" />
          </div>

          <!-- 日志与通知 -->
          <div v-else-if="activeGroup === 'logging-notify'" class="settings-group">
            <a-card class="settings-panel" :bordered="false">
              <div class="section-head">
                <div class="section-title">日志采样</div>
                <div class="section-desc">控制防护日志的记录方式、采样率与保留天数。</div>
              </div>
              <a-form layout="vertical" class="section-form wide">
                <a-form-item label="控制模式">
                  <a-segmented v-model:value="logForm.logging_control_mode" :options="loggingModeOptions"
                    class="mode-segmented" />
                </a-form-item>

                <template v-if="logForm.logging_control_mode === 'manual'">
                  <div class="switch-stack">
                    <settings-switch-row v-model:checked="logForm.logging_enabled" title="全局日志记录"
                      description="关闭后不再写入新的防护日志（手动模式下）。" />
                    <settings-switch-row v-model:checked="logForm.logging_skip_observe" title="不记录观察模式"
                      description="仅记录拦截、挑战等动作，跳过观察命中。" />
                    <settings-switch-row v-model:checked="logForm.logging_detail_on_block" title="拦截类日志写详情"
                      description="拦截时写入更完整的请求详情字段。" />
                  </div>
                  <a-row :gutter="16">
                    <a-col :xs="24" :md="12">
                      <a-form-item label="默认观察采样率">
                        <percent-slider-field v-model="logForm.observe_sample_rate_idle" />
                      </a-form-item>
                    </a-col>
                    <a-col :xs="24" :md="12">
                      <a-form-item label="面板日志查看时观察采样率">
                        <percent-slider-field v-model="logForm.observe_sample_rate_active" />
                      </a-form-item>
                    </a-col>
                  </a-row>
                </template>

                <template v-else>
                  <a-alert type="info" show-icon message="流量低于阈值时不记录日志；任一窗口超过阈值时自动开启全部模式（含观察模式）。"
                    style="margin-bottom: 16px" />
                  <div class="threshold-grid">
                    <div v-for="th in logForm.logging_auto_thresholds" :key="th.window_sec" class="threshold-item">
                      <div class="threshold-label">{{ windowLabel(th.window_sec) }}</div>
                      <a-input-number v-model:value="th.max_requests" :min="1" style="width: 100%"
                        inputmode="numeric" />
                      <template v-if="trafficBySec[th.window_sec]">
                        <div class="traffic-hint">
                          当前 {{ trafficBySec[th.window_sec].requests }} 次
                          ({{ Number(trafficBySec[th.window_sec].qps || 0).toFixed(1) }} QPS)
                        </div>
                        <a-progress
                          :percent="Math.min(100, Math.round((trafficBySec[th.window_sec].requests / th.max_requests) * 100))"
                          size="small" />
                      </template>
                    </div>
                  </div>
                  <a-row :gutter="16" style="margin-top: 8px">
                    <a-col :xs="24" :md="12">
                      <a-form-item label="回落冷却时间">
                        <duration-field v-model="logForm.logging_auto_cooldown_sec" :min-seconds="10"
                          :max-seconds="3600" :units="['second', 'minute']" :quick-presets="cooldownPresets" />
                      </a-form-item>
                    </a-col>
                    <a-col :xs="24" :md="12">
                      <a-form-item label="自动开启时观察采样率">
                        <percent-slider-field v-model="logForm.logging_auto_observe_sample_rate" />
                      </a-form-item>
                    </a-col>
                  </a-row>
                </template>

                <a-form-item label="日志保留天数">
                  <preset-number-field v-model="logForm.log_retention_days" :presets="retentionPresets" :min="1"
                    :max="365" unit="天" />
                  <div class="traffic-hint">超过该天数的防护日志由 ClickHouse 自动清理（默认 30 天）。</div>
                </a-form-item>
              </a-form>
            </a-card>

            <settings-save-bar :dirty="loggingDirty" :loading="logSaving" label="保存" @save="saveLoggingGroup" />
          </div>

          <!-- 面板与通道 -->
          <div v-else-if="activeGroup === 'panels-channels'" class="settings-group settings-group--panels-channels">
            <a-card class="settings-panel settings-panel--flat" :bordered="false">
              <div class="section-head section-head--row">
                <div>
                  <div class="section-title">面板集成</div>
                  <div class="section-desc">宝塔 / 1Panel 账号，用于导入站点与同步证书。</div>
                </div>
                <a-button type="primary" @click="panelConnectionsRef?.openCreate()">添加面板账号</a-button>
              </div>
              <panel-connections-card ref="panelConnectionsRef" embedded />
            </a-card>

            <a-card class="settings-panel settings-panel--flat" :bordered="false">
              <div class="section-head section-head--row">
                <div>
                  <div class="section-title">通知通道</div>
                  <div class="section-desc">邮件等通知方式，供预警、证书与 AI 使用。</div>
                </div>
                <a-button type="primary" @click="notificationChannelsRef?.openCreate()">添加通知通道</a-button>
              </div>
              <notification-channels-card ref="notificationChannelsRef" embedded />
            </a-card>
          </div>

          <!-- 配置备份 -->
          <div v-else-if="activeGroup === 'integration-backup'" class="settings-group">
            <a-card class="settings-panel backup-panel" :bordered="false">
              <div class="section-head">
                <div class="section-title">导出 / 导入</div>
                <div class="section-desc">按模块备份或恢复配置 JSON。</div>
              </div>

              <a-segmented v-model:value="backupMode" :options="backupModeOptions" class="backup-mode-segmented" />

              <p class="backup-lead">
                <template v-if="backupMode === 'export'">
                  勾选要备份的模块并下载 JSON。证书含私钥，请妥善保管。
                </template>
                <template v-else>
                  上传此前导出的 JSON。同名或同域名会更新；导入后自动下发规则并尝试重载引擎。
                </template>
              </p>

              <template v-if="backupMode === 'export'">
                <div class="backup-block">
                  <div class="backup-block__head">
                    <span class="backup-block__title">导出模块</span>
                    <a class="backup-block__link" @click="selectAllExportSections">全选</a>
                  </div>
                  <div class="backup-checks">
                    <label v-for="item in backupSectionOptions" :key="item.key" class="backup-check"
                      :class="{ 'is-on': exportSections.includes(item.key) }">
                      <a-checkbox :checked="exportSections.includes(item.key)"
                        @change="(e: any) => toggleExportSection(item.key, e.target.checked)">
                        {{ item.label }}
                      </a-checkbox>
                    </label>
                  </div>
                </div>
                <div class="backup-footer">
                  <a-button type="primary" :loading="exporting" :disabled="!exportSections.length" @click="runExport">
                    导出 JSON
                  </a-button>
                </div>
              </template>

              <template v-else>
                <a-upload-dragger class="backup-drop" :before-upload="onBackupFile" :show-upload-list="false"
                  accept=".json,application/json">
                  <p class="backup-drop__icon"><inbox-outlined /></p>
                  <p class="backup-drop__title">
                    {{ importFileName || "点击或拖拽 JSON 备份文件到此处" }}
                  </p>
                  <p class="backup-drop__hint">仅支持流盾导出的 flow-shield-backup 文件</p>
                </a-upload-dragger>

                <div v-if="importPayload" class="backup-block">
                  <div class="backup-block__head">
                    <span class="backup-block__title">导入模块</span>
                    <a class="backup-block__link" @click="selectAllImportSections">全选</a>
                  </div>
                  <div class="backup-checks">
                    <label v-for="item in importSectionOptions" :key="item.key" class="backup-check"
                      :class="{ 'is-on': importSections.includes(item.key) }">
                      <a-checkbox :checked="importSections.includes(item.key)"
                        @change="(e: any) => toggleImportSection(item.key, e.target.checked)">
                        {{ item.label }}
                      </a-checkbox>
                    </label>
                  </div>
                </div>

                <div v-if="importResult" class="backup-result-line">
                  {{ importResultMessage }}
                </div>

                <div class="backup-footer">
                  <a-button type="primary" :loading="importing" :disabled="!importPayload || !importSections.length"
                    @click="runImport">
                    开始导入
                  </a-button>
                </div>
              </template>
            </a-card>
          </div>
        </fs-slide-transition>
      </div>
    </div>
  </page-shell>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Modal, message } from "ant-design-vue";
import { InboxOutlined } from "@ant-design/icons-vue";
import http, { api } from "@/api";
import { useAuthStore } from "@/stores/auth";
import { trafficWindowLabels } from "@/views/logs/constants";
import NotificationChannelsCard from "@/components/NotificationChannelsCard.vue";
import PanelConnectionsCard from "@/components/PanelConnectionsCard.vue";
import FsSlideTransition from "@/components/FsSlideTransition.vue";
import PageShell from "@/components/PageShell.vue";
import PageTemplateHints, { type TemplateVariable } from "@/components/PageTemplateHints.vue";
import DurationField from "@/components/settings/DurationField.vue";
import PercentSliderField from "@/components/settings/PercentSliderField.vue";
import PresetNumberField from "@/components/settings/PresetNumberField.vue";
import SettingsNav from "@/components/settings/SettingsNav.vue";
import SettingsSaveBar from "@/components/settings/SettingsSaveBar.vue";
import SettingsSwitchRow from "@/components/settings/SettingsSwitchRow.vue";
import { useAppSettingsStore } from "@/stores/appSettings";
import type { TimezoneOption } from "@/stores/appSettings";
import {
  LEGACY_TABS,
  SETTINGS_NAV_ITEMS,
  groupFromLegacyTab,
  legacyTabForGroup,
  type SettingsGroupKey,
} from "@/views/settings/settingsGroups";

const auth = useAuthStore();
const appSettings = useAppSettingsStore();
const route = useRoute();
const router = useRouter();

const navItems = SETTINGS_NAV_ITEMS;
const activeGroup = ref<SettingsGroupKey>(groupFromLegacyTab(tabFromQuery()));
const pendingGroup = ref<SettingsGroupKey | null>(null);
const panelConnectionsRef = ref<InstanceType<typeof PanelConnectionsCard> | null>(null);
const notificationChannelsRef = ref<InstanceType<typeof NotificationChannelsCard> | null>(null);

function tabFromQuery() {
  const raw = route.query.tab;
  const tab = Array.isArray(raw) ? raw[0] : raw;
  return typeof tab === "string" ? tab : "";
}

function snapshot<T>(value: T): string {
  return JSON.stringify(value);
}

const uploadPresets = [
  { value: 50, label: "50 MB" },
  { value: 100, label: "100 MB" },
  { value: 256, label: "256 MB" },
  { value: 512, label: "512 MB" },
];

const timeoutPresets = [
  { value: 30, label: "30 秒" },
  { value: 60, label: "60 秒" },
  { value: 120, label: "120 秒" },
  { value: 300, label: "300 秒" },
];

const challengePresets = [
  { seconds: 300, label: "5 分钟" },
  { seconds: 600, label: "10 分钟" },
  { seconds: 1800, label: "30 分钟" },
  { seconds: 3600, label: "1 小时" },
];

const challengeDurationUnits = ["minute", "hour"] as const;

const cooldownPresets = [
  { seconds: 30, label: "30 秒" },
  { seconds: 120, label: "2 分钟" },
  { seconds: 360, label: "5 分钟" },
];

const retentionPresets = [
  { value: 7, label: "7 天" },
  { value: 14, label: "14 天" },
  { value: 30, label: "30 天" },
  { value: 90, label: "90 天" },
];

const blockStatusOptions = [
  { value: 403, label: "403 禁止" },
  { value: 429, label: "429 限流" },
  { value: 451, label: "451 法律" },
  { value: 503, label: "503 不可用" },
];

const loggingModeOptions = [
  { value: "manual", label: "手动控制" },
  { value: "auto_by_traffic", label: "按流量自动" },
];

const backupModeOptions = [
  { value: "export", label: "导出配置" },
  { value: "import", label: "导入配置" },
];

interface BackupSectionOption {
  key: string;
  label: string;
}

const backupMode = ref<"export" | "import">("export");
const backupSectionOptions = ref<BackupSectionOption[]>([]);
const exportSections = ref<string[]>([]);
const exporting = ref(false);
const importing = ref(false);
const importFileName = ref("");
const importPayload = ref<any>(null);
const importSections = ref<string[]>([]);
const importResult = ref<any>(null);

const LEGACY_BACKUP_SECTIONS: Record<string, string[]> = {
  ai_guard: ["ai_config", "ai_policies"],
};

const accountProfile = reactive({ username: auth.username || "" });
const usernameForm = reactive({ new_username: "", current_password: "" });
const passwordForm = reactive({
  current_password: "",
  new_password: "",
  confirm_password: "",
});
const usernameSaving = ref(false);
const passwordSaving = ref(false);

interface DimensionOption {
  key: string;
  label: string;
  description: string;
  required?: boolean;
}

const form = reactive({
  js_challenge_ttl: 1800,
  captcha_ttl: 1800,
  clearance_fingerprint_dims: ["ip"] as string[],
});
const dimensionOptions = ref<DimensionOption[]>([]);

const engineForm = reactive({
  max_upload_size_mb: 50,
  origin_read_timeout_sec: 60,
});

const logForm = reactive({
  logging_control_mode: "manual",
  logging_enabled: true,
  logging_skip_observe: false,
  observe_sample_rate_idle: 100,
  observe_sample_rate_active: 100,
  logging_detail_on_block: true,
  logging_auto_thresholds: [
    { window_sec: 10, max_requests: 500 },
    { window_sec: 30, max_requests: 1200 },
    { window_sec: 60, max_requests: 2000 },
    { window_sec: 300, max_requests: 8000 },
    { window_sec: 1800, max_requests: 40000 },
    { window_sec: 3600, max_requests: 80000 },
  ],
  logging_auto_cooldown_sec: 120,
  logging_auto_observe_sample_rate: 100,
  log_retention_days: 30,
});

const debugForm = reactive({
  debug_mode: false,
  ratelimit_fail_open: true,
});

const displayForm = reactive<{
  timezone: string;
  timezone_options: TimezoneOption[];
  panel_public_url: string;
  acme_account_email: string;
}>({
  timezone: "Asia/Shanghai",
  timezone_options: [],
  panel_public_url: "",
  acme_account_email: "",
});

interface ResponsePageForm {
  status_code?: number;
  html: string;
  template_variables: TemplateVariable[];
}

const blockPageForm = reactive<ResponsePageForm>({
  status_code: 403,
  html: "",
  template_variables: [],
});
const captchaFooterForm = reactive<{ html: string; template_variables: TemplateVariable[] }>({
  html: "",
  template_variables: [],
});
const blockPageTextareaRef = ref<{ $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null>(null);
const captchaFooterTextareaRef = ref<{ $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null>(null);

const displaySaving = ref(false);
const logSaving = ref(false);
const engineGroupSaving = ref(false);
const visitorPagesSaving = ref(false);

const displaySnapshot = ref("");
const engineSnapshot = ref("");
const challengeSnapshot = ref("");
const debugSnapshot = ref("");
const blockPageSnapshot = ref("");
const captchaFooterSnapshot = ref("");
const loggingSnapshot = ref("");

const trafficWindows = ref<any[]>([]);
let trafficTimer: ReturnType<typeof setInterval> | null = null;

function rateToPercent(rate: unknown) {
  const n = Number(rate);
  if (!Number.isFinite(n)) return 100;
  return Math.round(Math.min(1, Math.max(0, n)) * 100);
}

function percentToRate(percent: unknown) {
  const n = Number(percent);
  if (!Number.isFinite(n)) return 1;
  return Math.min(1, Math.max(0, n / 100));
}

const trafficBySec = computed(() => {
  const map: Record<number, any> = {};
  for (const w of trafficWindows.value) map[w.sec] = w;
  return map;
});

const displayDirty = computed(() => snapshot(displayForm) !== displaySnapshot.value);

const engineDirty = computed(() => snapshot(engineForm) !== engineSnapshot.value);
const challengeDirty = computed(() => snapshot(form) !== challengeSnapshot.value);
const debugDirty = computed(() => snapshot(debugForm) !== debugSnapshot.value);
const engineGroupDirty = computed(() => engineDirty.value || challengeDirty.value || debugDirty.value);

const engineSaveLabel = computed(() => {
  return "保存";
});

const visitorPagesDirty = computed(
  () =>
    snapshot({ status_code: blockPageForm.status_code, html: blockPageForm.html }) !== blockPageSnapshot.value
    || snapshot({ html: captchaFooterForm.html }) !== captchaFooterSnapshot.value,
);

const loggingDirty = computed(() => snapshot(logForm) !== loggingSnapshot.value);

const importSectionOptions = computed(() => {
  const available = sectionsAvailableInPayload(importPayload.value);
  return backupSectionOptions.value.filter((item) => available.has(item.key));
});

const importResultMessage = computed(() => {
  const result = importResult.value;
  if (!result) return "";
  const parts = Object.entries(result.counts || {})
    .filter(([, n]) => Number(n) > 0)
    .map(([k, n]) => `${k}: ${n}`);
  const sync = result.engine_synced
    ? "引擎已同步"
    : result.engine_error || "引擎同步未完成";
  return parts.length ? `已处理 ${parts.join("，")}；${sync}` : sync;
});

function expandBackupSections(sections: string[] | undefined | null): Set<string> {
  const out = new Set<string>();
  for (const key of sections || []) {
    const aliases = LEGACY_BACKUP_SECTIONS[key];
    if (aliases) aliases.forEach((item) => out.add(item));
    else out.add(key);
  }
  return out;
}

function sectionsAvailableInPayload(payload: any): Set<string> {
  const available = expandBackupSections(payload?.sections);
  const data = payload?.data || {};
  if (data.ai_guard_settings != null) available.add("ai_config");
  if (Array.isArray(data.ai_guard_policies)) available.add("ai_policies");
  return available;
}

function windowLabel(sec: number) {
  return trafficWindowLabels[sec] || `${sec} 秒`;
}

function refreshSnapshots() {
  displaySnapshot.value = snapshot(displayForm);
  engineSnapshot.value = snapshot(engineForm);
  challengeSnapshot.value = snapshot(form);
  debugSnapshot.value = snapshot(debugForm);
  blockPageSnapshot.value = snapshot({ status_code: blockPageForm.status_code, html: blockPageForm.html });
  captchaFooterSnapshot.value = snapshot({ html: captchaFooterForm.html });
  loggingSnapshot.value = snapshot(logForm);
}

function groupHasDirty(group: SettingsGroupKey) {
  switch (group) {
    case "account-display":
      return displayDirty.value;
    case "engine-protection":
      return engineGroupDirty.value;
    case "visitor-pages":
      return visitorPagesDirty.value;
    case "logging-notify":
      return loggingDirty.value;
    default:
      return false;
  }
}

function onGroupChange(next: SettingsGroupKey) {
  if (next === activeGroup.value) return;
  if (!groupHasDirty(activeGroup.value)) {
    activeGroup.value = next;
    syncRouteTab();
    return;
  }
  pendingGroup.value = next;
  Modal.confirm({
    title: "有未保存的更改",
    content: "切换分组将丢弃当前未保存的修改，是否继续？",
    okText: "放弃更改",
    cancelText: "留在此页",
    onOk: () => {
      revertGroup(activeGroup.value);
      activeGroup.value = pendingGroup.value || next;
      pendingGroup.value = null;
      syncRouteTab();
    },
    onCancel: () => {
      pendingGroup.value = null;
    },
  });
}

function revertGroup(group: SettingsGroupKey) {
  if (group === "account-display" && displaySnapshot.value) {
    Object.assign(displayForm, JSON.parse(displaySnapshot.value));
  } else if (group === "engine-protection") {
    if (engineSnapshot.value) Object.assign(engineForm, JSON.parse(engineSnapshot.value));
    if (challengeSnapshot.value) Object.assign(form, JSON.parse(challengeSnapshot.value));
    if (debugSnapshot.value) Object.assign(debugForm, JSON.parse(debugSnapshot.value));
    ensureIpSelected();
  } else if (group === "visitor-pages") {
    if (blockPageSnapshot.value) {
      const parsed = JSON.parse(blockPageSnapshot.value);
      blockPageForm.status_code = parsed.status_code;
      blockPageForm.html = parsed.html;
    }
    if (captchaFooterSnapshot.value) {
      captchaFooterForm.html = JSON.parse(captchaFooterSnapshot.value).html;
    }
  } else if (group === "logging-notify" && loggingSnapshot.value) {
    Object.assign(logForm, JSON.parse(loggingSnapshot.value));
  }
}

function syncRouteTab() {
  const tab = legacyTabForGroup(activeGroup.value);
  if (route.query.tab === tab) return;
  router.replace({ query: { ...route.query, tab } });
}

function trimPanelUrl() {
  displayForm.panel_public_url = displayForm.panel_public_url.trim().replace(/\/+$/, "");
}

function toggleDimension(key: string, required?: boolean) {
  if (required) return;
  const set = new Set(form.clearance_fingerprint_dims);
  if (set.has(key)) set.delete(key);
  else set.add(key);
  form.clearance_fingerprint_dims = [...set];
  ensureIpSelected();
}

function startTrafficTimer() {
  if (trafficTimer) return;
  loadTraffic();
  trafficTimer = setInterval(loadTraffic, 5000);
}

function stopTrafficTimer() {
  if (!trafficTimer) return;
  clearInterval(trafficTimer);
  trafficTimer = null;
}

function resetUsernameForm() {
  usernameForm.new_username = "";
  usernameForm.current_password = "";
}

function resetPasswordForm() {
  passwordForm.current_password = "";
  passwordForm.new_password = "";
  passwordForm.confirm_password = "";
}

function ensureIpSelected() {
  if (!form.clearance_fingerprint_dims.includes("ip")) {
    form.clearance_fingerprint_dims = ["ip", ...form.clearance_fingerprint_dims];
  }
}

async function loadAccount() {
  const profile = await auth.fetchProfile();
  accountProfile.username = profile.username;
}

async function load() {
  const resp = await api.get<{
    js_challenge_ttl: number;
    captcha_ttl: number;
    clearance_fingerprint_dims: string[];
    fingerprint_dimension_options: DimensionOption[];
  }>("/api/v1/settings/challenge");
  form.js_challenge_ttl = resp.data.js_challenge_ttl;
  form.captcha_ttl = resp.data.captcha_ttl;
  form.clearance_fingerprint_dims = resp.data.clearance_fingerprint_dims;
  dimensionOptions.value = resp.data.fingerprint_dimension_options;
  ensureIpSelected();
}

async function loadLogging() {
  const resp = await api.get("/api/v1/settings/logging");
  Object.assign(logForm, {
    logging_control_mode: resp.data.logging_control_mode,
    logging_enabled: resp.data.logging_enabled,
    logging_skip_observe: resp.data.logging_skip_observe,
    observe_sample_rate_idle: rateToPercent(resp.data.observe_sample_rate_idle),
    observe_sample_rate_active: rateToPercent(resp.data.observe_sample_rate_active),
    logging_detail_on_block: resp.data.logging_detail_on_block,
    logging_auto_thresholds: resp.data.logging_auto_thresholds,
    logging_auto_cooldown_sec: resp.data.logging_auto_cooldown_sec,
    logging_auto_observe_sample_rate: rateToPercent(resp.data.logging_auto_observe_sample_rate),
    log_retention_days: resp.data.log_retention_days,
  });
}

async function loadDebug() {
  const resp = await api.get<{ debug_mode: boolean; ratelimit_fail_open: boolean }>("/api/v1/settings/debug");
  debugForm.debug_mode = resp.data.debug_mode;
  debugForm.ratelimit_fail_open = resp.data.ratelimit_fail_open ?? true;
}

async function loadDisplay() {
  if (!appSettings.loaded) await appSettings.fetch();
  displayForm.timezone = appSettings.timezone;
  displayForm.timezone_options = appSettings.timezoneOptions;
  displayForm.panel_public_url = appSettings.panelPublicUrl;
  displayForm.acme_account_email = appSettings.acmeAccountEmail;
}

async function loadEngine() {
  const resp = await api.get<{
    max_upload_size_mb: number;
    origin_read_timeout_sec: number;
  }>("/api/v1/settings/engine");
  engineForm.max_upload_size_mb = resp.data.max_upload_size_mb;
  engineForm.origin_read_timeout_sec = resp.data.origin_read_timeout_sec;
}

async function loadBlockPage() {
  const resp = await api.get<ResponsePageForm>("/api/v1/settings/block-page");
  blockPageForm.status_code = resp.data.status_code;
  blockPageForm.html = resp.data.html;
  blockPageForm.template_variables = resp.data.template_variables || [];
}

async function loadCaptchaFooter() {
  const resp = await api.get<{ html: string; template_variables: TemplateVariable[] }>(
    "/api/v1/settings/captcha-footer",
  );
  captchaFooterForm.html = resp.data.html;
  captchaFooterForm.template_variables = resp.data.template_variables || [];
}

async function loadTraffic() {
  const resp = await api.get("/api/v1/traffic/stats");
  trafficWindows.value = resp.data.global?.windows || [];
}

async function loadBackupSections() {
  const resp = await api.get("/api/v1/backup/sections");
  backupSectionOptions.value = resp.data || [];
  if (!exportSections.value.length) selectAllExportSections();
}

function textareaElement(
  refObj: { value: { $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null },
) {
  const comp = refObj.value;
  if (!comp) return null;
  return comp.resizableTextArea?.textArea || comp.$el;
}

function insertVariable(
  refObj: { value: { $el?: HTMLTextAreaElement; resizableTextArea?: { textArea: HTMLTextAreaElement } } | null },
  target: { html: string },
  field: "html",
  key: string,
) {
  const token = `{${key}}`;
  const el = textareaElement(refObj);
  if (!el) {
    target[field] += token;
    return;
  }
  const start = el.selectionStart ?? target[field].length;
  const end = el.selectionEnd ?? start;
  const value = target[field];
  target[field] = value.slice(0, start) + token + value.slice(end);
  const pos = start + token.length;
  requestAnimationFrame(() => {
    el.focus();
    el.setSelectionRange(pos, pos);
  });
}

async function saveUsername() {
  const newUsername = usernameForm.new_username.trim();
  if (!newUsername) {
    message.warning("请输入新用户名");
    return;
  }
  if (newUsername.length < 3 || newUsername.length > 64) {
    message.warning("用户名长度需在 3-64 个字符之间");
    return;
  }
  if (!/^[a-zA-Z0-9_-]+$/.test(newUsername)) {
    message.warning("用户名仅允许字母、数字、下划线和连字符");
    return;
  }
  if (!usernameForm.current_password) {
    message.warning("请输入当前密码以验证身份");
    return;
  }
  usernameSaving.value = true;
  try {
    await auth.changeUsername(usernameForm.current_password, newUsername);
    accountProfile.username = auth.username;
    resetUsernameForm();
    message.success("用户名已更新");
  } finally {
    usernameSaving.value = false;
  }
}

async function savePassword() {
  if (!passwordForm.current_password) {
    message.warning("请输入当前密码");
    return;
  }
  if (!passwordForm.new_password) {
    message.warning("请输入新密码");
    return;
  }
  if (passwordForm.new_password.length < 6) {
    message.warning("新密码至少 6 位");
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    message.warning("两次输入的新密码不一致");
    return;
  }
  passwordSaving.value = true;
  try {
    await auth.changePassword(passwordForm.current_password, passwordForm.new_password);
    resetPasswordForm();
    message.success("密码已更新，请使用新密码登录");
  } finally {
    passwordSaving.value = false;
  }
}

async function saveDisplayGroup() {
  const url = displayForm.panel_public_url.trim().replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(url)) {
    message.warning("面板地址必须以 http:// 或 https:// 开头");
    return;
  }
  const acmeEmail = displayForm.acme_account_email.trim();
  if (acmeEmail && (!acmeEmail.includes("@") || !acmeEmail.split("@")[1]?.includes("."))) {
    message.warning("ACME 账户邮箱格式无效");
    return;
  }
  displaySaving.value = true;
  try {
    await appSettings.updateDisplay({
      timezone: displayForm.timezone,
      panel_public_url: url,
      acme_account_email: acmeEmail || null,
    });
    displayForm.timezone = appSettings.timezone;
    displayForm.timezone_options = appSettings.timezoneOptions;
    displayForm.panel_public_url = appSettings.panelPublicUrl;
    displayForm.acme_account_email = appSettings.acmeAccountEmail;
    displaySnapshot.value = snapshot(displayForm);
    message.success("显示设置已保存");
  } finally {
    displaySaving.value = false;
  }
}

async function saveEngineOnly() {
  const mb = Number(engineForm.max_upload_size_mb);
  if (!Number.isInteger(mb) || mb < 1 || mb > 2048) {
    message.warning("最大上传限制需为 1–2048 的整数（MB）");
    return false;
  }
  const timeoutSec = Number(engineForm.origin_read_timeout_sec);
  if (!Number.isInteger(timeoutSec) || timeoutSec < 5 || timeoutSec > 600) {
    message.warning("源站响应超时需为 5–600 的整数（秒）");
    return false;
  }
  const resp = await api.put<{
    max_upload_size_mb: number;
    origin_read_timeout_sec: number;
  }>("/api/v1/settings/engine", {
    max_upload_size_mb: mb,
    origin_read_timeout_sec: timeoutSec,
  });
  engineForm.max_upload_size_mb = resp.data.max_upload_size_mb;
  engineForm.origin_read_timeout_sec = resp.data.origin_read_timeout_sec;
  engineSnapshot.value = snapshot(engineForm);
  if (resp.message && resp.message !== "ok") {
    message.warning(resp.message, 12);
    return false;
  }
  return true;
}

async function saveChallengeOnly() {
  ensureIpSelected();
  if (form.clearance_fingerprint_dims.length === 0) {
    message.error("请至少选择一个指纹维度");
    return false;
  }
  await api.put("/api/v1/settings/challenge", {
    js_challenge_ttl: form.js_challenge_ttl,
    captcha_ttl: form.captcha_ttl,
    clearance_fingerprint_dims: form.clearance_fingerprint_dims,
  });
  challengeSnapshot.value = snapshot(form);
  return true;
}

async function saveDebugOnly() {
  await api.put("/api/v1/settings/debug", {
    debug_mode: debugForm.debug_mode,
    ratelimit_fail_open: debugForm.ratelimit_fail_open,
  });
  debugSnapshot.value = snapshot(debugForm);
  return true;
}

async function saveEngineGroup() {
  if (!engineGroupDirty.value) return;
  const hadEngine = engineDirty.value;
  const hadChallenge = challengeDirty.value;
  const hadDebug = debugDirty.value;
  engineGroupSaving.value = true;
  try {
    let ok = true;
    if (hadEngine) {
      const engineOk = await saveEngineOnly();
      if (!engineOk && engineDirty.value) {
        return;
      }
      if (!engineOk) ok = false;
    }
    if (hadChallenge) {
      const challengeOk = await saveChallengeOnly();
      if (!challengeOk) ok = false;
    }
    if (hadDebug) {
      const debugOk = await saveDebugOnly();
      if (!debugOk) ok = false;
    }
    if (ok) {
      message.success(hadEngine ? "引擎与防护设置已保存" : "防护设置已保存并下发");
    }
  } finally {
    engineGroupSaving.value = false;
  }
}

async function saveVisitorPagesGroup() {
  if (!blockPageForm.html.trim()) {
    message.warning("请输入防护页面 HTML");
    return;
  }
  if (!captchaFooterForm.html.trim()) {
    message.warning("请输入页脚 HTML");
    return;
  }
  visitorPagesSaving.value = true;
  try {
    await api.put("/api/v1/settings/block-page", {
      status_code: blockPageForm.status_code,
      html: blockPageForm.html,
    });
    await api.put("/api/v1/settings/captcha-footer", {
      html: captchaFooterForm.html,
    });
    blockPageSnapshot.value = snapshot({ status_code: blockPageForm.status_code, html: blockPageForm.html });
    captchaFooterSnapshot.value = snapshot({ html: captchaFooterForm.html });
    message.success("访客页面已保存并下发");
  } finally {
    visitorPagesSaving.value = false;
  }
}

async function saveLoggingGroup() {
  logSaving.value = true;
  try {
    await api.put("/api/v1/settings/logging", {
      ...logForm,
      observe_sample_rate_idle: percentToRate(logForm.observe_sample_rate_idle),
      observe_sample_rate_active: percentToRate(logForm.observe_sample_rate_active),
      logging_auto_observe_sample_rate: percentToRate(logForm.logging_auto_observe_sample_rate),
    });
    loggingSnapshot.value = snapshot(logForm);
    message.success("日志设置已保存并下发");
  } finally {
    logSaving.value = false;
  }
}

function selectAllExportSections() {
  exportSections.value = backupSectionOptions.value.map((item) => item.key);
}

function selectAllImportSections() {
  importSections.value = importSectionOptions.value.map((item) => item.key);
}

function toggleExportSection(key: string, checked: boolean) {
  if (checked) {
    if (!exportSections.value.includes(key)) exportSections.value = [...exportSections.value, key];
    return;
  }
  exportSections.value = exportSections.value.filter((item) => item !== key);
}

function toggleImportSection(key: string, checked: boolean) {
  if (checked) {
    if (!importSections.value.includes(key)) importSections.value = [...importSections.value, key];
    return;
  }
  importSections.value = importSections.value.filter((item) => item !== key);
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

async function runExport() {
  if (!exportSections.value.length) {
    message.warning("请至少勾选一项导出内容");
    return;
  }
  exporting.value = true;
  try {
    const resp = (await http.post(
      "/api/v1/backup/export",
      { sections: exportSections.value },
      { timeout: 60000 },
    )) as { data: any };
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    downloadJson(`flow-shield-backup-${stamp}.json`, resp.data);
    message.success("配置已导出");
  } finally {
    exporting.value = false;
  }
}

function onBackupFile(file: File) {
  importResult.value = null;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result || ""));
      if (!parsed || parsed.format !== "flow-shield-waf-backup") {
        message.error("不是有效的流盾备份文件");
        importPayload.value = null;
        importFileName.value = "";
        return;
      }
      importPayload.value = parsed;
      importFileName.value = file.name;
      const available = sectionsAvailableInPayload(parsed);
      importSections.value = backupSectionOptions.value
        .map((item) => item.key)
        .filter((key) => available.has(key));
      message.success("备份文件已解析");
    } catch {
      message.error("无法解析 JSON 文件");
      importPayload.value = null;
      importFileName.value = "";
    }
  };
  reader.readAsText(file);
  return false;
}

async function runImport() {
  if (!importPayload.value || !importSections.value.length) {
    message.warning("请先选择备份文件并勾选导入项");
    return;
  }
  importing.value = true;
  importResult.value = null;
  try {
    const resp = (await http.post(
      "/api/v1/backup/import",
      {
        sections: importSections.value,
        payload: importPayload.value,
      },
      { timeout: 120000 },
    )) as { data: any; message?: string };
    importResult.value = resp.data;
    if (resp.message && resp.message !== "ok") {
      message.warning(resp.message, 12);
    } else {
      message.success("导入完成");
    }
    if (importSections.value.includes("system_settings")) {
      await loadDisplay();
      await loadEngine();
      await load();
      await loadLogging();
      await loadDebug();
      await loadBlockPage();
      await loadCaptchaFooter();
      refreshSnapshots();
    }
  } finally {
    importing.value = false;
  }
}

watch(activeGroup, (group) => {
  if (group === "logging-notify") startTrafficTimer();
  else stopTrafficTimer();
  syncRouteTab();
});

watch(
  () => route.query.tab,
  () => {
    const tab = tabFromQuery();
    if (!tab || !LEGACY_TABS.has(tab)) return;
    const next = groupFromLegacyTab(tab);
    if (next !== activeGroup.value && !groupHasDirty(activeGroup.value)) {
      activeGroup.value = next;
    }
  },
);

onMounted(async () => {
  await loadAccount();
  await load();
  await loadLogging();
  await loadDebug();
  await loadDisplay();
  await loadEngine();
  await loadBlockPage();
  await loadCaptchaFooter();
  await loadBackupSections();
  refreshSnapshots();
  if (activeGroup.value === "logging-notify") startTrafficTimer();
  syncRouteTab();
});

onUnmounted(() => {
  stopTrafficTimer();
});
</script>

<style scoped>
.settings-layout {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-main {
  flex: 1;
  min-width: 0;
}

.settings-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 8px;
  max-width: 860px;
}

.settings-group--panels-channels {
  max-width: none;
}

@media (min-width: 992px) {
  .settings-layout {
    flex-direction: row;
    align-items: flex-start;
    gap: 20px;
  }

  .settings-layout :deep(.settings-nav) {
    flex: 0 0 200px;
  }

  .settings-main {
    flex: 1;
  }
}

.settings-panel {
  height: 100%;
  background: var(--fs-bg-surface);
  border-radius: var(--fs-radius-md);
  box-shadow: var(--fs-shadow-sm);
  border: 1px solid var(--fs-border);
}

.settings-panel--flat :deep(.ant-card-body) {
  padding-top: 0;
}

.settings-panel :deep(.ant-card-body) {
  padding: 20px 24px;
}

.settings-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-head {
  margin-bottom: 16px;
}

.section-head--row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

.section-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--fs-text-secondary);
  line-height: 1.5;
}

.section-form {
  max-width: 420px;
}

.section-form.wide {
  max-width: 760px;
}

.readonly-value {
  min-height: 32px;
  padding: 4px 0;
  font-size: 14px;
  color: var(--fs-text-primary);
}

.hint {
  margin-top: 6px;
  color: var(--fs-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.hint-warn {
  color: #d26b17;
}

.switch-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.dim-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 10px;
  width: 100%;
}

.dim-card {
  display: block;
  width: 100%;
  min-height: 44px;
  padding: 10px 12px;
  border: 1px solid var(--fs-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--fs-border) 20%, transparent);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.dim-card.is-on {
  border-color: var(--fs-color-primary);
  background: color-mix(in srgb, var(--fs-color-primary) 8%, transparent);
}

.dim-card.is-locked {
  cursor: default;
  opacity: 0.92;
}

.dim-desc {
  margin-top: 4px;
  margin-left: 24px;
  color: var(--fs-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.dim-required {
  margin-left: 6px;
  font-size: 11px;
  line-height: 18px;
}

.threshold-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}

.threshold-item {
  padding: 12px;
  border: 1px solid var(--fs-border);
  border-radius: var(--fs-radius-md);
}

.threshold-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.traffic-hint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--fs-text-secondary);
}

.tab-notes {
  margin-top: 8px;
}

.notes {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  line-height: 1.7;
}

.debug-headers {
  margin-top: 8px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #6767670d;
}

.debug-headers-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 8px;
}

.debug-headers ul {
  margin: 0;
  padding-left: 18px;
  color: #475569;
  font-size: 13px;
  line-height: 1.8;
}

.status-segmented,
.mode-segmented,
.backup-mode-segmented {
  max-width: 100%;
}

.code-textarea :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

.backup-panel :deep(.ant-card-body) {
  max-width: 720px;
}

.backup-mode-segmented {
  margin-bottom: 14px;
}

.backup-lead {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--fs-text-secondary);
}

.backup-block {
  margin-bottom: 18px;
}

.backup-block__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.backup-block__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--fs-text-primary);
}

.backup-block__link {
  font-size: 13px;
}

.backup-checks {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.backup-check {
  display: flex;
  align-items: flex-start;
  margin: 0;
  padding: 10px 12px;
  min-height: 44px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--fs-border) 35%, transparent);
  cursor: pointer;
  transition: background 0.15s ease;
}

.backup-check.is-on {
  background: color-mix(in srgb, var(--fs-color-primary) 10%, transparent);
}

.backup-check :deep(.ant-checkbox-wrapper) {
  align-items: flex-start;
  white-space: normal;
  line-height: 1.45;
}

.backup-drop {
  display: block;
  margin-bottom: 18px;
}

.backup-drop :deep(.ant-upload-drag) {
  border-radius: 10px;
  background: color-mix(in srgb, var(--fs-border) 28%, transparent);
}

.backup-drop__icon {
  margin-bottom: 8px;
  font-size: 28px;
  color: var(--fs-color-primary);
}

.backup-drop__title {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--fs-text-primary);
}

.backup-drop__hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--fs-text-secondary);
}

.backup-result-line {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--fs-text-primary);
  background: color-mix(in srgb, #16a34a 12%, transparent);
}

.backup-footer {
  display: flex;
  justify-content: flex-start;
}

@media (max-width: 767px) {
  .settings-panel :deep(.ant-card-body) {
    padding: 16px;
  }

  .status-segmented :deep(.ant-segmented) {
    flex-wrap: wrap;
  }

  .backup-drop :deep(.ant-upload-drag) {
    padding: 16px 12px;
  }
}
</style>
