import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
export const metadata: Metadata = { title: "Workspace" };
export default function WorkspacePage() { return <AppShell />; }
