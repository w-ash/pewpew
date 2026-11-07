// Which control draws a param, by kind; and what a kind, or a widget of it,
// shows beside its label.
import type { ComponentType } from "react";
import type { Kind, Param } from "./schema";
import { AngleGlance } from "./controls/angle";
import { BoolControl } from "./controls/bool";
import { ChoiceControl } from "./controls/choice";
import { ColorControl, ColorSwatch } from "./controls/color";
import { NumberControl } from "./controls/number";
import { PaletteControl } from "./controls/palette";
import type { ControlProps, GlanceProps } from "./controls/types";
import { UnknownControl } from "./controls/unknown";

type Of<K extends Kind> = Extract<Param, { kind: K }>;

interface Entry<K extends Kind> {
  readonly default: ComponentType<ControlProps<Of<K>>>;
  readonly glance?: ComponentType<GlanceProps<Of<K>>>;
  /** A widget's own glance in place of the kind's: an angle's compass. */
  readonly glances?: Readonly<Record<string, ComponentType<GlanceProps<Of<K>>>>>;
}

const defs: { readonly [K in Kind]: Entry<K> } = {
  float: { default: NumberControl, glances: { angle: AngleGlance } },
  int: { default: NumberControl },
  bool: { default: BoolControl },
  choice: { default: ChoiceControl },
  color: { default: ColorControl, glance: ColorSwatch },
  palette: { default: PaletteControl },
};

export interface Drawn {
  readonly Control: ComponentType<ControlProps<Param>>;
  readonly Glance: ComponentType<GlanceProps<Param>> | null;
}

export function controlFor(p: Param): Drawn {
  const entry = p.kind === "unknown" ? undefined : (defs[p.kind] as Entry<Kind> | undefined);
  return {
    Control: (entry?.default ?? UnknownControl) as ComponentType<ControlProps<Param>>,
    Glance: (entry?.glances?.[p.widget] ?? entry?.glance ?? null) as ComponentType<GlanceProps<Param>> | null,
  };
}
