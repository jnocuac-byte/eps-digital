import { Link } from 'react-router';
import { HeartPulse, Mail, Phone } from 'lucide-react';

const PRIMARY = '#2B3E59';

export function Footer() {
  return (
    <footer style={{ backgroundColor: PRIMARY }} className="text-white mt-auto">
      <div className="max-w-[1440px] mx-auto px-6 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="bg-white rounded-full p-1.5">
                <HeartPulse size={18} color={PRIMARY} />
              </div>
              <span className="font-inter font-semibold text-lg">EPS Digital</span>
            </div>
            <p className="text-white/70 text-sm leading-relaxed">
              Plataforma digital para la gestión de citas médicas con Inteligencia Artificial.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-semibold mb-4">Enlaces rápidos</h4>
            <ul className="space-y-2 text-sm text-white/80">
              <li><Link to="/" className="hover:text-white transition-colors">Inicio</Link></li>
              <li><Link to="/servicios" className="hover:text-white transition-colors">Servicios</Link></li>
              <li><Link to="/ayuda" className="hover:text-white transition-colors">Ayuda</Link></li>
              <li><Link to="/citas/agendar" className="hover:text-white transition-colors">Agendar Cita</Link></li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold mb-4">Contacto</h4>
            <ul className="space-y-2 text-sm text-white/80">
              <li className="flex items-center gap-2">
                <Mail size={14} />
                <span>correo@epsdigital.com</span>
              </li>
              <li className="flex items-center gap-2">
                <Phone size={14} />
                <span>+57 (1) 800-123-456</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/20 mt-8 pt-6 flex flex-col sm:flex-row justify-between items-center gap-3">
          <p className="text-white/60 text-sm">© 2026 EPS Digital. Todos los derechos reservados.</p>
          <div className="flex gap-6 text-sm text-white/70">
            <button className="hover:text-white transition-colors">Política de Privacidad</button>
            <span>|</span>
            <button className="hover:text-white transition-colors">Términos y condiciones</button>
            <span>|</span>
            <Link to="/ayuda" className="hover:text-white transition-colors">Ayuda</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
