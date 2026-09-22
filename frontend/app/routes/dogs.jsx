import { useLocation, useNavigate, useNavigation } from 'react-router';
import { Button, ButtonLink } from '../components/button.jsx';
import { EmptyState } from '../components/states.jsx';
import { AnimalGrid } from '../components/animal-card.jsx';
import { ActiveFilters, FilterDialog, QuickTags } from '../components/discovery-filters.jsx';
import { Pagination } from '../components/pagination.jsx';
import { getDiscovery } from '../services/discovery.js';
import { discoveryHref, parseDiscoveryQuery, SORT_OPTIONS, updateDiscoveryQuery } from '../services/discovery-query.js';
import { loadRoute } from '../services/route-loader.js';
export { RouteError as ErrorBoundary } from '../components/route-error.jsx';

export function meta() { return [{ title: '아이들 찾기 · FURBEBE' }]; }
export function loader({ request }) {
  return loadRoute(() => getDiscovery({ signal: request.signal, search: new URL(request.url).search }));
}

function Listing({ data }) {
  const { state, filters, tags, pagination, items } = data;
  const navigate = useNavigate();
  const navigation = useNavigation();
  const pending = navigation.state !== 'idle';
  const change = (changes) => navigate(discoveryHref(updateDiscoveryQuery(state, changes)));
  const reset = () => navigate(discoveryHref({ ...parseDiscoveryQuery(), sort: state.sort }));
  function search(event) { event.preventDefault(); change({ q: new FormData(event.currentTarget).get('q') }); }
  return <div className="listing-page">
    <section className="listing-intro"><p className="eyebrow">FIND YOUR LITTLE FOREVER</p><h1>어쩌면, 나의 가족</h1><p className="mt-3 text-muted">가까이에서 기다리는 아이들의 소식을 살펴보세요.</p><p className="mt-2 text-xs text-muted">개, 고양이와 다른 구조동물의 소식을 함께 전해요.</p><p className="result-count mt-4" aria-live="polite">총 <strong>{pagination.total.toLocaleString('ko-KR')}</strong>명의 친구</p></section>
    <section aria-label="구조동물 탐색 조건"><fieldset className="listing-controls" disabled={pending}>
      <legend className="sr-only">검색, 태그와 필터</legend>
      <form onSubmit={search} role="search" className="animal-search">
        <label htmlFor="animal-query" className="sr-only">품종·보호소·지역 검색</label>
        <input id="animal-query" name="q" type="search" defaultValue={state.q} maxLength={50} placeholder="품종, 보호소 또는 지역을 검색해 보세요" />
        <Button type="submit">검색 <span aria-hidden="true">↗</span></Button>
      </form>
      <QuickTags tags={tags} selected={state.tag} onToggle={(key) => change({ tag: state.tag.includes(key) ? state.tag.filter((tag) => tag !== key) : [...state.tag, key] })} />
      <div className="listing-toolbar"><FilterDialog filters={filters} tags={tags} state={state} onApply={change} />
        <div className="sort-field"><label htmlFor="animal-sort" className="sr-only">정렬</label><select id="animal-sort" value={state.sort} onChange={(event) => change({ sort: event.target.value })}>{SORT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
      </div>
      <ActiveFilters state={state} filters={filters} tags={tags} onRemove={change} onReset={reset} />
    </fieldset></section>
    <section className={`listing-results ${pending ? 'is-pending' : ''}`} aria-label="검색 결과" aria-busy={pending}>
      <h2 className="sr-only">조건에 맞는 친구들</h2>
      {items.length ? <AnimalGrid animals={items} /> : <EmptyState title={pagination.total > 0 ? '이 페이지에는 친구가 없어요.' : '조건에 맞는 친구가 아직 없어요.'} message={pagination.total > 0 ? '첫 페이지부터 다시 살펴보세요.' : '조건을 조금 넓히면 다른 만남이 기다리고 있을 거예요.'}>
        <div className="mt-5"><ButtonLink to={pagination.total > 0 ? discoveryHref({ ...state, page: 1 }) : '/dogs'}>{pagination.total > 0 ? '첫 페이지로' : '모든 친구 보기'}</ButtonLink></div>
      </EmptyState>}
      <Pagination pagination={pagination} state={state} />
    </section>
  </div>;
}

export default function Dogs({ loaderData }) {
  const location = useLocation();
  return <Listing key={location.key} data={loaderData} />;
}
