import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      proxy: {
        // Mount key has no leading slash, and we explicitly prepend
        // the /api prefix in the rewrite to keep both sides consistent.
        // Vite's pathFilter treats "/api" as a literal match; the
        // rewrite re-prefixes the backend route.
        "/api": {
          target: proxyTarget,
          changeOrigin: false,
          rewrite: (p) => {
            // p starts with /api (matched by mount). Pass it through.
            return p;
          },
        },
        "/health": {
          target: proxyTarget,
          changeOrigin: false,
        },
      },
    },
    preview: {
      host: "0.0.0.0",
      port: 5173,
    },
  };
});