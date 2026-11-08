/**
 * Undo and redo as a stack of whole-arrangement snapshots.
 *
 * Arrangements are small immutable values, so a snapshot per step is cheap
 * and undo can never drift from what was compiled. A run of edits that share
 * a coalesce key within `COALESCE_MS` (one slider drag, one typed number)
 * replaces the top snapshot instead of pushing a new one.
 */

export const HISTORY_LIMIT = 200;
export const COALESCE_MS = 800;

export interface History<T> {
  past: T[];
  present: T;
  future: T[];
  lastKey: string | null;
  lastAt: number;
}

export function createHistory<T>(present: T): History<T> {
  return { past: [], present, future: [], lastKey: null, lastAt: 0 };
}

export function commit<T>(
  h: History<T>,
  next: T,
  key: string | null = null,
  now = 0,
): History<T> {
  if (next === h.present) return h;
  const merge =
    key !== null && key === h.lastKey && now - h.lastAt <= COALESCE_MS;
  const past = merge ? h.past : [...h.past, h.present].slice(-HISTORY_LIMIT);
  return { past, present: next, future: [], lastKey: key, lastAt: now };
}

export function undo<T>(h: History<T>): History<T> {
  if (h.past.length === 0) return h;
  const present = h.past[h.past.length - 1]!;
  return {
    past: h.past.slice(0, -1),
    present,
    future: [h.present, ...h.future],
    lastKey: null,
    lastAt: 0,
  };
}

export function redo<T>(h: History<T>): History<T> {
  if (h.future.length === 0) return h;
  const [present, ...future] = h.future;
  return {
    past: [...h.past, h.present],
    present: present!,
    future,
    lastKey: null,
    lastAt: 0,
  };
}
