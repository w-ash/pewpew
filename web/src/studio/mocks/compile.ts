/**
 * A stand-in for `POST /api/compile`, for dev and tests only.
 *
 * The real compiler is Python (`compile_rig` in src/pewpew/rig/compile.py on
 * branch studio-ws1-rig); the app never runs this. It expands `ring` with the
 * formula in docs/studio/domain-model.md §3 so the default golden rings look
 * right, `array` row-major with its `member` pose (models.py:489-516 there),
 * and puts attachments on frames rotated as `pose.anchor_frame` does
 * (pose.py:161-175 there): end_a is a half turn about z. It ignores `aim`.
 * Its report and issues are invented placeholders that exercise every style
 * the report panel has.
 */
import { MathUtils, Matrix4, Vector3 } from "three";
import type {
  Arrangement,
  CompiledFixture,
  CompiledRig,
  Issue,
  Pose,
} from "../api/types";
import { IDENTITY_POSE, poseMatrix as poseQMatrix } from "../editor/pose";
import { MOCK_PIXELS_PER_BAR, mockCatalog } from "./catalog";

const L = 1.0;
const MAX_FIXTURES = 200;
const BARS_PER_OUTPUT = 8;

function poseMatrix(pose: Pose | undefined): Matrix4 {
  return poseQMatrix({
    position_m: pose?.position_m ?? IDENTITY_POSE.position_m,
    quat_xyzw: pose?.quat_xyzw ?? IDENTITY_POSE.quat_xyzw,
  });
}

const END_FRAMES: Record<string, Matrix4> = {
  end_a: new Matrix4().set(
    -1,
    0,
    0,
    0,
    0,
    -1,
    0,
    -L / 2,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
  ),
  end_b: new Matrix4().makeTranslation(0, L / 2, 0),
};

interface Member {
  id: string;
  group: string | null;
  type: string;
  matrix: Matrix4;
  attach: Record<string, string | null>;
}

function expand(arr: Arrangement): Member[] {
  const out: Member[] = [];
  for (const g of arr.groups ?? []) {
    const base = poseMatrix(g.pose);
    if (g.preset === "ring") {
      const a = MathUtils.degToRad(g.tilt_deg ?? 0);
      const roll = new Matrix4().makeRotationY(
        MathUtils.degToRad(g.roll_deg ?? 0),
      );
      const outer = g.data_in === "outer";
      for (let k = 0; k < g.count; k++) {
        const t = MathUtils.degToRad(
          (g.angle_offset_deg ?? 0) + (360 * k) / g.count,
        );
        const mid = g.start_radius_m + L / 2;
        const x = new Vector3(-Math.sin(t), 0, Math.cos(t));
        const y = new Vector3(
          Math.cos(a) * Math.cos(t),
          Math.sin(a),
          Math.cos(a) * Math.sin(t),
        );
        const z = new Vector3().crossVectors(x, y);
        const r = new Matrix4().makeBasis(x, y, z).multiply(roll);
        if (outer) r.multiply(new Matrix4().makeRotationZ(Math.PI));
        r.setPosition(mid * Math.cos(t), 0, mid * Math.sin(t));
        const inner = g.attach?.inner ?? null;
        const outerEnd = g.attach?.outer ?? null;
        out.push({
          id: `${g.id}/${k}`,
          group: g.id,
          type: g.type,
          matrix: base.clone().multiply(r),
          attach: {
            end_a: outer ? outerEnd : inner,
            end_b: outer ? inner : outerEnd,
          },
        });
      }
    } else {
      const [n, m = 1] = g.counts;
      const [s0 = [0, 0, 0], s1 = [0, 0, 0]] = g.steps_m;
      const member = poseMatrix(g.member);
      let k = 0;
      for (let i = 0; i < n; i++) {
        for (let j = 0; j < m; j++) {
          const p = new Vector3(...s0)
            .multiplyScalar(i)
            .add(new Vector3(...s1).multiplyScalar(j));
          out.push({
            id: `${g.id}/${k++}`,
            group: g.id,
            type: g.type,
            matrix: base
              .clone()
              .multiply(new Matrix4().makeTranslation(p))
              .multiply(member),
            attach: { end_a: null, end_b: null, ...g.attach },
          });
        }
      }
    }
  }
  for (const f of arr.fixtures ?? []) {
    out.push({
      id: f.id,
      group: null,
      type: f.type,
      matrix: poseMatrix(f.pose),
      attach: { end_a: null, end_b: null, ...f.attach },
    });
  }
  return out;
}

export class MockCompileError extends Error {
  issues: Issue[];
  constructor(issues: Issue[]) {
    super(issues[0]?.message ?? "invalid arrangement");
    this.issues = issues;
  }
}

const round = (m: Matrix4) =>
  m.elements.map((v) => Math.round(v * 1e9) / 1e9 + 0);

