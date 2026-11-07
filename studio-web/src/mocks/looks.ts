/**
 * `GET /api/looks` for the mock: the current look of each
 * examples/*.look.json, by the file's name, as the server gives them. Read
 * through a glob, so `tsc` in the image build needs no examples/.
 */
import type { LookDocument } from "@/api/types";

interface Book {
  current: string;
  looks: Record<string, LookDocument>;
}

const files = import.meta.glob<Book>("../../../examples/*.look.json", {
  eager: true,
  import: "default",
});

export const MOCK_LOOKS: Record<string, LookDocument> = Object.fromEntries(
  Object.entries(files).map(([path, book]) => [
    path.replace(/^.*\//, "").replace(/\.look\.json$/, ""),
    book.looks[book.current],
  ]),
);
