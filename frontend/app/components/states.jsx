import { Button, ButtonLink } from './button.jsx';

export function LoadingState({ message = '아이들의 소식을 불러오고 있어요.' }) {
  return <div role="status" aria-live="polite" className="rounded-lg bg-butter/35 px-4 py-3 text-center">{message}</div>;
}

export function EmptyState({ title = '조건에 맞는 아이가 없어요.', message = '검색 조건을 바꾸어 다시 찾아보세요.', children }) {
  return <section className="state-box"><h2>{title}</h2><p className="mt-2 text-muted">{message}</p>{children}</section>;
}

export function ErrorState({ title = '정보를 불러오지 못했어요.', message = '잠시 후 다시 시도해 주세요.', requestId, onRetry, retrying = false }) {
  return (
    <section className="state-box" role="alert">
      <h1 className="text-2xl">{title}</h1>
      <p className="mt-3 text-muted">{message}</p>
      {requestId && <p className="mt-2 break-all text-xs text-muted">문의 번호: {requestId}</p>}
      <div className="mt-5 flex flex-wrap justify-center gap-3">
        {onRetry && <Button onClick={onRetry} disabled={retrying}>{retrying ? '다시 불러오는 중…' : '다시 시도'}</Button>}
        <ButtonLink to="/" variant="secondary">홈으로</ButtonLink>
      </div>
    </section>
  );
}

export function ImageEmptyState({ label = '아직 등록된 사진이 없어요.' }) {
  return (
    <div className="animal-image flex flex-col items-center justify-center gap-4 rounded-lg bg-cream/45 p-5 text-center text-muted" role="img" aria-label={label}>
      <svg viewBox="0 0 96 96" width="64" height="64" fill="currentColor" aria-hidden="true">
        <ellipse cx="30" cy="30" rx="9" ry="12" transform="rotate(-25 30 30)" />
        <ellipse cx="51" cy="25" rx="9" ry="12" />
        <ellipse cx="72" cy="36" rx="9" ry="12" transform="rotate(25 72 36)" />
        <path d="M27 66c0-14 12-24 23-24s25 12 25 26c0 17-14 12-24 10-11 2-24 6-24-12Z" />
      </svg>
      <span aria-hidden="true" className="text-sm">{label}</span>
    </div>
  );
}
