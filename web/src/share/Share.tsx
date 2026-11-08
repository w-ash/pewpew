// What the hello's offers add to the Console, in one file loaded on demand (app/App.tsx): the page
// always loads none of it.
import ExportLooks from "./ExportLooks";
import GalleryChrome from "./Gallery";
import PublishSlot from "./Publish";

export type SharePart = { readonly part: "gallery" } | { readonly part: "export" } | { readonly part: "publish"; onClose(): void };

/** One part: the Gallery's banner and idle pause, the looks' export, or Publish. */
export default function Share(props: SharePart) {
  if (props.part === "gallery") return <GalleryChrome />;
  if (props.part === "export") return <ExportLooks />;
  return <PublishSlot onClose={props.onClose} />;
}
