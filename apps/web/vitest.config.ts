import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.spec.ts'],
    tsconfig: 'tsconfig.spec.json',
    setupFiles: ['src/test-setup.ts'],
  },
});
