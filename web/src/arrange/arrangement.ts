/**
 * Edits to an arrangement. Each returns a new arrangement and leaves the
 * input untouched.
 *
 * None of these expand presets or place pixels: the engine does that on
 * compile. `explodeGroup` reads the member matrices the engine compiled.
 */
import type {
  Arrangement,
  AttachmentRef,
  FixtureEntry,
  Group,
  PowerLimit,
} from "./types";
import {
  flipPose,
  IDENTITY_POSE,
  matrixPose,
  type PoseQ,
  resolvePose,
} from "./pose";

/** A fixture as the engine compiled it: the studio's compile body's, or the `rig` of the Console's
 * `hello` and `layout`. */
export interface Placed {
  readonly id: string;
  readonly type_id: string;
  readonly base_type_id: string;
  /** Absent in a compile from before the field: the group is then the `group/k` the id names. */
  readonly group?: string | null;
  /** The world matrix, 16 numbers column-major. */
  readonly matrix: readonly number[];
  readonly tags: readonly string[];
  readonly dims: Readonly<Record<string, number>>;
  readonly attachments: Readonly<Record<string, string | null>>;
}

export type Selection =
  | { kind: "fixture"; id: string }
  | { kind: "group"; id: string };

export type End = "end_a" | "end_b";
export type RingEnd = "inner" | "outer";

export { IDENTITY_POSE };

/** The group a compiled fixture came from: its `group`, else the `group/k` its id names. */
export function groupOf(f: Placed): string | null {
  if (f.group !== undefined) return f.group;
  const slash = f.id.lastIndexOf("/");
  return slash > 0 ? f.id.slice(0, slash) : null;
}

/** The arrangement entity a compiled fixture came from. */
export function entityOf(
  arrangement: Arrangement,
  fixture: Placed,
): Selection | null {
  const group = groupOf(fixture);
  if (group && arrangement.groups.some((g) => g.id === group)) {
    return { kind: "group", id: group };
  }
  if (arrangement.fixtures.some((f) => f.id === fixture.id)) {
    return { kind: "fixture", id: fixture.id };
  }
  return null;
}

/** Compiled fixture indices that belong to a selection. */
export function fixturesOf(
  fixtures: readonly Placed[],
  selection: Selection | null,
): number[] {
  if (!selection) return [];
  const out: number[] = [];
  fixtures.forEach((f, i) => {
    if (
      selection.kind === "fixture"
        ? f.id === selection.id && !groupOf(f)
        : groupOf(f) === selection.id
    ) {
      out.push(i);
    }
  });
  return out;
}

function takenIds(arrangement: Arrangement): Set<string> {
  return new Set([
    ...arrangement.fixtures.map((f) => f.id),
    ...arrangement.groups.map((g) => g.id),
  ]);
}

/** `base`, or `base-2`, `base-3`… whichever is free. */
export function freshId(arrangement: Arrangement, base: string): string {
  const taken = takenIds(arrangement);
  const stem = base.replace(/-\d+$/, "") || "fixture";
  if (!taken.has(base)) return base;
  for (let k = 2; ; k++) {
    const id = `${stem}-${k}`;
    if (!taken.has(id)) return id;
  }
}

/**
 * The selection's pose with defaults filled in. A free fixture placed by
 * `aim` reads its rotation from the engine's matrix; a group placed by
 * `aim` has no editable pose, so this returns null.
 */
export function poseOf(
  arrangement: Arrangement,
  selection: Selection,
  compiled: readonly Placed[] = [],
): PoseQ | null {
  if (selection.kind === "group") {
    const g = arrangement.groups.find((e) => e.id === selection.id);
    return g ? resolvePose(g.pose) : null;
  }
  const f = arrangement.fixtures.find((e) => e.id === selection.id);
  if (!f) return null;
  const resolved = resolvePose(f.pose);
  if (resolved) return resolved;
  const m = compiled.find((c) => c.id === f.id && !groupOf(c));
  return m ? matrixPose(m.matrix) : null;
}

/** Write a pose as position and quaternion; any `aim` it had is replaced. */
export function setPose(
  arrangement: Arrangement,
  selection: Selection,
  pose: PoseQ,
): Arrangement {
  if (selection.kind === "fixture") {
    return {
      ...arrangement,
      fixtures: arrangement.fixtures.map((f) =>
        f.id === selection.id ? { ...f, pose } : f,
      ),
    };
  }
  return {
    ...arrangement,
    groups: arrangement.groups.map((g) =>
      g.id === selection.id ? { ...g, pose } : g,
    ),
  };
}

export function addFixture(
  arrangement: Arrangement,
  type: string,
  pose: PoseQ = { position_m: [0, 0.5, 0], quat_xyzw: [0, 0, 0, 1] },
): { arrangement: Arrangement; id: string } {
  const id = freshId(arrangement, "bar-1");
  const fixture: FixtureEntry = { id, type, pose };
  return {
    arrangement: {
      ...arrangement,
      fixtures: [...arrangement.fixtures, fixture],
    },
    id,
  };
}

const OFFSET_M = 0.1;

