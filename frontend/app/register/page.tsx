import type { Metadata } from "next";
import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";
export const metadata: Metadata = { title: "Create account" };
export default function RegisterPage() { return <AuthShell title="Meet your new copilot" copy="Create an account and give your plans a place to grow."><AuthForm mode="register" /></AuthShell>; }
