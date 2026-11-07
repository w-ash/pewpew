/** A sign's paths on a 16-unit grid: a stroked part and a filled part. */
interface Glyph {
  readonly stroke?: string;
  readonly fill?: string;
}

/** The signs neither Martian font has. */
const ICONS = {
  // ✕ ✓ ⋯
  close: { stroke: "M4 4l8 8M12 4l-8 8" },
  check: { stroke: "M3.5 8.5l3 3 6-7" },
  more: { fill: "M2.25 8a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0-2.5 0M6.75 8a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0-2.5 0M11.25 8a1.25 1.25 0 1 0 2.5 0a1.25 1.25 0 1 0-2.5 0" },
  // ▾ for a list or menu; ⌄ for a disclosure, turned to point right while shut.
  caret: { fill: "M4.5 6.5h7L8 10.5z" },
  chevron: { stroke: "M4 6l4 4 4-4" },
  // ▲ ▼ ◂ ▸
  up: { fill: "M8 4.5l4.5 7h-9z" },
  down: { fill: "M3.5 4.5h9L8 11.5z" },
  left: { fill: "M10.5 4.5v7L5 8z" },
  right: { fill: "M5.5 4.5v7L11 8z" },
  // ● live; ✦ draft; ◼ a pattern; ≡ steps
  dot: { fill: "M5 8a3 3 0 1 0 6 0a3 3 0 1 0-6 0" },
  sparkle: { fill: "M8 2l1.5 4.5L14 8l-4.5 1.5L8 14l-1.5-4.5L2 8l4.5-1.5z" },
  square: { fill: "M5 4h6a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z" },
  lines: { stroke: "M3 4.5h10M3 8h10M3 11.5h10" },
  // ↻ in shuffle; ↺ back to saved; ↩ returns here; ⤒ shown above
  cycle: { stroke: "M13 8a5 5 0 1 1-1.46-3.54M11.54 1.9v2.56H8.98" },
  reset: { stroke: "M3 8a5 5 0 1 0 1.46-3.54M4.46 1.9v2.56h2.56" },
  return: { stroke: "M6 9.5l-3-3 3-3M3 6.5h6.5a3.5 3.5 0 0 1 0 7H7" },
  pin: { stroke: "M3 2.5h10M8 13.5v-8M4.5 9L8 5.5 11.5 9" },
  // ⌕ find; ⠿ drag; ⌘ the command key; ↕ order
  search: { stroke: "M7 3a4 4 0 1 0 0 8a4 4 0 1 0 0-8M10 10l3.5 3.5" },
  grip: { fill: "M4.9 4a1.1 1.1 0 1 0 2.2 0a1.1 1.1 0 1 0-2.2 0M8.9 4a1.1 1.1 0 1 0 2.2 0a1.1 1.1 0 1 0-2.2 0M4.9 8a1.1 1.1 0 1 0 2.2 0a1.1 1.1 0 1 0-2.2 0M8.9 8a1.1 1.1 0 1 0 2.2 0a1.1 1.1 0 1 0-2.2 0M4.9 12a1.1 1.1 0 1 0 2.2 0a1.1 1.1 0 1 0-2.2 0M8.9 12a1.1 1.1 0 1 0 2.2 0a1.1 1.1 0 1 0-2.2 0" },
  command: { stroke: "M6 10V4.5A1.5 1.5 0 1 0 4.5 6h7A1.5 1.5 0 1 0 10 4.5v7a1.5 1.5 0 1 0 1.5-1.5h-7A1.5 1.5 0 1 0 6 11.5z" },
  updown: { stroke: "M8 2.5v11M5 5.5l3-3 3 3M5 10.5l3 3 3-3" },
  // ☀ brightness; ⚄ surprise me; ≈ vary this
  sun: { stroke: "M8 5.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5M8 1.5V3M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1.06 1.06M11.54 11.54l1.06 1.06M3.4 12.6l1.06-1.06M11.54 4.46l1.06-1.06" },
  dice: {
    stroke: "M4 2.5h8A1.5 1.5 0 0 1 13.5 4v8a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 12V4A1.5 1.5 0 0 1 4 2.5z",
    fill: "M4.6 5.5a.9.9 0 1 0 1.8 0a.9.9 0 1 0-1.8 0M9.6 5.5a.9.9 0 1 0 1.8 0a.9.9 0 1 0-1.8 0M7.1 8a.9.9 0 1 0 1.8 0a.9.9 0 1 0-1.8 0M4.6 10.5a.9.9 0 1 0 1.8 0a.9.9 0 1 0-1.8 0M9.6 10.5a.9.9 0 1 0 1.8 0a.9.9 0 1 0-1.8 0",
  },
  approx: { stroke: "M3 6.25c1.67-1.5 3.33-1.5 5 0s3.33 1.5 5 0M3 10.25c1.67-1.5 3.33-1.5 5 0s3.33 1.5 5 0" },
  // ≤ ≥
  le: { stroke: "M11 3.5l-6 3 6 3M5 12.5h6" },
  ge: { stroke: "M5 3.5l6 3-6 3M5 12.5h6" },
} satisfies Record<string, Glyph>;

export type IconName = keyof typeof ICONS;

/** Every icon's name. */
export const ICON_NAMES = Object.keys(ICONS) as readonly IconName[];

/** A sign as an inline SVG in the current colour, --icon square on its 16-unit grid, so its strokes land on
 * pixels; a mark in a corner or a caption is drawn smaller (controls.css).
 * Always hidden from assistive tech: the control or the words beside it carry the meaning. */
export function Icon({ name }: { name: IconName }) {
  const icon: Glyph = ICONS[name];
  return (
    <svg className="icon" data-icon={name} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      {icon.stroke && <path d={icon.stroke} />}
      {icon.fill && <path className="fill" d={icon.fill} />}
    </svg>
  );
}
