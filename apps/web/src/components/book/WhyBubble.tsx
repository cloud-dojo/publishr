export function WhyBubble({ reason }: { reason: string }) {
  return (
    <div className="why-bubble">
      <div className="why-tag">✦ なぜ、あなたに</div>
      <div className="why-text">{reason}</div>
    </div>
  );
}
