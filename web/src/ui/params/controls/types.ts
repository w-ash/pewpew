import type { Param, ValueOf } from "../../../domain/params/schema";

/** What every control gets from its ParamField. */
export interface ControlProps<P extends Param> {
  readonly p: P;
  readonly value: ValueOf<P>;
  /** The control moved; the value is sent. */
  onChange(v: ValueOf<P>): void;
  /** The control let go. */
  onCommit(): void;
  /** What became of a typed value the control could not take as typed, or null. */
  onNote(note: string | null): void;
  /** The id of the field's label, for controls that name their own parts. */
  readonly labelId: string;
  /** The field's name in words, its context after its label: what a part of the control (a typed
   * entry, a ± button, a color's strip) is named after. */
  readonly name: string;
  /** The ids of what describes the control (its help, what moves it), or undefined. */
  readonly describedBy?: string | undefined;
  /** Where a route moves a number knob now (the `mod` readout), or null when none does: drawn as
   * a mark, while the control's own value, which it shows and sets, stays the knob's. */
  readonly live?: number | null;
}

/** What a kind shows beside the field's label, for a glance. */
export interface GlanceProps<P extends Param> {
  readonly p: P;
  readonly value: ValueOf<P>;
}
