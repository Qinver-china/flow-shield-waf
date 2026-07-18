<template>
  <a-dropdown
    :trigger="trigger"
    :placement="placement"
    :mouse-enter-delay="mouseEnterDelay"
    :mouse-leave-delay="mouseLeaveDelay"
  >
    <slot />
    <template #overlay>
      <slot name="overlay" />
    </template>
  </a-dropdown>
</template>

<script setup lang="ts">
import type { DropdownProps } from "ant-design-vue";
import {
  OVERLAY_HOVER_ENTER_DELAY,
  OVERLAY_HOVER_LEAVE_DELAY,
} from "@/constants/overlay";

withDefaults(
  defineProps<{
    trigger?: DropdownProps["trigger"];
    placement?: DropdownProps["placement"];
    mouseEnterDelay?: number;
    mouseLeaveDelay?: number;
  }>(),
  {
    trigger: () => ["hover"],
    placement: "bottomLeft",
    mouseEnterDelay: OVERLAY_HOVER_ENTER_DELAY,
    mouseLeaveDelay: OVERLAY_HOVER_LEAVE_DELAY,
  },
);
</script>
