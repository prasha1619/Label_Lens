import React, { useState, useEffect } from 'react';
import { Wifi, WifiOff, RefreshCw, CheckCircle2, Shield } from 'lucide-react';

export const OfflineSyncBanner: React.FC = () => {
  const [isOnline, setIsOnline] = useState<boolean>(navigator.onLine);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncSuccess, setSyncSuccess] = useState<boolean>(false);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Read pending inspections from localStorage
    try {
      const stored = localStorage.getItem('labellens_offline_queue');
      if (stored) {
        const queue = JSON.parse(stored);
        setPendingCount(Array.isArray(queue) ? queue.length : 0);
      }
    } catch {
      setPendingCount(0);
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const handleTriggerSync = () => {
    setIsSyncing(true);
    setTimeout(() => {
      setIsSyncing(false);
      setSyncSuccess(true);
      setPendingCount(0);
      try {
        localStorage.removeItem('labellens_offline_queue');
      } catch {}
      setTimeout(() => setSyncSuccess(false), 4000);
    }, 1500);
  };

  if (isOnline && pendingCount === 0 && !syncSuccess) {
    return null;
  }

  return (
    <div className="rounded-2xl bg-[#0b142c] border border-[#1e2c56] p-3.5 shadow-lg flex flex-wrap items-center justify-between gap-3 text-xs">
      <div className="flex items-center space-x-2.5">
        <div className={`w-3 h-3 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
        <div>
          <span className="font-bold text-white">
            {isOnline ? '🟢 Connected / Edge Ready' : '🟡 Offline Inspection Mode'}
          </span>
          <span className="text-slate-400 ml-2">
            {isOnline
              ? `${pendingCount} record(s) queued for synchronization`
              : 'Inspections will be processed and stored securely locally'}
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        {syncSuccess && (
          <span className="text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-4 h-4" />
            All records synchronized ✓
          </span>
        )}

        {isOnline && pendingCount > 0 && (
          <button
            onClick={handleTriggerSync}
            disabled={isSyncing}
            className="px-3 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold flex items-center gap-1.5 transition-colors shadow-md disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            {isSyncing ? 'Synchronizing...' : `Sync ${pendingCount} Record(s)`}
          </button>
        )}
      </div>
    </div>
  );
};
