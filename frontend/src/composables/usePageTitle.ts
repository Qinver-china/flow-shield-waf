import { ref } from "vue";

/** Page-level heading from the active view (e.g. PageShell title). */
export const pageTitleOverride = ref("");

export function setPageTitleOverride(title: string) {
  pageTitleOverride.value = title;
}

export function clearPageTitleOverride() {
  pageTitleOverride.value = "";
}
