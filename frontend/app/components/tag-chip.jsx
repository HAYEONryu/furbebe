export function TagChip({ label, emoji, type = 'fact' }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm ${type === 'vibe' ? 'bg-butter/60' : 'bg-cream/65'}`}>
    {emoji && <span aria-hidden="true">{emoji}</span>}{label}
  </span>;
}
