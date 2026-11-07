import type { ButtonHTMLAttributes, ReactNode, Ref } from "react";
import { Icon } from "./Icon";
import { splitPress, usePress, type Act, type PressOptions } from "./press";
import { spaced } from "./spaced";

export interface TileProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "type">, PressOptions {
  /** What it is called. */
  readonly name: string;
  /** Signs after its name (↻, ↩). */
  readonly children?: ReactNode;
  /** What a press does; absent, a press is the `onClick` it is given (an Ark item's, through asChild). */
  readonly onPress?: Act;
  /** What the room shows now: amber tint, ● and weight 600. A tile that can be live is given true or false:
   * a tile shows the ● as a pip in its corner, and a row of a list keeps room for it at its end, so a look
   * going live moves nothing. */
  readonly live?: boolean;
  /** A cue holds it: amber tint and edge. */
  readonly held?: boolean;
  /** Picked here, for the page to show: the selected fill and weight 600, never amber. */
  readonly selected?: boolean;
  /** A row of a list, flat on its region (RA-27b's Row), not raised. */
  readonly flat?: boolean;
  readonly ref?: Ref<HTMLButtonElement> | undefined;
}

/** `name` (in an element of `className`), as wide as at weight 600, so being picked, open or live moves
 * nothing after it. */
export function SizedName({ name, className }: { name: string; className?: string }) {
  return (
    <span className="tile-name">
      <span className={className}>{name}</span>
      <span className="sizer" aria-hidden="true">
        {name}
      </span>
    </span>
  );
}

/** A thing to pick, not an action: a saved look, a pattern. Raised, with no edge (an edge is a verb's); `flat`,
 * a row of a list. Its name holds the room its weight 600 takes, so being picked or live moves nothing. */
export function Tile(props: TileProps) {
  const [options, { name, children, onPress, live, held, selected, flat, ref, className, onClick, ...native }] = splitPress(props);
  const { button, armed, press } = usePress((click) => onPress?.(click), options, ref);
  return (
    <button
      ref={button}
      type="button"
      {...native}
      className={spaced("tile", className)}
      data-live={live || undefined}
      data-held={held || undefined}
      data-selected={selected || undefined}
      data-flat={flat || undefined}
      data-armed={armed || undefined}
      data-busy={options.busy || undefined}
      aria-busy={options.busy || undefined}
      onClick={onPress ? press : onClick}
    >
      <SizedName name={name} />
      {children}
      {live !== undefined && <Icon name="dot" />}
    </button>
  );
}
