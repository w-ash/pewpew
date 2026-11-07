// The page's actions. A Button is a verb in one of three ranks: primary (solid amber, one per region, shown
// only while it can act, never destructive), secondary (an edge) and tertiary (a word or a sign in a fixed
// slot). IconButton is a square one named by its aria-label; ToggleButton stays on or off. Each takes the
// press options (press.tsx): a confirm, busy, a reason, a key.
import type { ButtonHTMLAttributes, ReactNode, Ref } from "react";
import { Icon, type IconName } from "./Icon";
import { splitPress, usePress, type Act, type PressOptions } from "./press";
import { spaced } from "./spaced";

type Native = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onClick" | "children" | "type">;

export type Variant = "primary" | "secondary" | "tertiary";

interface PressableProps extends Native, PressOptions {
  readonly onPress: Act;
  readonly ref?: Ref<HTMLButtonElement> | undefined;
}

interface BaseProps extends PressableProps {
  readonly variant: Variant;
  /** danger: it darkens or removes; accent: on, it arms what the room answers (a toggle only). */
  readonly tone?: "danger" | "accent" | undefined;
  /** A square holding one sign. */
  readonly square?: boolean;
  /** A cue holding its look: amber tint and edge. */
  readonly held?: boolean | undefined;
  /** A sign before `children`. */
  readonly icon?: IconName | undefined;
  readonly children?: ReactNode;
}

function ButtonBase(props: BaseProps) {
  const [options, { variant, tone, square, held, icon, children, onPress, ref, className, ...native }] = splitPress(props);
  const { button, armed, press } = usePress(onPress, options, ref);
  const { confirm, busy, reason, note } = options;
  const off = !!reason;
  const face = (
    <>
      {icon && <Icon name={icon} />}
      {children}
    </>
  );
  return (
    <button
      ref={button}
      type="button"
      {...native}
      className={spaced("button", className)}
      data-variant={variant}
      data-tone={tone}
      data-square={square || undefined}
      data-held={held || undefined}
      data-armed={armed || undefined}
      data-busy={busy || undefined}
      aria-busy={busy || undefined}
      aria-disabled={off || native["aria-disabled"] || undefined}
      aria-describedby={spaced(native["aria-describedby"], off && note?.id) || undefined}
      onClick={press}
    >
      {confirm && !square ? (
        // Both faces at once, the one not shown hidden, so arming it moves nothing.
        <span className="faces">
          <span className="idle-face" aria-hidden={armed || undefined}>
            {face}
          </span>
          <span className="armed-face" aria-hidden={!armed || undefined}>
            {confirm}
          </span>
        </span>
      ) : (
        face
      )}
    </button>
  );
}

export interface ButtonProps extends PressableProps {
  /** Secondary unless named. */
  readonly variant?: Variant;
  readonly tone?: "danger";
  /** A sign before the words. */
  readonly icon?: IconName;
  readonly held?: boolean;
  readonly children: ReactNode;
}

/** An action, a verb. */
export function Button({ variant, ...rest }: ButtonProps) {
  return <ButtonBase {...rest} variant={variant ?? "secondary"} />;
}

export interface IconButtonProps extends PressableProps {
  /** What it does, for assistive tech: it shows only a sign. */
  readonly label: string;
  readonly icon?: IconName;
  /** A sign the fonts have ("?", "−", "+"), in place of an icon. */
  readonly glyph?: string;
  /** Tertiary unless named; primary only as the second half of a split button, joined to its primary. */
  readonly variant?: Variant;
  readonly tone?: "danger";
}

/** A square action that shows one sign. */
export function IconButton({ label, glyph, variant, ...rest }: IconButtonProps) {
  return (
    <ButtonBase {...rest} variant={variant ?? "tertiary"} square aria-label={label}>
      {glyph && <span aria-hidden="true">{glyph}</span>}
    </ButtonBase>
  );
}

export interface ToggleButtonProps extends Omit<PressableProps, "onPress" | "confirm" | "twoPress"> {
  readonly pressed: boolean;
  onPressedChange(pressed: boolean): void;
  readonly children?: ReactNode;
  readonly icon?: IconName;
  /** Its name, when it shows only its icon. */
  readonly label?: string;
  /** On, it arms what the room answers: amber tint and edge, in place of the selected fill. */
  readonly tone?: "accent";
  readonly variant?: "secondary" | "tertiary";
  /** What a first press shows when turning it off takes two ("again to disarm"). */
  readonly confirmOff?: string;
}

/** A button that stays on or off (the APG toggle button: aria-pressed). On, it takes the selected fill. */
export function ToggleButton({ pressed, onPressedChange, children, label, variant, confirmOff, ...rest }: ToggleButtonProps) {
  const square = children === undefined;
  return (
    <ButtonBase
      {...rest}
      variant={variant ?? "secondary"}
      square={square}
      aria-pressed={pressed}
      aria-label={square ? label : undefined}
      confirm={confirmOff}
      twoPress={pressed}
      onPress={() => onPressedChange(!pressed)}
    >
      {children}
    </ButtonBase>
  );
}
