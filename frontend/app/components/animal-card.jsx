import { Link } from 'react-router';
import { AnimalImage } from './animal-image.jsx';
import { FavoriteButton } from './favorite-button.jsx';
import { TagChip } from './tag-chip.jsx';
import { discoveryTags } from '../services/discovery-query.js';

export function AnimalCard({ animal }) {
  const name = animal.breed || '품종 정보 없음';
  const tags = discoveryTags(animal.tags).slice(0, 3);
  const age = animal.birth_year != null ? `${animal.birth_year}년생` : animal.age_text || '나이 미상';
  const weight = animal.weight_kg != null ? `${animal.weight_kg.toLocaleString('ko-KR')}kg` : '체중 미상';
  return <article className="animal-card">
    <Link to={`/dogs/${animal.id}`} className="animal-card-link" aria-label={`${name} · ${animal.region.display || '지역 정보 없음'} 자세히 보기`}>
      <div className="card-photo"><AnimalImage src={animal.primary_image?.url} alt={`${name}의 보호소 등록 사진`} /></div>
      <div className="card-content">
        <div className="flex items-start justify-between gap-2"><h3 className="min-w-0 break-words text-lg font-bold">{name}</h3><span className="state-label">{animal.process_state || '상태 미상'}</span></div>
        <p className="mt-1 text-sm text-muted">{age}<span aria-hidden="true"> · </span><span>{weight}</span></p>
        <p className="mt-2 truncate text-sm text-muted" title={animal.region.display || undefined}>{animal.region.display || '지역 정보 없음'}</p>
        {tags.length > 0 && <ul aria-label="대표 태그" className="mt-3 flex flex-wrap gap-1.5">
          {tags.map((tag) => <li key={tag.key}><TagChip label={tag.label} emoji={tag.emoji} type={tag.type} /></li>)}
        </ul>}
      </div>
    </Link>
    <FavoriteButton animalId={animal.id} name={name} compact />
  </article>;
}

export function AnimalGrid({ animals, recent = false }) {
  return <ul className={`animal-grid ${recent ? 'animal-grid-recent' : ''}`} aria-label={recent ? '최근 등록된 구조동물' : '구조동물 검색 결과'}>
    {animals.map((animal) => <li key={animal.id}><AnimalCard animal={animal} /></li>)}
  </ul>;
}
