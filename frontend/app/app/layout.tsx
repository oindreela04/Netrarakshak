"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Shell } from "@/components/app/shell";
import { Loading } from "@/components/app/bits";

function Guard({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  const router = useRouter();
  useEffect(() => { if (!loading && !me) router.replace("/login"); }, [loading, me, router]);
  if (loading || !me) return <div className="flex min-h-screen items-center justify-center"><Loading label="Opening NetraRakshak" /></div>;
  return <Shell>{children}</Shell>;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider><Guard>{children}</Guard></AuthProvider>;
}
