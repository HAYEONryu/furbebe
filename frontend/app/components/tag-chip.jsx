import { TagHelp } from './tag-tooltip.jsx';
import { tagMeaning } from '../services/tag-presentation.js';

export function TagChip({ tagKey, label, emoji, type = 'fact', description }) {
  return <TagHelp description={tagMeaning({ key: tagKey, description })}>
    <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm ${type === 'vibe' ? 'bg-butter/60' : 'bg-cream/65'}`}>
      {label}{emoji && <span aria-hidden="true">{emoji}</span>}
    </span>
  </TagHelp>;
}