export function mockCompile(arr: Arrangement): CompiledRig {
  const errors: Issue[] = [];
  if (arr?.format !== "pewpew.arrangement") {
    throw new MockCompileError([
      {
        level: "error",
        code: "format",
        message: 'format must be "pewpew.arrangement"',
        ref: null,
      },
    ]);
  }
  const ids = new Set<string>();
  for (const e of [...(arr.groups ?? []), ...(arr.fixtures ?? [])]) {
    if (ids.has(e.id)) {
      errors.push({
        level: "error",
        code: "duplicate_id",
        message: `id ${e.id} is used twice`,
        ref: e.id,
      });
    }
    ids.add(e.id);
    if (!mockCatalog.fixture_types.some((t) => t.id === e.type)) {
      errors.push({
        level: "error",
        code: "unknown_type",
        message: `unknown fixture type ${e.type}`,
        ref: e.id,
      });
    }
  }
  const members = errors.length ? [] : expand(arr);
  if (members.length > MAX_FIXTURES) {
    errors.push({
      level: "error",
      code: "too_many_fixtures",
      message: `the arrangement has ${members.length} fixtures; the limit is ${MAX_FIXTURES}`,
      ref: null,
    });
  }
  if (errors.length) throw new MockCompileError(errors);

  const fixtures: CompiledFixture[] = members.map((m, i) => ({
    id: m.id,
    type_id: m.type,
    group: m.group,
    matrix: round(m.matrix),
    attachments: m.attach,
    attachment_matrices: Object.fromEntries(
      Object.entries(m.attach).map(([end, id]) => [
        end,
        id ? round(m.matrix.clone().multiply(END_FRAMES[end]!)) : null,
      ]),
    ),
    pixel_start: i * MOCK_PIXELS_PER_BAR,
    pixel_count: MOCK_PIXELS_PER_BAR,
  }));
  const n = fixtures.length * MOCK_PIXELS_PER_BAR;
  const outputs = Math.ceil(fixtures.length / BARS_PER_OUTPUT);
  const issues: Issue[] = [
    {
      level: "warning",
      code: "assumed",
      message:
        "Feed currents rest on the connector rating, which is assumed (M12's 4 A).",
      ref: null,
    },
  ];
  if (outputs > 12) {
    issues.unshift({
      level: "violation",
      code: "output_over_cap",
      message: `Mock: ${outputs} outputs needed, more than the 12 the mock's three boards have.`,
      ref: null,
    });
  }
  const maxW = fixtures.length * 25.6;
  // RGB through WLED's Accurate auto-white reaches 2 of a bar's 4 channels.
  const rgbW = maxW / 2;
  // The server's PowerCap.watts: that × brightness, at most max_watts.
  const cappedW = Math.min(
    rgbW * (arr.power?.max_brightness ?? 1),
    arr.power?.max_watts ?? Number.POSITIVE_INFINITY,
  );
  // One Mean Well LRS-350-24 at 80%: 0.8 × 14.6 A × 24 V.
  const psuCount = Math.max(1, Math.ceil(cappedW / 280.32));
  const slices = Array.from({ length: outputs }, (_, k) => ({
    controller: `auto-${Math.floor(k / 4) + 1}`,
    output: `rmt${k % 4}`,
    start: k * BARS_PER_OUTPUT * MOCK_PIXELS_PER_BAR,
    count:
      Math.min(BARS_PER_OUTPUT, fixtures.length - k * BARS_PER_OUTPUT) *
      MOCK_PIXELS_PER_BAR,
    led_type: 30,
    color_order: "GRBW",
  }));
  return {
    n,
    catalog_digest: mockCatalog.digest ?? "mock",
    fixtures,
    slices,
    report: {
      totals: {
        fixtures: fixtures.length,
        pixels: n,
        worst_w: maxW,
        worst_a: maxW / 24,
        rgb_worst_w: rgbW,
        rgb_worst_a: rgbW / 24,
        capped_w: cappedW,
        capped_a: cappedW / 24,
        controllers: Math.ceil(outputs / 4),
        psus: psuCount,
        feeds: Math.ceil(fixtures.length / 2),
      },
      outputs: slices.map((s) => ({
        controller: s.controller,
        output: s.output,
        chain: `${s.controller}.${s.output}`,
        pixels: s.count,
        led_type: s.led_type,
        led_label: "SK6812 RGBW",
        frame_s: s.count * 30e-6 + 80e-6,
        wire_fps: 1 / (s.count * 30e-6 + 80e-6),
        fps: Math.min(1 / (s.count * 30e-6 + 80e-6), 1 / 0.015),
      })),
      hops: slices.map((s) => ({
        chain: `${s.controller}.${s.output}`,
        kind: "lead",
        source: s.controller,
        target: `${s.controller}.${s.output}`,
        run_m: 1.5,
        path_m: 1.8,
      })),
      feeds: Array.from({ length: Math.ceil(fixtures.length / 2) }, (_, k) => ({
        id: `f${k + 1}`,
        psu: `p${Math.floor(k / 5) + 1}`,
        chain: "mock",
        fixtures: fixtures.slice(k * 2, k * 2 + 2).map((f) => f.id),
        cable: "18 AWG 2c",
        length_m: 2.5,
        current_a: 2.133,
        connector_a: 4,
        fuse_a: 5,
        loop_ohm: 0.04,
        drop_v: 0.17,
        drop_fraction: 0.0071,
        va: 51.2,
      })),
      psus: Array.from({ length: psuCount }, (_, k) => ({
        id: `p${k + 1}`,
        type: "mock-24v",
        v_out: 24,
        i_max_a: 14.6,
        current_a: cappedW / psuCount / 24,
        worst_a: maxW / psuCount / 24,
        load_fraction: cappedW / psuCount / 24 / 14.6,
        watts: cappedW / psuCount,
        feeds: [],
      })),
      bom: [
        {
          kind: "fixture",
          item: "bar",
          name: "Mock bar",
          count: fixtures.length,
          length_m: null,
        },
        {
          kind: "cable",
          item: "18awg",
          name: "18 AWG 2c",
          count: 1,
          length_m: 60,
        },
      ],
      basis: [
        {
          fact: "connector.m12.rated_a",
          v: 4,
          status: "assumed",
          src: "M12, RES-017",
          used_for: ["feeds"],
        },
      ],
      notes: [],
    },
    issues,
  };
}
