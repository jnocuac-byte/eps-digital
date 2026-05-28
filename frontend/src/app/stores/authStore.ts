import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  userId: string | null;
  user: User | null;
  isAuthenticated: boolean;
  rol: string | null;
  medicoId: string | null;
  login: (token: string, refreshToken: string, userId: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
  setRol: (rol: string) => void;
  setMedicoId: (medicoId: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      userId: null,
      user: null,
      isAuthenticated: false,
      rol: null,
      medicoId: null,
      login: (token, refreshToken, userId) =>
        set({ token, refreshToken, userId, isAuthenticated: true }),
      logout: () =>
        set({ token: null, refreshToken: null, userId: null, user: null, isAuthenticated: false, rol: null, medicoId: null }),
      setUser: (user) => set({ user }),
      setRol: (rol) => set({ rol }),
      setMedicoId: (medicoId) => set({ medicoId }),
    }),
    {
      name: 'eps-auth-storage',
    }
  )
);
