import { Slider } from "@ark-ui/react/slider";
import type { ReactNode } from "react";
import { percent } from "../params/format";
import { capText, MASTER_STEP, stepMaster } from "../aura/master";
import { useRefusal, useSender } from "../wire/store";
import { IconButton } from "../design/Button";
import { DisclosureButton, DisclosureNote, useDisclosure } from "../design/Disclosure";
import { Icon } from "../design/Icon";
import { SliderBody } from "../design/SliderBody";
import { sayStep } from "../design/StepStatus";
import { useDraft } from "../design/useDraft";
import { useOnChange } from "../design/useOnChange";

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
 * tap cannot jump the room), and − and + joined round its readout, as wide as a knob's entry, so its
 * slider is as long as a knob's. On touch one row: ☀ alone names it, then the slider, the whole width the
 * steps leave, then the steps, the readout giving the max over the level. The readout is drawn only: the
 * slider's value text says it, and a step says where it left the brightness. */
export function Master({ master, cap, lead }: Props) {
  const sender = useSender();
  const about = useDisclosure();
  const draft = useDraft(master, Object.is);
  useOnChange(useRefusal("master"), draft.drop);
  const change = (v: number) => {
    draft.change(v);
    sender.sendLatest({ type: "master", value: v });
  };
  const step = (steps: number) => {
    const v = stepMaster(draft.shown, cap, steps);
    change(v);
    draft.release();
    sayStep(`brightness ${percent(v)}`);
  };
  const by = percent(MASTER_STEP);
  const capped = cap < 1;
  return (
    <Slider.Root
      className="master"
      min={0}
      max={cap}
      step={0.01}
      value={[draft.shown]}
      getAriaValueText={(d) => percent(d.value)}
      onValueChange={(d) => change(d.value[0] ?? draft.shown)}
      onValueChangeEnd={draft.release}
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
      <div className="joined">
        <IconButton variant="secondary" glyph="−" label={`brightness down ${by}`} onPress={() => step(-1)} />
        <span className="readout t-value" aria-hidden="true">
          {capped && (
            <span className="readout-word">
              <Icon name="le" />
              {percent(cap)}
            </span>
          )}
          <span className="level">
            {Math.round(draft.shown * 100)}
            <span className="unit">%</span>
          </span>
        </span>
        <IconButton variant="secondary" glyph="+" label={`brightness up ${by}`} onPress={() => step(1)} />
      </div>
      {capped && <DisclosureNote disclosure={about}>{MAX_ABOUT}</DisclosureNote>}
    </Slider.Root>
  );
}
