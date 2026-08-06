/** Brand static assets (served from `frontend/public/`). */
export const BRAND = {
  favicon: "/favicon.png",
  /** Transparent mark — works on light and dark surfaces. */
  icon: "/brand/icon.png",
  logoSquareLight: "/brand/logo-square-light.png",
  logoSquareDark: "/brand/logo-square-dark.png",
  logoHorizontalLight: "/brand/logo-horizontal-light.svg",
  logoHorizontalDark: "/brand/logo-horizontal-dark.svg",
  name: "流盾WAF",
  tagline: "守住每一次真实访问",
} as const;

export type BrandSurface = "light" | "dark";

/** Square mark for light/dark surfaces (legacy tiles with baked backgrounds). */
export function brandLogoSquare(surface: BrandSurface): string {
  return surface === "dark" ? BRAND.logoSquareDark : BRAND.logoSquareLight;
}

/** Horizontal wordmark for light/dark surfaces. */
export function brandLogoHorizontal(surface: BrandSurface): string {
  return surface === "dark" ? BRAND.logoHorizontalDark : BRAND.logoHorizontalLight;
}
