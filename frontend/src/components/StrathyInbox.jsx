import { useEffect, useMemo, useRef, useState } from "react";
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
  ShieldAlert,
  Hourglass,
  Copy,
} from "lucide-react";

const BRAND = {
  red: "#C8102E",
  blue: "#0033A0",
  gold: "#EAAA00",
  slate: "#0F172A",
  soft: "#F8FAFC",
};

function normalizeTextForDisplay(text = "") {
  // Goal: "email-like" wrapping:
  // - Keep paragraph breaks (blank lines)
  // - Remove hard line breaks inside paragraphs so text fills width
  // - Keep list formatting reasonably intact
  const t = String(text || "").replace(/\r/g, "").trim();
  if (!t) return "";

  const blocks = t.split(/\n\s*\n+/); // split paragraphs by blank lines

  const cleaned = blocks.map((blk) => {
    const lines = blk.split("\n").map((l) => l.trimEnd());

    // If it's a list-ish block, keep newlines
    const listish = lines.some((l) => /^(\-|\*|\d+\.)\s+/.test(l.trim()));
    if (listish) return lines.join("\n").trim();

    // Otherwise, collapse internal newlines into spaces
    return lines.map((l) => l.trim()).join(" ").replace(/\s+/g, " ").trim();
  });

  return cleaned.join("\n\n").trim();
}

function getStoredMessages(storageKey) {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(storageKey);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.warn("Failed to parse stored inbox data", err);
    return [];
  }
}

function parseEmailAddress(fromHeader = "") {
  if (!fromHeader) return { email: "", name: "" };
  const m = fromHeader.match(/<([^>]+)>/);
  const email = (m && m[1]) || fromHeader;
  const namePart = fromHeader.split("<")[0].trim().replace(/(^"|"$)/g, "");
  return { email: (email || "").toLowerCase().trim(), name: namePart || "" };
}

function prettyNameFromEmail(email) {
  if (!email) return "";
  const local = email.split("@")[0];
  const tokens = local.replace(/[._\-]/g, " ").split(/\s+/).filter(Boolean);
  return tokens
    .map((t) => t.charAt(0).toUpperCase() + t.slice(1))
    .join(" ");
}

