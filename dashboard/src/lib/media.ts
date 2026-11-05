import { useSyncExternalStore } from "react";

/** Live media-query match, e.g. useMedia("(max-width: 767px)"). */
export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (cb) => { const m = window.matchMedia(query); m.addEventListener("change", cb); return () => m.removeEventListener("change", cb); },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Phone-sized viewport (below Tailwind's md breakpoint). */
export const useIsPhone = () => useMedia("(max-width: 767px)");

/** True on touch-first devices, where blur filters and hover effects only cost battery. */
export const coarsePointer = typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;
