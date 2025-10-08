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
  Clock,
  ChevronLeft,
  ChevronRight,
  XCircle,
} from "lucide-react";

const BRAND = {
  red: "#C8102E",
  blue: "#0033A0",
  gold: "#EAAA00",
  slate: "#0F172A",
  soft: "#F8FAFC",
};

// ✅ Add the same blocked rules here (so frontend can display Blocked)
const BLOCKED_EMAILS = [
  "strathmorecommunication@gmail.com",
  "allstudents@strathmore.edu",
  "allstaff@strathmore.edu",
];

export default function StrathyInbox() {
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [filter, setFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const pageSize = 50;

  const fetchUnread = async () => {
    setError("");
    setLoading(true);
    setSent(false);
    try {
      const res = await fetch("http://localhost:8000/gmail/unread");
      if (!res.ok) {
        if (res.status === 307 || res.redirected) {
          window.location.href = "http://localhost:8000/oauth2/login";
          return;
        }
        throw new Error(`Failed to load messages (${res.status})`);
      }
      const data = await res.json();

      const normalized = (Array.isArray(data) ? data : []).map((m) => {
        const fromEmail = (m.from || "").split("<").pop()?.replace(">", "").toLowerCase();
        const isBlocked =
          BLOCKED_EMAILS.includes(fromEmail) || !fromEmail.endsWith("@strathmore.edu");

        return {
          ...m,
          role: "student",
          status: isBlocked ? "blocked" : m.ai_reply ? "replied" : "new",
        };
      });

      setMessages(normalized);
      if (normalized.length > 0) setSelected(normalized[0]);
      else setSelected(null);
      setCurrentPage(1);
    } catch (e) {
      setError(e.message || "Something went wrong while fetching emails");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnread();
  }, []);

  // Poll for new AI replies every 20s
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://localhost:8000/gmail/last-reply");
        if (!res.ok) return;
        const data = await res.json();
        if (data.ok && data.ai_reply && data.subject) {
          setMessages((prev) =>
            prev.map((m) =>
              m.subject === data.subject
                ? {
                    ...m,
                    ai_reply: data.ai_reply,
                    ai_replied_at: new Date().toISOString(),
                    status: "replied",
                  }
                : m
            )
          );
          setSelected((cur) =>
            cur && cur.subject === data.subject
              ? {
                  ...cur,
                  ai_reply: data.ai_reply,
                  ai_replied_at: new Date().toISOString(),
                  status: "replied",
                }
              : cur
          );
        }
      } catch (err) {
        console.error("Polling failed", err);
      }
    }, 20000);
    return () => clearInterval(interval);
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return messages;
    return messages.filter((m) =>
      [m.subject, m.from, m.student_query]
        .filter(Boolean)
        .some((t) => String(t).toLowerCase().includes(q))
    );
  }, [messages, filter]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const paginated = filtered.slice(startIndex, startIndex + pageSize);

  const onSend = async () => {
    if (!selected) return;
    if (!reply.trim()) return alert("Type a reply first ✍️");
    setSending(true);
    setSent(false);
    try {
      const res = await fetch("http://localhost:8000/gmail/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: selected.id, body_text: reply }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Send failed (${res.status})`);
      }

      setSent(true);
      setReply("");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === selected.id
            ? { ...m, status: "replied", ai_replied_at: new Date().toISOString() }
            : m
        )
      );
      setSelected((s) =>
        s ? { ...s, status: "replied", ai_replied_at: new Date().toISOString() } : s
      );
    } catch (e) {
      alert(e.message || "Failed to send");
    } finally {
      setSending(false);
    }
  };

  const onEscalate = (msgId) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, status: "escalated" } : m))
    );
    setSelected((s) => (s && s.id === msgId ? { ...s, status: "escalated" } : s));
    alert("Message escalated 🚨");
  };

  return (
    <div className="h-screen flex flex-col" style={{ background: BRAND.soft }}>
      {/* HEADER */}
      <header
        className="w-full shadow-sm flex-none"
        style={{
          background: `linear-gradient(120deg, ${BRAND.red} 0%, ${BRAND.blue} 100%)`,
          color: "white",
        }}
      >
        <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center gap-3">
          <Mail className="w-6 h-6" />
          <h1 className="text-xl font-semibold">Strathmore SCES Communication Inbox</h1>
          <div className="ml-auto flex gap-3">
            <button
              onClick={fetchUnread}
              className="px-3 py-2 rounded-lg bg-white/15 hover:bg-white/25 transition text-sm flex items-center gap-2"
            >
              <RefreshCcw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex overflow-hidden">
        {/* INBOX LIST */}
        <aside className="w-1/3 border-r bg-white overflow-y-auto flex flex-col">
          <div className="p-3 border-b flex items-center gap-2 sticky top-0 bg-white z-10">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search queries…"
              className="flex-1 px-2 py-2 text-sm rounded border"
            />
          </div>

          {error && (
            <div className="p-3 bg-red-50 border-b text-red-700 text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4" /> {error}
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="p-6 text-center text-slate-500 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading…
              </div>
            )}
            {!loading && paginated.length === 0 && (
              <div className="p-6 text-center text-slate-500">
                <Inbox className="w-6 h-6 mx-auto mb-2 opacity-60" />
                No queries found
              </div>
            )}
            {!loading &&
              paginated.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setSelected(m)}
                  className={`w-full text-left px-4 py-3 border-b hover:bg-slate-50 transition ${
                    selected?.id === m.id ? "bg-slate-100" : "bg-white"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {m.subject || "(no subject)"}
                      </div>
                      <div className="text-xs text-slate-500 truncate mt-1">
                        {m.student_query || ""}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {m.relative_time || "Unknown"}
                      </div>
                    </div>
                    <div className="ml-3 text-right">
                      <div className="text-xs text-slate-400 truncate">
                        {m.from ? m.from.split("<")[0].trim() : ""}
                      </div>
                      <div className="mt-1">
                        {m.status === "replied" && (
                          <span className="text-xs text-green-600">Replied</span>
                        )}
                        {m.status === "escalated" && (
                          <span className="text-xs text-red-600">Escalated</span>
                        )}
                        {m.status === "new" && (
                          <span className="text-xs text-slate-400">New</span>
                        )}
                        {m.status === "blocked" && (
                          <span className="text-xs text-red-500 font-semibold flex items-center gap-1">
                            <XCircle className="w-3 h-3" /> Blocked
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="p-3 border-t flex items-center justify-between bg-white sticky bottom-0">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="flex items-center gap-1 px-3 py-1 text-sm rounded border disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" /> Prev
              </button>
              <span className="text-sm text-slate-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="flex items-center gap-1 px-3 py-1 text-sm rounded border disabled:opacity-40"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </aside>

        {/* READER PANEL */}
        <section className="flex-1 overflow-y-auto p-6 bg-white">
          {!selected ? (
            <div className="p-8 rounded-xl border text-center text-slate-500 mt-20">
              <ArrowLeft className="w-6 h-6 mx-auto mb-2" /> Select a query
            </div>
          ) : (
            <>
              {/* Student Query */}
              <div className="rounded-xl border p-4 bg-white shadow-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.blue }}>
                      Student Query
                    </div>
                    <div className="font-semibold text-lg">
                      {selected.subject || "(no subject)"}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{selected.from}</div>
                    {selected.date && (
                      <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" />{" "}
                        {new Date(selected.date).toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-4 text-sm text-slate-700 whitespace-pre-wrap">
                  {selected.student_query}
                </div>
              </div>

              {/* AI Reply */}
              {selected.ai_reply ? (
                <div className="rounded-xl border p-4 bg-slate-50 mt-4">
                  <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.red }}>
                    Strathy AI Response
                  </div>
                  {selected.ai_replied_at && (
                    <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                      <Clock className="w-3 h-3" />{" "}
                      {new Date(selected.ai_replied_at).toLocaleString()}
                    </div>
                  )}
                  <div className="mt-2 text-sm text-slate-800 whitespace-pre-wrap">
                    {selected.ai_reply}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border p-4 bg-white/30 text-slate-500 mt-4">
                  <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.red }}>
                    Strathy AI Response
                  </div>
                  <div className="mt-2 text-sm">No automated response yet.</div>
                </div>
              )}

              {/* Admin Reply */}
              {selected.status === "blocked" ? (
                <div className="mt-6 rounded-xl border p-4 bg-red-50 text-red-600">
                  ⚠️ This email is blocked — replies are disabled.
                </div>
              ) : selected.status !== "escalated" ? (
                <div className="mt-6 rounded-xl border p-4 bg-white">
                  <div
                    className="text-xs uppercase tracking-wide mb-2"
                    style={{ color: BRAND.blue }}
                  >
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
                      className="px-4 py-2 rounded-xl text-white shadow-sm disabled:opacity-60 flex items-center gap-2"
                      style={{ background: BRAND.red }}
                    >
                      {sending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
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
                <div className="mt-6 rounded-xl border p-4 bg-white/50 text-red-600">
                  This message has been escalated — please follow up manually.
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}
