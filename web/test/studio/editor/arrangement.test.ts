import { describe, expect, it } from "vitest";
import type { Arrangement, CompiledFixture, RingGroup } from "../../../src/studio/api/types";
import { compiledFixture, stubCompile, threeBarRig } from "../fixtures/rig";
import { DEFAULT_ARRANGEMENT } from "../../../src/studio/store/doc";
import {
  addFixture,
  asArrangement,
  duplicate,
  entityOf,
  explodeGroup,
  fixturesOf,
  flip,
  freshId,
  poseOf,
  powerOf,
  remove,
  setAttachment,
  setPower,
} from "../../../src/studio/editor/arrangement";
import { matrixPose } from "../../../src/rig3d/pose";

const withBar = (): Arrangement => ({
  ...DEFAULT_ARRANGEMENT,
  fixtures: [
    {
      id: "bar-1",
      type: "clen-rgbw-bar-1m",
      pose: { position_m: [0, 0.5, 0], quat_xyzw: [0, 0, 0, 1] },
      attach: { end_a: "point-v0", end_b: null },
    },
  ],
});

describe("selection mapping", () => {
  it("maps compiled fixtures to free fixtures and to their groups", () => {
    const a = withBar();
    const rig = stubCompile(a);
    expect(entityOf(a, rig.fixtures[48]!)).toEqual({
      kind: "fixture",
      id: "bar-1",
    });
    expect(entityOf(a, rig.fixtures[3]!)).toEqual({
      kind: "group",
      id: "inner",
    });
    expect(entityOf(a, { ...rig.fixtures[3]!, group: "nope" })).toBeNull();
    // A rig without `group` falls back to the `group/k` id.
    expect(entityOf(a, { ...rig.fixtures[30]!, group: undefined } as unknown as CompiledFixture)).toEqual({
      kind: "group",
      id: "outer",
    });
  });

  it("finds every compiled member of a group", () => {
    const rig = stubCompile(withBar());
    expect(
      fixturesOf(rig.fixtures, { kind: "group", id: "outer" }),
    ).toHaveLength(24);
    expect(fixturesOf(rig.fixtures, { kind: "fixture", id: "bar-1" })).toEqual([
      48,
    ]);
    expect(fixturesOf(rig.fixtures, null)).toEqual([]);
  });
});

describe("edits", () => {
  it("adds bars with fresh ids", () => {
    const a1 = addFixture(DEFAULT_ARRANGEMENT, "clen-rgbw-bar-1m");
    const a2 = addFixture(a1.arrangement, "clen-rgbw-bar-1m");
    expect([a1.id, a2.id]).toEqual(["bar-1", "bar-2"]);
    expect(freshId(a2.arrangement, "inner")).toBe("inner-2");
  });

  it("duplicates beside the original and selects the copy", () => {
    const r = duplicate(withBar(), { kind: "fixture", id: "bar-1" });
    expect(r?.selection).toEqual({ kind: "fixture", id: "bar-2" });
    expect(r?.arrangement.fixtures[1]?.pose?.position_m).toEqual([0.1, 0.5, 0]);
    expect(r?.arrangement.fixtures[1]?.attach).toEqual({
      end_a: "point-v0",
      end_b: null,
    });
    const g = duplicate(DEFAULT_ARRANGEMENT, { kind: "group", id: "inner" });
    expect(g?.arrangement.groups.map((x) => x.id)).toEqual([
      "inner",
      "outer",
      "inner-2",
    ]);
  });

  it("deletes", () => {
    expect(
      remove(withBar(), { kind: "fixture", id: "bar-1" }).fixtures,
    ).toEqual([]);
    expect(
      remove(DEFAULT_ARRANGEMENT, { kind: "group", id: "inner" }).groups.map(
        (g) => g.id,
      ),
    ).toEqual(["outer"]);
  });

  it("flips a bar's data direction and keeps its end pieces where they were", () => {
    const flipped = flip(withBar(), { kind: "fixture", id: "bar-1" })
      ?.fixtures[0];
    expect(flipped?.attach).toEqual({ end_a: null, end_b: "point-v0" });
    expect(flipped?.pose).toEqual({
      position_m: [0, 0.5, 0],
      quat_xyzw: [0, 0, 1, 0],
    });
  });

  it("flips a ring by swapping data_in, which defaults to inner", () => {
    const g = flip(DEFAULT_ARRANGEMENT, { kind: "group", id: "inner" })
      ?.groups[0] as RingGroup;
    expect(g.data_in).toBe("outer");
    expect(g.attach).toEqual({ inner: "point-v0", outer: "eye-v0" });
  });

  it("flips an array's member pose", () => {
    const a: Arrangement = {
      ...DEFAULT_ARRANGEMENT,
      groups: [
        {
          id: "row",
          preset: "array",
          type: "clen-rgbw-bar-1m",
          counts: [3],
          steps_m: [[0.1, 0, 0]],
          attach: { end_a: "point-v0" },
        },
      ],
    };
    const g = flip(a, { kind: "group", id: "row" })?.groups[0];
    expect(g).toMatchObject({
      member: { position_m: [0, 0, 0], quat_xyzw: [0, 0, 1, 0] },
      attach: { end_a: null, end_b: "point-v0" },
    });
  });

  it("reads an aimed fixture's rotation from the server and refuses to flip an aimed group", () => {
    const aimed: Arrangement = {
      ...DEFAULT_ARRANGEMENT,
      fixtures: [
        {
          id: "a",
          type: "clen-rgbw-bar-1m",
          pose: { aim: { axis: [1, 0, 0] } },
        },
      ],
    };
    const compiled = [
      {
        ...threeBarRig.fixtures[1]!,
        id: "a",
        group: null,
      },
    ];
    expect(
      poseOf(aimed, { kind: "fixture", id: "a" }, compiled)?.position_m,
    ).toEqual([0, 1.2, 0]);
    expect(poseOf(aimed, { kind: "fixture", id: "a" })).toBeNull();
    const aimedGroup: Arrangement = {
      ...DEFAULT_ARRANGEMENT,
      groups: [
        {
          ...DEFAULT_ARRANGEMENT.groups[0],
          preset: "array",
          counts: [2],
          steps_m: [[1, 0, 0]],
          member: { aim: { axis: [1, 0, 0] } },
        } as Arrangement["groups"][number],
      ],
    };
    expect(flip(aimedGroup, { kind: "group", id: "inner" })).toBeNull();
  });

  it("sets what sits on an end", () => {
    const a = setAttachment(
      withBar(),
      { kind: "fixture", id: "bar-1" },
      "end_b",
      "eye-v0",
    );
    expect(a.fixtures[0]?.attach).toEqual({
      end_a: "point-v0",
      end_b: "eye-v0",
    });
    const r = setAttachment(
      DEFAULT_ARRANGEMENT,
      { kind: "group", id: "outer" },
      "inner",
      null,
    );
    expect((r.groups[1] as RingGroup).attach).toEqual({
      inner: null,
      outer: "eye-v0",
    });
  });
});

