// Every input type that takes no typed text; any other input does.
const NOT_TEXT = new Set(["checkbox", "radio", "range", "button", "submit", "reset", "image", "file", "color", "hidden"]);

/** Whether `el` takes typed text, where keys belong to the text: shortcuts,
 * Esc and Backspace-to-reset stay out. A switch's or a segment's hidden
 * input is not text entry, nor is a list: it takes only letters, for its
 * type-ahead. */
export function isTextEntry(el: Element | null): boolean {
  if (!el) return false;
  if (el instanceof HTMLInputElement) return !NOT_TEXT.has(el.type);
  return el instanceof HTMLTextAreaElement || (el as HTMLElement).isContentEditable;
}
