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
import { Button, SectionHeading, Select } from "./ui";

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
    <div className="flex items-baseline justify-between gap-2 text-sm">
      <label htmlFor={htmlFor} className="text-muted" title={spec.help}>
        {spec.label}
      </label>
      {readout !== undefined && (
        <output htmlFor={htmlFor} className="font-data tabular-nums">
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
    <div className="flex flex-col gap-1">
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
        className="h-11 w-full accent-accent"
      />
    </div>
  );
}

function Toggle({ spec, send }: { spec: BoolParam; send: Send }) {
  const id = useId();
  const { shown, setShown } = useShown(spec);
  return (
    <div className="flex min-h-11 items-center justify-between gap-2">
      <Label htmlFor={id} spec={spec} />
      <input
        id={id}
        type="checkbox"
        role="switch"
        aria-checked={shown}
        checked={shown}
        onChange={(e) => {
          setShown(e.target.checked);
          send(spec.name, e.target.checked);
        }}
        className="size-6 accent-accent"
      />
    </div>
  );
}

function Choice({ spec, send }: { spec: ChoiceParam; send: Send }) {
  const { shown, setShown } = useShown(spec);
  return (
    <Select
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
    <div className="flex min-h-11 items-center justify-between gap-2">
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
        className="h-11 w-16 cursor-pointer rounded-md border border-line bg-bg text-base"
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
    <div className="flex flex-col gap-1">
      {spec.presets.length > 0 ? (
        <Select
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
        <span className="text-xs text-muted" title={spec.help}>
          {spec.label}
        </span>
      )}
      <div
        role="img"
        aria-label={`${spec.label}: ${shown.label || "custom"} gradient`}
        data-testid={`palette-${spec.name}`}
        className="h-3 w-full rounded-sm border border-line"
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
      return (
        <p className="text-sm text-muted">
          {spec.label}: this page cannot set it.
        </p>
      );
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
    <div className="flex flex-col gap-5">
      <section>
        <SectionHeading>Pattern</SectionHeading>
        {patterns.length ? (
          <Select
            label="Running on the server"
            value={pattern}
            options={patterns.map((p) => ({ value: p, label: p }))}
            onChange={(name) => client?.setPattern(name)}
          />
        ) : (
          <p className="text-sm text-muted">
            {connection === "open"
              ? "No patterns."
              : "Connecting to the engine…"}
          </p>
        )}
        <p className="mt-2 text-xs text-muted">
          Rendered by pewpew at {fps} fps
          {watts !== null && (
            <>
              {" · "}
              <span className="font-data text-ink" data-testid="effect-watts">
                {watts.toFixed(1)} W
              </span>{" "}
              now
            </>
          )}
        </p>
      </section>

      <section className="flex flex-col gap-3" aria-label="Pattern controls">
        <SectionHeading>Controls</SectionHeading>
        {params.length === 0 && (
          <p className="text-sm text-muted">This pattern has no controls.</p>
        )}
        {params.map((p) => (
          <Control key={`${pattern}:${p.name}`} spec={p} send={send} />
        ))}
        {params.length > 0 && (
          <div>
            <Button
              onClick={() => {
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
