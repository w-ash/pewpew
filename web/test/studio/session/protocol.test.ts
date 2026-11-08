import { describe, expect, it } from "vitest";
import { sessionUrl } from "../../../src/studio/session/protocol";

describe("sessionUrl", () => {
  it("uses wss over https and ws otherwise", () => {
    expect(sessionUrl({ protocol: "https:", host: "studio.example" })).toBe(
      "wss://studio.example/ws/session",
    );
    expect(sessionUrl({ protocol: "http:", host: "127.0.0.1:5173" })).toBe(
      "ws://127.0.0.1:5173/ws/session",
    );
  });
});
