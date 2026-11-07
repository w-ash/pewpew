// Aura health (pewpew.health.HealthMonitor.state()), and the one fact only the
// page can see: frames that stop arriving. From here a stalled render loop and
// a weak link to this phone look the same, so the page says only that frames
// are not reaching it.

export type Level = "pending" | "ok" | "warn" | "bad";

/** One DDP board, in board order. A field the board has not reported is null. */
export interface BoardHealth {
  readonly host: string;
  /** The room's name for it. */
  readonly board: string | null;
  /** Where frames go: its host, what its mDNS name resolved to, or null while not found. */
  readonly address: string | null;
  /** Learned from its first reply. */
  readonly mac: string | null;
  /** Another device answers at its address, or two polls in a row went unanswered. */
  readonly lost: boolean;
  /** One sentence on what to do. */
  readonly fix: string | null;
  readonly level: Level;
  /** One short text per threshold crossed. */
  readonly reasons: readonly string[];
  readonly live: boolean | null;
  readonly lip: string | null;
  /** Whether `lip` is this laptop; null when unknown. */
  readonly from_us: boolean | null;
  /** The board's own `leds.fps`. */
  readonly fps: number | null;
  readonly count: number | null;
  /** The pixels streamed to it. */
  readonly expected: number;
  readonly rssi: number | null;
  readonly channel: number | null;
  readonly uptime: number | null;
  readonly freeheap: number | null;
  readonly ver: string | null;
  /** The `uptime` drops seen this run. */
  readonly reboots: number;
  readonly reset_reason: number | string | null;
}

/** The render loop. */
export interface LoopHealth {
  readonly level: Level;
  readonly fps: number | null;
  readonly target: number | null;
  /** Blown deadlines. */
  readonly skips: number | null;
  /** The watchdog timeout in seconds; null when off. */
  readonly watchdog: number | null;
  /** What to do when it warns. */
  readonly fix: string | null;
}

/** The sleep assertion. */
export interface AwakeHealth {
  readonly level: Level;
  /** The run asked for it. */
  readonly requested: boolean;
  /** caffeinate holds it. */
  readonly held: boolean;
  /** Why it is not held. */
  readonly detail: string | null;
  /** What to do when it is asked for and not held. */
  readonly fix: string | null;
}

export interface FoundBoard {
  readonly address: string;
  readonly mac: string | null;
  readonly name: string | null;
  readonly ver: string | null;
  readonly live: boolean | null;
  readonly lm: string | null;
  readonly lip: string | null;
  /** The room board with this MAC. */
  readonly board: string | null;
  /** The room board streamed to this address. */
  readonly at: string | null;
}

export interface ScanState {
  readonly running: boolean;
  readonly subnet: string;
  readonly found: readonly FoundBoard[];
  readonly error: string | null;
}

export interface HealthState {
  /** The worst of the parts; "pending" while nothing is known. */
  readonly level: Level;
  readonly boards: readonly BoardHealth[];
  /** The DDP rate actually sent. */
  readonly sent_fps: number | null;
  readonly loop: LoopHealth;
  readonly awake: AwakeHealth;
  /** Null until a scan starts. */
  readonly scan: ScanState | null;
}

/** Frames older than this mean frames are not reaching the page. */
export const STALE_MS = 2000;

/** Seconds since the last frame once it passes STALE_MS, else 0. `lastFrameAt` 0 means none yet. */
export function frameGap(now: number, lastFrameAt: number): number {
  const gap = lastFrameAt ? now - lastFrameAt : 0;
  return gap > STALE_MS ? gap / 1000 : 0;
}

export function uptime(s: number | null): string | null {
  if (s == null) return null;
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  return d ? `up ${d}d ${h}h` : h ? `up ${h}h ${m}m` : `up ${m}m`;
}

export function mac(m: string | null): string {
  return m ? (m.match(/../g) ?? []).join(":") : "?";
}

export interface Chip {
  readonly level: Level;
  readonly text: string;
  readonly label: string;
}

/** The top bar's chip: bad while no frames reach this page, or while a layer's render raises
 * (`failed`), else the aura's level. */
export function chip(health: HealthState, gap: number, failed = false): Chip {
  const level = gap || failed ? "bad" : health.level;
  const bad = health.boards.filter((b) => b.level === "bad").length;
  const warn = health.boards.filter((b) => b.level === "warn").length;
  const n = health.boards.length;
  const text = gap ? "no frames here"
    : failed ? "error"
    : bad ? `${bad} bad`
    : warn ? `${warn} warn`
    : level === "pending" ? "…"
    : level === "ok" ? (n ? `${n} ok` : "ok")
    : level;
  return { level, text, label: `aura health: ${gap ? "no frames reaching this page" : failed ? "a layer's render fails" : text}` };
}

export interface HealthRow {
  readonly key: string;
  readonly name: string;
  readonly level: Level | "off";
  /** The level in words after the name, when not the level itself; "" for none. */
  readonly says?: string;
  readonly facts: string;
  readonly reasons: readonly string[];
  readonly fix: string | null;
  readonly link: string | null;
}

function facts(parts: readonly (string | null | undefined | false)[]): string {
  return parts.filter((x): x is string => !!x).join(" · ");
}

