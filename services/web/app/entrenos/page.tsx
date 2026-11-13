"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { RedirectTo } from "@/lib/redirect";

function Inner() {
  const view = useSearchParams().get("view");
  return <RedirectTo to={`/rutinas?tab=historial${view ? `&view=${encodeURIComponent(view)}` : ""}`} />;
}

export default function Entrenos() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <Inner />
    </Suspense>
  );
}
