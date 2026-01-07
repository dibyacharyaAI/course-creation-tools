/**
 * Canonical ID Helpers for CourseFlow
 * Enforces U1..U6 format internally while dealing with readable "UNIT 1" labels.
 */

/**
 * Normalizes input string to canonical module ID (e.g. "UNIT 1" -> "U1").
 * Returns original if no match found (best-effort).
 * @param {string} id 
 * @returns {string} canonicalId ie "U1"
 */
export function normalizeModuleId(id) {
    if (!id) return id;
    const str = String(id).trim().toUpperCase();

    // "UNIT 1" -> "U1"
    const unitMatch = str.match(/^UNIT\s*(\d+)$/);
    if (unitMatch) {
        return `U${unitMatch[1]}`;
    }

    // "U 1" -> "U1"
    const uMatch = str.match(/^U\s*(\d+)$/);
    if (uMatch) {
        return `U${uMatch[1]}`;
    }

    return str; // Already canonical or unknown format
}

/**
 * Returns human-readable label for display (e.g. "U1" -> "UNIT 1").
 * @param {string} id 
 * @returns {string}
 */
export function displayModuleLabel(id) {
    if (!id) return "";
    const str = String(id).trim().toUpperCase();

    // "U1" -> "UNIT 1"
    const uMatch = str.match(/^U(\d+)$/);
    if (uMatch) {
        return `UNIT ${uMatch[1]}`;
    }

    return str; // Fallback
}

/**
 * Normalizes topic ID (e.g. "U1T2" is canonical).
 * Best effort currently just trims/upcases.
 * @param {string} id 
 * @returns {string}
 */
export function normalizeTopicId(id) {
    if (!id) return id;
    return String(id).trim().toUpperCase();
}
