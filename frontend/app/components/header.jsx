import { Link, NavLink } from 'react-router';

export function Header() {
  return (
    <header className="border-b border-cream">
      <div className="page-width flex min-h-20 flex-wrap items-center justify-between gap-2 py-3">
        <Link to="/" aria-label="FURBEBE 홈" className="inline-flex min-h-11 items-center text-xl font-bold tracking-widest">FURBEBE</Link>
        <nav aria-label="주 메뉴" className="flex gap-2">
          <NavLink to="/" end className={({ isActive }) => `rounded-lg px-4 py-2.5 ${isActive ? 'bg-butter font-bold' : ''}`}>홈</NavLink>
          <NavLink to="/dogs" className={({ isActive }) => `rounded-lg px-4 py-2.5 ${isActive ? 'bg-butter font-bold' : ''}`}>아이들 찾기</NavLink>
        </nav>
      </div>
    </header>
  );
}
