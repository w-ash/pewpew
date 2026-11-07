import { getResponse } from "msw";
import { onTestFinished, vi } from "vitest";
import { httpHandlers } from "../../src/studio/mocks/handlers";

/** Answers the page's fetches from the studio's mock handlers until the test
 * ends, and returns the paths it asked for, in order. A fetch no handler
 * answers fails. */
export function mockApi(): string[] {
  const asked: string[] = [];
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(typeof input === "string" ? new URL(input, location.href) : input, init);
    asked.push(new URL(request.url).pathname);
    const response = await getResponse(httpHandlers, request);
    if (!response) throw new Error(`no mock answers ${request.method} ${request.url}`);
    return response;
  });
  onTestFinished(() => {
    vi.unstubAllGlobals();
  });
  return asked;
}
