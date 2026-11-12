"use client";

import { BottomNav } from "@/components/BottomNav";
import { GarminCard } from "@/components/integrations/GarminCard";
import { useToken } from "@/lib/useToken";

export default function CuentaConexiones() {
  const token = useToken();
  return (
    <main className="dashboard">
      <BottomNav />
      {token && <GarminCard token={token} />}
    </main>
  );
}
