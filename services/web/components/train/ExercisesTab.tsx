"use client";

import { Dumbbell } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ExerciseLibrary } from "@/components/gym/ExerciseLibrary";
import { ExerciseDetail } from "@/components/train/ExerciseDetail";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useIsExpanded } from "@/lib/useMediaQuery";
import { useToken } from "@/lib/useToken";

export function ExercisesTab() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <ExercisesInner />
    </Suspense>
  );
}

function ExercisesInner() {
  const token = useToken();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const expanded = useIsExpanded();
  const selectedId = params.get("id");

  const update = (id: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (id) next.set("id", id);
    else next.delete("id");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  };

  const library = (
    <div className="tab-body">
      <p className="subtitle">Biblioteca, favoritos y tu historial por ejercicio.</p>
      <ExerciseLibrary
        token={token}
        selectedId={selectedId}
        onPick={expanded ? (ex) => update(ex.id) : undefined}
      />
    </div>
  );

  if (!expanded) return library;
  return (
    <div className="split">
      <div className="split-list">{library}</div>
      <div className="split-detail">
        {selectedId ? (
          <ExerciseDetail key={selectedId} id={selectedId} embedded onDeleted={() => update(null)} />
        ) : (
          <EmptyState
            icon={<Dumbbell size={28} strokeWidth={1.75} />}
            title="Selecciona un ejercicio"
            text="Elige uno de la lista para ver técnica e historial."
          />
        )}
      </div>
    </div>
  );
}
