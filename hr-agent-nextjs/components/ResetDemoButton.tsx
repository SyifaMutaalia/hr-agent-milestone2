"use client";
import { useState } from "react";

export default function ResetDemoButton({ onReset }: { onReset?: () => void }) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  async function reset() {
    if (!window.confirm("Hapus SEMUA proposal dan pengajuan demo Alya & Bima, lalu pulihkan saldo awal?")) return;
    const pin = window.prompt("Masukkan PIN Reset Demo (khusus HR Admin):");
    if (pin === null) return;
    setBusy(true); setNotice("");
    try {
      const response = await fetch("/api/demo/reset", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || "Reset gagal");
      setNotice("Data demo berhasil direset. Saldo Alya: 8 hari, Bima: 3 hari.");
      onReset?.();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Reset gagal");
    } finally { setBusy(false); }
  }
  return <div style={{ display: "grid", gap: 8, margin: "16px 0" }}>
    <button type="button" disabled={busy} onClick={reset} className="secondary-btn">
      {busy ? "Mereset..." : "Reset Data Demo"}
    </button>
    {notice && <p role="status">{notice}</p>}
  </div>;
}
