import { expect, test } from "vitest";
import { upgradeAllowed } from "../dev-origin.ts";

test.each([
  ["127.0.0.1:5173", "http://127.0.0.1:5173", true],
  ["localhost:5173", "http://localhost:5173", true],
  ["[::1]:5173", "http://[::1]:5173", true],
  ["127.0.0.1:5173", undefined, true],
  ["127.0.0.1:5173", "http://evil.example", false],
  ["127.0.0.1:5173", "http://127.0.0.1:8080", false],
  ["127.0.0.1:5173", "null", false],
  ["evil.example:5173", "http://evil.example:5173", false],
  [undefined, "http://127.0.0.1:5173", false],
] as const)("Host %s, Origin %s: allowed %s", (host, origin, allowed) => {
  expect(upgradeAllowed(host, origin)).toBe(allowed);
});
