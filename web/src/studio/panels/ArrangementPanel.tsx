import { Block } from "../../design/Block";
import { Button } from "../../design/Button";
import { Field, SelectField } from "../../design/Field";
import { Segments } from "../../design/Segments";
import { Tile } from "../../design/Tile";
import { NumberField, type NumberRange } from "../../params/NumberField";
import { useRef } from "react";
import { ApiError } from "../api/client";
import { compileArrangement } from "../api/endpoints";
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
} from "../api/types";
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
} from "../editor/arrangement";
import {
  type PoseQ,
  quatToYpr,
  resolvePose,
  roundVec,
  type YawPitchRoll,
  yprToQuat,
} from "../editor/pose";
import { useDoc } from "../store/doc";

const DEFAULT_TYPE = "clen-rgbw-bar-1m";

/** A position or a step, in meters. */
const METERS: NumberRange = {
  lo: -100,
  hi: 100,
  step: 0.01,
  decimals: 4,
  unit: "m",
  periodic: false,
};
/** A turn, in degrees, which wraps past a half turn either way. */
const DEGREES: NumberRange = {
  lo: -180,
  hi: 180,
  step: 1,
  decimals: 1,
  unit: "°",
  periodic: true,
};
/** A count of 1 to `hi`. */
const count = (hi: number): NumberRange => ({
  lo: 1,
  hi,
  step: 1,
  decimals: 0,
  unit: "",
  periodic: false,
});

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
  const commit = useDoc((s) => s.commit);
  const undo = useDoc((s) => s.undo);
  const redo = useDoc((s) => s.redo);
  const select = useDoc((s) => s.select);
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
      type: types[0]!.id,
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
      type: types[0]!.id,
      counts: [4],
      steps_m: [[0.1, 0, 0]],
      pose: { position_m: [0, 0.5, 0], quat_xyzw: [0, 0, 0, 1] },
    };
    addGroup(group);
  };

  return (
    <div className="studio-panel">
      <div className="block fields">
        <Field label="Name">
          <input
            value={arrangement.name ?? ""}
            onChange={(e) =>
              commit({ ...arrangement, name: e.target.value }, "name")
            }
            placeholder="Untitled arrangement"
          />
        </Field>
        <div className="row wrap">
          <Button onPress={undo} disabled={!canUndo} title="Undo (⌘Z)">
            Undo
          </Button>
          <Button onPress={redo} disabled={!canRedo} title="Redo (⇧⌘Z)">
            Redo
          </Button>
          <Button
            onPress={exportJson}
            title="Download this arrangement as JSON"
          >
            Export
          </Button>
          <Button
            onPress={() => fileInput.current?.click()}
            title="Open an arrangement JSON file"
          >
            Import
          </Button>
          <input
            ref={fileInput}
            type="file"
            accept="application/json,.json"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void importJson(file);
            }}
          />
        </div>
      </div>

      <Block className="fields" title="Add">
        <div className="row wrap">
          <Button
            onPress={() => {
              const { arrangement: next, id } = addFixture(
                arrangement,
                types[0]!.id,
              );
              commit(next);
              select({ kind: "fixture", id });
            }}
          >
            Bar
          </Button>
          <Button onPress={addRing}>Ring</Button>
          <Button onPress={addArray}>Array</Button>
        </div>
      </Block>

      <Block className="fields" title="Fixtures">
        <ul className="studio-entities" data-testid="entity-list">
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
            <li className="t-label">
              Nothing yet. Add a bar, a ring or an array.
            </li>
          )}
        </ul>
      </Block>

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
      <Tile
        name={label}
        flat
        selected={active}
        aria-pressed={active}
        onPress={onClick}
      >
        <span className="t-caption">{detail}</span>
      </Tile>
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
    <Block className="fields" title={`Selected · ${selection.id}`}>
      <div className="row wrap">
        <Button
          onPress={() => {
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
          onPress={() => flipped && edit(flipped)}
          title="Swap the data-in and data-out ends"
        >
          Flip
        </Button>
        {group && (
          <Button
            disabled={!canExplode}
            title="Turn this group into free fixtures at their compiled poses"
            onPress={() => {
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
          tone="danger"
          onPress={() => {
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
        <p className="t-label">
          This group's rotation is an <span className="t-code">aim</span>, which
          only the server resolves. Explode it to edit its fixtures.
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
    </Block>
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
    <>
      {(["x", "y", "z"] as const).map((axis, i) => (
        <NumberField
          key={axis}
          label={axis}
          range={METERS}
          value={pose.position_m[i]!}
          onChange={(v) => setPos(i, v)}
        />
      ))}
      <NumberField
        label="Yaw, about Y"
        range={DEGREES}
        value={ypr.yaw}
        onChange={(v) => setRot("yaw", v)}
      />
      <NumberField
        label="Pitch, about X"
        range={DEGREES}
        value={ypr.pitch}
        onChange={(v) => setRot("pitch", v)}
      />
      <NumberField
        label="Roll, about Z"
        range={DEGREES}
        value={ypr.roll}
        onChange={(v) => setRot("roll", v)}
      />
      <p className="note">
        Turns apply yaw, then pitch, then roll, each about the fixture's own
        axes.
      </p>
    </>
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
  // "" stands for a bare end.
  const items = [
    { value: "", label: "None" },
    ...(catalog?.attachment_types ?? []).map((a) => ({
      value: a.id,
      label: a.name,
    })),
  ];
  return ends.map(([end, label, current]) => (
    <div key={end} className="field">
      <span className="field-label">{label}</span>
      <Segments
        label={label}
        items={items}
        value={current ?? ""}
        onChange={(id) => onChange(end, id || null)}
      />
    </div>
  ));
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
    <SelectField
      label="Fixture type"
      value={value}
      items={fixtureTypes(catalog).map((t) => ({
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
    <Block className="fields" title="Ring">
      <TypeSelect
        catalog={catalog}
        value={group.type}
        onChange={(type) => onChange({ type }, "type")}
      />
      <NumberField
        label="Count"
        range={count(360)}
        value={group.count}
        onChange={(count) => onChange({ count }, "count")}
      />
      <NumberField
        label="Start radius"
        range={{ ...METERS, lo: 0, decimals: 6 }}
        value={group.start_radius_m}
        onChange={(start_radius_m) =>
          onChange({ start_radius_m }, "start_radius_m")
        }
      />
      <NumberField
        label="Angle offset"
        range={{ ...DEGREES, step: 0.5, decimals: 2 }}
        value={group.angle_offset_deg ?? 0}
        onChange={(angle_offset_deg) =>
          onChange({ angle_offset_deg }, "angle_offset_deg")
        }
      />
      <NumberField
        label="Tilt"
        range={{ ...DEGREES, lo: -90, hi: 90, decimals: 2, periodic: false }}
        value={group.tilt_deg ?? 0}
        onChange={(tilt_deg) => onChange({ tilt_deg }, "tilt_deg")}
      />
      <NumberField
        label="Roll, about the bar"
        range={{ ...DEGREES, decimals: 2 }}
        value={group.roll_deg ?? 0}
        onChange={(roll_deg) => onChange({ roll_deg }, "roll_deg")}
      />
      <SelectField<DataIn>
        label="Data in"
        value={group.data_in ?? "inner"}
        items={[
          { value: "inner", label: "Inner end" },
          { value: "outer", label: "Outer end" },
        ]}
        onChange={(data_in) => onChange({ data_in }, "data_in")}
      />
    </Block>
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
    next[row]![i] = v;
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
    <Block className="fields" title="Array">
      <TypeSelect
        catalog={catalog}
        value={group.type}
        onChange={(type) => onChange({ type }, "type")}
      />
      <NumberField
        label="Count"
        range={count(200)}
        value={n}
        onChange={(v) => setCounts(v, m ?? 1)}
      />
      <NumberField
        label="Rows"
        range={count(200)}
        value={m ?? 1}
        onChange={(v) => setCounts(n, v)}
      />
      {[0, ...(m && m > 1 ? [1] : [])].flatMap((row) =>
        (["x", "y", "z"] as const).map((axis, i) => (
          <NumberField
            key={`${row}${axis}`}
            label={`${row === 0 ? "Step" : "Row step"} ${axis}`}
            range={METERS}
            value={steps[row]?.[i] ?? 0}
            onChange={(v) => setStep(row, i, v)}
          />
        )),
      )}
      {memberPose && member ? (
        (["yaw", "pitch", "roll"] as const).map((field) => (
          <NumberField
            key={field}
            label={`Member ${field}`}
            range={DEGREES}
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
        ))
      ) : (
        <p className="t-label">
          The member rotation is an <span className="t-code">aim</span>; edit it
          in the file.
        </p>
      )}
    </Block>
  );
}
