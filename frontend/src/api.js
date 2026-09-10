export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
      signal: AbortSignal.timeout(40000),
    });
  } catch {
    throw new Error(
      "The server could not be reached or the request timed out. Refresh saved entries before retrying; the operation may already have completed.",
    );
  }
  if (response.status === 204) return null;
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error(
      "The server returned an unreadable response. Refresh saved entries before retrying.",
    );
  }
  if (!response.ok)
    throw new Error(
      body?.error?.message ||
        (typeof body?.detail === "string"
          ? body.detail
          : "Something went wrong. Please try again."),
    );
  return body;
}
