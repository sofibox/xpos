/** Legal names and login IDs are deliberately not accepted as fallbacks. */
export function publicNickname(value: unknown): string {
    return typeof value === "string" && value.trim() ? value.trim() : "STAFF";
}
