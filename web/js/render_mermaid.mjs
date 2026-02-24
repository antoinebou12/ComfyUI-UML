#!/usr/bin/env node
/**
 * Render Mermaid source to SVG or ASCII using beautiful-mermaid.
 * Reads source from stdin or from a file path (first argument).
 * Theme: set BEAUTIFUL_MERMAID_THEME to a built-in theme name (e.g. tokyo-night).
 * Output: set BEAUTIFUL_MERMAID_OUTPUT to "ascii" (or "svg", default) to export ASCII instead of SVG.
 * ASCII mode: set BEAUTIFUL_MERMAID_ASCII_USE_ASCII=1 for pure ASCII; otherwise Unicode box-drawing.
 * Writes to stdout; errors go to stderr and exit code 1.
 */

import { readFileSync } from "fs";
import { renderMermaidSVG, renderMermaidASCII, THEMES } from "beautiful-mermaid";

function main() {
  let code;
  if (process.argv[2]) {
    code = readFileSync(process.argv[2], "utf8");
  } else {
    if (process.stdin.isTTY) {
      console.error("Usage: node render_mermaid.mjs [path-to-mermaid-file]");
      console.error("Env: BEAUTIFUL_MERMAID_THEME, BEAUTIFUL_MERMAID_OUTPUT=svg|ascii, BEAUTIFUL_MERMAID_ASCII_USE_ASCII=1");
      process.exit(1);
    }
    code = readFileSync(0, "utf8");
  }

  if (!code || !code.trim()) {
    console.error("Empty Mermaid source.");
    process.exit(1);
  }

  const outputMode = (process.env.BEAUTIFUL_MERMAID_OUTPUT || "svg").toLowerCase().trim();
  const useAscii = process.env.BEAUTIFUL_MERMAID_ASCII_USE_ASCII === "1" || process.env.BEAUTIFUL_MERMAID_ASCII_USE_ASCII === "true";

  if (outputMode === "ascii") {
    try {
      const themeName = process.env.BEAUTIFUL_MERMAID_THEME;
      const themeOptions = themeName && THEMES[themeName] ? THEMES[themeName] : {};
      const ascii = renderMermaidASCII(code.trim(), {
        useAscii,
        theme: themeOptions,
      });
      process.stdout.write(ascii);
    } catch (err) {
      console.error(err instanceof Error ? err.message : String(err));
      process.exit(1);
    }
    return;
  }

  const themeName = process.env.BEAUTIFUL_MERMAID_THEME;
  const options = themeName && THEMES[themeName] ? { ...THEMES[themeName] } : {};
  options.transparent = true;

  try {
    const svg = renderMermaidSVG(code.trim(), options);
    process.stdout.write(svg);
  } catch (err) {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
  }
}

main();
