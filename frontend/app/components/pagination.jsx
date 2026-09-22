import { Link } from 'react-router';
import { discoveryHref } from '../services/discovery-query.js';

export function Pagination({ pagination, state }) {
  const { page, total_pages: total, has_next, has_previous } = pagination;
  if (total <= 1) return null;
  const first = Math.max(1, Math.min(page - 2, total - 4));
  const pages = Array.from({ length: Math.min(5, total) }, (_, index) => first + index);
  const href = (value) => discoveryHref({ ...state, page: value });
  return <nav aria-label="검색 결과 페이지" className="pagination">
    {has_previous ? <Link to={href(Math.max(1, Math.min(page - 1, total)))} aria-label="이전 페이지" className="page-link">←</Link> : <span className="page-link page-disabled" aria-disabled="true" aria-label="이전 페이지">←</span>}
    {first > 1 && <Link to={href(1)} aria-label="1페이지" className="page-link page-edge">1</Link>}
    {pages.map((value) => <Link key={value} to={href(value)} className={`page-link ${Math.abs(value - Math.min(page, total)) > 1 ? 'page-window-extra' : ''}`} aria-current={value === page ? 'page' : undefined} aria-label={`${value}페이지`}>{value}</Link>)}
    {first + pages.length <= total && <Link to={href(total)} aria-label={`${total}페이지`} className="page-link page-edge">{total}</Link>}
    {has_next ? <Link to={href(page + 1)} aria-label="다음 페이지" className="page-link">→</Link> : <span className="page-link page-disabled" aria-disabled="true" aria-label="다음 페이지">→</span>}
    <p className="w-full text-center text-xs text-muted">{page.toLocaleString('ko-KR')} / {total.toLocaleString('ko-KR')} 페이지</p>
  </nav>;
}
