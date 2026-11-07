import { Component, type ReactNode } from "react";

interface Props {
  readonly fallback: ReactNode;
  readonly children: ReactNode;
  /** A new value tries the children again. */
  readonly resetKey?: unknown;
}

interface State {
  readonly failed: boolean;
  readonly resetKey: unknown;
}

/** Shows `fallback` in place of a part of the page that threw while
 * rendering, so one bad value cannot blank the whole control surface. */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { failed: false, resetKey: this.props.resetKey };

  static getDerivedStateFromError(): Partial<State> {
    return { failed: true };
  }

  static getDerivedStateFromProps(props: Props, state: State): Partial<State> | null {
    return Object.is(props.resetKey, state.resetKey) ? null : { failed: false, resetKey: props.resetKey };
  }

  override render(): ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
