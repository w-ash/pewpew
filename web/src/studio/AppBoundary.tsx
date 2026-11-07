import { Button } from "../design/Button";
import { Component, type ReactNode } from "react";
import { useDoc } from "./store/doc";

/**
 * Shows a render error instead of a blank page. The draft and its undo
 * history live in the doc store, outside React, so they survive the error and
 * undoing the change that caused it usually recovers the page.
 */
export class AppBoundary extends Component<
  { children: ReactNode },
  { error: string | null }
> {
  state: { error: string | null } = { error: null };

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : String(error) };
  }

  render() {
    if (this.state.error === null) return this.props.children;
    const canUndo = useDoc.getState().history.past.length > 0;
    return (
      <div role="alert" className="fields studio-boundary">
        <p>The studio hit an error: {this.state.error}</p>
        <div className="row wrap">
          {canUndo && (
            <Button
              variant="primary"
              onPress={() => {
                useDoc.getState().undo();
                this.setState({ error: null });
              }}
            >
              Undo the last change
            </Button>
          )}
          <Button onPress={() => window.location.reload()}>Reload</Button>
        </div>
      </div>
    );
  }
}
