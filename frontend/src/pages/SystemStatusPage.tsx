import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Database, 
  Cpu, 
  Scan, 
  Scale, 
  CheckCircle2, 
  AlertCircle, 
  RefreshCw, 
  Clock,
  Server
} from 'lucide-react';
import { request } from '../services/api';
import { LegalDisclaimerBanner } from '../components/common/LegalDisclaimerBanner';

interface SystemHealthData {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  database: {
    status: string;
    url_type: string;
  };
  computer_vision: {
    yolo_detector: string;
    model_path: string;
    is_yolo_loaded: boolean;
  };
  ocr_service: {
    active_engine: string;
    version: string;
  };
  rule_engine: {
    version: string;
    active_categories: number;
  };
}

export const SystemStatusPage: React.FC = () => {
  const [health, setHealth] = useState<SystemHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await request<SystemHealthData>('/health');
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'Could not connect to backend service.');
    } finally {
      setLoading(false);
    }
  };

  const formatUptime = (sec: number) => {
    const hours = Math.floor(sec / 3600);
    const minutes = Math.floor((sec % 3600) / 60);
    const seconds = Math.floor(sec % 60);
    return `${hours}h ${minutes}m ${seconds}s`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fadeIn">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <Activity className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-extrabold text-white tracking-tight">System Status & Architecture Health</h1>
          </div>
          <p className="text-xs text-slate-400">
            Real-time diagnostics of ML models, OCR engine, rule database, and API telemetry.
          </p>
        </div>

        <button
          onClick={fetchHealth}
          className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Status</span>
        </button>
      </div>

      {error ? (
        <div className="p-6 rounded-3xl bg-rose-500/10 border border-rose-500/30 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-bold text-white">Backend Offline or Unreachable</h3>
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      ) : health ? (
        <div className="space-y-6">
          
          {/* Main Status Banner */}
          <div className="p-6 rounded-3xl bg-slate-900/80 border border-slate-800 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Server className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-lg font-bold text-white">{health.app_name}</span>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-400">
                    v{health.version}
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Environment: <b className="text-slate-300 uppercase">{health.environment}</b> | Uptime: <b className="text-slate-300">{formatUptime(health.uptime_seconds)}</b>
                </p>
              </div>
            </div>

            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-xs font-mono font-bold self-start sm:self-auto">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>CORE API ONLINE</span>
            </div>
          </div>

          {/* Subsystem Health Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            
            {/* 1. Database Subsystem */}
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Database className="w-5 h-5 text-blue-400" />
                  <h3 className="text-sm font-bold text-slate-200">Database Engine</h3>
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  {health.database.status}
                </span>
              </div>
              <div className="text-xs text-slate-400 font-mono space-y-1 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
                <div>Provider: <b className="text-slate-200">{health.database.url_type}</b></div>
                <div>Connection Pool: <b className="text-slate-200">SQLAlchemy Active</b></div>
              </div>
            </div>

            {/* 2. Computer Vision & YOLO Detector */}
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Cpu className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-200">CV / YOLO Region Detector</h3>
                </div>
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                  health.computer_vision.is_yolo_loaded 
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' 
                    : 'text-slate-400 bg-slate-800 border-slate-700'
                }`}>
                  {health.computer_vision.is_yolo_loaded ? 'MODEL ACTIVE' : 'UNCONFIGURED'}
                </span>
              </div>
              <div className="text-xs text-slate-400 font-mono space-y-1 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
                <div className="truncate">Model Path: <b className="text-slate-200">{health.computer_vision.model_path}</b></div>
                <div>Status: <b className={health.computer_vision.is_yolo_loaded ? 'text-emerald-400' : 'text-slate-400'}>{health.computer_vision.yolo_detector}</b></div>
              </div>
            </div>

            {/* 3. OCR Engine */}
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Scan className="w-5 h-5 text-teal-400" />
                  <h3 className="text-sm font-bold text-slate-200">Optical Character Recognition (OCR)</h3>
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  READY
                </span>
              </div>
              <div className="text-xs text-slate-400 font-mono space-y-1 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
                <div>Active Engine: <b className="text-slate-200">{health.ocr_service.active_engine}</b></div>
                <div>Version: <b className="text-slate-200">{health.ocr_service.version}</b></div>
              </div>
            </div>

            {/* 4. Legal Metrology Rule Engine */}
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Scale className="w-5 h-5 text-amber-400" />
                  <h3 className="text-sm font-bold text-slate-200">Legal Rule Engine</h3>
                </div>
                <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  {health.rule_engine.active_categories} CATEGORIES
                </span>
              </div>
              <div className="text-xs text-slate-400 font-mono space-y-1 bg-slate-950/60 p-3 rounded-xl border border-slate-800/60">
                <div>Rule-set Version: <b className="text-slate-200">{health.rule_engine.version}</b></div>
                <div>Regulations: <b className="text-slate-200">Legal Metrology (PC) Rules, 2011</b></div>
              </div>
            </div>

          </div>

        </div>
      ) : null}

      <LegalDisclaimerBanner />

    </div>
  );
};