function offset<P extends { position_m?: [number, number, number] }>(
  pose: P | undefined,
): P {
  const [x, y, z] = pose?.position_m ?? [0, 0, 0];
  return {
    ...(pose as P),
    position_m: [Math.round((x + OFFSET_M) * 1e4) / 1e4, y, z],
  };
}

export function duplicate(
  arrangement: Arrangement,
  selection: Selection,
): { arrangement: Arrangement; selection: Selection } | null {
  if (selection.kind === "fixture") {
    const src = arrangement.fixtures.find((f) => f.id === selection.id);
    if (!src) return null;
    const id = freshId(arrangement, src.id);
    const copy: FixtureEntry = structuredClone({
      ...src,
      id,
      pose: offset(src.pose),
    });
    return {
      arrangement: {
        ...arrangement,
        fixtures: [...arrangement.fixtures, copy],
      },
      selection: { kind: "fixture", id },
    };
  }
  const src = arrangement.groups.find((g) => g.id === selection.id);
  if (!src) return null;
  const id = freshId(arrangement, src.id);
  const copy: Group = structuredClone({ ...src, id, pose: offset(src.pose) });
  return {
    arrangement: { ...arrangement, groups: [...arrangement.groups, copy] },
    selection: { kind: "group", id },
  };
}

/** A chain of `wiring.chains`, as far as the editor reads it. */
interface ChainRef {
  id?: unknown;
  fixtures?: unknown;
}

/** A feed of `wiring.feeds`: it powers `count` fixtures of `chain` from index `first`. */
interface FeedRef {
  chain?: unknown;
  first?: unknown;
  count?: unknown;
}

/** `wiring` without the fixtures `gone` matches: each chain loses them (a chain left with none goes, as a
 * chain names at least one), and each feed keeps the fixtures it powered that are left, or goes with none. */
function unwire(wiring: Arrangement["wiring"], gone: (id: string) => boolean): Arrangement["wiring"] {
  if (!wiring || !Array.isArray(wiring.chains)) return wiring;
  const chains: ChainRef[] = wiring.chains;
  // Per chain id: how many fixtures it keeps, and for each old index, how many before it went.
  const kept = new Map<unknown, { left: number; before: number[] }>();
  let changed = false;
  const nextChains = chains.flatMap((c) => {
    if (!Array.isArray(c?.fixtures)) return [c];
    const before: number[] = [];
    let removed = 0;
    const fixtures = c.fixtures.filter((id: unknown) => {
      before.push(removed);
      const drop = typeof id === "string" && gone(id);
      if (drop) removed++;
      return !drop;
    });
    before.push(removed);
    kept.set(c.id, { left: fixtures.length, before });
    if (removed === 0) return [c];
    changed = true;
    return fixtures.length ? [{ ...c, fixtures }] : [];
  });
  if (!changed) return wiring;
  const feeds = Array.isArray(wiring.feeds)
    ? wiring.feeds.flatMap((f: FeedRef) => {
        const k = kept.get(f?.chain);
        if (!k || typeof f.first !== "number" || typeof f.count !== "number") return [f];
        if (k.left === 0) return [];
        // How many went before index `i`; an index past the chain's end counts every one that went.
        const went = (i: number) => k.before[Math.min(Math.max(i, 0), k.before.length - 1)]!;
        const first = f.first - went(f.first);
        const count = f.count - (went(f.first + f.count) - went(f.first));
        if (count <= 0) return [];
        return first === f.first && count === f.count ? [f] : [{ ...f, first, count }];
      })
    : wiring.feeds;
  return { ...wiring, chains: nextChains, ...(feeds !== undefined && { feeds }) };
}

/**
 * Delete a fixture or a group, and every reference to it: a chain lists it no more (a chain left empty
 * goes), and a feed powers what is left of its run (a feed left with none goes). A group's members are
 * its `group/k` fixtures.
 */
export function remove(
  arrangement: Arrangement,
  selection: Selection,
): Arrangement {
  const prefix = `${selection.id}/`;
  const gone = selection.kind === "fixture" ? (id: string) => id === selection.id : (id: string) => id.startsWith(prefix);
  const wiring = unwire(arrangement.wiring, gone);
  const rest = selection.kind === "fixture"
    ? {
        ...arrangement,
        fixtures: arrangement.fixtures.filter((f) => f.id !== selection.id),
      }
    : {
        ...arrangement,
        groups: arrangement.groups.filter((g) => g.id !== selection.id),
      };
  return wiring === arrangement.wiring ? rest : { ...rest, wiring };
}

function swapEnds(attach: FixtureEntry["attach"]): FixtureEntry["attach"] {
  if (!attach) return attach;
  const { end_a = null, end_b = null, ...rest } = attach;
  return { ...rest, end_a: end_b, end_b: end_a };
}

/**
 * Reverse the data direction. A free fixture turns half a turn about its
 * LED facing and its attachments swap ends so they stay where they were; a
 * ring swaps `data_in`; an array does the fixture's flip to its `member`
 * pose. Returns null when the pose is an `aim` the editor cannot turn.
 */
