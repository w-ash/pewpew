// What this device remembers. Storage can be blocked (private mode, a
// policy): then a choice holds for this visit only.

/** The text kept under `key`, or null when none is or storage is blocked. */
export function loadLocal(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

/** Keep `value` under `key`; null forgets it. */
export function saveLocal(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // blocked: the page's own state still holds the choice
  }
}
