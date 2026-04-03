import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../types';

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  userId: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (token: string, refreshToken: string, userId: string) => void;
  logout: () => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      userId: null,
      user: null,
      isAuthenticated: false,
      login: (token, refreshToken, userId) =>
        set({ token, refreshToken, userId, isAuthenticated: true }),
      logout: () =>
        set({ token: null, refreshToken: null, userId: null, user: null, isAuthenticated: false }),
      setUser: (user) => set({ user }),
    }),
    {
      name: 'eps-auth-storage',
    }
  )
);
