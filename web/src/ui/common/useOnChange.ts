import { useState } from "react";

/** Run `onChange` during render when `value` differs from the last render's:
 * how a component resets its own state on news (a refusal, a new session). */
export function useOnChange<T>(value: T, onChange: () => void): void {
  const [seen, setSeen] = useState(value);
  if (!Object.is(seen, value)) {
    setSeen(value);
    onChange();
  }
}
