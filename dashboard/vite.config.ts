import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// base "./" makes the build work at any path: GitHub Pages (/Evolvra/), a custom domain, or file://
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: { output: { manualChunks: { react: ["react", "react-dom"], motion: ["motion"], diff: ["diff"] } } },
  },
});
