/**
 * Package-level CSS rules that can't be expressed inline (descendant selectors,
 * keyframes, pseudo-classes). Rendered once via `<style>` at the top of
 * `<SlideCanvas>` so the package stays self-contained without Tailwind.
 *
 * The `.slide-renderer-prose` rules are intentionally minimal "browser-default
 * resets" — they un-do the user-agent stylesheet (1em <p> margin, KaTeX block
 * margin) so the slide JSON is the single source of truth. They do not
 * positively style anything; spacing comes from the data via the
 * `--paragraphSpace` CSS variable, which is unset when undefined in data.
 */
export declare const SLIDE_RENDERER_STYLES = "\n.slide-renderer-prose p {\n  margin-top: 0;\n  margin-bottom: var(--paragraphSpace, 0);\n}\n.slide-renderer-prose p:last-child {\n  margin-bottom: 0;\n}\n.slide-renderer-prose .katex-display {\n  margin: 0 !important;\n}\n/* Table cell inner container \u2014 matches the classroom (Vue) .cell-text design:\n   tight base line-height, and a small spacing between adjacent <p> siblings\n   so multi-paragraph cells don't collapse into a single visual block. The\n   <p> margin reset above sets the baseline to 0; this rule re-adds spacing\n   only between adjacent siblings, leaving the first/last paragraph flush. */\n.slide-renderer-cell-text p + p {\n  margin-top: 0.4em;\n}\n@keyframes slide-renderer-pulse {\n  50% { opacity: 0.5; }\n}\n@keyframes slide-renderer-ping {\n  75%, 100% { transform: scale(2); opacity: 0; }\n}\n@keyframes slide-renderer-code-cursor-blink {\n  0%, 100% { opacity: 1; }\n  50% { opacity: 0; }\n}\n.slide-renderer-pulse {\n  animation: slide-renderer-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;\n}\n.slide-renderer-ping {\n  animation: slide-renderer-ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;\n}\n";
