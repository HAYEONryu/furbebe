import { Link, useRevalidator } from 'react-router';
import { AnimalGrid } from '../components/animal-card.jsx';
import { AnimalImage } from '../components/animal-image.jsx';
import { Button } from '../components/button.jsx';
import { FavoriteButton } from '../components/favorite-button.jsx';
import { ImageGallery } from '../components/image-gallery.jsx';
import { ShareButton } from '../components/share-button.jsx';
import { TagChip } from '../components/tag-chip.jsx';
import { birthLabel, factLabel, getAnimalDetailPage, hasText, shelterPhoneHref, textOrUnknown, weightLabel } from '../services/animal-detail.js';
import { loadRoute } from '../services/route-loader.js';
export { RouteError as ErrorBoundary } from '../components/route-error.jsx';

export function meta({ loaderData } = {}) {
  return [{ title: loaderData?.seo.title ?? '아이의 소식 · FURBEBE' }, ...(loaderData?.seo ? [{ name: 'description', content: loaderData.seo.description }] : [])];
}
export function loader({ params, request }) {
  return loadRoute(() => getAnimalDetailPage(params.animalId, { signal: request.signal }));
}

function Facts({ rows }) {
  return <dl className="detail-facts">{rows.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value ?? '정보 없음'}</dd></div>)}</dl>;
}

