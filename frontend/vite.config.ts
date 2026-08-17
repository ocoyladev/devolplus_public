import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En dev, Vite sirve en 5173 y proxya /api y /ws al backend (8000).
// En build, FastAPI sirve dist/ con same-origin, así que el proxy no aplica.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  build: { outDir: "dist" },
});
