// Optional in-process build for Windows sandboxes that cannot create child-process pipes.
// Standard `npm run build` continues to use Vite's default esbuild pipeline.
import "./portable-runtime.mjs";
import { build } from "vite";
import ts from "typescript";

await build({
  configFile: false,
  esbuild: false,
  plugins: [
    {
      name: "typescript-portable",
      enforce: "pre",
      transform(code, id) {
        if (!/\.[cm]?[jt]sx?(?:\?|$)/.test(id)) return null;
        // Resolve the only environment references used by this app and its React dependencies
        // before Vite's define plugin, which otherwise starts an esbuild subprocess.
        code = code
          .replace(/\bprocess\.env\.NODE_ENV\b/g, '"production"')
          .replace(/\bprocess\.env\b/g, "({})")
          .replace(/\bimport\.meta\.hot\b/g, "undefined")
          .replace(
            /\bimport\.meta\.env\.VITE_API_URL\b/g,
            JSON.stringify(process.env.VITE_API_URL || "/api"),
          );
        if (/\.[cm]?tsx?(?:\?|$)/.test(id) && !id.includes("node_modules")) {
          code = ts.transpileModule(code, {
            fileName: id.split("?")[0],
            compilerOptions: {
              target: ts.ScriptTarget.ES2022,
              module: ts.ModuleKind.ESNext,
              jsx: ts.JsxEmit.ReactJSX,
              sourceMap: false,
            },
          }).outputText;
        }
        return { code, map: null };
      },
    },
  ],
  build: { target: "esnext", minify: false, chunkSizeWarningLimit: 1500 },
});
