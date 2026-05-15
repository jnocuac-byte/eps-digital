import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router';
import { Send, Mic, CalendarPlus, CalendarCheck, MapPin, Bot, User, Loader2 } from 'lucide-react';
import { aiApi } from '../lib/apiClient';
import type { ChatMessage } from '../types';

const QUICK_ACTIONS = [
  { label: 'Agendar Cita', icon: <CalendarPlus size={16} />, to: '/citas/agendar' },
  { label: 'Ver mis Citas', icon: <CalendarCheck size={16} />, to: '/citas/ver' },
  { label: 'Información General', icon: <MapPin size={16} />, to: '/ayuda' },
];

const WELCOME_MSG: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: '¡Hola! Soy el Asistente EPSIA, tu asistente médico virtual. ¿En qué puedo ayudarte hoy?',
  timestamp: new Date(),
};

const SUGGESTIONS = [
  'Necesito agendar una cita con un cardiólogo',
  '¿Cuáles son los servicios disponibles?',
  '¿Cómo cancelo una cita?',
  'Tengo dolor de cabeza frecuente',
];

export default function AsistentePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MSG]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversacionId, setConversacionId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await aiApi.chat(text.trim(), conversacionId);
      const { respuesta, conversacion_id, clasificacion } = res.data;

      if (conversacion_id && !conversacionId) {
        setConversacionId(conversacion_id);
      }

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: respuesta,
        timestamp: new Date(),
        action: clasificacion,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      // Fallback response
      const fallback = getFallbackResponse(text);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: fallback,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-[600px]">
        {/* Left Panel */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col">
          {/* Avatar */}
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-28 h-28 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center mb-4 shadow-inner">
              <Bot size={52} className="text-[#2B3E59]" />
            </div>
            <h2 className="font-inter text-2xl font-bold text-[#2B3E59]">Asistente EPS</h2>
            <p className="text-gray-500 text-sm mt-1">Asistente Virtual Médico</p>
            <p className="text-gray-400 text-sm">EPSIA</p>
          </div>

          {/* Quick Actions */}
          <div className="space-y-3 flex-1">
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-2">Accesos rápidos</p>
            {QUICK_ACTIONS.map((action) => (
              <Link
                key={action.label}
                to={action.to}
                className="flex items-center gap-3 w-full border-2 border-[#2B3E59] text-[#2B3E59] rounded-xl px-4 py-3 text-sm font-semibold hover:bg-[#2B3E59] hover:text-white transition-colors"
              >
                {action.icon}
                {action.label}
              </Link>
            ))}
          </div>

          {/* Suggestions */}
          <div className="mt-6 pt-4 border-t border-gray-100">
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-2">Preguntas frecuentes</p>
            {SUGGESTIONS.slice(0, 2).map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="block w-full text-left text-xs text-gray-500 hover:text-[#2B3E59] py-1 hover:underline transition-colors"
              >
                → {s}
              </button>
            ))}
          </div>
        </div>

        {/* Chat Panel */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
          {/* Chat Header */}
          <div className="flex items-center gap-3 px-5 py-4 bg-[#2B3E59] rounded-t-2xl">
            <Bot size={20} className="text-white" />
            <div>
              <span className="text-white font-semibold text-sm">Asistente EPSIA</span>
              <span className="text-white/60 text-xs ml-2">- En Línea</span>
            </div>
            <div className="w-2.5 h-2.5 bg-green-400 rounded-full ml-auto animate-pulse" />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4" style={{ maxHeight: '460px' }}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mr-2 mt-0.5">
                    <Bot size={14} className="text-[#2B3E59]" />
                  </div>
                )}
                <div
                  className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed
                    ${msg.role === 'user'
                      ? 'bg-[#2B3E59] text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                    }`}
                >
                  {msg.content}
                  {msg.action && msg.action.especialidad_sugerida && (
                    <div className="mt-2">
                      <Link
                        to="/citas/agendar"
                        className="inline-flex items-center gap-1.5 bg-white text-[#2B3E59] text-xs font-semibold px-3 py-1.5 rounded-lg hover:bg-blue-50 transition-colors"
                      >
                        <CalendarPlus size={12} />
                        Buscar disponibilidad
                      </Link>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="w-7 h-7 rounded-full bg-[#2B3E59] flex items-center justify-center flex-shrink-0 ml-2 mt-0.5">
                    <User size={14} className="text-white" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mr-2">
                  <Bot size={14} className="text-[#2B3E59]" />
                </div>
                <div className="bg-gray-100 px-4 py-3 rounded-2xl rounded-bl-sm">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions Row */}
          <div className="px-4 pb-2 flex gap-2 overflow-x-auto scrollbar-hide">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendMessage(s)}
                className="flex-shrink-0 text-xs border border-[#2B3E59]/30 text-[#2B3E59] px-3 py-1 rounded-full hover:bg-blue-50 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>

          {/* Input */}
          <form onSubmit={handleSubmit} className="flex items-center gap-3 p-4 border-t border-gray-100">
            <button type="button" className="text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0">
              <Mic size={18} />
            </button>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe un mensaje..."
              className="flex-1 bg-gray-100 rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="bg-[#2B3E59] text-white p-2.5 rounded-full hover:bg-[#1e2d40] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function getFallbackResponse(input: string): string {
  const lower = input.toLowerCase();
  if (lower.includes('cita') && (lower.includes('agendar') || lower.includes('programar'))) {
    return 'Con gusto te ayudo a agendar una cita. Puedes hacerlo directamente desde la sección "Citas Médicas" → "Agendar nueva cita", o puedo orientarte sobre qué especialidad necesitas. ¿Tienes algún síntoma específico?';
  }
  if (lower.includes('cardio') || lower.includes('corazón') || lower.includes('corazon')) {
    return 'Para consultas de cardiología, te recomiendo agendar con uno de nuestros especialistas cardiólogos disponibles. ¿Te gustaría que te lleve al formulario de agendamiento?';
  }
  if (lower.includes('cancelar')) {
    return 'Para cancelar una cita, ve a "Citas Médicas" → "Cancelar o Reprogramar". Allí podrás seleccionar la cita y cancelarla con el motivo correspondiente.';
  }
  if (lower.includes('servicio') || lower.includes('especialidad')) {
    return 'Ofrecemos servicios de Medicina General, Cardiología, Pediatría, Odontología, Neurología, Ginecología, y más. Visita nuestra sección de "Servicios" para ver la lista completa.';
  }
  return 'Entiendo tu consulta. Como asistente de EPS Digital, puedo ayudarte a agendar citas, consultar disponibilidad de médicos, o resolver dudas sobre nuestros servicios. ¿En qué más puedo ayudarte?';
}
