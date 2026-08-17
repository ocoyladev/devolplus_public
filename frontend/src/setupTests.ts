import "@testing-library/jest-dom";

// jsdom no implementa scrollIntoView; shim mínimo para los componentes que lo usan.
if (typeof Element.prototype.scrollIntoView !== "function") {
  Element.prototype.scrollIntoView = (): void => {};
}

// jsdom no implementa WebSocket; shim mínimo para los componentes que lo usan.
if (typeof globalThis.WebSocket === "undefined") {
  class FakeWebSocket {
    onopen: (() => void) | null = null;
    onclose: (() => void) | null = null;
    onmessage: ((ev: MessageEvent) => void) | null = null;
    constructor(_url: string) {}
    close(): void {}
    send(): void {}
  }
  (globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket;
}
