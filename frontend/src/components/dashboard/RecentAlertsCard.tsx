import React from 'react';
import { AlertTriangle, Clock, Info } from 'lucide-react';

interface RecentAlertsCardProps {
  onViewAll: () => void;
}

export const RecentAlertsCard: React.FC<RecentAlertsCardProps> = ({ onViewAll }) => {
  const alerts = [
    {
      id: 'alt-1',
      title: 'Non-Compliant Product Found',
      desc: 'Tata Salt (1kg) at Retail Store, Sector 15, Bhiwadi',
      time: '2h ago',
      type: 'danger',
      icon: AlertTriangle,
      iconColor: 'text-rose-400',
      bgColor: 'bg-rose-500/10 border-rose-500/20',
    },
    {
      id: 'alt-2',
      title: 'License Expiring Soon',
      desc: 'Sharma Traders License expires on 15 Jun 2025',
      time: '5h ago',
      type: 'warning',
      icon: Clock,
      iconColor: 'text-amber-400',
      bgColor: 'bg-amber-500/10 border-amber-500/20',
    },
    {
      id: 'alt-3',
      title: 'New Complaint Received',
      desc: 'Incorrect weight in packaged product.',
      time: '1d ago',
      type: 'info',
      icon: Info,
      iconColor: 'text-blue-400',
      bgColor: 'bg-blue-500/10 border-blue-500/20',
    },
  ];

  return (
    <div className="rounded-2xl bg-[#0d1430] border border-[#1d274d] p-5 shadow-xl flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white tracking-wide">Recent Alerts</h3>
        <button
          onClick={onViewAll}
          className="text-xs font-semibold text-purple-400 hover:text-purple-300 transition-colors"
        >
          View All
        </button>
      </div>

      {/* Alert Items */}
      <div className="space-y-3 flex-1">
        {alerts.map((alert) => {
          const Icon = alert.icon;
          return (
            <div
              key={alert.id}
              className="flex items-start space-x-3 p-2.5 rounded-xl hover:bg-[#141d3d] transition-colors border border-transparent hover:border-[#222e5a]"
            >
              <div className={`p-2 rounded-xl border flex-shrink-0 ${alert.bgColor}`}>
                <Icon className={`w-4 h-4 ${alert.iconColor}`} />
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-100 truncate">
                    {alert.title}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono ml-2">
                    {alert.time}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5 leading-snug">
                  {alert.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
