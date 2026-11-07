import { act } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { renderHook } from "vitest-browser-react";
import { ARM_MS, CONFIRM_MIN_MS, disarmAll, useArm } from "../../src/design/useArm";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

test("the first press arms, the second fires", async () => {
  const fire = vi.fn();
  const { result } = await renderHook(() => useArm());
  act(() => result.current.press(fire));
  expect(result.current.armed).toBe(true);
  expect(fire).not.toHaveBeenCalled();
  await act(() => vi.advanceTimersByTime(CONFIRM_MIN_MS));
  act(() => result.current.press(fire));
  expect(fire).toHaveBeenCalledTimes(1);
  expect(result.current.armed).toBe(false);
});

test("a second press sooner than CONFIRM_MIN_MS is a double tap, not a confirm", async () => {
  const fire = vi.fn();
  const { result } = await renderHook(() => useArm());
  act(() => result.current.press(fire));
  await act(() => vi.advanceTimersByTime(CONFIRM_MIN_MS - 1));
  act(() => result.current.press(fire));
  expect(fire).not.toHaveBeenCalled();
  expect(result.current.armed).toBe(true);
});

test("the arm lapses after ARM_MS", async () => {
  const fire = vi.fn();
  const { result } = await renderHook(() => useArm());
  act(() => result.current.press(fire));
  await act(() => vi.advanceTimersByTime(ARM_MS));
  expect(result.current.armed).toBe(false);
  act(() => result.current.press(fire));
  expect(fire).not.toHaveBeenCalled();
});

test("one action is armed at a time, and Esc disarms it", async () => {
  const fire = vi.fn();
  const a = await renderHook(() => useArm());
  const b = await renderHook(() => useArm());
  act(() => a.result.current.press(fire));
  act(() => b.result.current.press(fire));
  expect(a.result.current.armed).toBe(false);
  expect(b.result.current.armed).toBe(true);
  act(() => disarmAll());
  expect(b.result.current.armed).toBe(false);
  expect(fire).not.toHaveBeenCalled();
});
