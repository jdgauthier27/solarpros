import React, { useState } from "react";
import {
  useOutreachQueue,
  useLinkedInActions,
  useCallList,
  useDirectMailQueue,
  useUpdateOutreachTouch,
} from "../../hooks/useApi";
import type { OutreachTouch } from "../../api/client";

type Tab = "all" | "linkedin" | "phone" | "direct_mail";

const TABS: { key: Tab; label: string }[] = [
  { key: "all", label: "All Outreach" },
  { key: "linkedin", label: "LinkedIn Actions" },
  { key: "phone", label: "Call List" },
  { key: "direct_mail", label: "Direct Mail" },
];

const STATUS_OPTIONS = ["pending", "sent", "delivered", "opened", "replied", "completed", "skipped"];

const statusColors: Record<string, { bg: string; text: string }> = {
  pending: { bg: "#f3f4f6", text: "#6b7280" },
  sent: { bg: "#dbeafe", text: "#1e40af" },
  delivered: { bg: "#dcfce7", text: "#166534" },
  opened: { bg: "#fef3c7", text: "#92400e" },
  replied: { bg: "#d1fae5", text: "#065f46" },
  completed: { bg: "#dcfce7", text: "#166534" },
  answered: { bg: "#dcfce7", text: "#166534" },
  connected: { bg: "#dbeafe", text: "#1e40af" },
  skipped: { bg: "#fee2e2", text: "#991b1b" },
};

const channelColors: Record<string, { bg: string; text: string }> = {
  email: { bg: "#dbeafe", text: "#1e40af" },
  linkedin: { bg: "#e0e7ff", text: "#3730a3" },
  phone: { bg: "#dcfce7", text: "#166534" },
  direct_mail: { bg: "#fef3c7", text: "#92400e" },
};

const styles = {
  container: { padding: "24px", fontFamily: "system-ui, sans-serif" } as React.CSSProperties,
  tabs: { display: "flex", gap: "0", marginBottom: "20px", borderBottom: "2px solid #e5e7eb" } as React.CSSProperties,
  tab: (active: boolean) =>
    ({
      padding: "10px 20px",
      cursor: "pointer",
      fontWeight: active ? 600 : 400,
      color: active ? "#2563eb" : "#6b7280",
      borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
      marginBottom: "-2px",
      fontSize: "14px",
      background: "none",
      border: "none",
      borderBottomWidth: "2px",
      borderBottomStyle: "solid",
      borderBottomColor: active ? "#2563eb" : "transparent",
    }) as React.CSSProperties,
  card: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: "12px", padding: "20px" } as React.CSSProperties,
  table: { width: "100%", borderCollapse: "collapse" as const, fontSize: "13px" } as React.CSSProperties,
  th: { padding: "10px 12px", textAlign: "left" as const, borderBottom: "2px solid #e5e7eb", fontWeight: 600, color: "#374151", fontSize: "12px", textTransform: "uppercase" as const, letterSpacing: "0.5px" } as React.CSSProperties,
  td: { padding: "8px 12px", borderBottom: "1px solid #f3f4f6", color: "#4b5563", verticalAlign: "top" as const } as React.CSSProperties,
  badge: (status: string) =>
    ({
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: "12px",
      fontSize: "11px",
      fontWeight: 600,
      backgroundColor: statusColors[status]?.bg ?? "#f3f4f6",
      color: statusColors[status]?.text ?? "#6b7280",
    }) as React.CSSProperties,
  channelBadge: (channel: string) =>
    ({
      display: "inline-block",
      padding: "2px 10px",
      borderRadius: "12px",
      fontSize: "11px",
      fontWeight: 600,
      backgroundColor: channelColors[channel]?.bg ?? "#f3f4f6",
      color: channelColors[channel]?.text ?? "#6b7280",
    }) as React.CSSProperties,
  select: { padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: "4px", fontSize: "12px", background: "#fff" } as React.CSSProperties,
  notesInput: { padding: "4px 8px", border: "1px solid #d1d5db", borderRadius: "4px", fontSize: "12px", width: "100%" } as React.CSSProperties,
  saveBtn: { padding: "4px 10px", backgroundColor: "#2563eb", color: "#fff", border: "none", borderRadius: "4px", fontSize: "12px", cursor: "pointer", fontWeight: 600 } as React.CSSProperties,
};

function formatDate(ts: string | null): string {
  if (!ts) return "-";
  return new Date(ts).toLocaleString();
}

