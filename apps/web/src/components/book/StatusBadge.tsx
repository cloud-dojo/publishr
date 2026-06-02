import type { Book } from "@publishr/shared-schema";

type BadgeSpec = { cls: string; label: string; pulse: boolean };

function spec(status: Book["status"], shelf: Book["shelf"]): BadgeSpec {
  if (shelf === "odd") return { cls: "badge--odd", label: "異色作", pulse: false };
  switch (status) {
    case "writing":
      return { cls: "badge--writing", label: "執筆中", pulse: true };
    case "reserved":
      return { cls: "badge--writing", label: "執筆依頼中", pulse: true };
    case "published":
      return { cls: "badge--done", label: shelf === "library" ? "読了" : "入荷", pulse: false };
    case "draft":
    default:
      return shelf === "press"
        ? { cls: "badge--soon", label: "もうすぐ", pulse: false }
        : { cls: "badge--new", label: "NEW 入荷", pulse: true };
  }
}

export function StatusBadge({
  status,
  shelf,
  floating = true,
}: {
  status: Book["status"];
  shelf: Book["shelf"];
  floating?: boolean;
}) {
  const { cls, label, pulse } = spec(status, shelf);
  return (
    <span className={`${floating ? "book-badge " : ""}badge ${cls}`}>
      {pulse ? <span className="pulse" /> : null}
      {label}
    </span>
  );
}
