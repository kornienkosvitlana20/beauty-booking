import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" потрібен, щоб Electron відкривав dist/index.html через file://
export default defineConfig({ plugins: [react()], base: "./" });
