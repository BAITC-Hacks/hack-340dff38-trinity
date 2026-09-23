import "./portable-runtime.mjs";
import { preview } from "vite";
const server = await preview({
  configFile: false,
  preview: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
server.printUrls();
