"use client";

import { BottomNav } from "@/components/BottomNav";
import { GoalsForm } from "@/components/account/GoalsForm";

export default function CuentaObjetivos() {

  return (
    <main className="dashboard">
      <BottomNav />
      <GoalsForm />
    </main>
  );
}
