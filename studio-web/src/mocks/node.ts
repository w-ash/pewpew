import { setupServer } from "msw/node";
import { httpHandlers } from "./handlers";

export const server = setupServer(...httpHandlers);
