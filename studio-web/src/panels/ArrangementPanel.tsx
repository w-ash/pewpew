import { useRef } from "react";
import { ApiError } from "@/api/client";
import { compileArrangement } from "@/api/endpoints";
import type {
  Arrangement,
  ArrayGroup,
  AttachmentRef,
  Catalog,
  CompiledRig,
  DataIn,
  Group,
  RingGroup,
  Vec3,
} from "@/api/types";
import {
  addFixture,
  asArrangement,
  duplicate,
  type End,
  explodeGroup,
  flip,
  freshId,
  IDENTITY_POSE,
  poseOf,
  type RingEnd,
  remove,
  type Selection,
  setAttachment,
  setPose,
  updateGroup,
} from "@/editor/arrangement";
import {
  type PoseQ,
  quatToYpr,
  resolvePose,
  roundVec,
  type YawPitchRoll,
  yprToQuat,
} from "@/editor/pose";
import { cn } from "@/lib/cn";
import { useDoc } from "@/store/doc";
import { Button, NumberField, SectionHeading, Select } from "./ui";

const DEFAULT_TYPE = "clen-rgbw-bar-1m";

function fixtureTypes(catalog: Catalog | null) {
  const list = catalog?.fixture_types ?? [];
  return list.length ? list : [{ id: DEFAULT_TYPE, name: "1M LED Pixel Bar" }];
}

export function ArrangementPanel({
  catalog,
  rig,
  rigIsCurrent,
}: {
  catalog: Catalog | null;
  rig: CompiledRig | null;
  rigIsCurrent: boolean;
}) {
  const arrangement = useDoc((s) => s.history.present);
  const canUndo = useDoc((s) => s.history.past.length > 0);
  const canRedo = useDoc((s) => s.history.future.length > 0);
  const selection = useDoc((s) => s.selection);
  const { commit, undo, redo, select } = useDoc.getState();
  const fileInput = useRef<HTMLInputElement>(null);
  const types = fixtureTypes(catalog);

  const exportJson = () => {
    const blob = new Blob([`${JSON.stringify(arrangement, null, 2)}\n`], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(arrangement.name || "arrangement").replace(/[^\w.-]+/g, "-")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importJson = async (file: File) => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(await file.text());
    } catch {
      alert(`${file.name} is not JSON.`);
      return;
    }
    const next = asArrangement(parsed);
    if (!next) {
      alert(
        `${file.name} is not a pewpew arrangement (format "pewpew.arrangement").`,
      );
      return;
    }
    // The server checks every field the editors read, so only a file it
    // compiles reaches the document.
    try {
      await compileArrangement(next);
    } catch (e) {
      const why =
        e instanceof ApiError && e.status === 422
          ? e.issues.map((i) => i.message).join("; ") || e.message
          : "the server could not check it";
      alert(`${file.name} was not imported: ${why}.`);
      return;
    }
    select(null);
    commit(next);
  };

  const addGroup = (group: RingGroup | ArrayGroup) => {
    commit({ ...arrangement, groups: [...arrangement.groups, group] });
    select({ kind: "group", id: group.id });
  };

  const addRing = () => {
    const ring: RingGroup = {
      id: freshId(arrangement, "ring-1"),
      preset: "ring",
      type: types[0].id,
      count: 8,
      start_radius_m: 0.618034,
      angle_offset_deg: 0,
      tilt_deg: 30,
      roll_deg: 0,
      data_in: "inner",
      pose: IDENTITY_POSE,
    };
    addGroup(ring);
  };

  const addArray = () => {
    const group: ArrayGroup = {
      id: freshId(arrangement, "array-1"),
      preset: "array",
      type: types[0].id,
      counts: [4],
      steps_m: [[0.1, 0, 0]],
      pose: { position_m: [0, 0.5, 0], quat_xyzw: [0, 0, 0, 1] },
    };
    addGroup(group);
  };

  return (
    <div className="flex flex-col gap-5">
      <section>
        <label className="flex flex-col gap-1 text-xs text-muted">
          <span>Name</span>
          <input
            value={arrangement.name ?? ""}
            onChange={(e) =>
              commit({ ...arrangement, name: e.target.value }, "name")
            }
            placeholder="Untitled arrangement"
            className="h-11 rounded-md border border-line bg-bg px-2 text-base text-ink focus:border-accent focus:outline-none"
          />
        </label>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button onClick={undo} disabled={!canUndo} title="Undo (⌘Z)">
            Undo
          </Button>
          <Button onClick={redo} disabled={!canRedo} title="Redo (⇧⌘Z)">
            Redo
          </Button>
          <Button
            onClick={exportJson}
            title="Download this arrangement as JSON"
          >
            Export
          </Button>
          <Button
            onClick={() => fileInput.current?.click()}
            title="Open an arrangement JSON file"
          >
            Import
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void importJson(file);
            }}
          />
        </div>
      </section>

      <section>
        <SectionHeading>Add</SectionHeading>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => {
              const { arrangement: next, id } = addFixture(
                arrangement,
                types[0].id,
              );
              commit(next);
              select({ kind: "fixture", id });
            }}
          >
            Bar
          </Button>
          <Button onClick={addRing}>Ring</Button>
          <Button onClick={addArray}>Array</Button>
        </div>
      </section>

      <section>
        <SectionHeading>Fixtures</SectionHeading>
        <ul className="flex flex-col gap-1" data-testid="entity-list">
          {arrangement.groups.map((g) => (
            <EntityRow
              key={`g:${g.id}`}
              label={g.id}
              detail={
                g.preset === "ring"
                  ? `ring of ${g.count}`
                  : `array ${g.counts.join("×")}`
              }
              active={selection?.kind === "group" && selection.id === g.id}
              onClick={() => select({ kind: "group", id: g.id })}
            />
          ))}
          {arrangement.fixtures.map((f) => (
            <EntityRow
              key={`f:${f.id}`}
              label={f.id}
              detail={types.find((t) => t.id === f.type)?.name ?? f.type}
              active={selection?.kind === "fixture" && selection.id === f.id}
              onClick={() => select({ kind: "fixture", id: f.id })}
            />
          ))}
          {arrangement.groups.length + arrangement.fixtures.length === 0 && (
            <li className="text-sm text-muted">
              Nothing yet. Add a bar, a ring or an array.
            </li>
          )}
        </ul>
      </section>

      {selection && (
        <SelectionEditor
          key={`${selection.kind}:${selection.id}`}
          arrangement={arrangement}
          selection={selection}
          catalog={catalog}
          rig={rig}
          rigIsCurrent={rigIsCurrent}
          edit={commit}
        />
      )}
    </div>
  );
}

