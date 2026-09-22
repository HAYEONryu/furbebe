import { useState } from 'react';
import { useFavorites } from '../hooks/use-favorites.js';
import { Button } from './button.jsx';

export function FavoriteButton({ animalId, name, compact = false }) {
  const { isFavorite, toggleFavorite } = useFavorites();
  const [notice, setNotice] = useState('');
  const saved = isFavorite(animalId);
  function toggle() {
    const result = toggleFavorite(animalId);
    setNotice(result.persisted ? '' : '브라우저에 저장할 수 없어 이번 방문 중에만 기억해요.');
  }
  return <div className={compact ? 'card-favorite' : undefined}>
    <Button variant="secondary" className={compact ? 'favorite-icon' : ''} onClick={toggle} aria-pressed={saved} aria-label={`${name} 관심 동물 ${saved ? '해제' : '저장'}`}>
      <span aria-hidden="true">{saved ? '♥' : '♡'}</span>{!compact && (saved ? '관심 동물로 저장됨' : '관심 동물로 저장')}
    </Button>
    <p role="status" className={compact ? 'favorite-notice' : 'mt-2 text-sm text-muted'}>{notice}</p>
  </div>;
}
