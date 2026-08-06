<template>
  <a-dropdown
    :arrow="arrow"
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
    arrow?: boolean;
  }>(),
  {
    trigger: () => ["hover"],
    placement: "bottomLeft",
    mouseEnterDelay: OVERLAY_HOVER_ENTER_DELAY,
    mouseLeaveDelay: OVERLAY_HOVER_LEAVE_DELAY,
    arrow: false,
  },
);
</script>
