import { expect, it } from 'vitest';
import { displayTags } from '../app/services/tag-presentation.js';

it('assigns distinct meaning-specific emojis to generated visible tags and preserves other source emojis', () => {
  const keys = ['white', 'cream', 'black', 'brown', 'gentle', 'shy', 'playful', 'calm', 'people_friendly'];
  const tags = displayTags(keys.map((key) => ({ key, label: key, emoji: '🐾' })));
  expect(new Set(tags.map((tag) => tag.emoji)).size).toBe(keys.length);
  expect(tags.find((tag) => tag.key === 'gentle')).toMatchObject({ label: '순딩이', emoji: '🙂' });
  expect(displayTags([{ key: 'friendly', label: '외부 태그', emoji: null }])[0].emoji).toBeNull();
  expect(displayTags([{ key: 'custom', label: '기타', emoji: '🌟' }])[0].emoji).toBe('🌟');
});

it('does not attach a misleading shared emoji to unknown tags', () => {
  expect(displayTags([{ key: 'unknown', label: '미확인', emoji: null }])[0].emoji).toBeNull();
});

it('uses 수줍요정 for the legacy shy label and places its emoji after the label', () => {
  expect(displayTags([{ key: 'shy', label: '낯가림', emoji: null }])[0])
    .toMatchObject({ label: '수줍요정', emoji: '🧚' });
});

it('merges cloud and white into one 흰둥이 tag, including cached cloud-only responses', () => {
  const cloud = { key: 'cloud', type: 'vibe', label: '뭉개 구름이', emoji: '☁️' };
  const white = { key: 'white', type: 'fact', label: '흰둥이', evidence: 'colorCd=흰색' };
  for (const input of [[cloud, white], [white, cloud], [cloud]]) {
    expect(displayTags(input)).toHaveLength(1);
    expect(displayTags(input)[0]).toMatchObject({ key: 'white', type: 'fact', label: '흰둥이', emoji: '🤍' });
  }
  expect(displayTags([white, cloud])[0].evidence).toBe(white.evidence);
});