/** What the page itself sees: the newest frame's engine time, and the pixels drawn of the map's total. */
export interface Seen {
  readonly t: number;
  readonly n: number;
  readonly total: number;
}

function boardRow(b: BoardHealth, sentFps: number | null): HealthRow {
  return {
    key: `board:${b.host}`,
    name: b.board ? `${b.board} · ${b.host}` : b.host,
    level: b.level,
    facts: facts([
      b.address == null ? "not found" : b.address !== b.host && `at ${b.address}`,
      b.mac && `MAC ${mac(b.mac)}`,
      b.live != null && (b.live ? (b.from_us === false ? `live from ${b.lip}` : "live") : "not live"),
      b.fps != null && `${b.fps}${sentFps ? "/" + Math.round(sentFps) : ""} fps`,
      b.rssi != null && `${b.rssi} dBm${b.channel != null ? " ch " + b.channel : ""}`,
      uptime(b.uptime),
      !!b.reboots && `rebooted ${b.reboots}×${b.reset_reason != null ? ` (reason ${b.reset_reason})` : ""}`,
      b.freeheap != null && `heap ${Math.round(b.freeheap / 1000)}k`,
      b.count != null && `${b.count}/${b.expected} px`,
      b.ver,
    ]),
    reasons: b.reasons,
    // A healthy board's fix is the one they all share: okHint shows it once.
    fix: b.level === "ok" ? null : b.fix,
    link: b.address ? `http://${b.address}/` : null,
  };
}

/** The health panel: one row per board, then the rendering, bad while a layer's render fails (`failed` says
 * which, as the chip turns red for it), and whether the laptop can sleep. `local`: the page runs on the
 * laptop, where a command line flag is worth naming. */
export function healthRows(health: HealthState, gap: number, seen: Seen | null, local = false, failed: string | null = null): HealthRow[] {
  const { loop, awake } = health;
  return [
    ...health.boards.map((b) => boardRow(b, health.sent_fps)),
    {
      key: "loop",
      name: "rendering",
      level: gap || failed ? "bad" : loop.level,
      facts: facts([
        seen && `t=${Math.floor(seen.t)} s`,
        seen && `${seen.n}${seen.total > seen.n ? "/" + seen.total : ""} px`,
        loop.fps != null && `${loop.fps}/${loop.target} fps`,
        loop.skips != null && `${loop.skips} skips`,
        loop.watchdog ? `watchdog ${loop.watchdog} s` : "watchdog off",
      ]),
      reasons: gap ? [`no frames reaching this page for ${Math.round(gap)} s`] : failed ? [failed] : [],
      fix: gap || failed ? null : loop.fix,
      link: null,
    },
    {
      key: "sleep",
      name: awake.requested && awake.held ? "laptop kept awake" : "laptop can sleep",
      level: awake.requested ? awake.level : "off",
      says: "",
      facts: !awake.requested ? `this run did not ask to keep it awake${local ? " (start it with --keep-awake)" : ""}`
        : awake.held ? "held by caffeinate" : "NOT held",
      reasons: awake.requested && !awake.held && awake.detail ? [awake.detail] : [],
      fix: awake.fix,
      link: null,
    },
  ];
}

/** What to check when healthy boards stay dark, once for them all, or null. */
export function okHint(health: HealthState): string | null {
  return health.boards.find((b) => b.level === "ok" && b.fix)?.fix ?? null;
}

export function badBoards(health: HealthState | null): BoardHealth[] {
  return health ? health.boards.filter((b) => b.level === "bad") : [];
}

/** The banner line for the bad boards, or "" when none is bad. A page leads it with ✕. */
export function bannerText(bad: readonly BoardHealth[]): string {
  const [first] = bad;
  if (!first) return "";
  if (bad.length === 1) return `Board ${first.board ?? first.host}: ${first.reasons[0] ?? "bad"}. Tap for the fix.`;
  return `${bad.length} boards need attention: ${bad.map((b) => b.board ?? b.host).join(", ")}. Tap for details.`;
}

/** The scan button's label. The engine's fix sentences quote "find boards", so it keeps that name. */
export function scanButton(scan: ScanState | null): string {
  return scan?.running ? "finding…" : "find boards";
}

export function scanNote(scan: ScanState | null): string {
  if (!scan) return "lists the WLED boards on this laptop's network";
  if (scan.running) return `asking every address in ${scan.subnet}…`;
  if (scan.error) return `the scan failed: ${scan.error}`;
  return `${scan.found.length} WLED board${scan.found.length === 1 ? "" : "s"} in ${scan.subnet}`;
}

export function foundFacts(f: FoundBoard): string {
  return `MAC ${mac(f.mac)} · WLED ${f.ver} · ${f.live ? `live ${f.lm} from ${f.lip}` : "not live"}`;
}

const IPV4 = /^\d{1,3}(\.\d{1,3}){3}$/;

/** The lost room boards a found board could be rebound to. Only a board named
 * by IPv4 address can be rebound: one named by mDNS is followed by name. */
export function rebindOffers(found: FoundBoard, boards: readonly BoardHealth[]): string[] {
  return boards
    .filter((b) => b.lost && b.board && IPV4.test(b.host) && found.at !== b.board && !(found.board && found.board !== b.board))
    .map((b) => b.board as string);
}
