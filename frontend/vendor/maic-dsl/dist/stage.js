// ---------------------------------------------------------------------------
// Pure discriminant guards
// ---------------------------------------------------------------------------
/**
 * Narrow a candidate to {@link SlideContent}. Accepts any value tagged with a
 * `type: SceneType` discriminant — including an app-widened content union that
 * adds interactive / pbl kinds beyond the contract's universal two.
 * Pure, no runtime deps.
 */
export function isSlideContent(content) {
    return content.type === 'slide';
}
/**
 * Narrow a candidate to {@link QuizContent}. Accepts any value tagged with a
 * `type: SceneType` discriminant — including an app-widened content union that
 * adds interactive / pbl kinds beyond the contract's universal two.
 * Pure, no runtime deps.
 */
export function isQuizContent(content) {
    return content.type === 'quiz';
}
//# sourceMappingURL=stage.js.map