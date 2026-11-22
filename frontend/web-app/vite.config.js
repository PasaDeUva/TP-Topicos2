import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const identityProxyTarget = process.env.IDENTITY_PROXY_TARGET || "http://identity-service:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5174,
    strictPort: true,
    cors: false,
    proxy: { "/auth": { target: identityProxyTarget }, "/admin": { target: identityProxyTarget } },
  },
});
