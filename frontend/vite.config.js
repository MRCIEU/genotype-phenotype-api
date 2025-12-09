import { resolve } from "path";
import { defineConfig } from "vite";
import { readdirSync, statSync } from "fs";

function findHtmlFiles(dir, baseDir = dir) {
    const files = {};

    try {
        const entries = readdirSync(dir);

        for (const entry of entries) {
            const fullPath = resolve(dir, entry);
            const stat = statSync(fullPath);

            if (stat.isDirectory()) {
                Object.assign(files, findHtmlFiles(fullPath, baseDir));
            } else if (entry.endsWith(".html")) {
                const relativePath = fullPath.replace(baseDir + "/", "");
                const key = relativePath.includes("/")
                    ? relativePath.replace(".html", "").replace("/", "-")
                    : entry.replace(".html", "");
                files[key] = fullPath;
            }
        }
    } catch (error) {
        console.warn(`Could not read directory ${dir}:`, error.message);
    }

    return files;
}

const htmlFiles = findHtmlFiles(__dirname);

export default defineConfig({
    css: {
        devSourcemap: true, // Enable CSS source maps
    },
    watch: {
        usePolling: true,
    },
    base: "./",
    build: {
        sourcemap: true, // Enable source maps for production
        chunkSizeWarningLimit: 1024, // kB
        rollupOptions: {
            input: htmlFiles,
        },
    },
});
