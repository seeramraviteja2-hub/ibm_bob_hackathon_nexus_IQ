"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, Zap } from "lucide-react";
import api from "@/lib/api";
import { saveAuth } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "", password: "", first_name: "", last_name: "", role: "employee",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.post("/api/v1/auth/register", form);
      saveAuth(res.data);
      router.replace(res.data.role === "manager" ? "/manager/dashboard" : "/employee/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.error || "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(p => ({ ...p, [k]: e.target.value }));

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0f] px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 text-indigo-400 font-bold text-xl">
            <Zap size={20} /> NexusIQ
          </div>
          <h1 className="text-2xl font-bold text-white">Create account</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-white/50 uppercase tracking-widest">First Name</label>
              <input value={form.first_name} onChange={f("first_name")} required
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition" />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-white/50 uppercase tracking-widest">Last Name</label>
              <input value={form.last_name} onChange={f("last_name")} required
                className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition" />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-widest">Email</label>
            <input type="email" value={form.email} onChange={f("email")} required
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-widest">Password</label>
            <input type="password" value={form.password} onChange={f("password")} required minLength={6}
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-white/50 uppercase tracking-widest">Role</label>
            <select value={form.role} onChange={f("role")}
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition">
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
            </select>
          </div>

          {error && <p className="text-red-400 text-xs text-center">{error}</p>}

          <button type="submit" disabled={isLoading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2 text-sm">
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : null}
            Create Account
          </button>
        </form>

        <p className="text-center text-sm text-white/40">
          Have an account?{" "}
          <Link href="/auth/login" className="text-indigo-400 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
