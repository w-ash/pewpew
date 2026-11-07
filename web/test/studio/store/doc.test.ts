import { beforeEach, describe, expect, it } from "vitest";
import type { Arrangement } from "../../../src/studio/api/types";
import { DEFAULT_ARRANGEMENT, useDoc } from "../../../src/studio/store/doc";

const renamed = (name: string): Arrangement => ({
  ...DEFAULT_ARRANGEMENT,
  name,
});

describe("doc store", () => {
  beforeEach(() =>
    useDoc.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" }),
  );

  it("forks a saved link on undo, so the link never names other content", () => {
    const doc = useDoc.getState();
    const edited = renamed("edited");
    doc.commit(edited);
    doc.markSaved(edited, "X");
    expect(useDoc.getState().share).toEqual({ mode: "shared", id: "X" });
    doc.undo();
    expect(useDoc.getState().share).toEqual({ mode: "fork", from: "X" });
  });

  it("forks when the document changed while it was being saved", () => {
    const doc = useDoc.getState();
    const saved = renamed("saved");
    doc.commit(saved);
    doc.commit(renamed("edited during the save"));
    doc.markSaved(saved, "X");
    expect(useDoc.getState().share).toEqual({ mode: "fork", from: "X" });
  });

  it("ignores edits while a shared link loads", () => {
    const doc = useDoc.getState();
    doc.setShare({ mode: "loading", id: "X" });
    doc.commit(renamed("lost"));
    doc.undo();
    expect(useDoc.getState().history.present).toBe(DEFAULT_ARRANGEMENT);
    expect(useDoc.getState().history.past).toEqual([]);
  });
});
