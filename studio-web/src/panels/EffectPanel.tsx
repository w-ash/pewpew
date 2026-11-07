import { Button, Switch } from "@pewpew/page";
import { useEffect, useId, useRef, useState } from "react";
import type {
  BoolParam,
  ChoiceParam,
  ColorParam,
  FloatParam,
  IntParam,
  PaletteParam,
  ParamSpec,
  ParamValue,
} from "@/api/types";
import type { SessionClient } from "@/session/client";
import {
  gradientCss,
  hexToHsv,
  hsvToHex,
  presetOf,
  valueFor,
} from "@/session/params";
import { useSession } from "@/store/session";
import { SectionHeading, SelectField } from "./ui";

type Send = (name: string, value: ParamValue) => void;

/**
 * The value a control shows: what the engine holds, except while the
 * visitor holds the control, so an echo cannot fight a drag. A refusal
 * snaps it back to what the engine holds, even mid-drag.
 */
function useShown<P extends ParamSpec>(spec: P) {
  const accepted = valueFor(
    spec,
    useSession((s) => s.accepted[spec.name]),
  );
  const refusedAt = useSession((s) => s.refusedAt[spec.name] ?? 0);
  const [shown, setShown] = useState<P["default"]>(accepted);
  const holding = useRef(false);
  const key = JSON.stringify(accepted);
  // biome-ignore lint/correctness/useExhaustiveDependencies: `key` stands for `accepted`, which is a new object per echo.
  useEffect(() => {
    if (!holding.current) setShown(accepted);
  }, [key]);
  // biome-ignore lint/correctness/useExhaustiveDependencies: a refusal snaps back even mid-drag.
  useEffect(() => {
    if (refusedAt) setShown(accepted);
  }, [refusedAt]);
  const hold = {
    onPointerDown: () => {
      holding.current = true;
    },
    onPointerUp: () => {
      holding.current = false;
    },
    onPointerCancel: () => {
      holding.current = false;
    },
    onBlur: () => {
      holding.current = false;
    },
  };
  return { shown, setShown, hold };
}

function Label({
  htmlFor,
  spec,
  readout,
}: {
  htmlFor: string;
  spec: ParamSpec;
  readout?: string;
}) {
  return (
    <div className="studio-param-head">
      <label htmlFor={htmlFor} className="field-label" title={spec.help}>
        {spec.label}
      </label>
      {readout !== undefined && (
        <output htmlFor={htmlFor} className="t-value">
          {readout}
        </output>
      )}
    </div>
  );
}

/** A slider over the engine's range and step, as for every float and int. */
function NumberLever({
  spec,
  send,
}: {
  spec: FloatParam | IntParam;
  send: Send;
}) {
  const id = useId();
  const { shown, setShown, hold } = useShown(spec);
  const decimals = spec.kind === "int" ? 0 : spec.decimals;
  return (
    <div className="studio-field">
      <Label
        htmlFor={id}
        spec={spec}
        readout={`${shown.toFixed(decimals)}${spec.unit ? ` ${spec.unit}` : ""}`}
      />
      <input
        id={id}
        type="range"
        min={spec.lo}
        max={spec.hi}
        step={spec.kind === "int" ? 1 : spec.step}
        value={shown}
        {...hold}
        onChange={(e) => {
          const raw = Number(e.target.value);
          const v = spec.kind === "int" ? Math.round(raw) : raw;
          setShown(v);
          send(spec.name, v);
        }}
        className="studio-range"
      />
    </div>
  );
}

function Toggle({ spec, send }: { spec: BoolParam; send: Send }) {
  const { shown, setShown } = useShown(spec);
  return (
    <Switch
      checked={shown}
      onChange={(on) => {
        setShown(on);
        send(spec.name, on);
      }}
    >
      <span className="field-label" title={spec.help}>
        {spec.label}
      </span>
    </Switch>
  );
}

function Choice({ spec, send }: { spec: ChoiceParam; send: Send }) {
  const { shown, setShown } = useShown(spec);
  return (
    <SelectField
      label={spec.label}
      value={shown}
      options={spec.options}
      onChange={(v) => {
        setShown(v);
        send(spec.name, v);
      }}
    />
  );
}

