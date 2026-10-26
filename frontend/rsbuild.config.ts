import { defineConfig } from '@rsbuild/core';
import { pluginReact } from '@rsbuild/plugin-react';

// `npm run dev` serves on :3000 and forwards /api to the Python server (REQDOC_PORT, default 8000).
// `npm run build` writes frontend/dist, which the Python server serves at "/".
const apiPort = process.env.REQDOC_PORT ?? '8000';

export default defineConfig({
  plugins: [pluginReact()],
  html: { title: 'ReqDoc AI' },
  server: {
    port: 3000,
    proxy: { '/api': `http://localhost:${apiPort}` },
  },
});
