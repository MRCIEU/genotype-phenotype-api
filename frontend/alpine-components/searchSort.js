/**
 * Sort order for /search/options rows (traits + genes) in typeahead UIs.
 * 1) Any colocalisation groups first; rare-only (zero coloc groups) second.
 * 2) Within each tier, higher (rare + coloc) totals first.
 */
export function compareSearchTerms(a, b) {
    const ca = a.num_coloc_groups ?? 0;
    const cb = b.num_coloc_groups ?? 0;
    const aHasColoc = ca > 0;
    const bHasColoc = cb > 0;
    if (aHasColoc !== bHasColoc) {
        return Number(bHasColoc) - Number(aHasColoc);
    }
    const totalA = (a.num_rare_results ?? 0) + ca;
    const totalB = (b.num_rare_results ?? 0) + cb;
    return totalB - totalA;
}
