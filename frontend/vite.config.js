import path from "path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import frameworkUI from "@framework/ui/vite";
import { VitePWA } from "vite-plugin-pwa";

const appRoot = path.resolve(import.meta.dirname, "..");
const outDir = path.resolve(appRoot, "kxcompliance/public/frontend");

export default defineConfig({
	plugins: [
		frappeui({
			frontendRoute: "/compliance",
			frappeProxy: true,
			lucideIcons: true,
			jinjaBootData: true,
			buildConfig: {
				outDir,
				indexHtmlPath: path.resolve(appRoot, "kxcompliance/www/compliance.html"),
				baseUrl: "/assets/kxcompliance/frontend/",
				emptyOutDir: true,
			},
		}),
		vue(),
		// Frappe's own shared components (apps/frappe/ui), compiled here with this app's copies.
		frameworkUI(),
		VitePWA({
			// The manifest comes from /compliance_manifest.json, which carries each site's
			// own app name and logo; the worker is served from /compliance_sw.js and
			// registered in main.js, so it can control /compliance.
			manifest: false,
			injectRegister: false,
			filename: "sw.js",
			workbox: {
				// The worker is served from /compliance_sw.js, so each built file needs its full
				// path; index.html is only the template Frappe renders as /compliance.
				modifyURLPrefix: { "": "/assets/kxcompliance/frontend/" },
				// The privacy notice's editor and a record's activity are used online; phones need not
				// keep them.
				globIgnores: [
					"**/index.html",
					"**/NoticeEditor-*.js",
					"**/NoticeEditor-*.css",
					"**/RecordActivity-*.js",
					"**/RecordActivity-*.css",
					// The editor they share, for the notice and comments: online only.
					"**/editor-*.js",
					"**/editor-*.css",
				],
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
						// The ping is left alone: it is how the app asks whether the server answers.
						urlPattern: ({ url, request }) =>
							request.method === "GET" &&
							url.pathname.startsWith("/api/") &&
							url.pathname !== "/api/method/ping",
						handler: "NetworkFirst",
						options: {
							cacheName: "compliance-reads",
							networkTimeoutSeconds: 4,
							expiration: { maxEntries: 500, maxAgeSeconds: 14 * 24 * 60 * 60 },
							plugins: [
								{
									// Mark a saved copy, so the page knows the server did not answer.
									cachedResponseWillBeUsed: async ({ cachedResponse }) => {
										if (!cachedResponse) return cachedResponse;
										const headers = new Headers(cachedResponse.headers);
										headers.set("X-Served-From", "cache");
										return new Response(await cachedResponse.blob(), {
											status: cachedResponse.status,
											statusText: cachedResponse.statusText,
											headers,
										});
									},
								},
							],
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
		// The screenshot capture under e2e/ runs with Playwright, not Vitest.
		include: ["src/**/*.test.js"],
	},
});
