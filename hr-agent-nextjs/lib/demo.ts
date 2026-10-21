import { ChatMessage, Conversation, DemoData, Leave, Role } from "./types";
export const STORAGE_KEY = "nusahr-demo-v1";
export const SESSION_KEY = "nusahr-session-v1";
export const emptyData: DemoData = { conversations: [], leaves: [] };
export function loadData(): DemoData {
  try { const raw = localStorage.getItem(STORAGE_KEY); if (raw) { const data = JSON.parse(raw); return { conversations: data.conversations || [], leaves: data.leaves || [] }; } } catch {}
  return emptyData;
}
export function saveData(data: DemoData) { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); window.dispatchEvent(new Event("nusahr-updated")); }
export const makeId = () => crypto.randomUUID();
export const makeMessage = (from: ChatMessage["from"], text: string): ChatMessage => ({ id: makeId(), from, text, time: Date.now() });
export function newConversation(role: Role): Conversation { return { id: makeId(), role, title: "Percakapan baru", messages: [], createdAt: Date.now() }; }
export function fmtDate(value: string) { if (!value) return "—"; return new Date(value + "T12:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }); }
export function fmtTime(time: number) { return new Date(time).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }); }
export function statusLabel(status: Leave["status"]) { return ({ draft: "Perlu konfirmasi", pending_manager_review: "Menunggu persetujuan", approved: "Disetujui", rejected: "Ditolak" })[status]; }
export type LeaveDraft = { start?: string; end?: string; reason?: string };
export function parseLeaveDates(text: string): { start?: string; end?: string } {
  const iso = [...text.matchAll(/\b(20\d{2})-(\d{2})-(\d{2})\b/g)].map(m => `${m[1]}-${m[2]}-${m[3]}`);
  if (iso.length >= 2) return { start: iso[0], end: iso[1] };
  const months: Record<string,number> = { januari:1, februari:2, maret:3, april:4, mei:5, juni:6, juli:7, agustus:8, september:9, oktober:10, november:11, desember:12 };
  const matches = [...text.toLowerCase().matchAll(/\b(\d{1,2})\s+(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\s+(20\d{2})\b/g)];
  const parsed = matches.map(m => `${m[3]}-${String(months[m[2]]).padStart(2,"0")}-${m[1].padStart(2,"0")}`);
  return { start: parsed[0], end: parsed[1] };
}
export function demoReply(text: string, messages: ChatMessage[], draft: LeaveDraft): { reply: string; draft: LeaveDraft; ready: boolean } {
  const lower = text.toLowerCase();
  const leaveIntent = /cuti|izin|leave/.test(lower) || Boolean(draft.start || draft.end || draft.reason);
  if (!leaveIntent) {
    if (/halo|hai|hello|hi\b/.test(lower)) return { reply: "Hai! 👋 Aku Nusa, asisten HR kamu. Aku bisa membantu informasi kebijakan HR, saldo cuti, atau membuat pengajuan cuti. Ada yang bisa kubantu?", draft: {}, ready: false };
    return { reply: "Aku siap membantu. Kamu bisa bertanya tentang kebijakan HR atau bilang 'mau cuti' untuk mulai pengajuan. Untuk jawaban berbasis dokumen RAG, sambungkan frontend ini ke FastAPI.", draft: {}, ready: false };
  }
  const dates = parseLeaveDates(text);
  const next = { ...draft, ...Object.fromEntries(Object.entries(dates).filter(([,v]) => Boolean(v))) } as LeaveDraft;
  const reasonMatch = text.match(/(?:alasan(?:nya)?|karena|untuk|keperluan)\s*[:\-]?\s*(.+)/i);
  if (reasonMatch) next.reason = reasonMatch[1].trim().replace(/[.!]+$/, "");
  else if (draft.start && draft.end && !draft.reason && !dates.start && text.trim().length > 3 && !/\b(cuti|tanggal|dari|sampai)\b/i.test(text)) next.reason = text.trim();
  if (!next.start || !next.end) return { reply: "Tentu, aku bantu ajukan cutinya! 😊 Kapan tanggal mulai dan tanggal akhir cutinya? Contoh: **21 Oktober 2026 sampai 23 Oktober 2026**.", draft: next, ready: false };
  if (next.end < next.start) return { reply: "Tanggal akhir tidak boleh sebelum tanggal mulai. Bisa periksa lagi tanggal cutinya?", draft: { ...next, end: undefined }, ready: false };
  if (!next.reason) return { reply: `Oke, cutinya dari **${fmtDate(next.start)}** sampai **${fmtDate(next.end)}**. Untuk keperluan apa cutinya?`, draft: next, ready: false };
  return { reply: `Siap! Aku sudah menyiapkan pengajuan cuti **${fmtDate(next.start)} – ${fmtDate(next.end)}** dengan alasan **${next.reason}**. Periksa ringkasannya, lalu klik **Konfirmasi pengajuan** agar masuk ke antrean HR.`, draft: next, ready: true };
}
