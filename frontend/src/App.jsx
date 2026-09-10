import { useEffect, useRef, useState } from "react";
import { request } from "./api";

const MAX = 10000;
const SAMPLE =
  "The product team reviewed the customer onboarding pilot on Monday. Users found the new checklist helpful, but several had trouble finding the document upload button. The team agreed to make the button more visible and simplify the help text before the next pilot. Priya will prepare the design changes by Friday, and the support team will collect feedback from the next group of testers. No launch date has been confirmed.";

const date = (value) =>
  new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
const Tags = ({ tags }) => (
  <div className="tags">
    {tags.map((tag) => (
      <span key={tag}>{tag}</span>
    ))}
  </div>
);

export default function App() {
  const [text, setText] = useState("");
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState(null);
  const [saving, setSaving] = useState(false);
  const [listing, setListing] = useState(true);
  const [opening, setOpening] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [formError, setFormError] = useState("");
  const [listError, setListError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [notice, setNotice] = useState("");
  const [health, setHealth] = useState(null);
  const detailRequest = useRef(0);
  const listRequest = useRef(0);
  const historyPanel = useRef(null);
  const detailPanel = useRef(null);
  // Refs close the gap before React renders disabled controls.
  const submitLock = useRef(false);
  const deleteLock = useRef(false);

  async function loadEntries(append = false) {
    if (deleteLock.current) return;
    const version = ++listRequest.current;
    setListing(true);
    setListError("");
    try {
      const data = await request(
        `/entries?limit=20&offset=${append ? entries.length : 0}`,
      );
      // An earlier refresh must not replace a newer post-save list.
      if (version !== listRequest.current) return;
      setEntries((previous) =>
        append
          ? [
              ...previous,
              ...data.entries.filter(
                (item) => !previous.some((old) => old.id === item.id),
              ),
            ]
          : data.entries,
      );
      setTotal(data.total);
      if (!append && historyPanel.current) historyPanel.current.scrollTop = 0;
    } catch (error) {
      if (version === listRequest.current) setListError(error.message);
    } finally {
      if (version === listRequest.current) setListing(false);
    }
  }

  useEffect(() => {
    loadEntries();
    request("/health")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (detailPanel.current) detailPanel.current.scrollTop = 0;
  }, [selected?.id]);

  async function submit(event) {
    event.preventDefault();
    if (submitLock.current || deleteLock.current) return;
    setFormError("");
    setNotice("");
    if (!text.trim() || text.length > MAX) {
      setFormError("Enter between 1 and 10,000 characters.");
      return;
    }
    submitLock.current = true;
    setSaving(true);
    try {
      const entry = await request("/entries", {
        method: "POST",
        body: JSON.stringify({ text }),
      });
      detailRequest.current += 1;
      setOpening(false);
      setDetailError("");
      setSelected(entry);
      setText("");
      setNotice("Summary saved. Review it in the detail panel below.");
      await loadEntries();
    } catch (error) {
      setFormError(error.message);
    } finally {
      submitLock.current = false;
      setSaving(false);
    }
  }

  async function openEntry(id) {
    if (deleteLock.current) return;
    // Only the latest selection may publish a detail response.
    const version = ++detailRequest.current;
    setOpening(true);
    setDetailError("");
    try {
      const entry = await request(`/entries/${id}`);
      if (version === detailRequest.current) setSelected(entry);
    } catch (error) {
      if (version === detailRequest.current) setDetailError(error.message);
    } finally {
      if (version === detailRequest.current) setOpening(false);
    }
  }

  async function deleteEntry(id) {
    if (deleteLock.current || submitLock.current || listing) return;
    deleteLock.current = true;
    // Cancel pending detail reads before deleting, even if they have not
    // selected this row yet. Otherwise a late response can resurrect it.
    detailRequest.current += 1;
    setOpening(false);
    setDetailError("");
    setNotice("");
    setDeletingId(id);
    setListError("");
    try {
      await request(`/entries/${id}`, { method: "DELETE" });
      setEntries((previous) => previous.filter((entry) => entry.id !== id));
      setTotal((previous) => Math.max(0, previous - 1));
      setSelected((previous) => (previous?.id === id ? null : previous));
      setNotice("Summary deleted.");
    } catch (error) {
      setListError(error.message);
    } finally {
      deleteLock.current = false;
      setDeletingId(null);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Slate home">
          SLATE
        </a>
      </header>
      <main>
        {health && !health.ai_configured && (
          <div className="configuration" role="status">
            AI setup needed · Add {health.api_key_env} for{" "}
            {health.provider_label} to the server’s .env file and restart the
            backend. Saved entries are still available.
          </div>
        )}
        <section className="composer card" aria-labelledby="compose-title">
          <div className="section-heading">
            <div>
              <h1 id="compose-title">Summarize your text</h1>
              <p className="heading-copy">
                Get a concise summary and three useful tags.
              </p>
            </div>
            <button
              type="button"
              className="text-button"
              disabled={saving}
              onClick={() => {
                setText(SAMPLE);
                setFormError("");
                setNotice("");
              }}
            >
              Try sample text <span aria-hidden="true">↗</span>
            </button>
          </div>
          <form onSubmit={submit}>
            <label htmlFor="source" className="sr-only">
              Text to summarize
            </label>
            <textarea
              id="source"
              placeholder="Paste your meeting notes, an article draft, or an idea worth keeping…"
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                setNotice("");
              }}
              maxLength={MAX}
              disabled={saving}
              autoFocus
              aria-describedby="text-help text-count"
            />
            <div className="input-meta">
              <span id="text-help">A short summary. Exactly three tags.</span>
              <span id="text-count">
                {text.length.toLocaleString()} / 10,000
              </span>
            </div>
            <div className="composer-footer">
              <p className="privacy">
                Your text is sent to{" "}
                {health?.data_destination || "the configured AI provider"} and
                saved locally. Use non-sensitive content.
              </p>
              <button
                className="primary"
                disabled={saving || deletingId !== null || !text.trim()}
                type="submit"
              >
                {saving ? (
                  <>
                    <span className="spinner" />
                    Generating…
                  </>
                ) : (
                  <>
                    Summarize & save <span aria-hidden="true">→</span>
                  </>
                )}
              </button>
            </div>
            {saving && (
              <p className="status" role="status">
                Creating your summary and tags. This can take up to 30 seconds.
              </p>
            )}
            {formError && (
              <p className="error" role="alert">
                {formError}
              </p>
            )}
            {notice && (
              <p className="success" role="status">
                {notice}
              </p>
            )}
          </form>
        </section>
        <section className="library" aria-labelledby="library-title">
          <div className="section-heading library-heading">
            <h2 id="library-title">
              Saved summaries <span className="count">{total}</span>
            </h2>
            <button
              className="text-button"
              disabled={listing || saving || deletingId !== null}
              onClick={() => loadEntries()}
            >
              Refresh <span aria-hidden="true">↻</span>
            </button>
          </div>
          <div className="library-grid">
            <div className="entry-list" ref={historyPanel}>
              {listError && (
                <p className="error" role="alert">
                  {listError}
                </p>
              )}
              {listing && (
                <p className="status" role="status">
                  Loading saved entries…
                </p>
              )}
              {!listing && !listError && entries.length === 0 && (
                <div className="empty card">
                  <span className="empty-icon" aria-hidden="true">
                    ≡
                  </span>
                  <h3>No saved summaries</h3>
                  <p>Create a summary to begin your history.</p>
                </div>
              )}
              {entries.map((entry) => (
                <div
                  className={`entry-shell card ${selected?.id === entry.id ? "selected" : ""}`}
                  key={entry.id}
                >
                  <button
                    className="entry-card"
                    onClick={() => openEntry(entry.id)}
                    aria-pressed={selected?.id === entry.id}
                    disabled={deletingId !== null}
                  >
                    <div className="entry-meta">
                      <span>ENTRY {String(entry.id).padStart(2, "0")}</span>
                      <time dateTime={entry.created_at}>
                        {date(entry.created_at)}
                      </time>
                    </div>
                    <p>{entry.summary}</p>
                    <Tags tags={entry.tags} />
                  </button>
                  <button
                    type="button"
                    className="delete-entry"
                    aria-label={`Delete entry ${entry.id}`}
                    title="Delete summary"
                    disabled={deletingId !== null || listing || saving}
                    onClick={() => deleteEntry(entry.id)}
                  >
                    {deletingId === entry.id ? "…" : "×"}
                  </button>
                </div>
              ))}
              {entries.length < total && (
                <button
                  className="text-button load-more"
                  disabled={listing || saving || deletingId !== null}
                  onClick={() => loadEntries(true)}
                >
                  Load more entries
                </button>
              )}
            </div>
            <article
              ref={detailPanel}
              tabIndex={0}
              className="detail card"
              aria-label="Entry detail"
              aria-busy={opening}
            >
              {opening ? (
                <p className="status" role="status">
                  Opening entry…
                </p>
              ) : detailError ? (
                <p className="error" role="alert">
                  {detailError}
                </p>
              ) : selected ? (
                <>
                  <div className="entry-meta">
                    <span>SAVED SUMMARY</span>
                    <time dateTime={selected.created_at}>
                      {date(selected.created_at)}
                    </time>
                  </div>
                  <h3>Summary</h3>
                  <p className="summary">{selected.summary}</p>
                  <Tags tags={selected.tags} />
                  <div className="original">
                    <h4>ORIGINAL TEXT</h4>
                    <p>{selected.text}</p>
                  </div>
                  <p className="review-note">
                    AI-generated. Review against the original for accuracy.
                  </p>
                </>
              ) : (
                <div className="detail-empty">
                  <span aria-hidden="true">↖</span>
                  <h3>Select a saved summary</h3>
                  <p>Review its tags and original text here.</p>
                </div>
              )}
            </article>
          </div>
        </section>
      </main>
      <footer>
        <span>Slate · AI Content Assistant</span>
      </footer>
    </div>
  );
}
