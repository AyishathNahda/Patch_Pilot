import type { CSSProperties } from "react";

const paths = {
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  terminal: "m5 7 5 5-5 5m8 0h6",
  arrow: "M5 12h14m-5-5 5 5-5 5",
  bug: "M8 8h8v8a4 4 0 0 1-8 0V8Zm2-4 2 4 2-4M3 10h5m8 0h5M3 16h5m8 0h5M12 9v11",
  shield: "m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Zm-4 9 3 3 5-6",
  code: "m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18",
  check: "m5 12 4 4L19 6",
  book: "M4 4h6l2 2 2-2h6v15h-6l-2 2-2-2H4V4Zm8 2v15",
  refresh: "M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 14 6M4 12a8 8 0 0 0 14 6",
  pulse: "M2 12h5l3-8 4 16 3-8h5",
  external: "M14 3h7v7m0-7L10 14M10 3H3v18h18v-7",
} as const;
export type IconName = keyof typeof paths;
export function Icon({ name, size = 18, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}><path d={paths[name]} /></svg>;
}
