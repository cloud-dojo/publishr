"use client";

import { useState } from "react";

export function StarRating({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (n: number) => void;
}) {
  const [hover, setHover] = useState(0);
  const current = hover || value || 0;
  return (
    <div className="stars" role="radiogroup" aria-label="評価">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={`star ${n <= current ? "on" : ""}`}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onChange(n)}
          aria-label={`${n}つ星`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
