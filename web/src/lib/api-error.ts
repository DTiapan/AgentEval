/** Map FastAPI / engine error bodies to a single toast-friendly string. */

export function formatApiErrorBody(body: unknown, fallback = "Request failed"): string {
  if (body === null || body === undefined) return fallback;
  if (typeof body === "string") return body;
  if (typeof body !== "object") return String(body);

  const record = body as Record<string, unknown>;
  const detail = record.detail;

  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const row = item as { msg?: string; loc?: unknown };
          const msg = row.msg ?? "";
          const loc = Array.isArray(row.loc) ? row.loc.filter(Boolean).join(".") : "";
          return loc ? `${loc}: ${msg}` : msg;
        }
        return JSON.stringify(item);
      })
      .filter(Boolean);
    if (parts.length) return parts.join("; ");
  }

  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }

  const message = record.message;
  if (typeof message === "string" && message.trim()) return message;

  try {
    return JSON.stringify(body);
  } catch {
    return fallback;
  }
}
