import { useEffect, useState } from "react";
import { planError, planUrl, roomOf, type MapShape, type Size } from "../../domain/room/layout";

export interface PlanImage {
  readonly image: HTMLImageElement | null;
  readonly size: Size | null;
  /** Why the plan is not drawn, or null. */
  readonly note: string | null;
}

const UNREADABLE = "the floor plan image could not be loaded; drawing the room without it";

/** The room's floor plan, fetched from the laptop's fixed URL. A missing or
 * undecodable image leaves the room drawn without it, and says so. */
export function usePlanImage(map: MapShape | null): PlanImage {
  const room = roomOf(map);
  const url = planUrl(room);
  const [loaded, setLoaded] = useState<{ url: string; image: HTMLImageElement | null } | null>(null);
  useEffect(() => {
    if (!url) return;
    let live = true;
    const img = new Image();
    img.onload = () => live && setLoaded({ url, image: img });
    img.onerror = () => live && setLoaded({ url, image: null });
    img.src = url;
    return () => {
      live = false;
    };
  }, [url]);
  const mine = loaded && loaded.url === url ? loaded : null;
  const image = mine?.image ?? null;
  return {
    image,
    size: image && { width: image.naturalWidth, height: image.naturalHeight },
    note: planError(room) ?? (mine && !image ? UNREADABLE : null),
  };
}
