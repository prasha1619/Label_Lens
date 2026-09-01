import React, { useEffect, useState } from 'react';
import { 
  ClipboardList, 
  ShieldCheck, 
  AlertTriangle, 
  Users, 
  ArrowUp, 
  ArrowDown 
} from 'lucide-react';
import { InspectionsChart } from '../components/dashboard/InspectionsChart';
import { CategoryDonutChart } from '../components/dashboard/CategoryDonutChart';
import { QuickActionsCard } from '../components/dashboard/QuickActionsCard';
import { RecentInspectionsList } from '../components/dashboard/RecentInspectionsList';
import { DistrictHeatmap } from '../components/dashboard/DistrictHeatmap';
import { RecentAlertsCard } from '../components/dashboard/RecentAlertsCard';
import { BottomStatsBar } from '../components/dashboard/BottomStatsBar';
import { inspectionService } from '../services/inspectionService';
import { DashboardMetrics } from '../types/inspection';
import { useAuth } from '../auth/AuthContext';

interface DashboardPageProps {
  onNewInspection: () => void;
  onViewInspection: (id: string) => void;
  onViewHistory: () => void;
  onOpenComplaintModal: () => void;
  onOpenLicenseeModal: () => void;
  onOpenChatbot: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNewInspection,
  onViewInspection,
  onViewHistory,
  onOpenComplaintModal,
  onOpenLicenseeModal,
  onOpenChatbot,
}) => {
  const { user, loading: authLoading } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [metricsError, setMetricsError] = useState(false);


  useEffect(() => {
    let active = true;
    inspectionService.getDashboardMetrics()
      .then((data) => active && setMetrics(data))
      .catch(() => active && setMetricsError(true));
    return () => { active = false; };
  }, []);

  const topMetrics = [
    {
      title: 'Total Inspections',
      value: metrics?.total_inspections.toLocaleString() ?? '—',
      trend: 'Saved reports',
      isPositive: true,
      icon: ClipboardList,
      iconBg: 'bg-gradient-to-br from-purple-500/20 to-indigo-600/30 text-purple-400 border border-purple-500/30',
      trendColor: 'text-purple-400',
    },
    {
      title: 'Compliant Products',
      value: metrics?.compliant_count.toLocaleString() ?? '—',
      trend: 'Passed audits',
      isPositive: true,
      icon: ShieldCheck,
      iconBg: 'bg-gradient-to-br from-blue-500/20 to-cyan-600/30 text-blue-400 border border-blue-500/30',
      trendColor: 'text-blue-400',
    },
    {
      title: 'Non-Compliant',
      value: metrics?.non_compliant_count.toLocaleString() ?? '—',
      trend: 'Require action',
      isPositive: false, // Decreased non-compliance is good, shows down arrow
      icon: AlertTriangle,
      iconBg: 'bg-gradient-to-br from-teal-500/20 to-emerald-600/30 text-teal-400 border border-teal-500/30',
      trendColor: 'text-teal-400',
    },
    {
      title: 'Average Compliance',
      value: metrics ? `${metrics.average_compliance_score}%` : '—',
      trend: 'Across reports',
      isPositive: true,
      icon: Users,
      iconBg: 'bg-gradient-to-br from-amber-500/20 to-yellow-600/30 text-amber-400 border border-amber-500/30',
      trendColor: 'text-amber-400',
    },
  ];

  return (
    <div className="space-y-6 animate-fadeIn pb-6">
      {/* Top Greeting Header */}
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
          {authLoading ? (
            <span className="inline-block h-8 w-56 animate-pulse rounded-xl bg-slate-800" />
          ) : (
            <span>नमस्ते, {user?.full_name || 'Inspector'}</span>
          )}
          <span className="inline-block animate-bounce">👋</span>
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 font-medium">
          Welcome to LabelLens - Legal Metrology Compliance Dashboard
        </p>
      </div>

      {/* 4 Top KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {topMetrics.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="rounded-2xl bg-[#0d1430] border border-[#1d274d] p-5 shadow-xl flex items-center justify-between hover:border-[#2d3a6d] transition-all duration-200"
            >
              <div>
                <div className="text-xs font-semibold text-slate-400 mb-1">
                  {item.title}
                </div>
                <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                  {item.value}
                </div>
                <div className="flex items-center space-x-1 mt-1.5">
                  {item.isPositive ? (
                    <span className="text-[11px] font-semibold text-purple-400 flex items-center">
                      <ArrowUp className="w-3 h-3 mr-0.5 inline" />
                      {item.trend}
                    </span>
                  ) : (
                    <span className="text-[11px] font-semibold text-teal-400 flex items-center">
                      <ArrowDown className="w-3 h-3 mr-0.5 inline" />
                      {item.trend}
                    </span>
                  )}
                </div>
              </div>

              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg ${item.iconBg}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          );
        })}
      </div>

      {metricsError && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">Dashboard data could not be refreshed. It will update automatically when the reports service is available.</div>}

      {/* Middle Row: Inspections Overview | Compliance by Category | Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 min-h-[300px]">
          <InspectionsChart
            total={metrics?.total_inspections ?? 0}
            compliant={metrics?.compliant_count ?? 0}
            nonCompliant={metrics?.non_compliant_count ?? 0}
            needsReview={metrics?.needs_review_count ?? 0}
            unableToVerify={metrics?.unable_to_verify_count ?? 0}
          />
        </div>
        <div className="lg:col-span-1 min-h-[300px]">
          <CategoryDonutChart distribution={metrics?.category_distribution ?? {}} total={metrics?.total_inspections ?? 0} />
        </div>
        <div className="lg:col-span-1 min-h-[300px]">
          <QuickActionsCard
            onScanVerify={onNewInspection}
            onAddInspection={onNewInspection}
            onRegisterComplaint={onOpenComplaintModal}
            onSearchLicensee={onOpenLicenseeModal}
          />
        </div>
      </div>

      {/* Bottom Row: Recent Inspections | Inspections by District | Recent Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 min-h-[340px]">
          <RecentInspectionsList
            inspections={metrics?.recent_inspections ?? []}
            onViewAll={onViewHistory}
            onSelectInspection={onViewInspection}
          />
        </div>
        <div className="lg:col-span-1 min-h-[340px]">
          <DistrictHeatmap />
        </div>
        <div className="lg:col-span-1 min-h-[340px]">
          <RecentAlertsCard onViewAll={onViewHistory} />
        </div>
      </div>

      {/* Persistent Bottom Bar with 4 Stats & AI Assistant */}
      <BottomStatsBar onOpenChatbot={onOpenChatbot} />
    </div>
  );
};
