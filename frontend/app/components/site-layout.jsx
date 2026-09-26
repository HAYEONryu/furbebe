import { useEffect, useRef } from 'react';
import { useLocation, useNavigation } from 'react-router';
import { Header } from './header.jsx';
import { Footer } from './footer.jsx';
import { LoadingState } from './states.jsx';

export function SiteLayout({ children }) {
  const location = useLocation();
  const navigation = useNavigation();
  const main = useRef(null);
  const previous = useRef(location.key);
  useEffect(() => {
    if (previous.current !== location.key) {
      main.current?.focus({ preventScroll: true });
      previous.current = location.key;
    }
  }, [location.key]);
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main-content" className="skip-link button">본문으로 바로가기</a>
      <Header />
      {navigation.state !== 'idle' && <div className="navigation-notice"><LoadingState /></div>}
      <main ref={main} id="main-content" tabIndex={-1} className="page-width flex-1 py-6 md:py-10" aria-busy={navigation.state !== 'idle'}>
        {children}
      </main>
      <Footer />
    </div>
  );
}
