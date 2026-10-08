import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Forward any request starting with /api to the Python backend.
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
