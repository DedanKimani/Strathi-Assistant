import { useEffect, useMemo, useState } from "react";
import {
  Mail,
  Send,
  RefreshCcw,
  Inbox,
  Loader2,
  ArrowLeft,
  Search,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";

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

  // --- Fetch unread (student only) ---
  const fetchUnread = async () => {
    setError("");
    setLoading(true);
    setSent(false);
    try {
      const res = await fetch("/gmail/unread");
      if (!res.ok) {
        if (res.status === 307 || res.redirected) {
          window.location.href = "/oauth2/login";
          return;
        }
        throw new Error(`Failed to load messages (${res.status})`);
      }
      const data = await res.json();
      // Ensure each item has: id, threadId (optional), from, subject, body_preview
      const withRoles = (Array.isArray(data) ? data : []).map((m) => ({
        ...m,
        role: "student",
        status: "new",
      }));
      setMessages(withRoles);
      if (withRoles.length > 0) setSelected(withRoles[0]);
      else setSelected(null);
    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
  }, []);

  // Poll AI replies every 20s and update both messages and selected if it matches
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("/gmail/last-reply");
        if (!res.ok) return;
        const data = await res.json();
        if (data.ok && data.ai_reply && data.thread_id) {
          setMessages((prev) =>
            prev.map((m) =>
              // match either message id or threadId (backend may use threadId)
              m.id === data.thread_id || m.threadId === data.thread_id
                ? { ...m, ai_reply: data.ai_reply, status: "replied" }
                : m
            )
          );

          // update selected view if it's the one that got AI reply
          setSelected((cur) => {
            if (!cur) return cur;
            if (cur.id === data.thread_id || cur.threadId === data.thread_id) {
              return { ...cur, ai_reply: data.ai_reply, status: "replied" };
            }
            return cur;
          });
        }
      } catch (err) {
        console.error("Polling failed", err);
      }
    }, 20000);
    return () => clearInterval(interval);
  }, []);

  const studentQueries = useMemo(() => messages.filter((m) => m.role === "student"), [messages]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return studentQueries;
    return studentQueries.filter((m) =>
      [m.subject, m.from, m.body_preview]
        .filter(Boolean)
        .some((t) => String(t).toLowerCase().includes(q))
    );
  }, [studentQueries, filter]);

  // --- Send reply (manual) ---
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
      // mark locally as replied
      setMessages((prev) => prev.map((m) => (m.id === selected.id ? { ...m, status: "replied" } : m)));
      setSelected((s) => (s ? { ...s, status: "replied" } : s));
    } catch (e) {
      alert(e.message || "Failed to send");
    } finally {
      setSending(false);
    }
  };

  // --- Escalate ---
  const onEscalate = (msgId) => {
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, status: "escalated" } : m)));
    setSelected((s) => (s && s.id === msgId ? { ...s, status: "escalated" } : s));
    alert("Message escalated 🚨");
  };

  return (
    <div className="min-h-screen w-full flex items-start justify-center p-6" style={{ background: BRAND.soft }}>
      <div className="w-full max-w-7xl rounded-2xl shadow-md overflow-hidden bg-white">
        {/* Header */}
        <header
          className="w-full border-b rounded-t-2xl"
          style={{
            background: `linear-gradient(120deg, ${BRAND.red} 0%, ${BRAND.blue} 100%)`,
            color: "white",
          }}
        >
          <div className="px-6 py-4 flex items-center gap-3">
            <Mail className="w-6 h-6" />
            <h1 className="text-xl font-semibold">Strathy – Admin Assistant</h1>
            <div className="ml-auto">
              <button
                onClick={fetchUnread}
                className="px-3 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition text-sm flex items-center gap-2"
              >
                <RefreshCcw className="w-4 h-4" /> Refresh
              </button>
            </div>
          </div>
        </header>

        {/* Main */}
        <main className="flex">
          {/* Sidebar */}
          <aside className="w-80 border-r bg-white flex flex-col">
            <div className="p-3 border-b flex items-center gap-2">
              <Search className="w-4 h-4 text-slate-400" />
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Search queries…"
                className="flex-1 px-2 py-2 text-sm rounded border"
              />
            </div>

            <div className="flex-1 overflow-auto">
              {loading && (
                <div className="p-6 text-center text-slate-500 flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading…
                </div>
              )}

              {!loading && filtered.length === 0 && (
                <div className="p-6 text-center text-slate-500">
                  <Inbox className="w-6 h-6 mx-auto mb-2 opacity-60" />
                  No queries
                </div>
              )}

              {!loading &&
                filtered.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setSelected(m)}
                    className={`w-full text-left px-4 py-3 border-b hover:bg-slate-50 transition ${
                      selected?.id === m.id ? "bg-slate-100" : "bg-white"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{m.subject || "(no subject)"}</div>
                        <div className="text-xs text-slate-500 truncate mt-1">{m.body_preview}</div>
                      </div>
                      <div className="ml-3 text-right">
                        <div className="text-xs text-slate-400">{m.from ? m.from.split("<")[0].trim() : ""}</div>
                        <div className="mt-1">
                          {m.status === "replied" && <span className="text-xs text-green-600">Replied</span>}
                          {m.status === "escalated" && <span className="text-xs text-red-600">Escalated</span>}
                          {m.status === "new" && <span className="text-xs text-slate-400">New</span>}
                        </div>
                      </div>
                    </div>
                  </button>
                ))}
            </div>
          </aside>

          {/* Reader */}
          <section className="flex-1 p-6 flex flex-col gap-4">
            {!selected ? (
              <div className="p-8 rounded-xl border text-center text-slate-500">
                <ArrowLeft className="w-6 h-6 mx-auto mb-2" /> Select a query
              </div>
            ) : (
              <>
                {/* Student message card */}
                <div className="rounded-xl border p-4 bg-white shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.blue }}>
                        Student Query
                      </div>
                      <div className="font-semibold text-lg">{selected.subject || "(no subject)"}</div>
                      <div className="text-xs text-slate-500 mt-1">{selected.from}</div>
                    </div>
                    <div className="text-sm">
                      {selected.status === "replied" && (
                        <span className="px-2 py-1 rounded-full text-xs bg-green-50 text-green-700">Replied</span>
                      )}
                      {selected.status === "escalated" && (
                        <span className="px-2 py-1 rounded-full text-xs bg-red-50 text-red-700">Escalated</span>
                      )}
                      {selected.status === "new" && (
                        <span className="px-2 py-1 rounded-full text-xs bg-slate-50 text-slate-600">New</span>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 text-sm text-slate-700 whitespace-pre-wrap">{selected.body_preview}</div>
                </div>

                {/* Model reply card (shows immediately below student query) */}
                {selected.ai_reply ? (
                  <div className="rounded-xl border p-4 bg-slate-50">
                    <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.red }}>
                      Strathy AI Response
                    </div>
                    <div className="mt-2 text-sm text-slate-800 whitespace-pre-wrap">{selected.ai_reply}</div>
                  </div>
                ) : (
                  // placeholder when AI hasn't replied yet
                  <div className="rounded-xl border p-4 bg-white/30 text-slate-500">
                    <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.red }}>
                      Strathy AI Response
                    </div>
                    <div className="mt-2 text-sm">No automated response yet.</div>
                  </div>
                )}

                {/* Admin reply / actions */}
                {selected.status !== "escalated" ? (
                  <div className="mt-auto rounded-xl border p-4 bg-white">
                    <div className="text-xs uppercase tracking-wide mb-2" style={{ color: BRAND.blue }}>
                      Your reply
                    </div>
                    <textarea
                      value={reply}
                      onChange={(e) => setReply(e.target.value)}
                      placeholder="Type your reply…"
                      className="w-full min-h-[140px] p-3 rounded-xl border"
                    />
                    <div className="mt-3 flex items-center gap-3">
                      <button
                        onClick={onSend}
                        disabled={sending || !reply.trim()}
                        className="px-4 py-2 rounded-xl text-white shadow-sm disabled:opacity-60"
                        style={{ background: BRAND.red }}
                      >
                        {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        {sending ? " Sending…" : " Send reply"}
                      </button>

                      <button
                        onClick={() => onEscalate(selected.id)}
                        className="px-4 py-2 rounded-xl flex items-center gap-2 text-red-600 border border-red-600"
                      >
                        <AlertTriangle className="w-4 h-4" /> Escalate
                      </button>

                      {sent && (
                        <span className="inline-flex items-center gap-1 text-sm" style={{ color: BRAND.blue }}>
                          <CheckCircle2 className="w-4 h-4" /> Reply sent
                        </span>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="mt-auto rounded-xl border p-4 bg-white/50 text-red-600">
                    This message has been escalated — please follow up manually.
                  </div>
                )}
              </>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}
