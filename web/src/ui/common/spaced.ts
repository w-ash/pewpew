/** The names given, space-separated, leaving out each that is absent: a class list or an id list. */
export function spaced(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(" ");
}