function EntityRow({
  label,
  detail,
  active,
  onClick,
}: {
  label: string;
  detail: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        aria-pressed={active}
        className={cn(
          "flex min-h-11 w-full items-center justify-between gap-3 rounded-md border px-3 text-left text-sm",
          active
            ? "border-accent bg-accent/10 text-ink"
            : "border-transparent text-ink hover:border-line",
        )}
      >
        <span className="truncate font-data">{label}</span>
        <span className="shrink-0 text-xs text-muted">{detail}</span>
      </button>
    </li>
  );
}

function SelectionEditor({
  arrangement,
  selection,
  catalog,
  rig,
  rigIsCurrent,
  edit,
}: {
  arrangement: Arrangement;
  selection: Selection;
  catalog: Catalog | null;
  rig: CompiledRig | null;
  rigIsCurrent: boolean;
  edit: (next: Arrangement, key?: string) => void;
}) {
  const select = useDoc((s) => s.select);
  const pose = poseOf(arrangement, selection, rig?.fixtures);
  const group =
    selection.kind === "group"
      ? arrangement.groups.find((g) => g.id === selection.id)
      : undefined;
  const fixture =
    selection.kind === "fixture"
      ? arrangement.fixtures.find((f) => f.id === selection.id)
      : undefined;
  if (!group && !fixture) return null;

  const canExplode =
    group !== undefined &&
    rigIsCurrent &&
    (rig?.fixtures.some((f) => f.group === group.id) ?? false);
  const flipped = flip(arrangement, selection, rig?.fixtures);
  const endAttach = group?.preset === "array" ? group.attach : fixture?.attach;

  return (
    <section
      className="flex flex-col gap-4 rounded-md border border-line p-3"
      aria-label="Selection"
    >
      <div className="flex items-baseline justify-between gap-2">
        <SectionHeading>Selected</SectionHeading>
        <span className="truncate font-data text-sm">{selection.id}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => {
            const r = duplicate(arrangement, selection);
            if (r) {
              edit(r.arrangement);
              select(r.selection);
            }
          }}
        >
          Duplicate
        </Button>
        <Button
          disabled={!flipped}
          onClick={() => flipped && edit(flipped)}
          title="Swap the data-in and data-out ends"
        >
          Flip
        </Button>
        {group && (
          <Button
            disabled={!canExplode}
            title="Turn this group into free fixtures at their compiled poses"
            onClick={() => {
              const next =
                rig && explodeGroup(arrangement, group.id, rig.fixtures);
              if (next) {
                edit(next);
                select(null);
              }
            }}
          >
            Explode
          </Button>
        )}
        <Button
          variant="danger"
          onClick={() => {
            edit(remove(arrangement, selection));
            select(null);
          }}
        >
          Delete
        </Button>
      </div>

      {pose ? (
        <PoseInspector
          pose={pose}
          onChange={(next, field) =>
            edit(
              setPose(arrangement, selection, next),
              `pose:${selection.id}:${field}`,
            )
          }
        />
      ) : (
        <p className="text-sm text-muted">
          This group's rotation is an <span className="font-data">aim</span>,
          which only the server resolves. Explode it to edit its fixtures.
        </p>
      )}

      <Ends
        catalog={catalog}
        ends={
          group?.preset === "ring"
            ? [
                ["inner", "Inner end", group.attach?.inner ?? null],
                ["outer", "Outer end", group.attach?.outer ?? null],
              ]
            : [
                ["end_a", "Data-in end", endAttach?.end_a ?? null],
                ["end_b", "Data-out end", endAttach?.end_b ?? null],
              ]
        }
        onChange={(end, id) =>
          edit(setAttachment(arrangement, selection, end, id))
        }
      />

      {group?.preset === "ring" && (
        <RingEditor
          group={group}
          catalog={catalog}
          onChange={(patch, key) =>
            edit(
              updateGroup(arrangement, group.id, patch),
              `ring:${group.id}:${key}`,
            )
          }
        />
      )}
      {group?.preset === "array" && (
        <ArrayEditor
          group={group}
          catalog={catalog}
          onChange={(patch, key) =>
            edit(
              updateGroup(arrangement, group.id, patch),
              `array:${group.id}:${key}`,
            )
          }
        />
      )}
    </section>
  );
}

