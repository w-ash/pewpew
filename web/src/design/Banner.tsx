import type { ReactNode } from "react";
import { IconButton } from "./Button";

export type BannerTone = "info" | "warning" | "error" | "lost";

interface BannerProps {
  /** Info is quiet; warning and error ask for a look; lost is the connection's, on the danger fill. Error by default. */
  readonly tone?: BannerTone;
  /** A banner that opens something is one button. */
  readonly onPress?: () => void;
  /** A ✕ at the end that clears it. */
  readonly onDismiss?: () => void;
  /** Called with the element, for a measure of its height. */
  readonly ref?: (el: HTMLElement | null) => void;
  readonly children: ReactNode;
}

/** A strip of words about the page: a bad board, a lost connection, a notice. Where it sits is the page's (page.css). */
export function Banner({ tone, onPress, onDismiss, ref, children }: BannerProps) {
  const kind = tone ?? "error";
  if (onPress) {
    return (
      <button ref={ref} type="button" className="banner" data-tone={kind} onClick={onPress}>
        {children}
      </button>
    );
  }
  return (
    <div ref={ref} className="banner" data-tone={kind} role={kind === "info" ? "status" : "alert"}>
      {children}
      {onDismiss && <IconButton icon="close" label="Dismiss" onPress={onDismiss} />}
    </div>
  );
}
