"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect } from "react";

const HISTORY_KEY = "publishr:navigation-history";
const MAX_HISTORY = 30;

function currentPath() {
  if (typeof window === "undefined") return "/";
  return `${window.location.pathname}${window.location.search}`;
}

function readHistory() {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(sessionStorage.getItem(HISTORY_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === "string") : [];
  } catch {
    return [];
  }
}

function writeHistory(paths: string[]) {
  sessionStorage.setItem(HISTORY_KEY, JSON.stringify(paths.slice(-MAX_HISTORY)));
}

export function NavigationHistoryTracker() {
  const pathname = usePathname();

  useEffect(() => {
    const path = currentPath();
    const history = readHistory();
    if (history[history.length - 1] === path) return;
    writeHistory([...history, path]);
  }, [pathname]);

  return null;
}

export function BackLink({
  href,
  className,
  children,
}: {
  href: string;
  className?: string;
  children: ReactNode;
}) {
  const router = useRouter();

  return (
    <Link
      href={href}
      className={className}
      onClick={(event) => {
        const path = currentPath();
        const history = readHistory();
        const currentIndex = history.lastIndexOf(path);
        const previous = currentIndex > 0 ? history[currentIndex - 1] : history.at(-2);
        if (!previous || previous === path) return;

        event.preventDefault();
        writeHistory(history.slice(0, Math.max(1, currentIndex)));
        router.push(previous);
      }}
    >
      {children}
    </Link>
  );
}