function extractAdmissionAndGroup(body = "") {
  const text = (body || "").replace(/\r/g, " ");
  let admission = null;
  let courseGroup = null;

  const admissionPatterns = [
    /admission(?:\s*no| number|#|:)?\s*[:#]?\s*([A-Za-z0-9\-]+)/i,
    /admn(?:\.)?\s*[:#]?\s*([A-Za-z0-9\-]+)/i,
    /reg(?:istration)?(?:\s*no| number|#|:)?\s*[:#]?\s*([A-Za-z0-9\-]+)/i,
    /student\s*no(?:\s*[:#])?\s*([A-Za-z0-9\-]+)/i,
  ];
  for (const re of admissionPatterns) {
    const m = text.match(re);
    if (m && m[1]) {
      admission = m[1].trim();
      break;
    }
  }

  const coursePatterns = [
    /([A-Z]{2,6}\s*[A-Z0-9]{0,4})\s+([1-4](?:\.[0-9])?)(?:\s*[-\/]?\s*([A-Z]))/i,
    /course\s*[:\-]?\s*([A-Za-z0-9\s\.]{2,30})\s*(year\s*)?([1-4](?:\.[0-9])?)\s*(group\s*)?([A-Za-z0-9]+)/i,
    /([A-Z]{2,6}\s*[A-Z0-9]{0,4})\s+(year)?\s*([1-4](?:\.[0-9])?)/i,
    /([A-Za-z]{2,10}\s*[A-Za-z0-9]{0,6})\s*-\s*([1-4](?:\.[0-9])?)/i,
  ];

  for (const re of coursePatterns) {
    const m = text.match(re);
    if (m) {
      const groups = m
        .slice(1)
        .filter(Boolean)
        .map((s) => String(s).trim());
      courseGroup = groups.join(" ").replace(/\s+/g, " ").trim();
      if (courseGroup) break;
    }
  }

  if (!courseGroup) {
    const g = text.match(/group(?:\s*[:#])?\s*([A-Za-z0-9]+)/i);
    const y = text.match(/year(?:\s*[:#])?\s*([1-4](?:\.[0-9])?)/i);
    if (g || y) {
      courseGroup = `${y ? y[1] : ""} ${g ? g[1] : ""}`.trim();
    }
  }

  return { admission: admission || "", courseGroup: courseGroup || "" };
}

export default function StrathyInbox() {
  const storageKey = "strathyInboxThreads";
  const [loading, setLoading] = useState(false);

const [messages, setMessages] = useState([]);
const [error, setError] = useState("");
const [selected, setSelected] = useState(null);

  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [filter, setFilter] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const messagesRef = useRef([]);

  const pageSize = 50;

  // Merge threads by threadId (one row per thread)
  const mergeMessages = (existing, incoming) => {
    const byId = new Map(existing.map((m) => [m.id, m])); // id === threadId

    incoming.forEach((msg) => {
      const prev = byId.get(msg.id);
      if (prev) {
        const rank = (s) => {
            const v = (s || "").toLowerCase();
            if (v === "replied") return 4;
            if (v === "escalated") return 3;
            if (v === "blocked") return 2;
            if (v === "pending") return 1;
            return 0; // new/empty
            };
        const status = rank(msg.status) > rank(prev.status) ? msg.status : prev.status;



        const ai_reply = prev.ai_reply || msg.ai_reply || null;
        const ai_replied_at = prev.ai_replied_at || msg.ai_replied_at || null;

        const thread_messages =
          (msg.thread_messages && msg.thread_messages.length
            ? msg.thread_messages
            : prev.thread_messages) || [];

        byId.set(msg.id, {
          ...prev,
          ...msg,
          status,
          ai_reply,
          ai_replied_at,
          thread_messages,
        });
      } else {
        byId.set(msg.id, msg);
      }
    });

    return Array.from(byId.values()).sort(
      (a, b) => new Date(b.received_at || 0) - new Date(a.received_at || 0)
    );
  };

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

      const normalized = (Array.isArray(data) ? data : []).map((m) => {
        const sender = m.from || m.sender || "";
        const { email: student_email, name: fromName } = parseEmailAddress(sender);

        const student_name =
          m.student_name ||
          m.name ||
          prettyNameFromEmail(student_email) ||
          fromName ||
          "";

        const body = m.student_query || m.body || m.body_text || "";
        const parsed = extractAdmissionAndGroup(body);

        let status = (m.status || "").toLowerCase();
        if (!status) status = m.ai_reply ? "replied" : "new";
        if (
          status !== "blocked" &&
          status !== "replied" &&
          status !== "escalated" &&
          status !== "pending"
        ) {
          status = status === "new" ? "new" : status;
        }

        // ✅ Thread messages for continuous chat
        const thread_messages = Array.isArray(m.thread_messages)
          ? m.thread_messages
          : [];

        // ✅ pick a Gmail message id we can reply to:
        // prefer the most recent STUDENT message in the thread
        let gmail_message_id = m.id || m.message_id || null;
        if (thread_messages.length) {
          const lastStudent = [...thread_messages]
            .reverse()
            .find((x) => (x.role || "").toUpperCase() !== "ADAM" && x.id);
          if (lastStudent?.id) gmail_message_id = lastStudent.id;
        }

        return {
          // ✅ UI row key is threadId (one row per conversation)
          id: m.threadId,
          threadId: m.threadId,

          // ✅ Actual Gmail message id to reply to
          gmail_message_id,

          from: sender,
          student_email,
          student_name,

          admission_number: m.admission_number || parsed.admission || "",
          course: m.course || "",
          year: m.year || "",
          semester: m.semester || "",
          group: m.group || "",
          course_group: m.course_group || parsed.courseGroup || "",
          full_thread_summary: m.full_thread_summary || "",

          subject: m.subject || "(no subject)",
          body,
          ai_reply: m.ai_reply || null,
          status,
          received_at: m.received_at || m.date || new Date().toISOString(),

          thread_messages,
          raw: m,
          details_status: m.details_status || "empty",
        };
      });

      setMessages((prev) => {
  const merged = mergeMessages(prev, normalized);

  // keep selected stable
  setSelected((cur) => {
    if (!merged.length) return null;
    if (!cur) return merged[0];
    return merged.find((m) => m.threadId === cur.threadId) || merged[0];
  });

  return merged;
});

setCurrentPage(1);


    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

const pollLastReply = async () => {
  try {
    const res = await fetch("/gmail/last-reply");
    if (!res.ok) return;

    const data = await res.json();

    // expected (any combo): { ok, ai_reply, threadId, subject, sent_at }
    if (!data?.ok || !data?.ai_reply) return;

    const replyText = String(data.ai_reply || "").trim();
    if (!replyText) return;

    const matchByThread = (m) =>
      data.threadId && (m.threadId === data.threadId || m.id === data.threadId);

    const matchBySubject = (m) =>
      data.subject && (m.subject || "").trim() === String(data.subject).trim();

    const shouldMatch = (m) => matchByThread(m) || matchBySubject(m);

    // ✅ Update inbox list + append to thread_messages
    setMessages((prev) =>
      prev.map((m) => {
        if (!shouldMatch(m)) return m;

        const existing = Array.isArray(m.thread_messages) ? m.thread_messages : [];

        // prevent duplicate ADAM reply
        const alreadyHas = existing.some(
          (x) =>
            (x.role || "").toUpperCase() === "ADAM" &&
            (x.body || "").trim() === replyText
        );

        const updatedThread = alreadyHas
          ? existing
          : [
              ...existing,
              {
                id: `adam-${(data.threadId || m.threadId || m.id)}-${data.sent_at || Date.now()}`,
                role: "ADAM",
                body: replyText,
                date: data.sent_at || new Date().toISOString(),
              },
            ];

        return {
          ...m,
          ai_reply: replyText,
          ai_replied_at: data.sent_at || new Date().toISOString(),
          status: "replied",
          thread_messages: updatedThread,
        };
      })
    );

    // ✅ Update selected panel too
    setSelected((cur) => {
      if (!cur || !shouldMatch(cur)) return cur;

      const existing = Array.isArray(cur.thread_messages) ? cur.thread_messages : [];
      const alreadyHas = existing.some(
        (x) =>
          (x.role || "").toUpperCase() === "ADAM" &&
          (x.body || "").trim() === replyText
      );

      return {
        ...cur,
        ai_reply: replyText,
        ai_replied_at: data.sent_at || new Date().toISOString(),
        status: "replied",
        thread_messages: alreadyHas
          ? existing
          : [
              ...existing,
              {
                id: `adam-${(data.threadId || cur.threadId || cur.id)}-${data.sent_at || Date.now()}`,
                role: "ADAM",
                body: replyText,
                date: data.sent_at || new Date().toISOString(),
              },
            ],
      };
    });
  } catch (err) {
    console.error("pollLastReply failed", err);
  }
};

  useEffect(() => {
    fetchUnread();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

//   useEffect(() => {
//     messagesRef.current = messages;
//     localStorage.setItem(storageKey, JSON.stringify(messages));
//   }, [messages]);
useEffect(() => {
  messagesRef.current = messages;
}, [messages]);

  // ✅ Poll by refreshing the inbox (thread-safe)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchUnread();
      pollLastReply();
    }, 20000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return messages;
    return messages.filter((m) =>
      [m.subject, m.student_name, m.student_email, m.body]
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

    const to = selected.student_email || "";
    const blockedList = [
      "strathmorecommunication@gmail.com",
      "allstudents@strathmore.edu",
      "allstaff@strathmore.edu",
    ];
    if (!to.endsWith("@strathmore.edu") || blockedList.includes(to)) {
      alert("Sending is not allowed to this recipient.");
      setMessages((prev) =>
        prev.map((m) => (m.id === selected.id ? { ...m, status: "blocked" } : m))
      );
      setSelected((s) => (s && s.id === selected.id ? { ...s, status: "blocked" } : s));
      return;
    }

    if (!selected.gmail_message_id) {
      alert("Cannot reply: missing Gmail message id for this thread.");
      return;
    }

    setSending(true);
    setSent(false);
    try {
      const res = await fetch("/gmail/reply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message_id: selected.gmail_message_id, body_text: reply }),
      });

      const data = await res.json().catch(() => ({}));

      if (res.status === 403 || (data.error && /not allowed/i.test(data.error))) {
        setMessages((prev) =>
          prev.map((m) => (m.id === selected.id ? { ...m, status: "blocked" } : m))
        );
        setSelected((s) => (s ? { ...s, status: "blocked" } : s));
        alert(data.error || "Message blocked by policy 🚫");
        return;
      }

      if (!res.ok || !data.ok) throw new Error(data.error || "Send failed");

      setSent(true);
      setReply("");

      // Refresh so thread messages update from backend
      fetchUnread();
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
      <header
        className="w-full shadow-sm flex-none"
        style={{
          background: `linear-gradient(120deg, ${BRAND.red} 0%, ${BRAND.blue} 100%)`,
          color: "white",
        }}
      >
        <div className="max-w-7xl mx-auto px-6 py-3.5 flex items-center gap-3">
          <Mail className="w-6 h-6" />
          <h1 className="text-xl font-semibold">Strathmore SCES Inbox</h1>
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

      <main className="flex-1 flex overflow-hidden">
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

          <div className="flex-1 overflow-y-auto">
            {error && (
              <div className="p-3 text-sm text-red-600 border-b bg-red-50">
                {error}
              </div>
            )}

            {loading && (
              <div className="p-6 text-center text-slate-500 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading…
              </div>
            )}

            {!loading && paginated.length === 0 && (
              <div className="p-6 text-center text-slate-500">
                <Inbox className="w-6 h-6 mx-auto mb-2 opacity-60" />
                No queries
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
                        {m.body?.slice(0, 80) || ""}
                      </div>
                      <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" />{" "}
                        {new Date(m.received_at || Date.now()).toLocaleString()}
                      </div>
                    </div>

                    <div className="ml-3 text-right w-[110px] flex flex-col items-end">
                      <div className="text-xs text-slate-400 truncate max-w-full text-right">
                        {m.student_name || (m.from ? m.from.split("<")[0].trim() : "")}
                      </div>
                      <div className="mt-1 w-full flex justify-end">
                        {m.status === "replied" && (
                          <span className="text-xs text-green-600 inline-flex items-center gap-1 w-[80px] justify-end">
                            <CheckCircle2 className="w-3 h-3" /> Replied
                          </span>
                        )}
                        {m.status === "blocked" && (
                          <span className="text-xs text-orange-600 inline-flex items-center gap-1 w-[80px] justify-end">
                            <ShieldAlert className="w-3 h-3" /> Blocked
                          </span>
                        )}
                        {m.status === "pending" && (
                          <span className="text-xs text-blue-600 inline-flex items-center gap-1 w-[80px] justify-end">
                            <Hourglass className="w-3 h-3" /> Pending
                          </span>
                        )}
                        {m.status === "escalated" && (
                          <span className="text-xs text-red-600 inline-flex items-center gap-1 w-[80px] justify-end">
                            <AlertTriangle className="w-3 h-3" /> Escalated
                          </span>
                        )}
                        {(!m.status || m.status === "new") && (
                          <span className="text-xs text-slate-500 inline-flex items-center gap-1 w-[80px] justify-end">
                            <Clock className="w-3 h-3" /> New
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
          </div>

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

        <section className="flex-1 overflow-y-auto p-6 bg-white">
          {!selected ? (
            <div className="p-8 rounded-xl border text-center text-slate-500 mt-20">
              <ArrowLeft className="w-6 h-6 mx-auto mb-2" /> Select a query
            </div>
          ) : (
            <>
              <div className="rounded-xl border p-4 bg-white shadow-sm">
                <div className="flex items-start justify-between gap-6">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.blue }}>
                      Student Details
                    </div>

                    <div className="flex items-center gap-4 mt-2">
                      <div>
                        <div className="text-sm font-semibold">
                          {selected.student_name ||
                            prettyNameFromEmail(selected.student_email) ||
                            "(Unknown Student)"}
                        </div>
                        <div className="text-xs text-slate-500">
                          {selected.student_email || "No email found"}
                        </div>
                      </div>

                      <div className="ml-auto text-right">
                        <div className="text-[11px] text-slate-400">
                          <span className="uppercase text-[11px] font-medium">Received</span>
                          <div>{new Date(selected.received_at).toLocaleString()}</div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-3 gap-3">
                      <div className="bg-slate-50 p-2 rounded">
                        <div className="text-[11px] text-slate-500">Admission No</div>
                        <div className="font-medium">{selected.admission_number || "—"}</div>
                      </div>

                      <div className="bg-slate-50 p-2 rounded col-span-2">
                        <div className="text-[11px] text-slate-500 mb-1">
                          Course · Year · Semester · Group
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className="px-2 py-1 bg-white rounded border text-sm">
                            {selected.course || "—"}
                          </span>
                          <span className="px-2 py-1 bg-white rounded border text-sm">
                            {selected.year || "—"}
                          </span>
                          <span className="px-2 py-1 bg-white rounded border text-sm">
                            {selected.semester || "—"}
                          </span>
                          <span className="px-2 py-1 bg-white rounded border text-sm">
                            {selected.group || "—"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {selected.full_thread_summary && (
                      <div className="bg-slate-50 p-3 rounded relative border border-slate-200 mt-4">
                        <div className="text-[11px] text-slate-500 mb-1 flex justify-between items-center">
                          <span>Full Thread Summary</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(selected.full_thread_summary);
                              alert("Full thread summary copied to clipboard");
                            }}
                            className="text-[11px] text-blue-600 hover:underline flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" /> Copy
                          </button>
                        </div>

                        <div className="text-sm text-slate-700 whitespace-pre-wrap">
                          {selected.full_thread_summary}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col items-stretch w-48 shrink-0 space-y-2">
                    {selected.details_status && (
                      <div className="text-xs flex items-center justify-center gap-2 text-center px-2 py-1 rounded-md border bg-slate-50">
                        {selected.details_status === "complete" && (
                          <span className="inline-flex items-center gap-1 text-green-600">
                            <CheckCircle2 className="w-3 h-3" /> Details complete
                          </span>
                        )}
                        {["partial", "empty"].includes(selected.details_status) && (
                          <span className="inline-flex items-center gap-1 text-yellow-700">
                            <Hourglass className="w-3 h-3" /> Requested — waiting for response
                          </span>
                        )}
                      </div>
                    )}

                    <button
                      onClick={() => {
                        if (selected.admission_number) {
                          navigator.clipboard.writeText(selected.admission_number);
                          alert("Admission number copied to clipboard");
                        } else {
                          alert("No admission number available");
                        }
                      }}
                      className="px-3 py-2 rounded-lg border text-sm flex justify-center items-center gap-2 hover:bg-slate-50"
                    >
                      <Copy className="w-4 h-4" />
                      Copy Admission No.
                    </button>

                    <button
                      onClick={() => {
                        if (selected.course_group) {
                          navigator.clipboard.writeText(selected.course_group);
                          alert("Course details copied to clipboard");
                        } else {
                          alert("No course details available");
                        }
                      }}
                      className="px-3 py-2 rounded-lg border text-sm flex justify-center items-center gap-2 hover:bg-slate-50"
                    >
                      <Copy className="w-4 h-4" />
                      Copy Course Details
                    </button>
                  </div>
                </div>
              </div>

              <hr className="my-4" />

              {/* ✅ Full Conversation Thread */}
              <div>
                <div className="text-xs uppercase tracking-wide" style={{ color: BRAND.blue }}>
                  Conversation
                </div>

                <div className="mt-3 space-y-3">
                  {(selected.thread_messages || []).length === 0 ? (
                    <div className="text-sm text-slate-500">No thread messages found.</div>
                  ) : (
                    (selected.thread_messages || []).map((tm) => {
                      const isAI = (tm.role || "").toUpperCase() === "ADAM";
                      return (
                        <div key={tm.id} className={`flex ${isAI ? "justify-end" : "justify-start"}`}>
                          <div
                              className={`w-full sm:w-[520px] md:w-[620px] lg:w-[1100px] rounded-xl border p-3 text-sm ${
                                  isAI
                                  ? "bg-gray-50 border-gray-200"
                                  : "bg-blue-50 border-blue-200"
                            }`}
                          >
                            <div className="text-[11px] text-slate-600 mb-2 flex items-center justify-between gap-3">

                              <span className="font-medium">
                                {isAI ? "ADAM" : (selected.student_name || "Student")}
                              </span>
                              <span>{tm.date ? new Date(tm.date).toLocaleString() : ""}</span>
                            </div>
                            <div className="text-slate-800 whitespace-pre-wrap break-words">
                                {tm.body || ""}

                          </div>
                        </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Notices */}
              {selected.status === "blocked" && (
                <div className="rounded-xl border p-4 mt-4 bg-orange-50 text-orange-700 flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5" />
                  Auto-reply blocked by policy — no message sent.
                </div>
              )}

              {/* Admin Reply */}
              {selected.status === "blocked" ? (
                <div className="mt-6 rounded-xl border p-4 bg-white/50 text-slate-500">
                  Replies are disabled for this sender.
                </div>
              ) : selected.status !== "escalated" ? (
                <div className="mt-6 rounded-xl border p-4 bg-white">
                  <div className="text-xs uppercase tracking-wide mb-2" style={{ color: BRAND.blue }}>
                    Your reply
                  </div>

                  <textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    placeholder={`Reply to ${selected.student_name || "the student"}…`}
                    className="w-full min-h-[140px] p-3 rounded-xl border"
                  />

                  <div className="mt-3 flex items-center gap-3">
                    <button
                      onClick={onSend}
                      disabled={sending || !reply.trim()}
                      className="px-4 py-2 rounded-xl text-white shadow-sm disabled:opacity-60 flex items-center gap-2"
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
