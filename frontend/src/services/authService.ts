import { request } from './api';

export interface User {
  id: string;
  full_name: string;
  email: string;
  organization?: string | null;
  role: 'inspector' | 'admin';
  profile_photo_url?: string | null;
  created_at: string;
  last_login_at?: string | null;
}

export const authService = {
  me: () => request<User>('/auth/me'),
  login: (email: string, password: string) =>
    request<{ user: User }>('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }),
  register: (payload: {
    full_name: string;
    email: string;
    password: string;
    confirm_password: string;
    organization?: string;
  }) =>
    request<{ user: User }>('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),
  update: (full_name: string, organization?: string) =>
    request<User>('/auth/me', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name, organization }),
    }),
  uploadPhoto: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return request<{ user: User }>('/auth/photo', {
      method: 'POST',
      body: formData,
    });
  },
  removePhoto: () => request<{ user: User }>('/auth/photo', { method: 'DELETE' }),
  changePassword: (current_password: string, new_password: string, confirm_password: string) =>
    request<{ message: string }>('/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password, new_password, confirm_password }),
    }),
};

