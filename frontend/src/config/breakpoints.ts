/**
 * Centralized breakpoint configuration
 *
 * Three-tier responsive system:
 * - Mobile: 0-479px (default styles)
 * - Tablet: 480-1023px (sm: prefix in Tailwind)
 * - Desktop: 1024px+ (lg: prefix in Tailwind)
 */

export const BREAKPOINTS = {
  /** Tablet breakpoint (480px) */
  sm: 480,
  /** Desktop breakpoint (1024px) */
  lg: 1024,
} as const;

/** Check if current viewport is mobile (< 480px) */
export const isMobileViewport = () => window.innerWidth < BREAKPOINTS.sm;

/** Check if current viewport is tablet (480-1023px) */
export const isTabletViewport = () =>
  window.innerWidth >= BREAKPOINTS.sm && window.innerWidth < BREAKPOINTS.lg;

/** Check if current viewport is desktop (>= 1024px) */
export const isDesktopViewport = () => window.innerWidth >= BREAKPOINTS.lg;

/** Check if viewport is below desktop (mobile or tablet) */
export const isBelowDesktop = () => window.innerWidth < BREAKPOINTS.lg;
