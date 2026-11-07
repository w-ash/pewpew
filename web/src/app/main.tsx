import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Socket } from "../infra/wire/socket";
import { WireContext, WireStore } from "../infra/wire/store";
import { ErrorBoundary } from "../ui/common/ErrorBoundary";
import "../ui/styles.css";
import { App } from "./App";

const store = new WireStore();
const socket = new Socket(store, { url: `ws://${location.host}/ws` });
socket.start();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WireContext.Provider value={{ store, sender: socket }}>
      <ErrorBoundary fallback={<p className="crashed">The page hit an error. Reload it; the aura keeps running.</p>}>
        <App />
      </ErrorBoundary>
    </WireContext.Provider>
  </StrictMode>,
);
