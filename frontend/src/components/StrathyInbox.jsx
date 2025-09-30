import { useEffect, useMemo, useState } from "react";
import { Mail, Send, RefreshCcw, Inbox, Loader2, ArrowLeft, Search, CheckCircle2 } from "lucide-react";

// --- Brand palette (approx. Strathmore crest colours) ---
// Primary Red, Royal Blue, Gold Accent
const BRAND = {
  red: "#C8102E",
  blue: "#0033A0",
  gold: "#EAAA00",
  slate: "#0F172A",
  soft: "#F8FAFC",
};

export default function StrathyInbox() {
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [filter, setFilter] = useState("");

  // Fetch unread messages from backend
  const fetchUnread = async () => {
    setError("");
    setLoading(true);
    setSent(false);
    try {
      const res = await fetch("/gmail/unread");
      if (!res.ok) {
        if (res.status === 307 || res.redirected) {
          // likely needs login
          window.location.href = "/oauth2/login";
          return;
        }
        throw new Error(`Failed to load messages (${res.status})`);
      }
      const data = await res.json();
      setMessages(Array.isArray(data) ? data : []);
      if (Array.isArray(data) && data.length > 0) {
        setSelected(data[0]);
      } else {
        setSelected(null);
      }
    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return messages;
    return messages.filter((m) =>
      [m.subject, m.from, m.body_preview]
        .filter(Boolean)
        .some((t) => String(t).toLowerCase().includes(q))
    );
  }, [messages, filter]);

  const onSend = async () => {
    if (!selected) return;
    if (!reply.trim()) return alert("Type a reply first ✍️");
    setSending(true);
    setSent(false);
    try {
      const res = await fetch("/gmail/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: selected.id, body_text: reply }),
      });
      if (!res.ok) throw new Error(`Send failed (${res.status})`);
      setSent(true);
      setReply("");
    } catch (e) {
      alert(e.message || "Failed to send");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen w-full" style={{ background: BRAND.soft }}>
      {/* Header */}
      <header
        className="w-full border-b shadow-sm"
        style={{
          background: `linear-gradient(120deg, ${BRAND.red} 0%, ${BRAND.blue} 100%)`,
          color: "white",
        }}
      >
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/15 grid place-items-center">
            <Mail className="w-5 h-5" />
          </div>
          <div className="flex flex-col">
            <h1 className="text-xl font-semibold tracking-tight">Strathy – Admin Assistant</h1>
            <p className="text-xs opacity-80">Strathmore University • Gmail triage</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={fetchUnread}
              className="px-3 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition text-sm flex items-center gap-2"
              title="Refresh"
            >
              <RefreshCcw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Main layout */}
      <main className="max-w-6xl mx-auto p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Inbox column */}
        <section className="md:col-span-1 rounded-2xl border bg-white shadow-sm overflow-hidden">
          <div className="p-3 border-b flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Search unread…"
                className="w-full pl-9 pr-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
                style={{
                  // subtle brand ring
                  // @ts-ignore
                  ["--brand"]: BRAND.red,
                }}
              />
            </div>
            <div className="px-2 py-1 rounded-md text-xs" style={{ background: BRAND.gold, color: BRAND.slate }}>
              {messages.length}
            </div>
          </div>

          <div className="max-h-[70vh] overflow-auto">
            {loading && (
              <div className="p-6 flex items-center justify-center gap-2 text-slate-500">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading…
              </div>
            )}
            {!loading && filtered.length === 0 && (
              <div className="p-6 text-center text-slate-500">
                <Inbox className="w-6 h-6 mx-auto mb-2 opacity-60" />
                No unread messages
              </div>
            )}
            {!loading && filtered.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelected(m)}
                className={`w-full text-left px-4 py-3 border-b hover:bg-slate-50 transition ${
                  selected?.id === m.id ? "bg-slate-50" : "bg-white"
                }`}
              >
                <div className="flex items-start gap-2">
                  <div className="mt-0.5 w-2 h-2 rounded-full" style={{ background: BRAND.red }} />
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">{m.subject || "(no subject)"}</div>
                    <div className="text-xs text-slate-500 truncate">{m.from}</div>
                    <div className="text-xs text-slate-500 line-clamp-2 mt-1">{m.body_preview}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </section>

        {/* Reader + reply */}
        <section className="md:col-span-2 rounded-2xl border bg-white shadow-sm">
          {!selected ? (
            <div className="p-10 text-center text-slate-500">
              <ArrowLeft className="w-6 h-6 mx-auto mb-2" /> Select a message
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <div className="p-4 border-b">
                <div className="text-xs uppercase tracking-wide mb-1" style={{ color: BRAND.blue }}>From</div>
                <div className="font-medium">{selected.from}</div>
                <div className="mt-2 text-2xl font-semibold">{selected.subject || "(no subject)"}</div>
              </div>
              <div className="p-4">
                <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border rounded-xl p-4 max-h-[40vh] overflow-auto">
                  {selected.body_preview || "(no preview)"}
                </pre>
              </div>

              <div className="mt-auto p-4 border-t bg-gradient-to-br from-white to-slate-50">
                <div className="mb-2 text-xs uppercase tracking-wide" style={{ color: BRAND.blue }}>Your reply</div>
                <textarea
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Type your response…"
                  className="w-full min-h-[120px] p-3 rounded-xl border focus:outline-none focus:ring-2"
                  style={{
                    borderColor: "#E2E8F0",
                    // @ts-ignore
                    ["--ring-color"]: BRAND.red,
                  }}
                />

                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={onSend}
                    disabled={sending || !reply.trim()}
                    className="px-4 py-2 rounded-xl text-white flex items-center gap-2 shadow-sm disabled:opacity-60"
                    style={{ background: BRAND.red }}
                  >
                    {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} {sending ? "Sending…" : "Send reply"}
                  </button>
                  {sent && (
                    <span className="inline-flex items-center gap-1 text-sm" style={{ color: BRAND.blue }}>
                      <CheckCircle2 className="w-4 h-4" /> Reply sent
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-4 py-6 text-xs text-slate-500">
        <span className="opacity-80">Made for Strathmore University</span>
        <span className="mx-2">•</span>
        <span className="opacity-60">Theme: Red/Blue/Gold</span>
      </footer>
    </div>
  );
}
