"use client";

import { useParams } from "next/navigation";

import { BottomNav } from "@/components/BottomNav";
import { SessionDetail } from "@/components/train/SessionDetail";

export default function EntrenoDetalle() {
  const params = useParams<{ id: string }>();
  return (
    <main className="dashboard">
      <BottomNav />
      <SessionDetail id={params.id} />
    </main>
  );
}
