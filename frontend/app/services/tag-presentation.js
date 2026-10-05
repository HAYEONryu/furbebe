import meanings from './tag-descriptions.json';

const removedKeys = new Set([
  'bean', 'cheese', 'baby_dog', 'senior_dog',
  'tiny', 'small', 'medium', 'large', 'puppy', 'young', 'adult', 'senior',
]);
const names = {
  white: ['흰둥이', '🤍'], cream: ['크림이', '🍦'],
  black: ['검둥이', '🖤'], brown: ['브라운', '🤎'],
  sensitive: ['새콤새침', '🌵'],
  gentle: ['순딩이', '🙂'],
  shy: ['수줍요정', '🧚'], playful: ['똥꼬발랄', '🤸'],
  calm: ['차분선비댕', '🍵'], people_friendly: ['사람좋아', '🥰'],
};
export function tagMeaning(tag) {
  const aliases = { cloud: 'white_coat', white: 'white_coat', cream: 'cream_coat', black: 'black_coat', brown: 'brownie' };
  return meanings[aliases[tag.key] ?? tag.key] ?? tag.description?.trim() ?? '';
}
// Canonicalize old responses too, so cached cloud + white tags produce one chip.
export function displayTags(tags) {
  const unique = new Map();
  for (const tag of tags.filter((item) => !removedKeys.has(item.key))) {
    const canonical = tag.key === 'cloud' ? { ...tag, key: 'white', type: 'fact' } : tag;
    const [label, emoji] = names[canonical.key] ?? [canonical.label, canonical.emoji ?? null];
    if (!unique.has(canonical.key) || tag.key !== 'cloud') {
      unique.set(canonical.key, { ...canonical, label, emoji, description: tagMeaning(canonical) });
    }
  }
  return [...unique.values()];
}
