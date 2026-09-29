import { useState } from 'react';
import { ImageEmptyState } from './states.jsx';

function usableUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password;
  } catch { return false; }
}

function SourceImage({ src, alt, priority, fit, natural }) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  if (failed) return <ImageEmptyState label="사진을 불러올 수 없어요." />;
  return <div className="source-image-frame">
    {!loaded && <div className="source-image-loading" aria-hidden="true"><ImageEmptyState label="사진을 불러오는 중이에요." /></div>}
    <img src={src} alt={alt} loading={priority ? 'eager' : 'lazy'} fetchPriority={priority ? 'high' : 'auto'} decoding="async" width="640" height="480" referrerPolicy="no-referrer" onLoad={() => setLoaded(true)} onError={() => setFailed(true)} className={`${natural ? 'h-auto' : 'aspect-[4/3]'} w-full rounded-lg ${fit === 'contain' ? 'object-contain' : 'object-cover'}`} />
  </div>;
}

export function AnimalImage({ src, alt, priority = false, fit = 'cover', natural = false }) {
  return usableUrl(src) ? <SourceImage key={src} src={src} alt={alt} priority={priority} fit={fit} natural={natural} /> : <ImageEmptyState />;
}
