import { badBoards, bannerText } from "../health/health";
import { useWire } from "../wire/store";
import { Banner } from "../design/Banner";
import { Icon } from "../design/Icon";

/** A bad board's cause under the top bar, so a dark or orange room is
 * explained without opening the health panel. */
export function BoardBanner({ onOpen }: { onOpen(): void }) {
  const text = bannerText(badBoards(useWire((s) => s.health)));
  if (!text) return null;
  return (
    <Banner onPress={onOpen}>
      <Icon name="close" />
      {text}
    </Banner>
  );
}
