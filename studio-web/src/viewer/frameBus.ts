import type { Frame } from "@pewpew/page/wire";

/**
 * The newest frame, handed from the socket to the render loop. Only the
 * latest one matters, so a slow render drops frames instead of queueing.
 */
export const frameBus = {
  frame: null as Frame | null,
  version: 0,
  push(frame: Frame) {
    this.frame = frame;
    this.version++;
  },
  clear() {
    this.frame = null;
    this.version++;
  },
};
