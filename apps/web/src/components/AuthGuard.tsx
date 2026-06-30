"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { dataSource, isFirebaseConfigured } from "@/data/config";
import { watchAuth } from "@/lib/firebase";

export function AuthGuard() {
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isFirebaseConfigured) return;
    // 無認証公開ショーケース（bff）では誰でも佐倉(demo_uid)を閲覧する設計のため /login へ誘導しない。
    // 詳細: docs/planning/hackathon-demo-strategy.md
    if (dataSource === "bff") return;

    let redirectTimer: ReturnType<typeof setTimeout> | null = null;
    const unsubscribe = watchAuth((user) => {
      if (redirectTimer) {
        clearTimeout(redirectTimer);
        redirectTimer = null;
      }

      if (!user) {
        redirectTimer = setTimeout(() => {
          const query = window.location.search.replace(/^\?/, "");
          const current = `${pathname ?? "/"}${query ? `?${query}` : ""}`;
          router.replace(`/login?next=${encodeURIComponent(current)}`);
        }, 600);
      }
    });

    return () => {
      if (redirectTimer) clearTimeout(redirectTimer);
      unsubscribe();
    };
  }, [pathname, router]);

  return null;
}
