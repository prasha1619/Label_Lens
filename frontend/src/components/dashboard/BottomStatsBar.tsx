import React from 'react';
import { FileText, Users, Scale, Calendar, MessageSquare, ArrowUp, ArrowDown } from 'lucide-react';

interface BottomStatsBarProps {
  onOpenChatbot: () => void;
}

export const BottomStatsBar: React.FC<BottomStatsBarProps> = ({ onOpenChatbot }) => {
  const stats = [
    {
      label: 'Reports Generated',
      value: '324',
      trend: '14.8%',
      isPositive: true,
      icon: FileText,
      iconBg: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    },
    {
      label: 'Complaints Resolved',
      value: '189',
      trend: '10.2%',
      isPositive: true,
      icon: Users,
      iconBg: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    },
    {
      label: 'Legal Actions Taken',
      value: '36',
      trend: '5.1%',
      isPositive: false,
      icon: Scale,
      iconBg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    },
    {
      label: 'Avg. Inspection Time',
      value: '45 min',
      trend: '3.2%',
      isPositive: false,
      icon: Calendar,
      iconBg: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
    },
  ];

  return (
    <div className="relative mt-8 pt-4">
      {/* Bottom Bar Container */}
      <div className="rounded-2xl bg-[#0a0f26]/90 border border-[#1d274d] p-4 shadow-2xl backdrop-blur-md">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 divide-y md:divide-y-0 md:divide-x divide-[#1a2448]">
          {stats.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div
                key={idx}
                className={`flex items-center space-x-3.5 ${idx !== 0 ? 'pt-3 md:pt-0 md:pl-4' : ''}`}
              >
                <div className={`p-2.5 rounded-xl border flex-shrink-0 ${stat.iconBg}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-400 font-medium">
                    {stat.label}
                  </div>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-base sm:text-lg font-extrabold text-white">
                      {stat.value}
                    </span>
                    <span
                      className={`inline-flex items-center text-[10px] font-semibold ${
                        stat.isPositive ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {stat.isPositive ? (
                        <ArrowUp className="w-2.5 h-2.5 mr-0.5 inline" />
                      ) : (
                        <ArrowDown className="w-2.5 h-2.5 mr-0.5 inline" />
                      )}
                      {stat.trend} this month
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Floating Chat Assistant Button */}
      <button
        onClick={onOpenChatbot}
        className="fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full bg-gradient-to-tr from-purple-600 via-indigo-600 to-pink-500 text-white flex items-center justify-center shadow-2xl shadow-purple-600/50 hover:scale-110 active:scale-95 transition-all duration-200 group border border-white/20"
        title="LabelLens AI Legal Assistant"
      >
        <MessageSquare className="w-5 h-5 group-hover:rotate-12 transition-transform" />
        <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-emerald-500 rounded-full ring-2 ring-[#080c1d] animate-pulse" />
      </button>
    </div>
  );
};
