"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { authApi } from "@/lib/api";

const loginSchema = z.object({ email: z.string().email("Enter a valid email"), password: z.string().min(1, "Password is required") });
const registerSchema = loginSchema.extend({
  displayName: z.string().trim().min(1, "Name is required").max(120),
  password: z.string().min(12, "Use at least 12 characters").refine((value) => [/[a-z]/.test(value), /[A-Z]/.test(value), /\d/.test(value)].filter(Boolean).length >= 2, "Use two of: uppercase, lowercase, number"),
});
type FormValues = z.infer<typeof registerSchema>;

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [serverError, setServerError] = useState("");
  const schema = mode === "register" ? registerSchema : loginSchema;
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError("");
    try {
      if (mode === "register") {
        await authApi.register({ email: values.email, password: values.password, display_name: values.displayName, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone });
      } else {
        await authApi.login({ email: values.email, password: values.password });
      }
      router.replace("/app");
    } catch (error) {
      setServerError(error instanceof Error ? error.message : "Unable to continue");
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit(onSubmit)} noValidate>
      {mode === "register" && <Field label="Your name" error={errors.displayName?.message}><input autoComplete="name" placeholder="Ada Lovelace" {...register("displayName")} /></Field>}
      <Field label="Email address" error={errors.email?.message}><input type="email" autoComplete="email" placeholder="you@example.com" {...register("email")} /></Field>
      <Field label="Password" error={errors.password?.message}><input type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} placeholder={mode === "register" ? "12+ characters" : "Your password"} {...register("password")} /></Field>
      {serverError && <p className="form-alert" role="alert">{serverError}</p>}
      <button className="primary-button" disabled={isSubmitting} type="submit">
        {isSubmitting ? <LoaderCircle className="spin" size={18} /> : <>{mode === "login" ? "Sign in" : "Create account"}<ArrowRight size={17} /></>}
      </button>
      <p className="auth-switch">{mode === "login" ? "New to Aster?" : "Already have an account?"} <Link href={mode === "login" ? "/register" : "/login"}>{mode === "login" ? "Create an account" : "Sign in"}</Link></p>
    </form>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return <label className="field"><span>{label}</span>{children}{error && <small>{error}</small>}</label>;
}
