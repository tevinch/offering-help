import { defineConfig } from "vite";

export default defineConfig({
  cacheDir: ".vite",
  define: { "process.env.IS_PREACT": JSON.stringify("false") },
});
