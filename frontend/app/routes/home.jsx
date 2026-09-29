import { Link } from 'react-router';
import { ButtonLink } from '../components/button.jsx';
import { AnimalImage } from '../components/animal-image.jsx';
import { AnimalGrid } from '../components/animal-card.jsx';
import { EmptyState } from '../components/states.jsx';
import { QuickDiscovery } from '../components/quick-discovery.jsx';
import { getDiscovery } from '../services/discovery.js';
import { loadRoute } from '../services/route-loader.js';
import { HOME_SEO, pageMeta, pageSeo } from '../services/seo.js';
export { RouteError as ErrorBoundary } from '../components/route-error.jsx';

export function meta({ loaderData, error } = {}) { return pageMeta(loaderData?.seo ?? HOME_SEO, error); }
export function loader({ request }) {
  return loadRoute(async () => ({ ...await getDiscovery({ signal: request.signal, home: true }), seo: pageSeo(HOME_SEO, request.url) }));
}

export default function Home({ loaderData }) {
  const featured = loaderData.items.find((animal) => animal.primary_image) ?? loaderData.items[0];
  return <div className="home-page">
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-copy"><p className="eyebrow">EVERY LITTLE PAW, A NEW BEGINNING</p>
        <p className="hero-english" lang="en">Find Your<br /><span>Forever.</span><span className="hero-dot" aria-hidden="true"> ✳</span></p>
        <h1 id="hero-title">가족을 기다리는 아이와,<br />아이를 기다리는 가족의<br />인연을 이어드립니다.</h1>
        <p className="hero-description">작은 관심에서 시작되는, 오래 함께할 이야기.</p>
        <ButtonLink to="/dogs">아이들 찾아보기 <span aria-hidden="true">↗</span></ButtonLink>
      </div>
      <div className="hero-visual">
        <div className="hero-note">반가워요, 나의 새로운 가족.</div>
        <figure className="hero-photo">
          <AnimalImage src={featured?.primary_image?.url} alt={featured ? `${featured.breed || '구조동물'}의 보호소 등록 사진` : '아직 등록된 사진이 없어요.'} priority />
          <figcaption><span><strong>{featured?.breed || '따뜻한 만남을 기다려요'}</strong><span className="mt-1 block text-xs text-muted">{featured?.region.display || '아이들의 소식을 만나보세요.'}</span></span>{featured && <Link className="hero-photo-link" to={`/dogs/${featured.id}`} aria-label="소개된 아이 자세히 보기">↗</Link>}</figcaption>
        </figure>
      </div>
    </section>
    <QuickDiscovery filters={loaderData.filters} tags={loaderData.tags} />
    <section aria-labelledby="recent-title" className="recent-section">
      <div className="section-heading"><div><p className="eyebrow">HELLO, NEW FRIENDS</p><h2 id="recent-title" className="section-title">최근 등록된 친구들</h2><p className="mt-2 text-muted">사진 너머, 한 아이의 이야기가 기다리고 있을 거예요.</p></div><Link to="/dogs" className="text-link">모든 친구 보기 <span aria-hidden="true">↗</span></Link></div>
      {loaderData.items.length ? <AnimalGrid animals={loaderData.items} recent /> : <EmptyState title="새로운 소식을 기다리고 있어요." message="아이들의 소식이 등록되면 이곳에서 만날 수 있어요." />}
    </section>
    <section className="more-cta"><div><p className="eyebrow">YOUR FOREVER STARTS HERE</p><h2 className="section-title">마음에 들어온 친구가 있나요?</h2><p className="mt-2 text-muted">하트를 눌러 기억해 두세요. 만남은 작은 관심에서 시작되니까요.</p></div><ButtonLink to="/dogs" variant="secondary">더 많은 친구 만나기 <span aria-hidden="true">↗</span></ButtonLink></section>
  </div>;
}
