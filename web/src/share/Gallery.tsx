// The Gallery's own chrome, loaded only on a hello with "gallery" (app/App.tsx).
import { Banner } from "../design/Banner";
import { useFrameGap, useOffers } from "../wire/store";
import { useBackoff } from "./backoff";
import { useIdlePause } from "./useIdlePause";

/** On the Gallery's page (capability "gallery"): the banner that says the layout is shared and read-only,
 * and while frames are stale, how to wake them; reconnects that back off; and on a session that pauses
 * (capability "pause"), the idle pause. */
export default function GalleryChrome() {
  const pauses = useOffers("pause");
  useBackoff();
  useIdlePause(pauses);
  const idle = useFrameGap() > 0 && pauses;
  return <Banner tone="info">Shared layout · read-only{idle && " · paused: press anywhere to resume"}</Banner>;
}
