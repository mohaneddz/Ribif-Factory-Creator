import { afterEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_SIM_PARAMS, gaussianRandom, generateTelemetry, poissonRandom } from "./digitalTwinUtils";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("gaussianRandom", () => {
  it("stays finite when Math.random returns 0", () => {
    vi.spyOn(Math, "random").mockReturnValue(0);
    expect(Number.isFinite(gaussianRandom(65, 5))).toBe(true);
  });

  it("centres on the mean", () => {
    const samples = Array.from({ length: 4000 }, () => gaussianRandom(65, 5));
    const mean = samples.reduce((sum, v) => sum + v, 0) / samples.length;
    expect(mean).toBeGreaterThan(64);
    expect(mean).toBeLessThan(66);
  });
});

describe("poissonRandom", () => {
  it("returns non-negative integers averaging lambda", () => {
    const samples = Array.from({ length: 4000 }, () => poissonRandom(2));
    expect(samples.every((v) => Number.isInteger(v) && v >= 0)).toBe(true);
    const mean = samples.reduce((sum, v) => sum + v, 0) / samples.length;
    expect(mean).toBeGreaterThan(1.8);
    expect(mean).toBeLessThan(2.2);
  });
});

describe("generateTelemetry", () => {
  it("keeps bounded readings in range", () => {
    for (let step = 0; step < 200; step++) {
      const frame = generateTelemetry(DEFAULT_SIM_PARAMS, step);
      expect(frame.deviceUsage).toBeGreaterThanOrEqual(0);
      expect(frame.deviceUsage).toBeLessThanOrEqual(100);
      expect(frame.vibration).toBeGreaterThanOrEqual(0);
      expect(frame.productionRate).toBeGreaterThanOrEqual(0);
      expect(frame.errorRate).toBeGreaterThanOrEqual(0);
    }
  });

  it("degrades remaining life linearly and never below zero", () => {
    expect(generateTelemetry(DEFAULT_SIM_PARAMS, 0).remainingLife).toBe(100);
    expect(generateTelemetry(DEFAULT_SIM_PARAMS, 1000).remainingLife).toBeCloseTo(90);
    expect(generateTelemetry(DEFAULT_SIM_PARAMS, 1_000_000).remainingLife).toBe(0);
  });
});
