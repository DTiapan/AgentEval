import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/v1": "http://127.0.0.1:8766",
      "/health": "http://127.0.0.1:8766",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
