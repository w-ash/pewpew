import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Socket } from "../wire/socket";
import { WireContext, WireStore } from "../wire/store";
import { ErrorBoundary } from "../design/ErrorBoundary";
import { EditHistory } from "../params/history";
import "../styles.css";
import { App } from "./App";

const store = new WireStore();
const socket = new Socket(store);
const edits = new EditHistory(store, socket);
socket.start();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WireContext.Provider value={{ store, sender: edits.sender, edits }}>
      <ErrorBoundary fallback={<p className="crashed">The page hit an error. Reload it; the aura keeps running.</p>}>
        <App />
      </ErrorBoundary>
    </WireContext.Provider>
  </StrictMode>,
);
