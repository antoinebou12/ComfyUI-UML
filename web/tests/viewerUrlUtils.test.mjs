/**
 * Unit tests for viewerUrlUtils.mjs (formatFromUrl, buildViewerQuery).
 * Browser-compatible: run by opening test-runner.html in a browser or via a test runner.
 */
import { formatFromUrl, buildViewerQuery } from "../viewerUrlUtils.mjs";

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(message || `Expected "${expected}", got "${actual}"`);
  }
}

function assertIncludes(str, substring, message) {
  if (!str || !str.includes(substring)) {
    throw new Error(message || `Expected string to contain "${substring}", got "${str}"`);
  }
}

const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

// --- formatFromUrl ---
test("formatFromUrl: null/undefined returns svg", () => {
  assertEqual(formatFromUrl(null), "svg");
  assertEqual(formatFromUrl(undefined), "svg");
});

test("formatFromUrl: empty string returns svg", () => {
  assertEqual(formatFromUrl(""), "svg");
});

test("formatFromUrl: data URL image/svg+xml returns svg", () => {
  assertEqual(formatFromUrl("data:image/svg+xml;base64,PHN2Zy8+"), "svg");
  assertEqual(formatFromUrl("data:image/svg+xml,<%3Csvg/>"), "svg");
});

test("formatFromUrl: data URL image/png or image/jpeg returns png", () => {
  assertEqual(formatFromUrl("data:image/png;base64,abc"), "png");
  assertEqual(formatFromUrl("data:image/jpeg;base64,xyz"), "png");
});

test("formatFromUrl: data URL text/plain returns txt", () => {
  assertEqual(formatFromUrl("data:text/plain;base64,SGVsbG8="), "txt");
  assertEqual(formatFromUrl("data:text/plain,hello"), "txt");
});

test("formatFromUrl: data URL text/markdown returns markdown", () => {
  assertEqual(formatFromUrl("data:text/markdown;base64,IyBo"), "markdown");
});

test("formatFromUrl: data URL unknown type returns svg", () => {
  assertEqual(formatFromUrl("data:application/octet-stream;base64,abc"), "svg");
});

test("formatFromUrl: Kroki-style path /svg/ returns svg", () => {
  assertEqual(formatFromUrl("https://kroki.io/plantuml/svg/abc"), "svg");
});

test("formatFromUrl: Kroki-style path /png/ or /jpeg/ returns png", () => {
  assertEqual(formatFromUrl("https://example.com/diagram/png/xyz"), "png");
  assertEqual(formatFromUrl("https://example.com/diagram/jpeg/xyz"), "png");
});

test("formatFromUrl: Kroki-style path /txt/ returns txt", () => {
  assertEqual(formatFromUrl("https://example.com/out/txt/foo"), "txt");
});

test("formatFromUrl: URL with no format path returns svg", () => {
  assertEqual(formatFromUrl("https://example.com/other"), "svg");
});

test("formatFromUrl: trims input", () => {
  assertEqual(formatFromUrl("  data:image/png;base64,x  "), "png");
});

// --- buildViewerQuery ---
test("buildViewerQuery: encodes url and adds format", () => {
  const q = buildViewerQuery("https://kroki.io/plantuml/svg/abc", "svg");
  assertIncludes(q, "?");
  assertIncludes(q, "url=");
  assertIncludes(q, "format=svg");
  assertEqual(q.startsWith("?"), true);
});

test("buildViewerQuery: url encoding", () => {
  const url = "https://example.com?a=1&b=2";
  const q = buildViewerQuery(url);
  assertIncludes(q, encodeURIComponent(url));
});

test("buildViewerQuery: embed=1 when embed true", () => {
  const q = buildViewerQuery("https://x.com/d", undefined, true);
  assertIncludes(q, "embed=1");
});

test("buildViewerQuery: no embed when embed false", () => {
  const q = buildViewerQuery("https://x.com/d", undefined, false);
  assertEqual(q.includes("embed=1"), false);
});

test("buildViewerQuery: infers format from url when format omitted", () => {
  const q = buildViewerQuery("https://kroki.io/plantuml/png/xyz");
  assertIncludes(q, "format=png");
});

test("buildViewerQuery: explicit format overrides inference", () => {
  const q = buildViewerQuery("https://kroki.io/plantuml/png/xyz", "svg");
  assertIncludes(q, "format=svg");
});

test("buildViewerQuery: empty format falls back to inference", () => {
  const q = buildViewerQuery("https://kroki.io/plantuml/txt/foo", "");
  assertIncludes(q, "format=txt");
});

/**
 * Run all tests. Returns { passed, failed, total, results }.
 * In browser, can be called from test-runner.html.
 */
export function run() {
  const results = [];
  let passed = 0;
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      fn();
      results.push({ name, ok: true });
      passed++;
    } catch (err) {
      results.push({ name, ok: false, error: err.message });
      failed++;
    }
  }
  return { passed, failed, total: tests.length, results };
}
