/**
 * Markdown view: renders markdown string to HTML (minimal subset, no deps).
 * Used when format is "markdown". Styled with ComfyUI theme vars.
 */
function simpleMarkdownToHtml(md) {
  if (typeof md !== "string") return "";
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const lines = html.split("\n");
  const out = [];
  let inCodeBlock = false;
  let codeBlockContent = [];
  let codeLang = "";

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("```")) {
      if (inCodeBlock) {
        out.push("<pre><code" + (codeLang ? ' class="language-' + codeLang + '"' : "") + ">");
        out.push(codeBlockContent.join("\n"));
        out.push("</code></pre>");
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

    let rest = line;
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
    out.push("<pre><code>");
    out.push(codeBlockContent.join("\n"));
    out.push("</code></pre>");
  }

  return out.join("\n");
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
  return Promise.resolve();
}
