/**
 * Strip the model's internal scratchpad out of a response.
 *
 * MISSION.md tells the tutor to keep its <pedagogical_plan> hidden, but that
 * is a steerability request, not a guarantee - it leaks often enough that
 * every surface rendering a raw stream has to defend against it.
 *
 * Lives here rather than inside a page because there are now two such
 * surfaces (the main chat and the lesson tutor panel). The first version of
 * this logic existed only in Chat.jsx, and the lesson panel shipped without
 * it - the plan block rendered straight to the learner. Sharing one
 * implementation is what stops that recurring.
 *
 * Mirrors backend/api/routes/chat.py::strip_internal_reasoning, which does
 * the same job for the DB-persisted copy; keep the two in step.
 */
export function stripReasoning(content) {
  if (!content) return content;

  let cleaned = content
    .replace(/<pedagogical_plan>[\s\S]*?<\/pedagogical_plan>/gi, '')
    .replace(/\*\*<pedagogical_plan>\*\*[\s\S]*?<\/pedagogical_plan>/gi, '')
    .replace(/<think>[\s\S]*?<\/think>/gi, '');

  // An UNMATCHED closing tag means the model emitted its scratchpad without
  // ever opening the tag, so the paired patterns above matched nothing and
  // the whole plan leaked - which reads as the answer being duplicated.
  // Everything up to and including that stray tag is scratchpad.
  if (/<\/(?:pedagogical_plan|think)>/i.test(cleaned)) {
    const stripped = cleaned.replace(/[\s\S]*<\/(?:pedagogical_plan|think)>\*{0,2}/i, '');
    // Never blank the message out entirely - if the scratchpad was all there
    // was, prefer showing it over showing nothing.
    if (stripped.trim()) cleaned = stripped;
  }

  // While a response is still streaming the opening tag arrives long before
  // its closing partner, so the paired rules above cannot fire yet. Hide the
  // partial block rather than letting the learner watch the plan type itself
  // out and then vanish.
  const openIdx = cleaned.search(/<pedagogical_plan>|<think>/i);
  if (openIdx !== -1) cleaned = cleaned.slice(0, openIdx);

  return cleaned.trim();
}
