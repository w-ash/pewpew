import type { FloatParam } from "../schema";
import { numericKind } from "./numeric";

export const float = numericKind<FloatParam>("float", false);
