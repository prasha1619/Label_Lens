import React from 'react';
import { Menu, Search, Bell, LogOut } from 'lucide-react';
import { User } from '../../services/authService';

interface TopHeaderProps {
  onToggleSidebar: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onOpenNotifications: () => void;
  user: User;
  onLogout: () => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  onToggleSidebar,
  searchQuery,
  onSearchChange,
  onOpenNotifications,
  user,
  onLogout,
}) => {
  return (
    <header className="sticky top-0 z-30 h-16 bg-[#080c1d]/90 backdrop-blur-md border-b border-[#151d3b] px-4 sm:px-6 lg:px-8 flex items-center justify-between">
      {/* Left section: Mobile menu toggle */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onToggleSidebar}
          className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
          title="Toggle Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Middle section: Global Search Bar */}
      <div className="flex-1 max-w-xl mx-4 lg:mx-8">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search products, licensees, reports..."
            className="w-full pl-10 pr-4 py-2 bg-[#101733]/80 border border-[#1d274d] rounded-full text-xs sm:text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/20 transition-all shadow-inner"
          />
        </div>
      </div>

      {/* Right section: Notifications & User Profile */}
      <div className="flex items-center space-x-4">
        {/* Notification Bell */}
        <button
          onClick={onOpenNotifications}
          className="relative p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
        >
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-pink-500 rounded-full ring-2 ring-[#080c1d]" />
        </button>

        {/* User Profile */}
        <div className="flex items-center space-x-3 pl-2 border-l border-[#1a2342]">
          <div className="relative">
            {user.profile_photo_url ? (
              <img
                src={user.profile_photo_url}
                alt={user.full_name}
                className="w-9 h-9 rounded-full object-cover ring-2 ring-emerald-500/30"
                onError={(e) => {
                  // Fallback to initials if photo fails to load
                  (e.currentTarget as HTMLElement).style.display = 'none';
                  const parent = e.currentTarget.parentElement;
                  const fallback = parent?.querySelector('.initials-fallback') as HTMLElement;
                  if (fallback) fallback.style.display = 'flex';
                }}
              />
            ) : null}
            <div
              className={`initials-fallback w-9 h-9 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-500 text-white text-xs font-extrabold flex items-center justify-center ring-2 ring-emerald-500/30 shadow-md ${
                user.profile_photo_url ? 'hidden' : 'flex'
              }`}
            >
              {user.full_name
                ? user.full_name
                    .trim()
                    .split(/\s+/)
                    .slice(0, 2)
                    .map((p) => p[0])
                    .join('')
                    .toUpperCase()
                : 'LM'}
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full ring-2 ring-[#080c1d]" />
          </div>
          <div className="hidden sm:block text-left">
            <div className="text-sm font-semibold text-white leading-tight">
              {user.full_name}
            </div>
            <div className="text-[11px] text-slate-400 font-medium capitalize">
              {user.role === 'admin' ? 'Administrator' : user.role || 'Inspector'}
            </div>
          </div>
        </div>
        <button onClick={onLogout} title="Log out" className="p-2 rounded-xl text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"><LogOut className="h-4 w-4" /></button>
      </div>
    </header>
  );
};
