// Layout mode: the build-day tools (input-end markers, blink a fixture), on
// only while the operator asks for them.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useSender } from "../wire/store";

/** How long a blink runs: pewpew.blink DURATION. */
export const BLINK_MS = 4000;

export interface LayoutMode {
  readonly on: boolean;
  setOn(on: boolean): void;
  readonly markers: boolean;
  setMarkers(on: boolean): void;
  /** The fixture the blink button flashes. */
  readonly fixture: string | null;
  setFixture(id: string | null): void;
  /** Blink a fixture, which it picks. */
  blink(id: string): void;
  /** The fixture blinking now, as far as this page asked; null after BLINK_MS. */
  readonly blinking: string | null;
}

const LayoutContext = createContext<LayoutMode | null>(null);

export function LayoutProvider({ children }: { children: ReactNode }) {
  const sender = useSender();
  const [on, setOn] = useState(false);
  const [markers, setMarkers] = useState(true);
  const [fixture, setFixture] = useState<string | null>(null);
  // An object per blink, so a second blink of the same fixture restarts the timer.
  const [blinked, setBlinked] = useState<{ readonly id: string } | null>(null);
  useEffect(() => {
    if (!blinked) return;
    const t = setTimeout(() => setBlinked(null), BLINK_MS);
    return () => clearTimeout(t);
  }, [blinked]);
  const blink = (id: string) => {
    setFixture(id);
    setBlinked({ id });
    sender.send({ type: "blink", fixture: id });
  };
  return (
    <LayoutContext.Provider value={{ on, setOn, markers, setMarkers, fixture, setFixture, blink, blinking: blinked?.id ?? null }}>
      {children}
    </LayoutContext.Provider>
  );
}

export function useLayoutMode(): LayoutMode {
  const mode = useContext(LayoutContext);
  if (!mode) throw new Error("no LayoutProvider");
  return mode;
}
