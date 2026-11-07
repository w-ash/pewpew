import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  onError: (message: string) => void;
}

/** Keeps a GLB that fails to load or parse from taking the whole canvas down. */
export class RigBoundary extends Component<Props, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: unknown) {
    this.props.onError(error instanceof Error ? error.message : String(error));
  }

  render() {
    return this.state.failed ? null : this.props.children;
  }
}
