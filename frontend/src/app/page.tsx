"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RootPage() {
  const router = useRouter();
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const role = localStorage.getItem("role");
    if (!token) {
      router.replace("/auth/login");
    } else if (role === "manager") {
      router.replace("/manager/dashboard");
    } else {
      router.replace("/employee/dashboard");
    }
  }, [router]);
  return null;
}
