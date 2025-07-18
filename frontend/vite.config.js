import { resolve } from 'path'
import { defineConfig } from 'vite'
// import glob from 'glob'

export default defineConfig({
    css: {
        devSourcemap: true,    // Enable CSS source maps
    },
    watch: {
        usePolling: true,
    },
    base: './',
    build: {
        sourcemap: true,    // Enable source maps for production
        chunkSizeWarningLimit: 1024, // kB
        rollupOptions: {
            input: {// Object.fromEntries(
                main: resolve(__dirname, 'index.html'),
                gene: resolve(__dirname, 'gene.html'),
                phenotype: resolve(__dirname, 'phenotype.html'),
                region: resolve(__dirname, 'region.html'),
                snp: resolve(__dirname, 'snp.html'),
                about: resolve(__dirname, 'about.html'),
                "navigation-bar": resolve(__dirname, 'web-components/navigation-bar.html'),
                "graph-options": resolve(__dirname, 'web-components/graph-options.html'),
                "pipeline-summary": resolve(__dirname, 'web-components/pipeline-summary.html'),
                // glob.sync('*.html').map(file => [
                    // file.slice(0, file.length - 5),
                    // resolve(__dirname, file)
                // ])
            // )
            }
        }
    }
})