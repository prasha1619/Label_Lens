import React from 'react';
import { X, Bell, AlertTriangle, CheckCircle2, Clock, Info } from 'lucide-react';

interface NotificationsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationsModal: React.FC<NotificationsModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const notifications = [
    {
      id: 'n1',
      title: 'Statutory Violation Notice',
      desc: 'High severity non-compliance identified on Tata Salt (1kg) batch #TS9042.',
      time: '2 hours ago',
      type: 'danger',
      icon: AlertTriangle,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10 border-rose-500/20',
    },
    {
      id: 'n2',
      title: 'License Renewal Due',
      desc: 'Sharma Traders License (LIC-2021-3321) expires in 15 days.',
      time: '5 hours ago',
      type: 'warning',
      icon: Clock,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/20',
    },
    {
      id: 'n3',
      title: 'Complaint Resolved',
      desc: 'Complaint docket LM-CMP-2026-8812 has been resolved and closed.',
      time: '1 day ago',
      type: 'success',
      icon: CheckCircle2,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-md rounded-2xl bg-[#0e1533] border border-[#232f58] shadow-2xl p-5 overflow-hidden">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/60 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 mb-4">
          <div className="w-9 h-9 rounded-xl bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
            <Bell className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Notifications & Alerts</h3>
            <p className="text-[11px] text-slate-400">3 unread system notifications</p>
          </div>
        </div>

        <div className="space-y-2.5">
          {notifications.map((n) => {
            const Icon = n.icon;
            return (
              <div key={n.id} className="p-3 rounded-xl bg-[#131c3e] border border-[#212e56] flex items-start space-x-3">
                <div className={`p-2 rounded-xl border flex-shrink-0 ${n.bg}`}>
                  <Icon className={`w-4 h-4 ${n.color}`} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-100">{n.title}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{n.time}</span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5">{n.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="pt-4 mt-4 border-t border-[#1d274d] text-center">
          <button
            onClick={onClose}
            className="text-xs font-semibold text-purple-400 hover:text-purple-300"
          >
            Mark all as read
          </button>
        </div>
      </div>
    </div>
  );
};
