import { onMounted, onUnmounted, ref } from "vue";

const DEFAULT_STORAGE_KEY = "waf_ai_fab_position";
const DRAG_THRESHOLD_PX = 5;

export interface FabPoint {
  x: number;
  y: number;
}

interface UseFabDragPositionOptions {
  size?: number;
  edgeMargin?: number;
  storageKey?: string;
  onTap?: () => void;
}

function readStoredPosition(key: string): FabPoint | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<FabPoint>;
    if (typeof parsed.x === "number" && typeof parsed.y === "number") {
      return { x: parsed.x, y: parsed.y };
    }
  } catch {
    // ignore invalid cache
  }
  return null;
}

export function useFabDragPosition(options: UseFabDragPositionOptions = {}) {
  const size = options.size ?? 48;
  const edgeMargin = options.edgeMargin ?? 8;
  const storageKey = options.storageKey ?? DEFAULT_STORAGE_KEY;

  const isDragging = ref(false);

  let dragStart: {
    pointerX: number;
    pointerY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null = null;

  function defaultPosition(): FabPoint {
    const fallbackMargin = 22;
    return {
      x: Math.max(edgeMargin, window.innerWidth - fallbackMargin - size),
      y: Math.max(edgeMargin, window.innerHeight - fallbackMargin - size),
    };
  }

  function clampPosition(pos: FabPoint): FabPoint {
    const maxX = Math.max(edgeMargin, window.innerWidth - size - edgeMargin);
    const maxY = Math.max(edgeMargin, window.innerHeight - size - edgeMargin);
    return {
      x: Math.min(Math.max(edgeMargin, pos.x), maxX),
      y: Math.min(Math.max(edgeMargin, pos.y), maxY),
    };
  }

  function persistPosition(pos: FabPoint) {
    localStorage.setItem(storageKey, JSON.stringify(pos));
  }

  function restorePosition(): FabPoint {
    const stored = readStoredPosition(storageKey);
    return clampPosition(stored ?? defaultPosition());
  }

  const fabPos = ref<FabPoint>(
    typeof window !== "undefined" ? restorePosition() : { x: 0, y: 0 },
  );

  function clearDragListeners() {
    window.removeEventListener("pointermove", onWindowPointerMove);
    window.removeEventListener("pointerup", onWindowPointerUp);
    window.removeEventListener("pointercancel", onWindowPointerUp);
  }

  function onWindowPointerMove(event: PointerEvent) {
    if (!dragStart) return;
    const dx = event.clientX - dragStart.pointerX;
    const dy = event.clientY - dragStart.pointerY;
    if (!dragStart.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
    dragStart.moved = true;
    isDragging.value = true;
    fabPos.value = clampPosition({
      x: dragStart.originX + dx,
      y: dragStart.originY + dy,
    });
  }

  function onWindowPointerUp() {
    if (!dragStart) return;
    const moved = dragStart.moved;
    if (moved) {
      persistPosition(fabPos.value);
    } else {
      options.onTap?.();
    }
    dragStart = null;
    isDragging.value = false;
    clearDragListeners();
  }

  function onFabPointerDown(event: PointerEvent) {
    if (event.button !== 0) return;
    event.preventDefault();
    dragStart = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      originX: fabPos.value.x,
      originY: fabPos.value.y,
      moved: false,
    };
    window.addEventListener("pointermove", onWindowPointerMove);
    window.addEventListener("pointerup", onWindowPointerUp);
    window.addEventListener("pointercancel", onWindowPointerUp);
  }

  function onResize() {
    fabPos.value = clampPosition(fabPos.value);
    persistPosition(fabPos.value);
  }

  onMounted(() => {
    fabPos.value = restorePosition();
    window.addEventListener("resize", onResize);
  });

  onUnmounted(() => {
    window.removeEventListener("resize", onResize);
    clearDragListeners();
  });

  return {
    fabPos,
    isDragging,
    onFabPointerDown,
  };
}
