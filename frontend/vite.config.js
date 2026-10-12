import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // File-change events don't cross Docker bind mounts on Windows/macOS, so poll instead.
    watch: { usePolling: true },
  },
});
