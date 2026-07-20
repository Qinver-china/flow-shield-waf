<template>
  <a-form layout="vertical">
    <fs-form-section title="策略信息">
      <template #extra>
        <form-enabled-switch v-model:checked="model.enabled" />
      </template>
      <a-form-item label="策略名称" required>
        <a-input v-model:value="model.name" placeholder="例如：流量突增自动分析" />
      </a-form-item>
      <a-form-item label="备注">
        <a-input v-model:value="model.remark" placeholder="可选" />
      </a-form-item>
    </fs-form-section>

    <fs-form-section title="触发条件">
      <a-form-item label="触发类型" required>
        <a-select v-model:value="model.trigger_type" @change="onTriggerChange">
          <a-select-option v-for="t in triggers" :key="t.type" :value="t.type">
            {{ t.label }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-row v-if="selectedTrigger?.params?.length" :gutter="16">
        <a-col v-for="p in selectedTrigger.params" :key="p.key" :span="12">
          <a-form-item :label="p.label || p.key" :required="p.required !== false">
            <a-input-number
              v-if="p.kind === 'number'"
              v-model:value="model.trigger_params[p.key]"
              style="width: 100%"
            />
            <site-single-select
              v-else-if="p.kind === 'site_id'"
              v-model:value="model.trigger_params[p.key]"
            />
          </a-form-item>
        </a-col>
      </a-row>
    </fs-form-section>

    <fs-form-section title="AI 分析指引">
      <a-form-item label="自定义提示词">
        <a-textarea
          v-model:value="model.custom_prompt"
          :rows="5"
          :maxlength="4000"
          show-count
          placeholder="可选。策略触发后，这段说明会一并发给 AI，用于补充业务背景或处置要求。例如：这是支付回调接口，优先识别伪造回调与重放；勿按 UA 封禁官方 SDK；建议先 observe。"
        />
      </a-form-item>
    </fs-form-section>

    <fs-form-section title="执行与通知">
      <a-form-item label="规则应用模式">
        <a-select v-model:value="model.apply_mode">
          <a-select-option value="suggest_only">仅生成建议</a-select-option>
          <a-select-option value="auto_observe">自动创建（观察）</a-select-option>
          <a-select-option value="auto_block">自动创建（拦截）</a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="通知阶段">
        <a-checkbox-group v-model:value="model.notify_on" :options="notifyOptions" />
      </a-form-item>

      <a-form-item label="通知通道">
        <a-select v-model:value="model.channel_ids" mode="multiple" placeholder="选择通道">
          <a-select-option v-for="c in channels" :key="c.id" :value="c.id">
            {{ c.name }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-form-item label="冷却时间（秒）">
        <a-input-number v-model:value="model.cooldown_sec" :min="30" style="width: 200px" />
      </a-form-item>
    </fs-form-section>
  </a-form>
</template>

<script setup lang="ts">
import { computed } from "vue";
import FormEnabledSwitch from "@/components/FormEnabledSwitch.vue";
import FsFormSection from "@/components/FsFormSection.vue";
import SiteSingleSelect from "@/components/SiteSingleSelect.vue";

const model = defineModel<any>({ required: true });

const props = defineProps<{
  triggers: any[];
  channels: any[];
}>();

const notifyOptions = [
  { label: "触发时", value: "trigger" },
  { label: "分析中", value: "analyzing" },
  { label: "结果", value: "result" },
];

const selectedTrigger = computed(() =>
  props.triggers.find((t) => t.type === model.value.trigger_type),
);

function onTriggerChange() {
  model.value.trigger_params = {};
}
</script>
