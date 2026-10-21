"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, ArrowLeft, ArrowRight, Bell, BookOpen, BriefcaseBusiness, CalendarDays, Check, CheckCircle2, ChevronDown, CircleAlert, Clock3, FileText, History, LayoutDashboard, LogOut, Menu, MessageCircle, Moon, Plus, Search, Send, ShieldCheck, Sparkles, Sun, Trash2, UserRound, Users, X } from "lucide-react";
import { Conversation, DemoData, Leave, Page, Role, ChatMessage, employeeName } from "@/lib/types";
import { emptyData, fmtDate, fmtTime, loadData, makeId, makeMessage, newConversation, saveData, SESSION_KEY, statusLabel, LeaveDraft } from "@/lib/demo";

const accounts: { role: Role; name: string; title: string; initials: string; color: string; description: string }[] = [
  { role: "alya", name: "Alya Putri", title: "Karyawan", initials: "AP", color: "pink", description: "Tanya kebijakan dan ajukan cuti" },
  { role: "bima", name: "Bima Pratama", title: "Karyawan", initials: "BP", color: "blue", description: "Kelola cuti dan riwayat pribadi" },
  { role: "hr", name: "HR Administrator", title: "HR Admin", initials: "HR", color: "purple", description: "Review dan kelola pengajuan cuti" },
  { role: "monitor", name: "Monitoring Admin", title: "Monitoring", initials: "MA", color: "green", description: "Pantau performa dan alert sistem" },
];
const greetings = ["Berapa saldo cuti saya?", "Hai, mau cuti nih", "Bagaimana kebijakan kerja remote?", "Lihat status pengajuan cuti saya"];
const isEmployee = (r: Role) => r === "alya" || r === "bima";

