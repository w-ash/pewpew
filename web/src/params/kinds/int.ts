import type { IntParam } from "../schema";
import { numericKind } from "./numeric";

export const int = numericKind<IntParam>("int", true);
