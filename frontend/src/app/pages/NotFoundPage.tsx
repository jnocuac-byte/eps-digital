import { Link } from 'react-router';
import { HeartPulse, Home, ArrowLeft } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="flex justify-center mb-6">
          <div className="bg-[#2B3E59]/10 rounded-full p-6">
            <HeartPulse size={56} className="text-[#2B3E59]" />
          </div>
        </div>
        <h1 className="font-inter text-7xl font-bold text-[#2B3E59] mb-4">404</h1>
        <h2 className="font-inter text-xl font-semibold text-gray-700 mb-3">
          Página no encontrada
        </h2>
        <p className="text-gray-500 mb-8">
          La página que buscas no existe o ha sido movida. Verifica la URL o regresa al inicio.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            to="/"
            className="inline-flex items-center justify-center gap-2 bg-[#2B3E59] text-white px-6 py-3 rounded-full hover:bg-[#1e2d40] transition-colors"
          >
            <Home size={16} /> Ir al inicio
          </Link>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 border border-gray-300 text-gray-600 px-6 py-3 rounded-full hover:bg-gray-50 transition-colors"
          >
            <ArrowLeft size={16} /> Volver atrás
          </button>
        </div>
      </div>
    </div>
  );
}