export default function Home() {
  const [ready, setReady] = useState(false);
  const [role, setRole] = useState<Role | null>(null);
  const [selectedRole, setSelectedRole] = useState<Role>("alya");
  const [theme, setTheme] = useState<"light" | "dark" | "system">("light");
  const [page, setPage] = useState<Page>("chat");
  const [data, setData] = useState<DemoData>(emptyData);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState<LeaveDraft>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState("");
  const [backend, setBackend] = useState<"demo" | "api">("demo");
  const [monitoring, setMonitoring] = useState<{ run_count: number; error_rate: number; p95_latency_ms: number; tool_calls: number } | null>(null);
  const [alerts, setAlerts] = useState<unknown>(null);
  const [monitorError, setMonitorError] = useState("");
  type HRLeaveRequest = {
    request_id: string;
    employee_id: string;
    employee_name: string;
    leave_type: string;
    start_date: string;
    end_date: string;
    business_days: number;
    status: string;
    created_at: string;
  };
  const [hrLeaves, setHrLeaves] = useState<HRLeaveRequest[]>([]);
  const [hrLoading, setHrLoading] = useState(false);
  const [hrError, setHrError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const dataRef = useRef(data);
  useEffect(() => { dataRef.current = data; }, [data]);
  useEffect(() => {
  if (ready && role === "hr") {
    void loadHRRequests();
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [ready, role]);
  const updateData = useCallback((fn: (prev: DemoData) => DemoData) => { const next = fn(dataRef.current); dataRef.current = next; setData(next); saveData(next); }, []);

  useEffect(() => {
    setData(loadData());
    const savedRole = sessionStorage.getItem(SESSION_KEY) as Role | null;
    if (savedRole && accounts.some(a => a.role === savedRole)) { setRole(savedRole); setPage(savedRole === "hr" ? "leaves" : savedRole === "monitor" ? "monitor" : "chat"); }
    const savedTheme = localStorage.getItem("nusahr-theme") as "light" | "dark" | "system" | null;
    if (savedTheme && ["light", "dark", "system"].includes(savedTheme)) setTheme(savedTheme);
    const onStorage = (e: StorageEvent) => { if (e.key === "nusahr-demo-v1") setData(loadData()); };
    const onUpdate = () => setData(loadData());
    window.addEventListener("storage", onStorage);
    window.addEventListener("nusahr-updated", onUpdate);
    setReady(true);
    return () => { window.removeEventListener("storage", onStorage); window.removeEventListener("nusahr-updated", onUpdate); };
  }, []);
  useEffect(() => {
    const dark = theme === "dark" || (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("nusahr-theme", theme);
  }, [theme]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [activeId, data.conversations]);
  useEffect(() => { if (!toast) return; const id = setTimeout(() => setToast(""), 3500); return () => clearTimeout(id); }, [toast]);

  const active = data.conversations.find(c => c.id === activeId && c.role === role);
  const conversations = useMemo(() => data.conversations.filter(c => c.role === role && c.title.toLowerCase().includes(search.toLowerCase())).sort((a,b) => b.createdAt-a.createdAt), [data.conversations, role, search]);
  const leaves = useMemo<Leave[]>(() => {
  if (role === "hr") {
    return hrLeaves.map((r) => ({
      id: r.request_id,
      employee: r.employee_id === "EMP-001" ? "alya" : "bima",
      start: r.start_date,
      end: r.end_date,
      reason: `${r.leave_type} · ${r.business_days} hari kerja`,
      status: r.status as Leave["status"],
      createdAt: new Date(r.created_at).getTime(),
      updatedAt: new Date(r.created_at).getTime(),
    }));
  }

  return data.leaves
  .filter((l) => l.employee === role && l.status !== "draft")
  .sort((a, b) => b.createdAt - a.createdAt);
}, [data.leaves, hrLeaves, role]);
  const pendingCount = hrLeaves.filter(
  (l) => l.status === "pending_manager_review"
).length;
  const currentAccount = accounts.find(a => a.role === role);

  function login() { sessionStorage.setItem(SESSION_KEY, selectedRole); setRole(selectedRole); setActiveId(null); setDraft({}); setPage(selectedRole === "hr" ? "leaves" : selectedRole === "monitor" ? "monitor" : "chat"); if (selectedRole === "hr") {
    void loadHRRequests();
  }}
  function logout() { sessionStorage.removeItem(SESSION_KEY); setRole(null); setActiveId(null); setInput(""); setDraft({}); setSidebarOpen(false); }
  function go(next: Page) { setPage(next); setSidebarOpen(false); if (next === "leaves" && role && isEmployee(role)) void loadMyRequests(); if (next === "monitor" && role === "monitor") void loadMonitoring(); if (next === "leaves" && role === "hr") {
  void loadHRRequests();
}}
  function startNew() { if (!role || !isEmployee(role)) return; const c = newConversation(role); updateData(prev => ({ ...prev, conversations: [c, ...prev.conversations] })); setActiveId(c.id); setDraft({}); setInput(""); go("chat"); }
  function openConversation(id: string) { setActiveId(id); setDraft({}); go("chat"); }
  function removeConversation(id: string) { updateData(prev => ({ ...prev, conversations: prev.conversations.filter(c => c.id !== id) })); if (activeId === id) setActiveId(null); setToast("Percakapan dihapus"); }
  function addAgentMessage(convId: string, text: string, citations?: ChatMessage["citations"], proposalId?: string) {
    updateData(prev => ({ ...prev, conversations: prev.conversations.map(c => c.id === convId ? { ...c, messages: [...c.messages, { ...makeMessage("agent", text), citations, proposalId }] } : c) }));
  }

  async function sendMessage(messageText?: string) {
    const message = (messageText ?? input).trim();

    if (!message || busy || !role || !isEmployee(role)) return;

    setInput("");
    setBusy(true);
    setPage("chat");

    let conv = active;

    if (!conv) {
      conv = newConversation(role);
      setActiveId(conv.id);
    }

    const id = conv.id;

    updateData(prev => {
      const exists = prev.conversations.some(c => c.id === id);
      const base = exists
      ? prev.conversations
      : [conv!, ...prev.conversations];

      return {
        ...prev,
        conversations: base.map(c =>
          c.id === id
          ? {
              ...c,
              title:
                c.messages.length === 0
                  ? message.slice(0, 45)
                  : c.title,
              messages: [
                ...c.messages,
                makeMessage("user", message),
              ],
            }
          : c
        ),
      };
    });

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          role,
          message,
          conversation_id: id,
        }),
      });

    const json = await response.json();

    if (!response.ok) {
      addAgentMessage(
        id,
        `⚠️ ${json.detail || json.error || "Gagal menghubungi backend."}`
      );
      return;
    }

    if (json.mode !== "api" || typeof json.answer !== "string") {
      addAgentMessage(
        id,
        "Respons backend tidak sesuai format yang diharapkan."
      );
      return;
    }

    setBackend("api");

    addAgentMessage(
      id,
      json.answer,
      json.citations,
      json.action_proposal?.proposal_id
    );

    const proposal = json.action_proposal;

    if (proposal?.proposal_id) {
      const existing = dataRef.current.leaves.some(
        l => l.proposalId === proposal.proposal_id
      );

      if (!existing) {
        const now = Date.now();

        const leave: Leave = {
          id: makeId(),
          employee: role,
          start: String(proposal.start_date || ""),
          end: String(proposal.end_date || ""),
          reason: String(proposal.reason || ""),
          status: "draft",
          createdAt: now,
          updatedAt: now,
          proposalId: proposal.proposal_id,
          idempotencyKey: makeId(),
        };

        updateData(prev => ({
          ...prev,
          leaves: [leave, ...prev.leaves],
        }));

        setToast(
          "Proposal cuti siap dikonfirmasi di room chat"
        );
      }
    }
  } catch (error) {
    console.error("Chat request failed:", error);

    addAgentMessage(
      id,
      "⚠️ Koneksi ke AI Agent gagal. Periksa apakah FastAPI berjalan."
    );
  } finally {
    setBusy(false);
  }
}

  async function confirmLeave(id: string) {
    const item = dataRef.current.leaves.find(l => l.id === id);
    if (!item || !role || !isEmployee(role)) return;
    if (item.proposalId) {
      try {
        const res = await fetch("/api/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role, proposal_id: item.proposalId, idempotency_key: item.idempotencyKey }) });
        const json = await res.json();
        if (!res.ok) { setToast(`Konfirmasi gagal: ${json.detail || json.error || res.status}`); return; }
        updateData(prev => ({ ...prev,leaves: prev.leaves.map(l =>l.id === id? { ...l,status: json.status || "pending_manager_review",updatedAt: Date.now(),}: l),}));
        setToast("Pengajuan berhasil dikirim ke backend HR");
      } catch { setToast("Koneksi konfirmasi gagal"); }
    } else {
  setToast("Proposal tidak ditemukan; pengajuan tidak dibuat.");
}
  }
  async function loadMyRequests() {
    if (!role || !isEmployee(role)) return;
    try {
      const res = await fetch(`/api/leaves?role=${role}`, { cache: "no-store" });
      if (!res.ok) return;
      const json = await res.json();
      const records = Array.isArray(json) ? json : Array.isArray(json.requests) ? json.requests : Array.isArray(json.items) ? json.items : [];
      updateData(prev => ({ ...prev, leaves: [ ...prev.leaves.filter(l => l.employee !== role || l.status === "draft"), ...records.map((r: Record<string, unknown>) => ({ id: String(r.request_id || r.id || makeId()), employee: role, start: String(r.start_date || r.start || ""), end: String(r.end_date || r.end || ""), reason: String(r.reason || ""), status: String(r.status || "pending_manager_review") as Leave["status"], createdAt: Date.now(), updatedAt: Date.now() })) ] }));
    } catch { /* keep cached view on network failure */ }
  }
  async function loadHRRequests() {
  setHrLoading(true);
  setHrError("");

  try {
    const response = await fetch("/api/hr-leaves", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const json: unknown = await response.json();

    if (!Array.isArray(json)) {
      throw new Error("Format respons HR tidak sesuai");
    }

    setHrLeaves(json as HRLeaveRequest[]);
  } catch (error) {
    console.error("Gagal mengambil pengajuan HR:", error);
    setHrError("Gagal mengambil data pengajuan cuti dari Neon.");
    setHrLeaves([]);
  } finally {
    setHrLoading(false);
  }
}
async function decideHRLeave(
  requestId: string,
  decision: "approved" | "rejected"
) {
  const action = decision === "approved" ? "menyetujui" : "menolak";

  if (!window.confirm(`Yakin ingin ${action} pengajuan cuti ini?`)) {
    return;
  }

  try {
    setHrLoading(true);
    setHrError("");

    const response = await fetch("/api/hr-decision", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        request_id: requestId,
        decision,
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || "Gagal memproses keputusan HR");
    }

    await loadHRRequests();

    window.alert(
      decision === "approved"
        ? "Pengajuan cuti berhasil disetujui."
        : "Pengajuan cuti berhasil ditolak."
    );
  } catch (error) {
    setHrError(
      error instanceof Error ? error.message : "Terjadi kesalahan"
    );
  } finally {
    setHrLoading(false);
  }
}
  async function loadMonitoring() {
    setMonitorError("");
    try {
      const [a,b] = await Promise.all([fetch("/api/monitoring?role=monitor&resource=summary"),fetch("/api/monitoring?role=monitor&resource=alerts")]);
      if (!a.ok || !b.ok) { setMonitorError(`Monitoring API gagal (${a.status}/${b.status}). Pastikan token admin terkonfigurasi.`); return; }
      setMonitoring(await a.json()); setAlerts(await b.json());
    } catch { setMonitorError("Gagal terhubung ke monitoring backend."); }
  }

  if (!ready) return <div className="loading-screen"><Sparkles size={28}/> Memuat HRAgent...</div>;
  if (!role) return <main className="login-shell"><div className="login-glow"/><div className="login-container">
    <div className="brand login-brand"><span className="brand-logo"><Sparkles size={23}/></span><span>HR<span className="brand-accent">Agent</span></span></div>
    <div className="login-head"><span className="eyebrow"><span className="live-dot"/> AI-powered HR workspace</span><h1>Selamat datang <span className="gradient-text">kembali.</span></h1><p>Asisten HR yang selalu siap membantu. Pilih akun demo untuk menjelajahi pengalaman sesuai peranmu.</p></div>
    <div className="login-card"><div className="section-heading"><div><h2>Pilih akun demo</h2><p>Masuk sebagai salah satu persona berikut</p></div><ShieldCheck size={19}/></div>
      <div className="account-list">{accounts.map(a => <button key={a.role} className={`account-option ${selectedRole === a.role ? "selected" : ""}`} onClick={() => setSelectedRole(a.role)}><span className={`avatar ${a.color}`}>{a.initials}</span><span className="account-info"><strong>{a.name}</strong><small>{a.title} · {a.description}</small></span><span className={`select-indicator ${selectedRole === a.role ? "checked" : ""}`}>{selectedRole === a.role && <Check size={13}/>}</span></button>)}</div>
      <button className="primary-btn login-btn" onClick={login}>Masuk sebagai {accounts.find(a => a.role === selectedRole)?.name} <ArrowRight size={18}/></button>
      <p className="demo-note"><CircleAlert size={15}/> Mode demo tanpa kata sandi — bukan login produksi.</p>
    </div><p className="login-footer">© 2026  · HR Agent Milestone 2</p></div></main>;

  return <div className="app-shell">
    {sidebarOpen && <button aria-label="Tutup sidebar" className="mobile-overlay" onClick={() => setSidebarOpen(false)}/>}
    <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
      <div className="sidebar-top"><div className="brand"><span className="brand-logo"><Sparkles size={19}/></span><span>HR<span className="brand-accent">Agent</span></span></div><button className="icon-btn mobile-close" onClick={() => setSidebarOpen(false)}><X size={19}/></button></div>
      <div className="sidebar-main">
        {isEmployee(role) && <><button className="new-chat" onClick={startNew}><Plus size={19}/> Obrolan baru <span className="kbd">⌘ K</span></button>
        <div className="nav-group"><div className="nav-caption">WORKSPACE</div><button className={`nav-item ${page === "chat" ? "active" : ""}`} onClick={() => go("chat")}><MessageCircle size={18}/> Percakapan</button><button className={`nav-item ${page === "history" ? "active" : ""}`} onClick={() => go("history")}><History size={18}/> Riwayat chat</button><button className={`nav-item ${page === "leaves" ? "active" : ""}`} onClick={() => go("leaves")}><CalendarDays size={18}/> Pengajuan cuti</button></div>
        <div className="nav-group history-group"><div className="nav-caption">TERBARU <span>{conversations.length}</span></div>{conversations.slice(0,6).map(c => <button key={c.id} className={`recent-item ${activeId === c.id && page === "chat" ? "current" : ""}`} onClick={() => openConversation(c.id)}><MessageCircle size={15}/><span>{c.title}</span></button>)}{conversations.length === 0 && <p className="empty-history">Belum ada percakapan</p>}</div></>}
        {role === "hr" && <div className="nav-group"><div className="nav-caption">HR WORKSPACE</div><button className={`nav-item ${page === "leaves" ? "active" : ""}`} onClick={() => go("leaves")}><LayoutDashboard size={18}/> Dashboard HR {pendingCount > 0 && <span className="nav-count">{pendingCount}</span>}</button></div>}
        {role === "monitor" && <div className="nav-group"><div className="nav-caption">ADMIN WORKSPACE</div><button className={`nav-item ${page === "monitor" ? "active" : ""}`} onClick={() => go("monitor")}><Activity size={18}/> Monitoring</button></div>}
      </div>
      <div className="sidebar-bottom"><div className="theme-box"><div className="theme-title"><Sun size={16}/> Tampilan</div><div className="theme-options"><button title="Terang" className={theme === "light" ? "selected" : ""} onClick={() => setTheme("light")}><Sun size={16}/></button><button title="Gelap" className={theme === "dark" ? "selected" : ""} onClick={() => setTheme("dark")}><Moon size={16}/></button><button title="Sistem" className={theme === "system" ? "selected" : ""} onClick={() => setTheme("system")}><span className="system-symbol">◐</span></button></div></div>
        <div className="profile-card"><span className={`avatar ${currentAccount?.color}`}>{currentAccount?.initials}</span><span className="profile-info"><strong>{currentAccount?.name}</strong><small>{currentAccount?.title}</small></span><button className="icon-btn" title="Keluar" onClick={logout}><LogOut size={18}/></button></div>
      </div>
    </aside>
    <main className="main-area"><header className="topbar"><div className="topbar-left"><button className="icon-btn menu-toggle" onClick={() => setSidebarOpen(true)}><Menu size={21}/></button><span className="breadcrumb">Workspace <span>/</span> <strong>{role === "hr" ? "Dashboard HR" : role === "monitor" ? "Monitoring" : page === "chat" ? "Percakapan" : page === "history" ? "Riwayat Chat" : "Pengajuan Cuti"}</strong></span></div><div className="topbar-right"><span className="demo-pill"><span className="live-dot"/> DEMO MODE</span><span className={`avatar tiny ${currentAccount?.color}`}>{currentAccount?.initials}</span></div></header>
    {role && isEmployee(role) && page === "chat" && <section className="chat-page"><div className="chat-scroll"><div className="chat-inner">
      {!active || active.messages.length === 0 ? <div className="welcome"><div className="welcome-icon"><Sparkles size={29}/></div><span className="eyebrow">PERSONAL HR ASSISTANT</span><h1>Hai, {employeeName(role).split(" ")[0]} <span className="wave">👋</span></h1><p>Ada yang bisa kubantu hari ini? Tanya seputar kebijakan HR, pengajuan cuti, atau informasi kepegawaian.</p><div className="suggestions">{greetings.map((g,i) => <button key={g} onClick={() => sendMessage(g)}><span className="suggestion-icon">{i===0?<CalendarDays size={17}/>:i===1?<Sparkles size={17}/>:i===2?<BookOpen size={17}/>:<FileText size={17}/>}</span><span>{g}</span><ArrowRight size={15}/></button>)}</div></div> : <div className="messages"><div className="conversation-date">Hari ini</div>{active.messages.map(m => <div className={`message-row ${m.from}`} key={m.id}>{m.from === "agent" && <div className="agent-avatar"><Sparkles size={16}/></div>}<div className="message-content"><div className="message-meta">{m.from === "agent" ? "HRAgent Assistant" : employeeName(role)} <span>{fmtTime(m.time)}</span></div><div className="bubble">{m.text.split(/(\*\*[^*]+\*\*)/g).map((chunk,i) => chunk.startsWith("**") && chunk.endsWith("**") ? <strong key={i}>{chunk.slice(2,-2)}</strong> : <span key={i}>{chunk}</span>)}</div>{m.citations && m.citations.length > 0 && <details className="citations"><summary><BookOpen size={14}/> {m.citations.length} sumber kebijakan</summary>{m.citations.map((c,i) => <div className="citation" key={i}><strong>{c.document_id} · {c.section}</strong><p>{c.excerpt}</p></div>)}</details>}{m.proposalId && (() => {const proposal = data.leaves.find((l) =>l.proposalId === m.proposalId &&l.employee === role);if (!proposal) return null;

  return (
    <div className="api-proposal">
      <div style={{ marginBottom: "12px" }}>
        <strong>Pengajuan Cuti</strong>

        <p>
          <strong>Tanggal:</strong>{" "}
          {fmtDate(proposal.start)} – {fmtDate(proposal.end)}
        </p>

        <p>
          <strong>Alasan:</strong> {proposal.reason}
        </p>
      </div>

      {proposal.status === "draft" ? (
        <button
          type="button"
          className="primary-btn"
          disabled={busy}
          onClick={() => {
            if (
              window.confirm(
                "Apakah data pengajuan cuti sudah benar dan ingin dikirim ke HR?"
              )
            ) {
              void confirmLeave(proposal.id);
            }
          }}
        >
          <CheckCircle2 size={17} />
          Konfirmasi Pengajuan
        </button>
      ) : (
        <span className="status pending_manager_review">
          Pengajuan telah dikirim ke HR
        </span>
      )}
    </div>
    );
})()}
</div>
</div>
)}
      {busy && <div className="message-row agent"><div className="agent-avatar"><Sparkles size={16}/></div><div className="typing"><span/><span/><span/></div></div>}
      {leaves.filter(l => l.status === "draft").length > 0 && (
  <div className="draft-banner">
    <div>
      <strong>Pengajuan cuti siap dikonfirmasi</strong>
      <p>Periksa detailnya sebelum dikirim ke HR.</p>
    </div>
    <button className="secondary-btn" onClick={() => go("leaves")}>
      Lihat detail <ArrowRight size={15} />
    </button>
  </div>
)}
      <div ref={bottomRef}/></div>}
      </div></div><div className="composer-wrap"><form className="composer" onSubmit={e => { e.preventDefault(); sendMessage(); }}><textarea aria-label="Tulis pesan" rows={1} placeholder="Tanya sesuatu atau ajukan cuti..." value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}/><button className="send-btn" type="submit" disabled={!input.trim() || busy} aria-label="Kirim"><Send size={19}/></button></form><p className="composer-note">HRAgent dapat membuat kesalahan. Verifikasi informasi penting. · {backend === "api" ? "Terhubung ke FastAPI" : "Mode percakapan demo"}</p></div></section>}
    {role && isEmployee(role) && page === "history" && <section className="content-page"><div className="page-title"><div><span className="eyebrow">YOUR CONVERSATIONS</span><h1>Riwayat percakapan</h1><p>Lanjutkan percakapan yang pernah kamu mulai.</p></div><button className="primary-btn" onClick={startNew}><Plus size={17}/> Chat baru</button></div><div className="search-box"><Search size={18}/><input placeholder="Cari percakapan..." value={search} onChange={e => setSearch(e.target.value)}/></div><div className="history-list">{conversations.map(c => <div className="history-card" key={c.id}><button onClick={() => openConversation(c.id)}><span className="history-icon"><MessageCircle size={19}/></span><span><strong>{c.title}</strong><small>{c.messages.length} pesan · {new Date(c.createdAt).toLocaleDateString("id-ID")}</small></span></button><button className="icon-btn delete-btn" title="Hapus" onClick={() => removeConversation(c.id)}><Trash2 size={17}/></button></div>)}{conversations.length===0 && <div className="empty-state"><History size={35}/><h3>Belum ada riwayat</h3><p>Mulai obrolan untuk menyimpan percakapan pertamamu.</p></div>}</div></section>}
    {role && (isEmployee(role) || role === "hr") && page === "leaves" && <section className="content-page"><div className="page-title"><div><span className="eyebrow">{role === "hr" ? "HR MANAGEMENT" : "LEAVE MANAGEMENT"}</span><h1>{role === "hr" ? "Dashboard HR" : "Pengajuan cuti"}</h1><p>{role === "hr" ? "Tinjau dan kelola pengajuan cuti karyawan." : "Pantau pengajuan dan status persetujuan cutimu."}</p></div></div>
      <div className="stat-grid"><div className="stat-card"><span className="stat-icon blue"><FileText size={21}/></span><span>Total pengajuan</span><strong>{leaves.length}</strong><small>Semua pengajuan</small></div><div className="stat-card"><span className="stat-icon amber"><Clock3 size={21}/></span><span>Menunggu review</span><strong>{leaves.filter(l => l.status === "pending_manager_review").length}</strong><small>Perlu tindak lanjut</small></div><div className="stat-card"><span className="stat-icon green"><CheckCircle2 size={21}/></span><span>Disetujui</span>
<strong>{leaves.filter(l => l.status === "approved").length}</strong>
<small>Pengajuan disetujui HR</small></div></div>
      <div className="table-card"><div className="table-heading"><div><h2>{role === "hr" ? "Pengajuan masuk" : "Daftar pengajuan"}</h2><p>{role === "hr" ? "Keputusan HR akan terlihat di akun karyawan pada browser demo yang sama." : "Pengajuan memerlukan konfirmasi sebelum diproses HR."}</p></div><span className="count-pill">{leaves.length} pengajuan</span></div>
      {leaves.length === 0 ? <div className="empty-state"><CalendarDays size={35}/><h3>Belum ada pengajuan</h3><p>{role === "hr" ? "Pengajuan karyawan akan tampil di sini." : "Katakan 'mau cuti' kepada AI Agent untuk memulai."}</p></div> : <div className="leave-list">{leaves.map(l => <div className="leave-card" key={l.id}><div className="leave-main"><div className="leave-icon"><CalendarDays size={21}/></div><div className="leave-details"><div className="leave-heading"><strong>{role === "hr" ? employeeName(l.employee) : "Cuti tahunan"}</strong><span className={`status ${l.status}`}>{statusLabel(l.status)}</span></div><p>{fmtDate(l.start)} – {fmtDate(l.end)}</p><small>{l.reason} · ID {l.id.slice(0,8)}</small></div></div><div className="leave-actions">{role === "hr" && l.status === "pending_manager_review" && (
  <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
    <button
      type="button"
      disabled={hrLoading}
      onClick={() => void decideHRLeave(l.id, "approved")}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 18px",
        borderRadius: "10px",
        border: "none",
        background: "#16a34a",
        color: "#ffffff",
        fontWeight: 600,
        cursor: hrLoading ? "wait" : "pointer",
      }}
    >
      <CheckCircle2 size={17} />
      Setujui
    </button>

    <button
      type="button"
      disabled={hrLoading}
      onClick={() => void decideHRLeave(l.id, "rejected")}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "8px",
        padding: "10px 18px",
        borderRadius: "10px",
        border: "1px solid rgba(239,68,68,0.35)",
        background: "rgba(239,68,68,0.10)",
        color: "#ef4444",
        fontWeight: 600,
        cursor: hrLoading ? "wait" : "pointer",
      }}
    >
      <X size={17} />
      Tolak
    </button>
  </div>
)}

