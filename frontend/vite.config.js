import path from "path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { VitePWA } from "vite-plugin-pwa";

const appRoot = path.resolve(import.meta.dirname, "..");
const outDir = path.resolve(appRoot, "compliance_plus/public/frontend");

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/compliance",
			frappeProxy: true,
			jinjaBootData: true,
			buildConfig: {
				outDir,
				indexHtmlPath: path.resolve(appRoot, "compliance_plus/www/compliance.html"),
				baseUrl: "/assets/compliance_plus/frontend/",
				emptyOutDir: true,
			},
		}),
		vue(),
		VitePWA({
			// The manifest comes from /compliance_manifest.json, which carries each site's
			// own app name and logo; the worker is served from /compliance_sw.js and
			// registered in main.js, so it can control /compliance.
			manifest: false,
			injectRegister: false,
			filename: "sw.js",
			workbox: {
				inlineWorkboxRuntime: true,
				cleanupOutdatedCaches: true,
				navigateFallback: null,
				runtimeCaching: [
					{
						urlPattern: ({ url, request }) =>
							request.mode === "navigate" && url.pathname.startsWith("/compliance"),
						handler: "NetworkFirst",
						options: { cacheName: "compliance-pages", networkTimeoutSeconds: 4 },
					},
					{
						urlPattern: ({ url, request }) =>
							request.method === "GET" && url.pathname.startsWith("/api/"),
						handler: "NetworkFirst",
						options: {
							cacheName: "compliance-reads",
							networkTimeoutSeconds: 4,
							expiration: { maxEntries: 500, maxAgeSeconds: 14 * 24 * 60 * 60 },
						},
					},
				],
			},
		}),
	],
	resolve: {
		alias: { "@": path.resolve(import.meta.dirname, "src") },
		dedupe: ["vue", "vue-router", "frappe-ui"],
	},
	test: {
		environment: "happy-dom",
	},
});