/** The screen color of the engine's HSV; a pick goes back as HSV. */
function ColorPick({ spec, send }: { spec: ColorParam; send: Send }) {
  const id = useId();
  const { shown, setShown, hold } = useShown(spec);
  const hex = hsvToHex(shown);
  return (
    <div className="studio-color-row">
      <Label htmlFor={id} spec={spec} readout={hex} />
      <input
        id={id}
        type="color"
        value={hex}
        {...hold}
        onChange={(e) => {
          const hsv = hexToHsv(e.target.value);
          if (!hsv) return;
          setShown(hsv);
          send(spec.name, hsv);
        }}
      />
    </div>
  );
}

const OWN = "";

/** The engine's gradient as a swatch, and a menu of its presets; a pick
 * goes back as the preset's label, which the engine reads as its stops. */
function PalettePick({ spec, send }: { spec: PaletteParam; send: Send }) {
  const { shown, setShown } = useShown(spec);
  const preset = presetOf(spec.presets, shown);
  const options = [
    ...(preset === null
      ? [{ value: OWN, label: shown.label || "Custom" }]
      : []),
    ...spec.presets.map((p) => ({ value: p.label, label: p.label })),
  ];
  return (
    <div className="studio-field">
      {spec.presets.length > 0 ? (
        <SelectField
          label={spec.label}
          value={preset ?? OWN}
          options={options}
          onChange={(label) => {
            const picked = spec.presets.find((p) => p.label === label);
            if (!picked) return;
            setShown(picked.value);
            send(spec.name, picked.label);
          }}
        />
      ) : (
        <span className="field-label" title={spec.help}>
          {spec.label}
        </span>
      )}
      <div
        role="img"
        aria-label={`${spec.label}: ${shown.label || "custom"} gradient`}
        data-testid={`palette-${spec.name}`}
        className="studio-swatch"
        style={{ backgroundImage: gradientCss(shown) }}
      />
    </div>
  );
}

/** One control per declared param, by its kind. */
function Control({ spec, send }: { spec: ParamSpec; send: Send }) {
  switch (spec.kind) {
    case "float":
    case "int":
      return <NumberLever spec={spec} send={send} />;
    case "bool":
      return <Toggle spec={spec} send={send} />;
    case "choice":
      return <Choice spec={spec} send={send} />;
    case "color":
      return <ColorPick spec={spec} send={send} />;
    case "palette":
      return <PalettePick spec={spec} send={send} />;
    default:
      return <p className="t-label">{spec.label}: this page cannot set it.</p>;
  }
}

export function EffectPanel({ client }: { client: SessionClient | null }) {
  const patterns = useSession((s) => s.patterns);
  const pattern = useSession((s) => s.pattern);
  const params = useSession((s) => s.params);
  const watts = useSession((s) => s.watts);
  const fps = useSession((s) => s.fps);
  const connection = useSession((s) => s.connection);
  const send: Send = (name, value) => client?.setParam(name, value);

  return (
    <div className="studio-panel">
      <section className="studio-section">
        <SectionHeading>Pattern</SectionHeading>
        {patterns.length ? (
          <SelectField
            label="Running on the server"
            value={pattern}
            options={patterns.map((p) => ({ value: p, label: p }))}
            onChange={(name) => client?.setPattern(name)}
          />
        ) : (
          <p className="t-label">
            {connection === "open"
              ? "No patterns."
              : "Connecting to the engine…"}
          </p>
        )}
        <p className="note">
          Rendered by pewpew at {fps} fps
          {watts !== null && (
            <>
              {" · "}
              <span className="t-value readout" data-testid="effect-watts">
                {watts.toFixed(1)} W
              </span>{" "}
              now
            </>
          )}
        </p>
      </section>

      <section className="studio-section" aria-label="Pattern controls">
        <SectionHeading>Controls</SectionHeading>
        {params.length === 0 && (
          <p className="t-label">This pattern has no controls.</p>
        )}
        {params.map((p) => (
          <Control key={`${pattern}:${p.name}`} spec={p} send={send} />
        ))}
        {params.length > 0 && (
          <div>
            <Button
              onPress={() => {
                for (const p of params)
                  if (p.kind !== "unknown") send(p.name, p.default);
              }}
            >
              Reset
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
