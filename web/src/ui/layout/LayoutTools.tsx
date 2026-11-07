import { roomOf } from "../../domain/room/layout";
import { useWire } from "../../infra/wire/store";
import { Button, ToggleButton } from "../common/Button";
import { onEngineHost } from "../common/host";
import { Icon } from "../common/Icon";
import { FINE_POINTER, useMedia } from "../common/useMedia";
import { Select } from "../common/Select";
import { BLINK_MS, useLayoutMode } from "./LayoutMode";

/** Markers at each fixture's input end, and blink a fixture: on the real
 * boards when DDP is on. A click on a fixture in the room blinks it, a tap
 * picks it and a second blinks it (Stage), as a line under the tools says. */
export function LayoutTools() {
  const mode = useLayoutMode();
  const fine = useMedia(FINE_POINTER);
  const room = roomOf(useWire((s) => s.map));
  if (!room) return <p className="layout-tools empty note">layout tools need a room map{onEngineHost() ? " (start the run with --room)" : ""}</p>;
  const fixture = mode.fixture && room.fixtures.some((f) => f.id === mode.fixture) ? mode.fixture : (room.fixtures[0]?.id ?? null);
  return (
    <div className="row layout-tools">
      <ToggleButton pressed={mode.markers} onPressedChange={mode.setMarkers} title="mark each bar's input end, where its cable plugs in">
        input ends
      </ToggleButton>
      <Select
        items={room.fixtures.map((f) => ({ value: f.id, label: f.id }))}
        value={fixture}
        onChange={mode.setFixture}
        label="fixture to blink"
      />
      <Button
        variant="primary"
        className="blink"
        disabled={!fixture}
        title={`flash the fixture white and off for ${BLINK_MS / 1000} s, on the real boards when DDP is on`}
        onPress={() => fixture && mode.blink(fixture)}
      >
        blink
      </Button>
      <span className="note" role="status">
        {mode.blinking && `blinking ${mode.blinking} · ${BLINK_MS / 1000} s`}
      </span>
      <p className="note layout-note">
        {fine ? "Click a bar to blink it." : "Tap a bar to pick it, again to blink it."} <Icon name="right" />
        <Icon name="left" /> mark each bar's input end, where its cable plugs in.
      </p>
    </div>
  );
}
