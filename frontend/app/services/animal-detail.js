import { getAnimal, getSimilarAnimals } from './animals.js';
import { ApiError } from './api.js';

export const hasText = (value) => typeof value === 'string' && value.trim().length > 0;
export const textOrUnknown = (value) => hasText(value) ? value : '정보 없음';

// Labels translate wire enums; classifications and measurements come from FastAPI.
const LABELS = {
  sex: { male: '수컷', female: '암컷' },
  neutered: { yes: '완료', no: '안 됨' },
  size: { tiny: '5kg 이하', small: '5kg 초과~10kg', medium: '10kg 초과~20kg', large: '20kg 초과' },
  age: { puppy: '추정 1세 이하', young: '추정 2~4세', adult: '추정 5~9세', senior: '추정 10세 이상' },
};
export function factLabel(group, value) {
  return Object.hasOwn(LABELS[group], value) ? LABELS[group][value] : '정보 없음';
}
export function birthLabel(animal) {
  return animal.birth_year != null ? `${animal.birth_year}년생` : textOrUnknown(animal.age_text);
}
export function weightLabel(animal) {
  return animal.weight_kg != null ? `${animal.weight_kg.toLocaleString('ko-KR')}kg` : textOrUnknown(animal.weight_text);
}

export function sourceImages(images) {
  const seen = new Set();
  return images.filter((image) => image.type === 'source').sort((a, b) => a.order - b.order)
    .filter((image) => {
      if (seen.has(image.url)) return false;
      seen.add(image.url);
      return true;
    });
}

export function shelterPhoneHref(value) {
  if (!hasText(value) || !/^\+?[\d\s().-]+$/.test(value.trim())) return null;
  const phone = value.replace(/[^\d+]/g, '');
  return phone.replace(/\D/g, '').length >= 6 ? `tel:${phone}` : null;
}

/** Metadata uses only validated FastAPI facts. */
export function detailSeo(detail) {
  const name = hasText(detail.animal.breed) ? detail.animal.breed : '구조동물';
  const facts = [name, detail.found.region.display, detail.notice.process_state].filter(hasText);
  return {
    title: `${name} · ${hasText(detail.found.region.display) ? `${detail.found.region.display} · ` : ''}FURBEBE`,
    description: `${facts.join(' · ')}. 등록된 구조동물 정보와 보호소 정보를 확인하세요.`,
    path: `/dogs/${detail.id}`,
    image: sourceImages(detail.images)[0]?.url,
  };
}

export async function getAnimalDetailPage(id, options = {}) {
  const [animal, recommendations] = await Promise.all([
    getAnimal(id, options),
    getSimilarAnimals(id, { ...options, limit: 4 }).catch((error) => {
      if (!(error instanceof ApiError)) throw error;
      return null;
    }),
  ]);
  const validSimilar = recommendations?.source_animal_id.toLowerCase() === animal.id.toLowerCase();
  const seen = new Set([animal.id.toLowerCase()]);
  const similar = validSimilar ? recommendations.items.filter((item) => {
    const key = item.id.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).slice(0, 4) : [];
  return { animal, similar, similarUnavailable: !validSimilar, seo: detailSeo(animal) };
}
