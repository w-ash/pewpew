import { useState, type ReactNode } from "react";
import { Button } from "../design/Button";
import { ErrorBoundary } from "../design/ErrorBoundary";
import { useDoc } from "./store/doc";

/**
 * Shows a render error instead of a blank page. The draft and its undo
 * history live in the doc store, outside React, so they survive the error and
 * undoing the change that caused it usually recovers the page.
 */
export function AppBoundary({ children }: { children: ReactNode }) {
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const canUndo = useDoc((s) => s.history.past.length > 0);
  const fallback = (
    <div role="alert" className="fields studio-boundary">
      <p>The studio hit an error: {error}</p>
      <div className="row wrap">
        {canUndo && (
          <Button
            variant="primary"
            onPress={() => {
              useDoc.getState().undo();
              setAttempt((a) => a + 1);
            }}
          >
            Undo the last change
          </Button>
        )}
        <Button onPress={() => window.location.reload()}>Reload</Button>
      </div>
    </div>
  );
  return (
    <ErrorBoundary resetKey={attempt} onError={setError} fallback={fallback}>
      {children}
    </ErrorBoundary>
  );
}
