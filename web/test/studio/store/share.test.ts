import { beforeEach, describe, expect, it } from "vitest";
import type { Arrangement } from "../../../src/studio/api/types";
import { useDoc } from "../../../src/arrange/doc";
import { DEFAULT_ARRANGEMENT, useShare } from "../../../src/studio/store/share";

const renamed = (name: string): Arrangement => ({
  ...DEFAULT_ARRANGEMENT,
  name,
});

describe("share store", () => {
  beforeEach(() => useShare.getState().load(DEFAULT_ARRANGEMENT, { mode: "draft" }));

  it("forks a saved link on undo, so the link never names other content", () => {
    const doc = useDoc.getState();
    const edited = renamed("edited");
    doc.commit(edited);
    useShare.getState().markSaved(edited, "X");
    expect(useShare.getState().share).toEqual({ mode: "shared", id: "X" });
    doc.undo();
    expect(useShare.getState().share).toEqual({ mode: "fork", from: "X" });
  });

  it("forks when the document changed while it was being saved", () => {
    const doc = useDoc.getState();
    const saved = renamed("saved");
    doc.commit(saved);
    doc.commit(renamed("edited during the save"));
    useShare.getState().markSaved(saved, "X");
    expect(useShare.getState().share).toEqual({ mode: "fork", from: "X" });
  });

  it("forks a shared arrangement on the first edit, and only then", () => {
    const shared: Arrangement = { ...DEFAULT_ARRANGEMENT, name: "shared" };
    useShare.getState().load(shared, { mode: "shared", id: "AAAAAAAAAAAAAAAAAAAAAA" });
    useDoc.getState().select({ kind: "group", id: "inner" });
    expect(useShare.getState().share.mode).toBe("shared");
    useDoc.getState().commit(shared);
    expect(useShare.getState().share.mode).toBe("shared");
    useDoc.getState().commit({ ...shared, name: "mine" });
    expect(useShare.getState().share).toEqual({ mode: "fork", from: "AAAAAAAAAAAAAAAAAAAAAA" });
  });

  it("ignores edits while a shared link loads", () => {
    const doc = useDoc.getState();
    useShare.getState().setShare({ mode: "loading", id: "X" });
    doc.commit(renamed("lost"));
    doc.undo();
    expect(useDoc.getState().history.present).toBe(DEFAULT_ARRANGEMENT);
    expect(useDoc.getState().history.past).toEqual([]);
    useShare.getState().setShare({ mode: "draft" });
  });
});
