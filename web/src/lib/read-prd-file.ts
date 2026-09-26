/** Client-side PRD import — text only; content is sent to POST /v1/suites/preview|init. */

export const PRD_FILE_ACCEPT = ".md,.markdown,.txt";
export const MAX_PRD_FILE_BYTES = 512 * 1024;

const ALLOWED_EXT = new Set(["md", "markdown", "txt"]);

export function prdFileExtension(name: string): string | null {
  const dot = name.lastIndexOf(".");
  if (dot < 0) return null;
  return name.slice(dot + 1).toLowerCase();
}

export function isAllowedPrdFile(file: File): boolean {
  const ext = prdFileExtension(file.name);
  return ext !== null && ALLOWED_EXT.has(ext);
}

/** Slug for agent id suggestion from filename (not validated server-side here). */
export function agentIdFromPrdFilename(name: string): string {
  const base = name.replace(/\.[^.]+$/, "");
  return base
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

export async function readPrdFile(file: File): Promise<string> {
  if (!isAllowedPrdFile(file)) {
    throw new Error(`Unsupported file type. Use ${PRD_FILE_ACCEPT}.`);
  }
  if (file.size > MAX_PRD_FILE_BYTES) {
    throw new Error(`File exceeds ${Math.round(MAX_PRD_FILE_BYTES / 1024)} KB limit.`);
  }
  const text = await file.text();
  if (!text.trim()) {
    throw new Error("File is empty.");
  }
  return text;
}
