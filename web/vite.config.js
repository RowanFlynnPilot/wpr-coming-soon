import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the widget deploys under any GitHub Pages path.
// Two pages: the public widget (index) and the internal editor queue.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL("index.html", import.meta.url)),
        queue: fileURLToPath(new URL("queue.html", import.meta.url)),
      },
    },
  },
});
