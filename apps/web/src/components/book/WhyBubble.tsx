export function WhyBubble({ reason }: { reason: string }) {
  return (
    <div className="why-bubble">
      <div className="why-tag">✦ この本で解けること</div>
      <div className="why-text">{reason}</div>
    </div>
  );
}
