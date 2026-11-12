"use client";

import { BottomNav } from "@/components/BottomNav";
import { AccountCard } from "@/components/account/AccountCard";
import { SecurityForms } from "@/components/account/SecurityForms";
import { useToken } from "@/lib/useToken";

export default function CuentaSeguridad() {
  const token = useToken();
  return (
    <main className="dashboard">
      <BottomNav />
      {token && <AccountCard token={token} />}
      <SecurityForms />
    </main>
  );
}
