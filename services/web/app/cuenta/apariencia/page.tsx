"use client";

import { BottomNav } from "@/components/BottomNav";
import { AppearanceCard } from "@/components/account/AppearanceCard";
import { InstallAppCard } from "@/components/InstallAppCard";

export default function CuentaApariencia() {

  return (
    <main className="dashboard">
      <BottomNav />
      <InstallAppCard />
      <AppearanceCard />
    </main>
  );
}
