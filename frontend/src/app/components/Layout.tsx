import { Outlet } from 'react-router';
import { Navbar } from './Navbar';
import { Footer } from './Footer';
import { Toaster } from 'sonner';

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-[#F5F5F5]">
      <Navbar />
      <main className="flex-1 pt-16">
        <Outlet />
      </main>
      <Footer />
      <Toaster position="top-right" richColors />
    </div>
  );
}
