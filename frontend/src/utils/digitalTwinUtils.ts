/**
 * Utility functions for simulating machine telemetry data.
 */

/**
 * Generates a value from a normal (Gaussian) distribution.
 * @param mean The mean of the distribution.
 * @param stdDev The standard deviation of the distribution.
 * @returns A pseudo-random value from the distribution.
 */
export function gaussianRandom(mean: number, stdDev: number): number {
    const u1 = Math.random();
    const u2 = Math.random();
    const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    return z0 * stdDev + mean;
}

/**
 * Generates a value from a Poisson distribution.
 * @param lambda The average rate (mean and variance).
 * @returns A pseudo-random value from the distribution.
 */
export function poissonRandom(lambda: number): number {
    let L = Math.exp(-lambda);
    let p = 1.0;
    let k = 0;
    do {
        k++;
        p *= Math.random();
    } while (p > L);
    return k - 1;
}

export interface TelemetryData {
    timestamp: string;
    temperature: number;
    powerUsage: number;
    deviceUsage: number; // OEE or capacity utilization
    vibration: number;
    soundLevel: number;
    productionRate: number;
    errorRate: number;
    remainingLife: number;
}

export interface SimulationParams {
    tempTarget: number;
    tempStdDev: number;
    powerBase: number;
    powerStdDev: number;
    usageTarget: number;
    usageStdDev: number;
    vibrationBase: number;
    vibrationStdDev: number;
    soundBase: number;
    soundStdDev: number;
    prodRateBase: number;
    prodRateStdDev: number;
    errorRateLambda: number;
    baseLife: number;
    degradationFactor: number;
}

export const DEFAULT_SIM_PARAMS: SimulationParams = {
    tempTarget: 65,
    tempStdDev: 5,
    powerBase: 85,
    powerStdDev: 10,
    usageTarget: 85,
    usageStdDev: 5,
    vibrationBase: 2.5,
    vibrationStdDev: 0.8,
    soundBase: 75,
    soundStdDev: 3,
    prodRateBase: 500,
    prodRateStdDev: 25,
    errorRateLambda: 2,
    baseLife: 100,
    degradationFactor: 0.01,
};

/**
 * Generates a single frame of telemetry data based on parameters.
 */
export function generateTelemetry(params: SimulationParams, timeStep: number): TelemetryData {
    return {
        timestamp: new Date().toLocaleTimeString(),
        temperature: gaussianRandom(params.tempTarget, params.tempStdDev),
        powerUsage: gaussianRandom(params.powerBase, params.powerStdDev),
        deviceUsage: Math.min(100, Math.max(0, gaussianRandom(params.usageTarget, params.usageStdDev))),
        vibration: Math.max(0, gaussianRandom(params.vibrationBase, params.vibrationStdDev)),
        soundLevel: gaussianRandom(params.soundBase, params.soundStdDev),
        productionRate: Math.max(0, gaussianRandom(params.prodRateBase, params.prodRateStdDev)),
        errorRate: (poissonRandom(params.errorRateLambda) / params.prodRateBase) * 100,
        remainingLife: Math.max(0, params.baseLife - (timeStep * params.degradationFactor)),
    };
}
