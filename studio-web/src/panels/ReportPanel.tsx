import { Details } from "@pewpew/page/design";
import type { ReactNode } from "react";
import type { Issue, IssueLevel, RigReport } from "@/api/types";
import { powerOf, setPower } from "@/editor/arrangement";
import { useDoc } from "@/store/doc";
import { useSession } from "@/store/session";
import { NumberField, SectionHeading } from "./ui";

const fixed = (digits: number) =>
  new Intl.NumberFormat("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
const oneDecimal = fixed(1);
const twoDecimals = fixed(2);
const whole = fixed(0);
const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const trimmed = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const exact = new Intl.NumberFormat("en-US", { maximumSignificantDigits: 6 });

/** Watts with one decimal place: 1,228.8 W. */
export const formatW = (w: number) => `${oneDecimal.format(w)} W`;
/** Amps with one decimal place: 51.2 A. */
export const formatA = (a: number) => `${oneDecimal.format(a)} A`;
/** Volts with two decimal places: 0.17 V. */
export const formatV = (v: number) => `${twoDecimals.format(v)} V`;
/** A fraction as a percentage with one decimal place: 62.5%. */
export const formatPct = (fraction: number) => percent.format(fraction);
export const formatInt = (n: number) => whole.format(n);
const formatM = (m: number) => `${trimmed.format(m)} m`;

const LEVELS: Record<IssueLevel, { title: string; mark: string }> = {
  error: { title: "Errors", mark: "✕" },
  violation: { title: "Violations", mark: "▲" },
  warning: { title: "Warnings", mark: "!" },
};

/** The page's fold, its count in its summary. */
function Disclosure({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: ReactNode;
}) {
  return <Details summary={`${title} (${count})`}>{children}</Details>;
}

function IssueItems({
  issues,
  level,
}: {
  issues: readonly Issue[];
  level: IssueLevel;
}) {
  const style = LEVELS[level];
  return (
    <ul className="studio-issues">
      {issues.map((issue, k) => (
        <li
          // biome-ignore lint/suspicious/noArrayIndexKey: issues have no id.
          key={k}
          data-level={level}
        >
          <span aria-hidden>{style.mark}</span>
          <span>
            {issue.message}
            <span className="t-caption studio-issue-code">
              {issue.code}
              {issue.ref ? ` · ${issue.ref}` : ""}
            </span>
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Errors and violations in full; warnings behind a disclosure. */
export function IssueList({ issues }: { issues: readonly Issue[] }) {
  if (issues.length === 0) return <p className="t-label">No issues.</p>;
  const of = (level: IssueLevel) => issues.filter((i) => i.level === level);
  const warnings = of("warning");
  return (
    <div className="studio-section">
      {(["error", "violation"] as const).map((level) => {
        const list = of(level);
        if (list.length === 0) return null;
        return (
          <div key={level} className="studio-section">
            <h3 className="t-label">
              {LEVELS[level].title} ({list.length})
            </h3>
            <IssueItems issues={list} level={level} />
          </div>
        );
      })}
      {warnings.length > 0 && (
        <Disclosure title="Warnings" count={warnings.length}>
          <IssueItems issues={warnings} level="warning" />
        </Disclosure>
      )}
    </div>
  );
}

// The report's sections, as `RigReport` in src/pewpew/rig/electrical.py sends them.
interface Totals {
  pixels?: number;
  worst_w?: number;
  worst_a?: number;
  /** The most the RGB stream draws through each board's auto-white. */
  rgb_worst_w?: number;
  rgb_worst_a?: number;
  /** That under the power cap: what the PSUs are sized for. */
  capped_w?: number;
  capped_a?: number;
  controllers?: number;
  psus?: number;
  feeds?: number;
}
interface OutputRow {
  controller: string;
  output: string;
  pixels: number;
  led_label: string | null;
  frame_s: number;
  wire_fps: number;
  /** The rate the output shows: the wire's, at most the firmware's. */
  fps?: number;
}
interface FeedRow {
  id: string;
  psu: string;
  fixtures: string[];
  cable: string;
  length_m: number;
  current_a: number;
  drop_v: number;
  drop_fraction: number;
  fuse_a: number | null;
  note: string | null;
}
interface PsuRow {
  id: string;
  type: string;
  v_out: number;
  i_max_a: number;
  current_a: number;
  load_fraction: number;
  watts: number;
}
interface HopRow {
  kind: string;
  source: string;
  target: string;
  run_m: number;
  path_m: number;
}
interface BomRow {
  kind: string;
  item: string;
  name: string;
  count: number;
  length_m: number | null;
}
interface BasisRow {
  fact: string;
  v: unknown;
  status: string;
  src: string | null;
  used_for: string[];
}

const rows = <T,>(v: unknown): T[] => (Array.isArray(v) ? (v as T[]) : []);

function Stat({
  label,
  children,
  testId,
}: {
  label: string;
  children: ReactNode;
  testId?: string;
}) {
  return (
    <div>
      <dt className="t-label">{label}</dt>
      <dd className="t-value" data-testid={testId}>
        {children}
      </dd>
    </div>
  );
}

/** One row: a name on the left, its figures on the right, an optional note beneath. */
function Row({
  name,
  figures,
  note,
}: {
  name: string;
  figures: string;
  note?: string;
}) {
  return (
    <li>
      <div className="studio-row-line">
        <span>{name}</span>
        <span className="t-value">{figures}</span>
      </div>
      {note && <div className="note">{note}</div>}
    </li>
  );
}

const display = (v: unknown) =>
  typeof v === "number"
    ? exact.format(v)
    : typeof v === "string"
      ? v
      : JSON.stringify(v);

function Sections({ report }: { report: RigReport }) {
  const outputs = rows<OutputRow>(report.outputs);
  const feeds = rows<FeedRow>(report.feeds);
  const psus = rows<PsuRow>(report.psus);
  const hops = rows<HopRow>(report.hops);
  const bom = rows<BomRow>(report.bom);
  const basis = rows<BasisRow>(report.basis);
  const notes = rows<string>(report.notes);
  return (
    <div className="studio-folds">
      <Disclosure title="Outputs" count={outputs.length}>
        <ul className="studio-rows">
          {outputs.map((o) => (
            <Row
              key={`${o.controller}.${o.output}`}
              name={`${o.controller}.${o.output}`}
              figures={`${formatInt(o.pixels)} px · ${trimmed.format(o.fps ?? o.wire_fps)} fps`}
              note={`${o.led_label ?? "unknown LED"} · frame ${trimmed.format(o.frame_s * 1000)} ms, ${trimmed.format(o.wire_fps)} fps on the wire`}
            />
          ))}
        </ul>
      </Disclosure>
      <Disclosure title="Feeds" count={feeds.length}>
        <ul className="studio-rows">
          {feeds.map((f) => (
            <Row
              key={f.id}
              name={`${f.id} from ${f.psu}`}
              figures={`${formatA(f.current_a)} · drop ${formatV(f.drop_v)} (${formatPct(f.drop_fraction)})`}
              note={`${f.fixtures.length} fixtures · ${f.cable}, ${formatM(f.length_m)}${f.fuse_a === null ? "" : ` · fuse ${formatA(f.fuse_a)}`}${f.note ? ` · ${f.note}` : ""}`}
            />
          ))}
        </ul>
      </Disclosure>
      <Disclosure title="PSUs" count={psus.length}>
        <ul className="studio-rows">
          {psus.map((p) => (
            <Row
              key={p.id}
              name={`${p.id} (${p.type})`}
              figures={`${formatW(p.watts)} · ${formatPct(p.load_fraction)}`}
              note={`${formatA(p.current_a)} of ${formatA(p.i_max_a)} at ${formatV(p.v_out)}`}
            />
          ))}
        </ul>
      </Disclosure>
      <Disclosure title="Hops" count={hops.length}>
        <ul className="studio-rows">
          {hops.map((h) => (
            <Row
              key={`${h.kind}:${h.source}>${h.target}`}
              name={`${h.kind}: ${h.source} to ${h.target}`}
              figures={`${formatM(h.run_m)} (path ${formatM(h.path_m)})`}
            />
          ))}
        </ul>
      </Disclosure>
      <Disclosure title="Bill of materials" count={bom.length}>
        <ul className="studio-rows">
          {bom.map((b) => (
            <Row
              key={`${b.kind}:${b.item}`}
              name={b.name}
              figures={
                b.length_m === null
                  ? `× ${formatInt(b.count)}`
                  : formatM(b.length_m)
              }
              note={b.kind}
            />
          ))}
        </ul>
      </Disclosure>
      <Disclosure title="Assumed values and sources" count={basis.length}>
        <ul className="studio-rows">
          {basis.map((b) => (
            <Row
              key={b.fact}
              name={b.fact}
              figures={`${display(b.v)} · ${b.status}`}
              note={`${b.src ?? "no source"} · used for ${b.used_for.join(", ")}`}
            />
          ))}
        </ul>
      </Disclosure>
      {notes.length > 0 && (
        <Disclosure title="Notes" count={notes.length}>
          <ul className="studio-rows">
            {notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </Disclosure>
      )}
    </div>
  );
}

/**
 * The arrangement's power cap. Each edit commits to the document, so the
 * next compile sizes the report for it and a share link keeps it.
 */
export function PowerCapEditor() {
  const arrangement = useDoc((s) => s.history.present);
  const commit = useDoc((s) => s.commit);
  const loading = useDoc((s) => s.share.mode === "loading");
  const cap = powerOf(arrangement);
  const write = (next: Partial<typeof cap>) =>
    commit(setPower(arrangement, { ...cap, ...next }), "power");
  return (
    <section className="studio-section" aria-label="Power cap">
      <SectionHeading>Power cap</SectionHeading>
      <fieldset disabled={loading} className="studio-grid-2">
        <NumberField
          label="Max watts"
          unit="W"
          value={cap.max_watts}
          placeholder="none"
          min={1}
          max={1e6}
          step={10}
          decimals={1}
          onChange={(v) => write({ max_watts: v })}
          onClear={() => write({ max_watts: null })}
        />
        <NumberField
          label="Max brightness"
          unit="%"
          value={cap.max_brightness * 100}
          min={0}
          max={100}
          step={1}
          decimals={1}
          onChange={(v) =>
            write({ max_brightness: Number((v / 100).toFixed(4)) })
          }
        />
      </fieldset>
      <p className="note">
        The engine caps every frame. Under a cap the report sizes PSUs and
        checks feeds at the capped current, and every feed needs a fuse at its
        head: it protects the connector if the cap fails.
      </p>
    </section>
  );
}

export function ReportPanel({
  report,
  issues,
  stale,
}: {
  report: RigReport | null;
  issues: readonly Issue[];
  stale: boolean;
}) {
  const watts = useSession((s) => s.watts);
  const uncapped = useSession((s) => s.uncappedWatts);
  const totals = (report?.totals ?? {}) as Totals;
  const psus = rows<PsuRow>(report?.psus);
  const outputs = rows<OutputRow>(report?.outputs);
  const peak = psus.reduce<PsuRow | null>(
    (a, p) => (a === null || p.load_fraction > a.load_fraction ? p : a),
    null,
  );
  const count = (level: IssueLevel) =>
    issues.filter((i) => i.level === level).length;
  const n = (v: number | undefined, f: (x: number) => string) =>
    v === undefined ? "—" : f(v);
  return (
    <div className="studio-panel">
      <section className="studio-section" aria-label="Summary">
        <SectionHeading>
          Summary{stale ? " (from the last good compile)" : ""}
        </SectionHeading>
        <dl className="studio-stats">
          <Stat label="Pixels">{n(totals.pixels, formatInt)}</Stat>
          <Stat label="Every channel full">
            <span>{n(totals.worst_w, formatW)}</span>{" "}
            <span>{n(totals.worst_a, formatA)}</span>
          </Stat>
          <Stat label="PSUs sized for" testId="report-capped">
            <span>{n(totals.capped_w, formatW)}</span>{" "}
            <span>{n(totals.capped_a, formatA)}</span>
            {totals.rgb_worst_w !== undefined && (
              <span className="note studio-stat-note">
                RGB draws at most {formatW(totals.rgb_worst_w)}
              </span>
            )}
          </Stat>
          <Stat label="Effect, live" testId="report-watts">
            {watts === null ? "—" : formatW(watts)}
            {watts !== null && uncapped !== null && uncapped > watts && (
              <span className="note studio-stat-note">
                {formatW(uncapped)} uncapped
              </span>
            )}
          </Stat>
          <Stat label="Boards · outputs used">
            {n(totals.controllers, formatInt)} · {formatInt(outputs.length)}
          </Stat>
          <Stat label="Feeds">{n(totals.feeds, formatInt)}</Stat>
          <Stat label="PSUs · peak load">
            {n(totals.psus, formatInt)}
            {peak
              ? ` · ${formatPct(peak.load_fraction)} (${formatW(peak.watts)})`
              : ""}
          </Stat>
          <Stat label="Errors · violations · warnings">
            {count("error")} · {count("violation")} · {count("warning")}
          </Stat>
        </dl>
      </section>
      <PowerCapEditor />
      <section className="studio-section">
        <SectionHeading>Issues</SectionHeading>
        <IssueList issues={issues} />
      </section>
      <section className="studio-section">
        <SectionHeading>Details</SectionHeading>
        {report ? (
          <Sections report={report} />
        ) : (
          <p className="t-label">The server sent no report for this rig.</p>
        )}
      </section>
    </div>
  );
}
