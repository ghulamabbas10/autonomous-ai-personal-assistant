import type { Metadata } from "next";
import { AuthForm } from "@/components/auth-form";
import { AuthShell } from "@/components/auth-shell";
export const metadata: Metadata = { title: "Sign in" };
export default function LoginPage() { return <AuthShell title="Welcome back" copy="Sign in to continue where you left off."><AuthForm mode="login" /></AuthShell>; }