export function PoseInspector({
  pose,
  onChange,
}: {
  pose: PoseQ;
  onChange: (pose: PoseQ, field: string) => void;
}) {
  const ypr = quatToYpr(pose.quat_xyzw);
  const setPos = (i: number, v: number) => {
    const p = [...pose.position_m] as Vec3;
    p[i] = v;
    onChange({ ...pose, position_m: roundVec(p) }, `p${i}`);
  };
  const setRot = (field: keyof YawPitchRoll, v: number) =>
    onChange({ ...pose, quat_xyzw: yprToQuat({ ...ypr, [field]: v }) }, field);
  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-3 gap-2">
        {(["x", "y", "z"] as const).map((axis, i) => (
          <NumberField
            key={axis}
            label={axis}
            unit="m"
            step={0.01}
            decimals={4}
            value={pose.position_m[i]}
            onChange={(v) => setPos(i, v)}
          />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2">
        <NumberField
          label="Yaw"
          unit="° about Y"
          step={1}
          decimals={1}
          value={ypr.yaw}
          onChange={(v) => setRot("yaw", v)}
        />
        <NumberField
          label="Pitch"
          unit="° about X"
          step={1}
          decimals={1}
          value={ypr.pitch}
          onChange={(v) => setRot("pitch", v)}
        />
        <NumberField
          label="Roll"
          unit="° about Z"
          step={1}
          decimals={1}
          value={ypr.roll}
          onChange={(v) => setRot("roll", v)}
        />
      </div>
      <p className="text-xs text-muted">
        Turns apply yaw, then pitch, then roll, each about the fixture's own
        axes.
      </p>
    </div>
  );
}

function Ends({
  catalog,
  ends,
  onChange,
}: {
  catalog: Catalog | null;
  ends: Array<[End | RingEnd, string, AttachmentRef]>;
  onChange: (end: End | RingEnd, id: AttachmentRef) => void;
}) {
  const options = [
    { id: null, name: "None" },
    ...(catalog?.attachment_types ?? []).map((a) => ({
      id: a.id,
      name: a.name,
    })),
  ];
  return (
    <div className="flex flex-col gap-2">
      {ends.map(([end, label, current]) => (
        <div key={end} className="flex flex-col gap-1">
          <span className="text-xs text-muted">{label}</span>
          <fieldset
            className="flex flex-wrap overflow-hidden rounded-md border border-line"
            aria-label={label}
          >
            {options.map((o) => (
              <button
                key={o.id ?? "none"}
                type="button"
                aria-pressed={current === o.id}
                onClick={() => onChange(end, o.id)}
                className={cn(
                  "min-h-11 flex-1 px-3 text-sm not-first:border-l not-first:border-line",
                  current === o.id
                    ? "bg-ink text-surface"
                    : "text-ink hover:bg-bg",
                )}
              >
                {o.name}
              </button>
            ))}
          </fieldset>
        </div>
      ))}
    </div>
  );
}

function TypeSelect({
  catalog,
  value,
  onChange,
}: {
  catalog: Catalog | null;
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <Select
      label="Fixture type"
      value={value}
      options={fixtureTypes(catalog).map((t) => ({
        value: t.id,
        label: t.name,
      }))}
      onChange={onChange}
    />
  );
}

function RingEditor({
  group,
  catalog,
  onChange,
}: {
  group: RingGroup;
  catalog: Catalog | null;
  onChange: (patch: Partial<Group>, key: string) => void;
}) {
  return (
    <section className="flex flex-col gap-2" aria-label="Ring">
      <SectionHeading>Ring</SectionHeading>
      <TypeSelect
        catalog={catalog}
        value={group.type}
        onChange={(type) => onChange({ type }, "type")}
      />
      <div className="grid grid-cols-2 gap-2">
        <NumberField
          label="Count"
          integer
          step={1}
          min={1}
          max={360}
          value={group.count}
          onChange={(count) => onChange({ count }, "count")}
        />
        <NumberField
          label="Start radius"
          unit="m"
          step={0.01}
          min={0}
          decimals={6}
          value={group.start_radius_m}
          onChange={(start_radius_m) =>
            onChange({ start_radius_m }, "start_radius_m")
          }
        />
        <NumberField
          label="Angle offset"
          unit="°"
          step={0.5}
          decimals={2}
          value={group.angle_offset_deg ?? 0}
          onChange={(angle_offset_deg) =>
            onChange({ angle_offset_deg }, "angle_offset_deg")
          }
        />
        <NumberField
          label="Tilt"
          unit="°"
          step={1}
          min={-90}
          max={90}
          decimals={2}
          value={group.tilt_deg ?? 0}
          onChange={(tilt_deg) => onChange({ tilt_deg }, "tilt_deg")}
        />
        <NumberField
          label="Roll"
          unit="° about the bar"
          step={1}
          decimals={2}
          value={group.roll_deg ?? 0}
          onChange={(roll_deg) => onChange({ roll_deg }, "roll_deg")}
        />
        <Select<DataIn>
          label="Data in"
          value={group.data_in ?? "inner"}
          options={[
            { value: "inner", label: "Inner end" },
            { value: "outer", label: "Outer end" },
          ]}
          onChange={(data_in) => onChange({ data_in }, "data_in")}
        />
      </div>
    </section>
  );
}

function ArrayEditor({
  group,
  catalog,
  onChange,
}: {
  group: ArrayGroup;
  catalog: Catalog | null;
  onChange: (patch: Partial<Group>, key: string) => void;
}) {
  const [n, m] = group.counts;
  const steps = group.steps_m;
  const memberPose = resolvePose(group.member);
  const member = memberPose ? quatToYpr(memberPose.quat_xyzw) : null;
  const setStep = (row: number, i: number, v: number) => {
    const next = steps.map((s) => [...s] as Vec3);
    while (next.length <= row) next.push([0, 0, 0]);
    next[row][i] = v;
    onChange({ steps_m: next }, `step${row}${i}`);
  };
  const setCounts = (a: number, b: number) =>
    onChange(
      b > 1
        ? {
            counts: [a, b],
            steps_m:
              steps.length > 1 ? steps : [steps[0] ?? [0.1, 0, 0], [0, 0, 0.1]],
          }
        : { counts: [a], steps_m: [steps[0] ?? [0.1, 0, 0]] },
      "counts",
    );
  return (
    <section className="flex flex-col gap-2" aria-label="Array">
      <SectionHeading>Array</SectionHeading>
      <TypeSelect
        catalog={catalog}
        value={group.type}
        onChange={(type) => onChange({ type }, "type")}
      />
      <div className="grid grid-cols-2 gap-2">
        <NumberField
          label="Count"
          integer
          step={1}
          min={1}
          max={200}
          value={n}
          onChange={(v) => setCounts(v, m ?? 1)}
        />
        <NumberField
          label="Rows"
          integer
          step={1}
          min={1}
          max={200}
          value={m ?? 1}
          onChange={(v) => setCounts(n, v)}
        />
      </div>
      {[0, ...(m && m > 1 ? [1] : [])].map((row) => (
        <div key={row} className="grid grid-cols-3 gap-2">
          {(["x", "y", "z"] as const).map((axis, i) => (
            <NumberField
              key={axis}
              label={`${row === 0 ? "Step" : "Row step"} ${axis}`}
              unit="m"
              step={0.01}
              decimals={4}
              value={steps[row]?.[i] ?? 0}
              onChange={(v) => setStep(row, i, v)}
            />
          ))}
        </div>
      ))}
      {memberPose && member ? (
        <div className="grid grid-cols-3 gap-2">
          {(["yaw", "pitch", "roll"] as const).map((field) => (
            <NumberField
              key={field}
              label={`Member ${field}`}
              unit="°"
              step={1}
              decimals={1}
              value={member[field]}
              onChange={(v) =>
                onChange(
                  {
                    member: {
                      ...memberPose,
                      quat_xyzw: yprToQuat({ ...member, [field]: v }),
                    },
                  },
                  `member-${field}`,
                )
              }
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">
          The member rotation is an <span className="font-data">aim</span>; edit
          it in the file.
        </p>
      )}
    </section>
  );
}
