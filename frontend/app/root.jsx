import { Links, Meta, Outlet, Scripts, ScrollRestoration } from 'react-router';
import { SiteLayout } from './components/site-layout.jsx';
import { RouteError } from './components/route-error.jsx';
import { LoadingState } from './components/states.jsx';
import './styles/app.css';
import { HOME_SEO, pageMeta } from './services/seo.js';

export function meta({ error } = {}) { return pageMeta(HOME_SEO, error); }

export function Layout({ children }) {
  return <html lang="ko">
    <head>
      <meta charSet="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <meta name="theme-color" content="#F6F0E4" />
      <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
      <Meta /><Links />
    </head>
    <body>{children}<ScrollRestoration /><Scripts /></body>
  </html>;
}

export default function App() { return <SiteLayout><Outlet /></SiteLayout>; }
export function ErrorBoundary() { return <SiteLayout><RouteError /></SiteLayout>; }
export function HydrateFallback() { return <SiteLayout><LoadingState /></SiteLayout>; }
