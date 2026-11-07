import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { AppBoundary } from "./AppBoundary";
import { createQueryClient } from "./api/queries";
import "../styles.css";
import "./studio.css";

async function start() {
  if (import.meta.env.MODE === "mock") {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass", quiet: true });
  }
  const root = document.getElementById("root");
  if (!root) throw new Error("Root element not found");
  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={createQueryClient()}>
        <AppBoundary>
          <App />
        </AppBoundary>
      </QueryClientProvider>
    </StrictMode>,
  );
}

void start();
