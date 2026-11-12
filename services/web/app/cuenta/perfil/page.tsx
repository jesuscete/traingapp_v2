"use client";

import { BottomNav } from "@/components/BottomNav";
import { ProfileForm } from "@/components/account/ProfileForm";

export default function CuentaPerfil() {

  return (
    <main className="dashboard">
      <BottomNav />
      <ProfileForm />
    </main>
  );
}
