#!/usr/bin/env node
/**
 * Render Mermaid source to SVG using beautiful-mermaid.
 * Reads source from stdin or from a file path (first argument).
 * Theme: set BEAUTIFUL_MERMAID_THEME to a built-in theme name (e.g. tokyo-night).
 * Writes SVG to stdout; errors go to stderr and exit code 1.
 */

import { readFileSync } from "fs";
import { renderMermaidSVG, THEMES } from "beautiful-mermaid";

function main() {
  let code;
  if (process.argv[2]) {
    code = readFileSync(process.argv[2], "utf8");
  } else {
    if (process.stdin.isTTY) {
      console.error("Usage: node render_mermaid.mjs [path-to-mermaid-file]");
      process.exit(1);
    }
    code = readFileSync(0, "utf8");
  }

  if (!code || !code.trim()) {
    console.error("Empty Mermaid source.");
    process.exit(1);
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
