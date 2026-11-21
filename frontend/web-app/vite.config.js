import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5174,
    strictPort: true,
    cors: false,
    proxy: { "/auth": { target: "http://identity-service:8000" } },
  },
});
