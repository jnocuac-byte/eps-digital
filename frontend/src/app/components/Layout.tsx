import { Outlet, useLocation } from 'react-router';
import { useEffect } from 'react';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import { Toaster } from 'sonner';

export function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }, [pathname]);

  return (
    <div className="min-h-screen flex flex-col bg-page-background">
      <Navbar />
      <main className="flex-1 pt-[4.5rem]">
        <div key={pathname} className="app-page-enter">
          <Outlet />
        </div>
      </main>
      <Footer />
      <Toaster position="top-right" richColors />
    </div>
  );
}
