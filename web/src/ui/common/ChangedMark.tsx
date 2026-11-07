/** "· changed" after the name of a look, a layer or a step changed since saved; assistive tech hears
 * "(changed)". A knob says it by its ↺ instead. */
export function ChangedMark() {
  return (
    <span className="changed">
      <span aria-hidden="true"> · changed</span>
      <span className="sr-only"> (changed)</span>
    </span>
  );
}