describe("explodeGroup", () => {
  it("replaces a group with free fixtures at the server's member poses", () => {
    const rig = stubCompile(DEFAULT_ARRANGEMENT);
    const next = explodeGroup(DEFAULT_ARRANGEMENT, "inner", rig.fixtures);
    expect(next?.groups.map((g) => g.id)).toEqual(["outer"]);
    expect(next?.fixtures).toHaveLength(24);
    const first = next?.fixtures[0];
    expect(first?.id).toBe("inner-0");
    expect(first?.attach).toEqual({ end_a: "point-v0", end_b: "eye-v0" });
    expect(first?.pose).toEqual(matrixPose(rig.fixtures[0]!.matrix));
    // The exploded rig draws the same bars in the same places.
    const again = stubCompile(next as Arrangement);
    const before = rig.fixtures.filter((f) => f.id.startsWith("inner/"));
    const after = again.fixtures.filter((f) => f.id.startsWith("inner-"));
    after.forEach((f, k) => {
      f.matrix.forEach((v, i) => {
        expect(v).toBeCloseTo(before[k]!.matrix[i]!, 6);
      });
    });
  });

  it("writes the base type, dims and tags of a variant member", () => {
    const group: Arrangement = {
      ...DEFAULT_ARRANGEMENT,
      fixtures: [],
      groups: [
        {
          id: "row",
          preset: "array",
          type: "strip",
          counts: [2],
          steps_m: [[1, 0, 0]],
        },
      ],
    };
    const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    const members = [0, 1].map((i) => compiledFixture({
      id: `row/${i}`,
      type_id: "strip.1a2b3c4d",
      base_type_id: "strip",
      dims: { pixels: 8 },
      tags: ["canopy"],
      group: "row",
      matrix: identity,
      attachments: {},
      pixel_start: i * 8,
      pixel_count: 8,
    }));
    const next = explodeGroup(group, "row", members);
    expect(next?.fixtures).toHaveLength(2);
    for (const f of next?.fixtures ?? []) {
      expect(f.type).toBe("strip");
      expect(f.dims).toEqual({ pixels: 8 });
      expect(f.tags).toEqual(["canopy"]);
    }
    expect(JSON.stringify(next)).not.toContain("strip.1a2b3c4d");
  });

  it("returns null without compiled members", () => {
    expect(explodeGroup(DEFAULT_ARRANGEMENT, "inner", [])).toBeNull();
  });
});

describe("asArrangement", () => {
  it("accepts an arrangement file and rejects other JSON", () => {
    expect(asArrangement({ format: "pewpew.arrangement", version: 1 })).toEqual(
      {
        format: "pewpew.arrangement",
        version: 1,
        fixtures: [],
        groups: [],
      },
    );
    expect(asArrangement({ format: "other", version: 1 })).toBeNull();
    expect(asArrangement([1])).toBeNull();
    const file = { format: "pewpew.arrangement", version: 1 };
    expect(asArrangement({ ...file, fixtures: {} })).toBeNull();
    expect(asArrangement({ ...file, groups: [null] })).toBeNull();
    expect(asArrangement(null)).toBeNull();
  });
});

describe("power cap", () => {
  it("fills the defaults in and leaves them out of the file", () => {
    expect(powerOf(DEFAULT_ARRANGEMENT)).toEqual({
      max_watts: null,
      max_brightness: 1,
    });
    const capped = setPower(DEFAULT_ARRANGEMENT, {
      max_watts: 500,
      max_brightness: 1,
    });
    expect(capped.power).toEqual({ max_watts: 500 });
    expect(powerOf(capped)).toEqual({ max_watts: 500, max_brightness: 1 });
    expect(DEFAULT_ARRANGEMENT).not.toHaveProperty("power");
    expect(setPower(capped, { max_watts: null, max_brightness: 1 })).toEqual(
      DEFAULT_ARRANGEMENT,
    );
  });
});
