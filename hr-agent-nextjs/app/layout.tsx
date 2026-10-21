import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "HR Agent · AI Assistant", description: "Demo HR Agent — AI chat, leave requests, and role dashboards" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="id"><body>{children}</body></html>; }
