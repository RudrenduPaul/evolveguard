import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'lcov'],
      include: ['src/evolveguard/**/*.ts'],
      exclude: ['src/evolveguard/**/*.test.ts', 'src/evolveguard/index.ts'],
      thresholds: {
        lines: 80,
      },
    },
  },
});