export function flip(
  arrangement: Arrangement,
  selection: Selection,
  compiled: readonly Placed[] = [],
): Arrangement | null {
  if (selection.kind === "fixture") {
    const pose = poseOf(arrangement, selection, compiled);
    if (!pose) return null;
    return {
      ...arrangement,
      fixtures: arrangement.fixtures.map((f) =>
        f.id === selection.id
          ? { ...f, pose: flipPose(pose), attach: swapEnds(f.attach) }
          : f,
      ),
    };
  }
  const g = arrangement.groups.find((e) => e.id === selection.id);
  if (!g) return null;
  let next: Group;
  if (g.preset === "ring") {
    next = {
      ...g,
      data_in: (g.data_in ?? "inner") === "inner" ? "outer" : "inner",
    };
  } else {
    const member = resolvePose(g.member);
    if (!member) return null;
    next = { ...g, member: flipPose(member), attach: swapEnds(g.attach) };
  }
  return {
    ...arrangement,
    groups: arrangement.groups.map((e) => (e.id === g.id ? next : e)),
  };
}

/** Set what sits on one end; `end` is `end_a`/`end_b` for fixtures and arrays, `inner`/`outer` for rings. */
export function setAttachment(
  arrangement: Arrangement,
  selection: Selection,
  end: End | RingEnd,
  attachment: AttachmentRef,
): Arrangement {
  if (selection.kind === "fixture") {
    return {
      ...arrangement,
      fixtures: arrangement.fixtures.map((f) =>
        f.id === selection.id
          ? { ...f, attach: { ...f.attach, [end]: attachment } }
          : f,
      ),
    };
  }
  return {
    ...arrangement,
    groups: arrangement.groups.map((g) =>
      g.id === selection.id
        ? ({ ...g, attach: { ...g.attach, [end]: attachment } } as Group)
        : g,
    ),
  };
}

export function updateGroup(
  arrangement: Arrangement,
  id: string,
  patch: Partial<Group>,
): Arrangement {
  return {
    ...arrangement,
    groups: arrangement.groups.map((g) =>
      g.id === id ? ({ ...g, ...patch } as Group) : g,
    ),
  };
}

/**
 * Replace a group with free fixtures at the poses the engine compiled for
 * its members. Returns null when `compiled` holds no members of the group.
 */
export function explodeGroup(
  arrangement: Arrangement,
  groupId: string,
  compiled: readonly Placed[],
): Arrangement | null {
  const group = arrangement.groups.find((g) => g.id === groupId);
  if (!group) return null;
  const members = compiled.filter((f) => groupOf(f) === groupId);
  if (members.length === 0) return null;
  let next: Arrangement = {
    ...arrangement,
    groups: arrangement.groups.filter((g) => g.id !== groupId),
  };
  for (const m of members) {
    const id = freshId(next, m.id.replace(/\//g, "-"));
    const fixture: FixtureEntry = {
      id,
      type: m.base_type_id ?? m.type_id,
      pose: matrixPose(m.matrix),
    };
    if (m.dims && Object.keys(m.dims).length) fixture.dims = { ...m.dims };
    if (m.tags?.length) fixture.tags = [...m.tags];
    if (Object.values(m.attachments ?? {}).some(Boolean)) {
      fixture.attach = { ...m.attachments };
    }
    next = { ...next, fixtures: [...next.fixtures, fixture] };
  }
  return next;
}

const isObjectList = (v: unknown) =>
  Array.isArray(v) &&
  v.every((x) => x !== null && typeof x === "object" && !Array.isArray(x));

/**
 * A light check that parsed JSON is an arrangement file: its format, and
 * fixtures and groups as lists of objects. The engine validates the rest.
 */
export function asArrangement(value: unknown): Arrangement | null {
  if (!value || typeof value !== "object") return null;
  const v = value as Partial<Arrangement>;
  if (v.format !== "pewpew.arrangement" || typeof v.version !== "number")
    return null;
  const fixtures = v.fixtures ?? [];
  const groups = v.groups ?? [];
  if (!isObjectList(fixtures) || !isObjectList(groups)) return null;
  return { ...v, fixtures, groups } as Arrangement;
}

/** A power cap with every field given. */
export interface PowerCap {
  max_watts: number | null;
  max_brightness: number;
}

/** The arrangement's power cap, with the defaults that cap nothing filled in. */
export function powerOf(arrangement: Arrangement): PowerCap {
  return {
    max_watts: arrangement.power?.max_watts ?? null,
    max_brightness: arrangement.power?.max_brightness ?? 1,
  };
}

/**
 * The arrangement with its power cap set. Each default value is left out,
 * and a cap that caps nothing removes the block, so an uncapped rig keeps
 * the file it had.
 */
export function setPower(arrangement: Arrangement, cap: PowerCap): Arrangement {
  const { power: _old, ...rest } = arrangement;
  const power: PowerLimit = {};
  if (cap.max_watts !== null) power.max_watts = cap.max_watts;
  if (cap.max_brightness !== 1) power.max_brightness = cap.max_brightness;
  return Object.keys(power).length ? { ...rest, power } : rest;
}
