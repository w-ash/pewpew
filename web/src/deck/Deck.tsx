import { useId, useRef, useState } from "react";
import { shuffleLine } from "../aura/looks";
import { armable } from "../aura/triggers";
import { useStandingAura } from "../wire/store";
import { Button, IconButton } from "../design/Button";
import { DisclosureNote, useDisclosure } from "../design/Disclosure";
import { useDismiss } from "../design/useDismiss";
import { useMedia, WIDE } from "../design/useMedia";
import { ALL_LOOKS } from "./AllLooks";
import { Blackout } from "./Blackout";
import { useFade } from "./fade";
import { FadeSelect } from "./FadeSelect";
import { KEYS, Looks, looksAbout, MarkSign } from "./Looks";
import { Master } from "./Master";
import { CuesOn, cuesAbout, CuesRow } from "./Triggers";
import { Variety } from "./Variety";

interface Props {
  /** Whether the list of every look is open, in the slot. */
  readonly allOpen?: boolean;
  /** Open or close the list of every look. */
  onAll?(): void;
}

/** The controls the operator plays, on one region card, a row each: the brightness, its head ending in
 * blackout; the saved looks, the first nine as tiles under a "looks" heading, then "all N ›" to the
 * list of every look past nine, then the "⋯" (wide with a mouse, those two end the caption's line, and the
 * tiles take the card's width in equal columns); the make actions, surprise me and vary this, on their own row
 * apart from the tiles; and while cues are on a button per cue. On a phone the brightness comes last, its
 * slider the whole width, and blackout under it on a row of its own, under the thumb; wide, the brightness
 * comes first, then the rows that wrap, so a new look moves neither. What is rarely needed waits behind
 * the "⋯": cues on or off, the fade a recall takes, what the signs shown now mean and what shuffle does;
 * its name says which of these the run has, and a run with none of them has no "⋯". It opens in the deck,
 * in a well under the row of its "⋯", pushing what is under it down; Esc or a press outside the deck closes
 * it. A row's own note (why a button is off, what a second press does) opens under that row. */
export function Deck({ allOpen, onAll }: Props) {
  const aura = useStandingAura();
  const wide = useMedia(WIDE);
  const deck = useRef<HTMLElement>(null);
  const moreId = useId();
  const captionId = useId();
  const moreButton = useRef<HTMLButtonElement>(null);
  const moreNote = useRef<HTMLDivElement>(null);
  const looksNote = useDisclosure();
  const madeNote = useDisclosure();
  const [fade, setFade] = useFade();
  const [more, setMore] = useState(false);
  // Closing it on Esc or a press elsewhere hands focus from inside it back to its "⋯".
  useDismiss(deck, more, (esc) => {
    if (esc && moreNote.current?.contains(document.activeElement)) moreButton.current?.focus();
    setMore(false);
  });
  if (!aura) return null;
  const { looks, triggers } = aura;
  const cues = armable(triggers);
  const fades = !!looks?.items.length;
  const marks = looks ? looksAbout(looks, triggers) : [];
  const about = [looks?.items.length && looks.idle !== null && shuffleLine, cues && cuesAbout(triggers)].filter((line): line is string => !!line);
  const holds = [cues && "cues", fades && "fade"].filter(Boolean).join(", ");
  // With nothing behind it, there is no "⋯".
  const hasMore = cues || fades || marks.length > 0 || about.length > 0;
  const ending = hasMore && (
    <IconButton
      ref={moreButton}
      icon="more"
      className="more"
      label={`more: ${holds ? `${holds} and ` : ""}what these do`}
      aria-expanded={more}
      aria-controls={moreId}
      onPress={() => setMore(!more)}
    />
  );
  const moreWell = hasMore && (
    <div key="more" ref={moreNote} id={moreId} className="note deck-more" hidden={!more}>
      <div className="row">
        <CuesOn triggers={triggers} />
        {fades && <FadeSelect fade={fade} onFade={setFade} />}
      </div>
      {marks.length > 0 && (
        <p className="marks">
          {marks.map((mark) => (
            <span key={mark.text} className="mark">
              <MarkSign mark={mark} />
              {mark.text}
            </span>
          ))}
        </p>
      )}
      {about.map((line) => (
        <p key={line}>{line}</p>
      ))}
    </div>
  );
  const blackout = <Blackout on={aura.blackout} />;
  const master = (
    <Master
      key="master"
      master={aura.master}
      cap={aura.cap}
      lead={
        <>
          {wide && blackout}
          {!looks && ending}
        </>
      }
    />
  );
  const hidden = looks ? looks.items.length - KEYS.length : 0;
  const saved = looks && (
    <div key="looks" className="deck-group looks-group">
      <span id={captionId} className="t-heading looks-caption">
        looks
      </span>
      <div className="row looks-row">
        <Looks looks={looks} triggers={triggers} note={looksNote} labelledBy={captionId} />
        {hidden > 0 && onAll && (
          <Button
            variant="tertiary"
            className="all-looks-button"
            aria-label={`all ${looks.items.length} looks`}
            aria-expanded={!!allOpen}
            aria-controls={allOpen ? ALL_LOOKS : undefined}
            onPress={onAll}
          >
            all {looks.items.length} ›
          </Button>
        )}
        {ending}
      </div>
      {moreWell}
      <DisclosureNote disclosure={looksNote} live />
    </div>
  );
  const made = looks && (
    <div key="made" className="deck-group">
      <div className="row made-row">
        <Variety aura={aura} looks={looks} note={madeNote} />
      </div>
      <DisclosureNote disclosure={madeNote} live />
    </div>
  );
  const cueRow = <CuesRow key="cues" triggers={triggers} />;
  const blackoutRow = (
    <div key="blackout" className="row blackout-row">
      {blackout}
    </div>
  );
  return (
    <section ref={deck} className="deck" aria-label="frame">
      <div className="deck-rows">
        {wide ? [master, !looks && moreWell, saved, made, cueRow] : [saved, made, cueRow, master, !looks && moreWell, blackoutRow]}
      </div>
    </section>
  );
}
