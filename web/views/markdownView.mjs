/**
 * Markdown view: renders markdown string to HTML (minimal subset, no deps).
 * Supports ```mermaid blocks (rendered by Mermaid.js) and $ / $$ math (rendered by KaTeX).
 * Used when format is "markdown". Styled with ComfyUI theme vars.
 */
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function simpleMarkdownToHtml(md) {
  if (typeof md !== "string") return "";
  const lines = md.split("\n");
  const out = [];
  let inCodeBlock = false;
  let codeBlockContent = [];
  let codeLang = "";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        const isMermaid = /^mermaid$/i.test(codeLang);
        if (isMermaid) {
          out.push("<div class=\"mermaid\">");
          out.push(codeBlockContent.join("\n"));
          out.push("</div>");
        } else {
          const escaped = escapeHtml(codeBlockContent.join("\n"));
          out.push("<pre><code" + (codeLang ? " class=\"language-" + escapeHtml(codeLang) + "\"" : "") + ">");
          out.push(escaped);
          out.push("</code></pre>");
        }
        codeBlockContent = [];
        codeLang = "";
        inCodeBlock = false;
      } else {
        codeLang = line.slice(3).trim();
        inCodeBlock = true;
      }
      continue;
    }
    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    const escapedLine = escapeHtml(line);
    let rest = escapedLine;
    if (/^#####\s/.test(rest)) {
      rest = "<h5>" + rest.slice(5).trim() + "</h5>";
    } else if (/^####\s/.test(rest)) {
      rest = "<h4>" + rest.slice(4).trim() + "</h4>";
    } else if (/^###\s/.test(rest)) {
      rest = "<h3>" + rest.slice(3).trim() + "</h3>";
    } else if (/^##\s/.test(rest)) {
      rest = "<h2>" + rest.slice(2).trim() + "</h2>";
    } else if (/^#\s/.test(rest)) {
      rest = "<h1>" + rest.slice(1).trim() + "</h1>";
    } else {
      rest = rest
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      if (rest.trim()) rest = "<p>" + rest + "</p>";
    }
    out.push(rest);
  }

  if (inCodeBlock) {
    const isMermaid = /^mermaid$/i.test(codeLang);
    if (isMermaid) {
      out.push("<div class=\"mermaid\">");
      out.push(codeBlockContent.join("\n"));
      out.push("</div>");
    } else {
      out.push("<pre><code>");
      out.push(escapeHtml(codeBlockContent.join("\n")));
      out.push("</code></pre>");
    }
  }

  return out.join("\n");
}

const MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
const KATEX_CSS = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css";
const KATEX_AUTORENDER = "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.mjs";

let mermaidLoaded = null;
let katexLoaded = null;

function ensureKatexCss() {
  const id = "comfyui-uml-katex-css";
  if (document.getElementById(id)) return;
  const link = document.createElement("link");
  link.id = id;
  link.rel = "stylesheet";
  link.href = KATEX_CSS;
  link.crossOrigin = "anonymous";
  document.head.appendChild(link);
}

async function runMermaid(wrap) {
  const nodes = wrap.querySelectorAll(".mermaid");
  if (!nodes.length) return;
  try {
    if (!mermaidLoaded) {
      const mod = await import(/* @vite-ignore */ MERMAID_CDN);
      const mermaid = mod.default;
      mermaid.initialize({ theme: "dark", startOnLoad: false });
      mermaidLoaded = mermaid;
    }
    await mermaidLoaded.run({ nodes });
  } catch (e) {
    Array.from(nodes).forEach((el) => {
      const raw = el.textContent || "";
      el.outerHTML =
        "<div class=\"mermaid-error\" style=\"background:var(--comfy-button-bg,#333);padding:12px;border-radius:4px;color:var(--comfy-error,#e66);font-size:13px;white-space:pre-wrap;\">" +
        "Mermaid error: " + escapeHtml(String(e && e.message ? e.message : e)) +
        (raw ? "\n\nRaw:\n" + escapeHtml(raw) : "") +
        "</div>";
    });
  }
}

async function runKaTeX(wrap) {
  ensureKatexCss();
  try {
    if (!katexLoaded) {
      katexLoaded = import(/* @vite-ignore */ KATEX_AUTORENDER);
    }
    const mod = await katexLoaded;
    const renderMathInElement = mod.default;
    if (typeof renderMathInElement !== "function") return;
    renderMathInElement(wrap, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
      ignoredClasses: ["mermaid"],
    });
  } catch (_) {
    // Leave math as plain text if CDN fails
  }
}

export function render(container, data) {
  if (!container) return Promise.resolve();
  const raw = typeof data === "string" ? data : String(data ?? "");
  const html = simpleMarkdownToHtml(raw);
  const wrap = document.createElement("div");
  wrap.className = "viewport markdown-body";
  wrap.style.cssText =
    "padding:20px; overflow:auto; color:var(--comfy-text,#AAA); font-size:14px; line-height:1.5; " +
    "max-width:100%; box-sizing:border-box;";
  wrap.innerHTML = html || "<p>(empty)</p>";
  wrap.querySelectorAll("a").forEach((a) => {
    a.style.color = "var(--comfy-link,#6af)";
  });
  wrap.querySelectorAll("code").forEach((c) => {
    c.style.cssText = "background:var(--comfy-button-bg,#333); padding:2px 6px; border-radius:4px; font-size:13px;";
  });
  wrap.querySelectorAll("pre").forEach((p) => {
    p.style.cssText = "background:var(--comfy-bg-node,#353535); padding:12px; border-radius:4px; overflow:auto;";
  });
  const layer = document.createElement("div");
  layer.className = "pan-zoom-layer";
  layer.appendChild(wrap);
  container.innerHTML = "";
  container.appendChild(layer);

  return (async () => {
    await runMermaid(wrap);
    await runKaTeX(wrap);
  })();
}