{l.status !== "draft" && (
  <span className="updated-at">
    Diperbarui{" "}
    {new Date(l.updatedAt).toLocaleDateString("id-ID")}
  </span>
)}</div></div>)}</div>}</div>
  <div className="info-note"><CircleAlert size={18}/><p><strong>Mode demo:</strong> status tersimpan di browser ini. Agar Alya, Bima, dan HR dapat mengakses data yang sama dari perangkat berbeda, endpoint HR dan database Neon harus diintegrasikan.</p></div></section>}
    {role === "monitor" && page === "monitor" && <section className="content-page"><div className="page-title"><div><span className="eyebrow">SYSTEM OBSERVABILITY</span><h1>Monitoring AI Agent</h1><p>Ringkasan aktivitas dan kesehatan sistem.</p></div><span className="demo-pill"><span className="live-dot"/> Data FastAPI</span><button className="secondary-btn" onClick={loadMonitoring}>Muat monitoring</button>{monitorError && <p role="alert">{monitorError}</p>}</div><div className="stat-grid four"><div className="stat-card"><span className="stat-icon blue"><Activity size={21}/></span><span>Total runs</span><strong>{monitoring ? monitoring.run_count : "—"}</strong><small>FastAPI</small></div><div className="stat-card"><span className="stat-icon red"><CircleAlert size={21}/></span><span>Error rate</span><strong>{monitoring ? `${(monitoring.error_rate*100).toFixed(1)}%` : "—"}</strong><small>FastAPI</small></div><div className="stat-card"><span className="stat-icon purple"><Clock3 size={21}/></span><span>p95 latency</span><strong>{monitoring ? Math.round(monitoring.p95_latency_ms) : "—"} <em>ms</em></strong><small>FastAPI</small></div><div className="stat-card"><span className="stat-icon green"><Sparkles size={21}/></span><span>Tool calls</span><strong>{monitoring ? monitoring.tool_calls : "—"}</strong><small>FastAPI</small></div></div><div className="monitor-grid"><div className="table-card"><div className="table-heading"><div><h2>Aktivitas AI Agent</h2><p>Visualisasi ilustratif, bukan metrik backend</p></div></div><div className="bars">{[34,60,45,78,54,88,72,100,62,80,57,93].map((v,i) => <div className="bar-col" key={i}><div style={{height:`${v}%`}}/><span>{i+1}</span></div>)}</div></div><div className="table-card"><div className="table-heading"><div><h2>Alert sistem</h2><p>Status monitoring</p></div></div><div className="alert-good"><CheckCircle2 size={26}/><strong>Tidak ada alert demo</strong><p>{alerts ? JSON.stringify(alerts) : "Belum ada data alert. Klik Muat monitoring."}</p></div></div></div><div className="info-note"><ShieldCheck size={18}/><p>Monitoring hanya ditampilkan untuk role Monitoring Admin. Perlindungan sebenarnya tetap harus diterapkan di backend dengan autentikasi dan otorisasi admin.</p></div></section>}
    </main>{toast && <div className="toast"><CheckCircle2 size={18}/>{toast}</div>}
  </div>;}