function TouchTable({ touches, showChannel }: { touches: OutreachTouch[]; showChannel: boolean }) {
  const updateTouch = useUpdateOutreachTouch();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editOutcome, setEditOutcome] = useState("");

  const startEdit = (touch: OutreachTouch) => {
    setEditingId(touch.id);
    setEditStatus(touch.status);
    setEditNotes(touch.notes ?? "");
    setEditOutcome(touch.call_outcome ?? touch.linkedin_connection_status ?? "");
  };

  const saveEdit = (touch: OutreachTouch) => {
    const payload: Record<string, string | number | undefined> = {};
    if (editStatus !== touch.status) payload.status = editStatus;
    if (editNotes !== (touch.notes ?? "")) payload.notes = editNotes;
    if (touch.channel === "phone" && editOutcome !== (touch.call_outcome ?? "")) {
      payload.call_outcome = editOutcome;
    }
    if (touch.channel === "linkedin" && editOutcome !== (touch.linkedin_connection_status ?? "")) {
      payload.linkedin_connection_status = editOutcome;
    }
    if (Object.keys(payload).length > 0) {
      updateTouch.mutate({ touchId: touch.id, payload });
    }
    setEditingId(null);
  };

  return (
    <table style={styles.table}>
      <thead>
        <tr>
          {showChannel && <th style={styles.th}>Channel</th>}
          <th style={styles.th}>Contact</th>
          <th style={styles.th}>Status</th>
          <th style={styles.th}>Sent</th>
          <th style={styles.th}>Outcome</th>
          <th style={styles.th}>Notes</th>
          <th style={styles.th}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {touches.map((touch) => (
          <tr key={touch.id}>
            {showChannel && (
              <td style={styles.td}>
                <span style={styles.channelBadge(touch.channel)}>{touch.channel.replace("_", " ")}</span>
              </td>
            )}
            <td style={styles.td}>
              <span style={{ fontSize: "12px", color: "#6b7280" }}>{touch.contact_id.slice(0, 8)}...</span>
            </td>
            <td style={styles.td}>
              {editingId === touch.id ? (
                <select style={styles.select} value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              ) : (
                <span style={styles.badge(touch.status)}>{touch.status}</span>
              )}
            </td>
            <td style={styles.td}>{formatDate(touch.sent_at)}</td>
            <td style={styles.td}>
              {editingId === touch.id ? (
                touch.channel === "phone" || touch.channel === "linkedin" ? (
                  <input style={styles.notesInput} value={editOutcome} onChange={(e) => setEditOutcome(e.target.value)} placeholder={touch.channel === "phone" ? "answered / voicemail / no_answer" : "pending / accepted / declined"} />
                ) : (
                  <span style={{ fontSize: "12px", color: "#9ca3af" }}>-</span>
                )
              ) : (
                <span style={{ fontSize: "12px" }}>
                  {touch.call_outcome ?? touch.linkedin_connection_status ?? touch.response_type ?? "-"}
                </span>
              )}
            </td>
            <td style={styles.td}>
              {editingId === touch.id ? (
                <input style={styles.notesInput} value={editNotes} onChange={(e) => setEditNotes(e.target.value)} placeholder="Add notes..." />
              ) : (
                <span style={{ fontSize: "12px", color: "#6b7280" }}>{touch.notes ?? "-"}</span>
              )}
            </td>
            <td style={styles.td}>
              {editingId === touch.id ? (
                <div style={{ display: "flex", gap: "4px" }}>
                  <button style={styles.saveBtn} onClick={() => saveEdit(touch)}>Save</button>
                  <button style={{ ...styles.saveBtn, backgroundColor: "#6b7280" }} onClick={() => setEditingId(null)}>Cancel</button>
                </div>
              ) : (
                <button style={{ ...styles.saveBtn, backgroundColor: "#f3f4f6", color: "#374151" }} onClick={() => startEdit(touch)}>Edit</button>
              )}
            </td>
          </tr>
        ))}
        {touches.length === 0 && (
          <tr>
            <td colSpan={showChannel ? 7 : 6} style={{ ...styles.td, textAlign: "center", color: "#9ca3af", padding: "40px" }}>
              No outreach touches found
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}

export function OutreachQueues() {
  const [activeTab, setActiveTab] = useState<Tab>("all");
  const [statusFilter, setStatusFilter] = useState("pending");

  const allQueue = useOutreachQueue({ status: statusFilter });
  const linkedInQueue = useLinkedInActions(statusFilter);
  const callQueue = useCallList(statusFilter);
  const mailQueue = useDirectMailQueue(statusFilter);

  const currentData = (() => {
    switch (activeTab) {
      case "linkedin": return linkedInQueue;
      case "phone": return callQueue;
      case "direct_mail": return mailQueue;
      default: return allQueue;
    }
  })();

  return (
    <div style={styles.container}>
      <h2 style={{ margin: "0 0 20px", fontSize: "24px", color: "#111827" }}>Outreach Queues</h2>

      {/* Tabs */}
      <div style={styles.tabs}>
        {TABS.map((tab) => (
          <button key={tab.key} style={styles.tab(activeTab === tab.key)} onClick={() => setActiveTab(tab.key)}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Status Filter */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "16px", alignItems: "center" }}>
        <span style={{ fontSize: "12px", fontWeight: 600, color: "#6b7280", textTransform: "uppercase" }}>Status</span>
        <select style={{ ...styles.select, padding: "8px 12px", fontSize: "14px" }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {currentData.isLoading && <span style={{ fontSize: "13px", color: "#6b7280" }}>Loading...</span>}
      </div>

      {currentData.error && (
        <div style={{ color: "#dc2626", padding: "12px", background: "#fef2f2", borderRadius: "8px", marginBottom: "16px" }}>
          Failed to load outreach data
        </div>
      )}

      {/* Table */}
      <div style={styles.card}>
        <TouchTable touches={currentData.data ?? []} showChannel={activeTab === "all"} />
      </div>
    </div>
  );
}

export default OutreachQueues;
