export function SafetyBadges({ badges = [] }) {
  if (!badges.length) return null;
  return <ul aria-label="안전 정보" className="mt-3 flex flex-wrap gap-2">
    {badges.map((badge) => <li key={badge.key}>
      <span className="inline-flex items-center gap-1 rounded-md border border-amber-700 bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-950" title={badge.evidence}>
        <span aria-hidden="true">⚠</span>{badge.label}
      </span>
    </li>)}
  </ul>;
}
