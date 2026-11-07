import { beforeEach } from "vitest";
import { commands } from "vitest/browser";

declare module "vitest/browser" {
  interface BrowserCommands {
    pointerAway(): Promise<void>;
  }
}

// Tests drive React through act(); this tells React it runs under a test.
(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// Each test starts with the pointer off the page. A pointer left where the last test clicked hovers what the
// next one renders there, a moment after it renders, so a style read at rest could read the hover.
beforeEach(() => commands.pointerAway());
