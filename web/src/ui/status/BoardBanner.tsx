import { badBoards, bannerText } from "../../domain/health/health";
import { useWire } from "../../infra/wire/store";
import { Icon } from "../common/Icon";

/** A bad board's cause under the top bar, so a dark or orange room is
 * explained without opening the health panel. */
export function BoardBanner({ onOpen }: { onOpen(): void }) {
  const text = bannerText(badBoards(useWire((s) => s.health)));
  if (!text) return null;
  return (
    <button type="button" className="banner" onClick={onOpen}>
      <Icon name="close" />
      {text}
    </button>
  );
}
