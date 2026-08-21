import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Tauri dev server must run on a fixed port; see tauri.conf.json devUrl.
export default defineConfig({
  plugins: [vue()],
  // Tauri requires a deterministic port and strict host for the dev server.
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "127.0.0.1",
  },
  // Env vars prefixed with TAURI_ are exposed to the frontend.
  envPrefix: ["VITE_", "TAURI_"],
  build: {
    // Tauri desktop builds favor larger chunks; leave warnings off for MVP.
    chunkSizeWarningLimit: 2000,
  },
});
