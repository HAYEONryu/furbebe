import { isRouteErrorResponse, useRevalidator, useRouteError } from 'react-router';
import { ErrorState } from './states.jsx';

export function RouteError() {
  const error = useRouteError();
  const revalidator = useRevalidator();
  const known = isRouteErrorResponse(error);
  const missing = known && error.status === 404;
  return <ErrorState
    title={missing ? '찾으시는 정보를 찾을 수 없어요.' : undefined}
    message={known && typeof error.data?.message === 'string' ? error.data.message : undefined}
    requestId={known ? error.data?.requestId : null}
    onRetry={missing ? undefined : () => revalidator.revalidate()}
    retrying={revalidator.state !== 'idle'}
  />;
}
