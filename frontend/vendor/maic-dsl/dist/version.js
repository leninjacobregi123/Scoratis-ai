/**
 * DSL version + migration scaffolding.
 *
 * The DSL version is independent of the npm package version: it identifies the
 * shape of the serialized slide contract so that persisted documents can be
 * migrated forward as the schema evolves.
 *
 * This is intentionally a stub: the real migration registry is filled in once
 * the first breaking schema change lands. The types below pin down the shape
 * that registry will take so callers can already code against it.
 */
/** Current version of the serialized slide contract. */
export const DSL_VERSION = '0.1.0';
/**
 * Ordered list of migrations. Empty until the first breaking change ships.
 * Keep entries sorted so `from(n).to === from(n+1).from`.
 */
export const DSL_MIGRATIONS = [];
//# sourceMappingURL=version.js.map