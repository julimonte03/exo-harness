import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  // Mirrors "paths" in tsconfig.json; '/src' is resolved from the project root.
  resolve: { alias: { '@': '/src' } },
  server: { proxy: { '/api': 'http://localhost:3000' } },
  test: { environment: 'jsdom' },
});
