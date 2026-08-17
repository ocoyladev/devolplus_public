import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En dev, Vite sirve en 5174 y proxya /api al backend admin (8090).
// En build, FastAPI sirve dist/ same-origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/api": "http://127.0.0.1:8090",
    },
  },
  build: { outDir: "dist" },
});
