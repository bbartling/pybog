export type Lane = 'system' | 'tool' | 'user';

export const LANES: Record<Lane, number> = {
  system: 220,
  tool: 640,
  user: 1060,
};

export const GRID = 18;

export function quantize(value: number, step = GRID) {
  return Math.round(value / step) * step;
}

export function nearestLaneX(x: number): number {
  const xs = Object.values(LANES);
  return xs.reduce((best, cur) => (Math.abs(cur - x) < Math.abs(best - x) ? cur : best), xs[0]);
}
