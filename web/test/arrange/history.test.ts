import { beforeEach, describe, expect, it } from "vitest";
import { useDoc } from "../../src/arrange/doc";
import { RINGS as DEFAULT_ARRANGEMENT } from "./fixtures";
import { addFixture } from "../../src/arrange/arrangement";
import {
  COALESCE_MS,
  commit,
  createHistory,
  HISTORY_LIMIT,
  redo,
  undo,
} from "../../src/arrange/history";

describe("history", () => {
  it("undoes and redoes in order", () => {
    let h = createHistory("a");
    h = commit(h, "b");
    h = commit(h, "c");
    h = undo(h);
    expect(h.present).toBe("b");
    h = undo(h);
    expect(h.present).toBe("a");
    expect(undo(h)).toBe(h);
    h = redo(h);
    h = redo(h);
    expect(h.present).toBe("c");
    expect(redo(h)).toBe(h);
  });

  it("drops the redo branch on a new edit", () => {
    let h = commit(commit(createHistory(1), 2), 3);
    h = commit(undo(h), 4);
    expect(h.future).toEqual([]);
    expect(h.past).toEqual([1, 2]);
  });

  it("merges a run of edits that share a key, within the window", () => {
    let h = createHistory(0);
    h = commit(h, 1, "tilt", 1000);
    h = commit(h, 2, "tilt", 1000 + COALESCE_MS - 1);
    h = commit(h, 3, "tilt", 1000 + 2 * COALESCE_MS - 2);
    expect(h.past).toEqual([0]);
    h = commit(h, 4, "count", 1000 + 2 * COALESCE_MS);
    expect(h.past).toEqual([0, 3]);
    h = commit(h, 5, "count", 1000 + 10 * COALESCE_MS);
    expect(h.past).toEqual([0, 3, 4]);
  });

  it("does not merge across an undo", () => {
    let h = commit(createHistory(0), 1, "k", 0);
    h = commit(h, 2, "k", 10 * COALESCE_MS);
    h = undo(h);
    h = commit(h, 3, "k", 10 * COALESCE_MS + 1);
    expect(h.past).toEqual([0, 1]);
  });

  it("ignores a commit of the present value", () => {
    const h = createHistory("x");
    expect(commit(h, "x")).toBe(h);
  });

  it(`keeps at most ${HISTORY_LIMIT} steps`, () => {
    let h = createHistory(0);
    for (let i = 1; i <= HISTORY_LIMIT + 10; i++) h = commit(h, i);
    expect(h.past.length).toBe(HISTORY_LIMIT);
    expect(h.past[0]).toBe(10);
  });
});

describe("the document store", () => {
  beforeEach(() =>
    useDoc.getState().load(DEFAULT_ARRANGEMENT),
  );

  it("starts on the golden rings", () => {
    const groups = useDoc.getState().history.present.groups;
    expect(groups.map((g) => g.id)).toEqual(["inner", "outer"]);
  });

  it("undoes an edit back to the same snapshot", () => {
    const before = useDoc.getState().history.present;
    const { arrangement } = addFixture(before, "clen-rgbw-bar-1m");
    useDoc.getState().commit(arrangement);
    expect(useDoc.getState().history.present.fixtures).toHaveLength(1);
    useDoc.getState().undo();
    expect(useDoc.getState().history.present).toBe(before);
    useDoc.getState().redo();
    expect(useDoc.getState().history.present).toBe(arrangement);
  });

  it("clears undo when a new document loads", () => {
    useDoc.getState().commit({ ...DEFAULT_ARRANGEMENT, name: "edited" });
    useDoc.getState().load(DEFAULT_ARRANGEMENT);
    expect(useDoc.getState().history.past).toEqual([]);
  });
});
