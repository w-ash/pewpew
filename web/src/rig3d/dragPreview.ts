import { useEffect } from "react";
import { Matrix4 } from "three";

/**
 * A gizmo drag in progress: `delta` is the motion since the view last drew `fixtures` from the server,
 * applied on top of their server matrices until the compile of what it committed settles
 * (`useSettledPreview`), or, on the Console, until the editor no longer holds what it committed (`held`).
 * A new drag of the same fixtures before then adds to the motion it holds, so it starts where the last
 * one left them.
 */
export const dragPreview = {
  delta: null as Matrix4 | null,
  fixtures: new Set<number>(),
  version: 0,
  /** The motion held when the drag began. */
  start: new Matrix4(),
  /** What the last drag committed while its preview waits for the view to draw it; null while dragging. */
  held: null as unknown,
  begin(fixtures: Iterable<number>) {
    const next = new Set(fixtures);
    const same = this.delta !== null && next.size === this.fixtures.size && [...next].every((i) => this.fixtures.has(i));
    this.start = same && this.delta ? this.delta.clone() : new Matrix4();
    this.fixtures = next;
    this.delta = this.start.clone();
    this.held = null;
    this.version++;
  },
  /** The proxy moved by `delta` since this drag began. */
  move(delta: Matrix4) {
    this.delta = new Matrix4().multiplyMatrices(delta, this.start);
    this.version++;
  },
  /** The drag committed `what`; the preview shows it until the view draws it. */
  hold(what: unknown) {
    this.held = what;
  },
  clear() {
    this.held = null;
    if (this.delta === null && this.fixtures.size === 0) return;
    this.delta = null;
    this.fixtures = new Set();
    this.start = new Matrix4();
    this.version++;
  },
};

/** Ends the drag preview when `answered` turns true: the server has answered for the current arrangement,
 * so the view shows its compile, or keeps the last good one after a refusal. Either way the preview has no
 * pose left to bridge, and one kept would draw a pose the document does not hold. */
export function useSettledPreview(answered: boolean) {
  useEffect(() => {
    if (answered) dragPreview.clear();
  }, [answered]);
}
