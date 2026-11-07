/** A WebSocket the tests drive, for the page's Socket: each one made is in `made`, what the page sends is in
 * `sent`, parsed, and `receive` plays what the server would. It opens on `open()`, as a real one does a
 * moment after it is made. */
export class FakeWebSocket {
  static readonly OPEN = 1;
  static made: FakeWebSocket[] = [];
  readyState = 0;
  binaryType: BinaryType = "blob";
  // Any, so a test reads a message's fields by name.
  sent: Record<string, any>[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((ev: { data: unknown }) => void) | null = null;
  constructor(readonly url: string) {
    FakeWebSocket.made.push(this);
  }
  send(text: string) {
    this.sent.push(JSON.parse(text));
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  /** A message from the server: text and frames as they are, an object as its JSON. */
  receive(data: string | ArrayBuffer | object) {
    this.onmessage?.({ data: typeof data === "string" || data instanceof ArrayBuffer ? data : JSON.stringify(data) });
  }
  types(): string[] {
    return this.sent.map((m) => m.type);
  }
}
