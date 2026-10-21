export type Role = "alya" | "bima" | "hr" | "monitor";
export type Page = "chat" | "history" | "leaves" | "monitor";
export type LeaveStatus = "draft" | "pending_manager_review" | "approved" | "rejected";
export type ChatMessage = { id: string; from: "user" | "agent"; text: string; time: number; citations?: { document_id: string; section: string; excerpt: string }[]; proposalId?: string };
export type Conversation = { id: string; role: Role; title: string; messages: ChatMessage[]; createdAt: number };
export type Leave = { id: string; employee: "alya" | "bima"; start: string; end: string; reason: string; status: LeaveStatus; createdAt: number; updatedAt: number; proposalId?: string; idempotencyKey?: string };
export type DemoData = { conversations: Conversation[]; leaves: Leave[] };
export const employeeName = (role: Role) => ({ alya: "Alya Putri", bima: "Bima Pratama", hr: "HR Administrator", monitor: "Monitoring Admin" })[role];
