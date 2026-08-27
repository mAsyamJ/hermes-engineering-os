import { build } from "esbuild";
import { mkdir } from "node:fs/promises";

await mkdir(new URL("./dist/", import.meta.url), { recursive: true });
await build({
  entryPoints: [new URL("./src/index.ts", import.meta.url).pathname],
  outfile: new URL("./dist/index.js", import.meta.url).pathname,
  bundle: true,
  format: "iife",
  target: "es2020",
  minify: false,
  legalComments: "inline",
  banner: { js: "/* Hermes Engineering OS dashboard — generated; do not edit */" },
});

