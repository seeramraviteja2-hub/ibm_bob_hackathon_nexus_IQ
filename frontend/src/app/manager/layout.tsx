"use client";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, BookOpen, LogOut, Zap } from "lucide-react";
import { clearAuth } from "@/lib/auth";

const navItems = [
  { href: "/manager/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/manager/courses",   label: "Courses",   icon: BookOpen },
];

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const handleLogout = () => {
    clearAuth();
    router.replace("/auth/login");
  };

  return (
    <div className="flex h-screen bg-[#0a0a0f] overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 flex flex-col border-r border-white/8 bg-[#111118]">
        <div className="px-5 py-5 flex items-center gap-2 border-b border-white/8">
          <Zap size={18} className="text-indigo-400" />
          <span className="font-bold text-white text-sm">NexusIQ</span>
          <span className="ml-auto text-[10px] text-white/30 uppercase tracking-widest">Manager</span>
        </div>
        <nav className="flex-1 p-3 space-y-0.5">
          {navItems.map(item => {
            const active = pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  active ? "bg-indigo-600/20 text-indigo-300 font-medium" : "text-white/50 hover:text-white hover:bg-white/5"
                }`}>
                <item.icon size={15} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-white/8">
          <button onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-white/40 hover:text-white hover:bg-white/5 transition">
            <LogOut size={15} /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
