import { Slider } from "@ark-ui/react/slider";
import { useState, type ReactNode } from "react";
import { percent } from "../params/format";
import { capText, MASTER_STEP } from "../aura/master";
import { NumberEntry } from "../params/controls/NumberEntry";
import { useRefusal, useSender } from "../wire/store";
import { DisclosureButton, DisclosureNote, useDisclosure } from "../design/Disclosure";
import { Icon } from "../design/Icon";
import { SliderBody } from "../design/SliderBody";
import { useDraft } from "../design/useDraft";
import { useOnChange } from "../design/useOnChange";
import { useSlideGuard } from "../design/useSlideGuard";

/** What the max is, for its "?". */
const MAX_ABOUT = "max: the highest brightness allowed in this run, set when the run started";

interface Props {
  readonly master: number;
  readonly cap: number;
  /** What ends its head: blackout. */
  readonly lead?: ReactNode;
}

/** The brightness (the master), one control on every screen, laid out as a knob's: its head names it, ☀
 * and the word, with its max and the max's "?", whose note opens under it, and ends with `lead`
 * (blackout); under it its slider, dragged by its thumb (a touch on the track does nothing, so a stray
 * tap cannot jump the room), and a knob's typed entry (`NumberEntry`: − and + step it by 5%, a typed level
 * goes on Enter or blur, up to the max), so its slider is as long as a knob's. On touch one row: ☀ alone
 * names it, then the slider, the whole width the entry leaves, then the entry. */
export function Master({ master, cap, lead }: Props) {
  const sender = useSender();
  const about = useDisclosure();
  const draft = useDraft(master, Object.is);
  useOnChange(useRefusal("master"), draft.drop);
  const change = (v: number) => {
    draft.change(v);
    sender.sendLatest({ type: "master", value: v });
  };
  const capped = cap < 1;
  const guard = useSlideGuard(draft.shown, change, draft.release);
  const [note, setNote] = useState<string | null>(null);
  // The entry types percents on the master's own grid, up to the max.
  const spec = { lo: 0, hi: Math.round(cap * 100), step: MASTER_STEP * 100, decimals: 0, periodic: false, unit: "%", text: [] };
  return (
    <Slider.Root
      className="master"
      min={0}
      max={cap}
      step={0.01}
      getAriaValueText={(d) => percent(d.value)}
      {...guard}
    >
      <div className="master-head">
        <Slider.Label className="field-label master-label">
          <Icon name="sun" />
          <span className="master-word">brightness</span>
        </Slider.Label>
        {capped && <span className="cap note t-value">{capText(cap)}</span>}
        {capped && <DisclosureButton disclosure={about} label="about max" />}
        {lead}
      </div>
      <SliderBody />
      <NumberEntry
        spec={spec}
        value={Math.round(draft.shown * 100)}
        label="brightness"
        onChange={(n) => change(n / 100)}
        onCommit={draft.release}
        onNote={setNote}
      />
      {note && (
        <p className="master-note note" role="status">
          {note}
        </p>
      )}
      {capped && <DisclosureNote disclosure={about}>{MAX_ABOUT}</DisclosureNote>}
    </Slider.Root>
  );
}