function Evidence({ title, id, rows }) {
  const present = rows.filter(([, value]) => hasText(value));
  if (!present.length) return null;
  return <section className="detail-section" aria-labelledby={id}>
    <h2 id={id} className="section-title">{title}</h2>
    <p className="detail-source-note">보호소 등록 원문</p>
    <dl className="evidence-list">{present.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
  </section>;
}

function AdoptionPromotion({ promotion }) {
  if (!promotion) return null;
  const rows = [['제목', promotion.title], ['시작일', promotion.start_date], ['종료일', promotion.end_date], ['입양 조건', promotion.condition_text]]
    .filter(([, value]) => hasText(value));
  return <section className="detail-section promotion-section" aria-labelledby="promotion-title">
    <p className="eyebrow">A NEW CHAPTER</p><h2 id="promotion-title" className="section-title">입양 홍보 정보</h2>
    <p className="detail-source-note">등록된 홍보 내용과 기간을 확인해 주세요.</p>
    {rows.length > 0 && <Facts rows={rows} />}
    {hasText(promotion.description) && <p className="source-paragraph">{promotion.description}</p>}
    {hasText(promotion.image_url) && <div className="promotion-image"><AnimalImage src={promotion.image_url} alt={hasText(promotion.title) ? `${promotion.title} 홍보 이미지` : '보호소에 등록된 입양 홍보 이미지'} fit="contain" natural /></div>}
  </section>;
}

function SimilarAnimals({ animals, unavailable }) {
  const revalidator = useRevalidator();
  return <section className="detail-similar" aria-labelledby="similar-title">
    <div className="section-heading"><div><p className="eyebrow">A LITTLE MORE DISCOVERY</p><h2 id="similar-title" className="section-title">함께 만나볼 친구들</h2></div><Link className="text-link" to="/dogs">모든 친구 보기 <span aria-hidden="true">↗</span></Link></div>
    {unavailable ? <div className="state-box" role="status"><p>함께 만나볼 친구들의 소식을 불러오지 못했어요.</p><Button className="mt-4" variant="secondary" onClick={() => revalidator.revalidate()} disabled={revalidator.state !== 'idle'}>다시 불러오기</Button></div>
      : animals.length ? <AnimalGrid animals={animals} /> : <p className="detail-muted-panel">함께 소개할 친구들의 소식이 아직 없어요.</p>}
  </section>;
}

function DetailContent({ data }) {
  const { animal: detail, similar, similarUnavailable, seo } = data;
  const { animal, notice, found, shelter, adoption_promotion: promotion } = detail;
  const descriptions = detail.descriptions ?? {};
  const name = hasText(animal.breed) ? animal.breed : '품종 정보 없음';
  const phone = shelterPhoneHref(shelter?.phone);
  return <article className="detail-page">
    <Link to="/dogs" className="text-link detail-back"><span aria-hidden="true">←</span> 아이들 찾기로</Link>
    <div className="detail-hero">
      <ImageGallery images={detail.images} name={name} />
      <header className="detail-summary">
        <p className="eyebrow">ONE LITTLE LIFE, ONE UNIQUE STORY</p>
        <span className="detail-state">{textOrUnknown(notice.process_state)}</span>
        <h1>{name}</h1>
        <p className="detail-region">{textOrUnknown(found.region.display)}</p>
        <p className="detail-at-a-glance">{factLabel('sex', animal.sex)} · {birthLabel(animal)} · {weightLabel(animal)}</p>
        {hasText(notice.notice_no) && <p className="detail-notice">공고번호 <span>{notice.notice_no}</span></p>}
        {detail.tags.length > 0 && <section className="detail-tags" aria-label="아이의 태그">
          <ul>{detail.tags.map((tag) => <li key={tag.key}><TagChip label={tag.label} emoji={tag.emoji} type={tag.type} /></li>)}</ul>
          {detail.tags.some((tag) => hasText(tag.evidence)) && <details className="tag-evidence"><summary>태그에 담긴 등록 정보</summary><dl>{detail.tags.filter((tag) => hasText(tag.evidence)).map((tag) => <div key={tag.key}><dt>{tag.label}</dt><dd>{tag.evidence}</dd></div>)}</dl></details>}
        </section>}
        <a href="#shelter-info" className="text-link">보호소 정보 살펴보기 <span aria-hidden="true">↓</span></a>
      </header>
    </div>
    <div className="detail-information">
      <section className="detail-section" aria-labelledby="facts-title"><h2 id="facts-title" className="section-title">기본 정보</h2>
        <Facts rows={[
          ['품종', name], ['성별', factLabel('sex', animal.sex)], ['중성화', factLabel('neutered', animal.neutered)],
          ['출생연도 / 나이', birthLabel(animal)], ['나이 그룹', factLabel('age', animal.age_group)],
          ['체중', weightLabel(animal)], ['크기 그룹', factLabel('size', animal.size_group)],
          ['털색', textOrUnknown(animal.color_text)], ['현재 상태', textOrUnknown(notice.process_state)],
        ]} /><p className="detail-source-note">나이 그룹은 출생연도 기반의 추정 범위이며, 크기 그룹은 체중에 따른 탐색 기준이에요.</p>
      </section>
      <section className="detail-section" aria-labelledby="found-title"><h2 id="found-title" className="section-title">발견 정보</h2>
        <Facts rows={[
          ['발견일', textOrUnknown(found.date)], ['발견 장소', textOrUnknown(found.place)], ['지역', textOrUnknown(found.region.display)],
          ...[['공고번호', notice.notice_no], ['공고 시작일', notice.start_date], ['공고 종료일', notice.end_date], ['종료 사유', notice.end_reason]].filter(([, value]) => hasText(value)),
        ]} />
      </section>
    </div>
    <Evidence title="아이의 이야기" id="description-title" rows={[
      ['특징 및 설명', descriptions.special_mark], ['기타 등록 정보', descriptions.etc],
    ]} />
    <Evidence title="행동 · 건강 정보" id="health-title" rows={[
      ['사회성', descriptions.social], ['건강', descriptions.health], ['예방접종', descriptions.vaccination], ['건강검진', descriptions.health_check],
    ]} />
    <section className="detail-section shelter-section" aria-labelledby="shelter-info">
      <p className="eyebrow">THE NEXT STEP, TOGETHER</p><h2 id="shelter-info" tabIndex={-1} className="section-title">보호소 정보</h2>
      {shelter ? <><h3 className="shelter-name">{hasText(shelter.name) ? shelter.name : '보호소 이름 정보 없음'}</h3><Facts rows={[
        ['전화', textOrUnknown(shelter.phone)], ['주소', textOrUnknown(shelter.address)], ['관할 기관', textOrUnknown(shelter.organization)],
      ]} /></> : <p className="mt-4 text-muted">등록된 보호소 정보가 아직 없어요.</p>}
    </section>
    <AdoptionPromotion promotion={promotion} />
    <section className="detail-connect" aria-labelledby="connect-title">
      <div><h2 id="connect-title" className="section-title">관심에서, 만남으로</h2><p className="mt-2 text-muted">현재 보호 상태와 입양 절차는 보호소에 확인해 주세요.</p></div>
      <div className="detail-actions"><FavoriteButton animalId={detail.id} name={name} /><ShareButton animalId={detail.id} seo={seo} /></div>
      {phone ? <a className="button shelter-cta" href={phone} aria-label={`${shelter.name || '보호소'}에 전화로 문의하기`}>보호소에 문의하기 <span aria-hidden="true">↗</span></a>
        : <p className="text-sm text-muted">{hasText(shelter?.phone) ? '등록된 전화번호를 확인해 문의해 주세요.' : '등록된 보호소 전화번호가 없어 전화 연결을 제공할 수 없어요.'}</p>}
    </section>
    <SimilarAnimals animals={similar} unavailable={similarUnavailable} />
  </article>;
}

export default function DogDetail({ loaderData }) {
  return <DetailContent key={loaderData.animal.id} data={loaderData} />;
}
