import { useEffect, useRef, useState } from 'react';

const accountNumber = '7979-28-75935';
const copyableAccountNumber = accountNumber.replace(/-/g, '');

export function Footer() {
  const [copyStatus, setCopyStatus] = useState('');
  const [copying, setCopying] = useState(false);
  const manualAccount = useRef(null);
  const copyNoticeTimer = useRef(null);

  useEffect(() => () => clearTimeout(copyNoticeTimer.current), []);

  useEffect(() => {
    if (copyStatus === 'error') {
      manualAccount.current?.focus();
      manualAccount.current?.select();
    }
  }, [copyStatus]);

  async function copyAccount() {
    clearTimeout(copyNoticeTimer.current);
    setCopying(true);
    setCopyStatus('');
    try {
      await navigator.clipboard.writeText(copyableAccountNumber);
      setCopyStatus('copied');
      copyNoticeTimer.current = setTimeout(() => setCopyStatus(''), 2000);
    } catch {
      setCopyStatus('error');
    } finally {
      setCopying(false);
    }
  }

  return (
    <footer className="mt-auto border-t border-cream bg-cream/10 py-6 text-sm text-muted">
      <div className="page-width grid gap-5 md:grid-cols-[minmax(0,1fr)_auto] md:gap-8">
        <div className="min-w-0">
          <p className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <span className="font-bold tracking-widest text-ink">FURBEBE</span>
            <span className="text-xs">가족을 만나는 따뜻한 시작</span>
          </p>
          <div className="mt-3 space-y-1 text-xs leading-relaxed">
            <p>동물 정보 출처: 국가동물보호정보시스템</p>
            <p>정확한 정보와 입양 절차는 보호소에 확인해 주세요.</p>
          </div>
        </div>
        <div className="min-w-0 border-t border-cream pt-5 md:border-t-0 md:border-l md:pt-0 md:pl-8">
          <p className="font-semibold text-ink">개발자 후원 🐾</p>
          <p className="mt-1 text-xs">작은 후원으로 FURBEBE를 함께 키워주세요.</p>
          <div className="mt-3 inline-flex max-w-full flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-cream bg-ivory px-3 py-1">
            <span className="text-xs">카카오뱅크</span>
            <button
              type="button"
              className="min-h-7 whitespace-nowrap font-medium text-ink tabular-nums underline decoration-outline/50 underline-offset-4 hover:decoration-ink"
              onClick={copyAccount}
              disabled={copying}
              aria-label={`후원 계좌번호 ${accountNumber} 복사`}
              title="클릭하여 계좌번호 복사"
            >
              {accountNumber}
            </button>
          </div>
          <p role="status" className="min-h-5 pt-1 text-xs">
            {copyStatus === 'copied' && '계좌번호를 복사했어요.'}
            {copyStatus === 'error' && '아래 번호를 직접 복사해 주세요.'}
          </p>
          {copyStatus === 'error' && (
            <input
              ref={manualAccount}
              aria-label="직접 복사할 후원 계좌번호"
              className="mt-1 w-full text-sm tabular-nums"
              readOnly
              value={copyableAccountNumber}
              onFocus={(event) => event.currentTarget.select()}
            />
          )}
        </div>
      </div>
    </footer>
  );
}
