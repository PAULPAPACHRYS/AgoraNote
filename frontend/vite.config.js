// vite.config.js: settings for Vite, the development server and build tool of the frontend.
// `npm run dev` serves the app with instant reloads; `npm run build` makes the production files in dist/.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()], // JSX support and fast refresh for React
  server: {
    port: 5173,
    // File-change events don't cross Docker bind mounts on Windows/macOS, so poll instead.
    watch: { usePolling: true },
  },
});
