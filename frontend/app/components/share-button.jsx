import { useEffect, useId, useRef, useState } from 'react';
import { Button } from './button.jsx';
import { detailShareUrl, shareDetail } from '../services/share.js';

export function ShareButton({ animalId, seo }) {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('');
  const [manualUrl, setManualUrl] = useState('');
  const input = useRef(null);
  const id = useId();
  useEffect(() => {
    if (manualUrl) { input.current?.focus(); input.current?.select(); }
  }, [manualUrl]);
  async function share() {
    setBusy(true);
    setManualUrl('');
    const url = detailShareUrl(animalId, window.location.href);
    try {
      const result = await shareDetail({ title: seo.title, text: seo.description, url });
      setStatus({ shared: '공유 메뉴를 열었어요.', copied: '링크를 복사했어요.', cancelled: '공유를 취소했어요.', manual: '아래 링크를 선택해 직접 복사해 주세요.' }[result]);
      if (result === 'manual') setManualUrl(url);
    } finally { setBusy(false); }
  }
  return <div className="detail-share">
    <Button variant="secondary" onClick={share} disabled={busy} aria-label="아이의 소식 공유">공유하기 <span aria-hidden="true">↗</span></Button>
    <p role="status" className="text-sm text-muted">{status}</p>
    {manualUrl && <div className="manual-share"><label htmlFor={id}>공유 링크</label><input ref={input} id={id} readOnly value={manualUrl} onFocus={(event) => event.currentTarget.select()} /></div>}
  </div>;
}
