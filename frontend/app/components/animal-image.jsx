import { useEffect, useRef, useState } from 'react';
import { ImageEmptyState } from './states.jsx';

export const IMAGE_LOAD_FAILURE_MESSAGE = '사진을 가지고 오는데 실패했습니다. 국가동물보호정보시스템 공고를 확인해 주세요.';

function usableUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password;
  } catch { return false; }
}

function SourceImage({ urls, alt, priority, onError, failureLabel }) {
  const [index, setIndex] = useState(0);
  const image = useRef(null);
  // SSR images can finish failing before React attaches its error listener.
  useEffect(() => {
    if (index < urls.length && image.current?.complete && image.current.naturalWidth === 0) {
      setIndex(index + 1);
      onError?.(urls[index]);
    }
  }, [index, urls, onError]);
  if (index >= urls.length) return <ImageEmptyState label={failureLabel} />;
  return <img ref={image} key={urls[index]} src={urls[index]} alt={alt} loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} width="640" height="480" referrerPolicy="no-referrer" onError={() => { setIndex(index + 1); onError?.(urls[index]); }} className="animal-image" />;
}

export function AnimalImage({ src, sources = [], alt, priority = false, onError, failureLabel = IMAGE_LOAD_FAILURE_MESSAGE }) {
  const urls = [...new Set([src, ...sources].filter(usableUrl))];
  return urls.length ? <SourceImage key={JSON.stringify(urls)} urls={urls} alt={alt} priority={priority} onError={onError} failureLabel={failureLabel} /> : <ImageEmptyState />;
}
