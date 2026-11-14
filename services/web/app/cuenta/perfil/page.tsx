"use client";

import { BottomNav } from "@/components/BottomNav";
import { EquipmentCard } from "@/components/account/EquipmentCard";
import { ProfileForm } from "@/components/account/ProfileForm";

export default function CuentaPerfil() {

  return (
    <main className="dashboard">
      <BottomNav />
      <ProfileForm />
      <div className="tab-body">
        <EquipmentCard />
      </div>
    </main>
  );
}
