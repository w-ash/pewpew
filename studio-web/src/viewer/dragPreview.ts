import { Matrix4 } from "three";

/**
 * A gizmo drag in progress: `delta` is the proxy's motion since the drag
 * began, applied on top of the server matrices of `fixtures` until the next
 * compile replaces them.
 */
export const dragPreview = {
  delta: null as Matrix4 | null,
  fixtures: new Set<number>(),
  version: 0,
  begin(fixtures: Iterable<number>) {
    this.fixtures = new Set(fixtures);
    this.delta = new Matrix4();
    this.version++;
  },
  move(delta: Matrix4) {
    this.delta = delta;
    this.version++;
  },
  clear() {
    if (this.delta === null && this.fixtures.size === 0) return;
    this.delta = null;
    this.fixtures = new Set();
    this.version++;
  },
};
