import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Leaf,
  LayoutDashboard,
  AlertTriangle,
  PlaySquare,
  Map,
  History,
  ShieldCheck,
  BookOpen,
  Settings,
  LogOut,
  ChevronLeft
} from 'lucide-react';
import clsx from 'clsx';
import { getHealth } from '@/api/client';

const navGroups = [
  {
    title: 'OPERATIONS',
    items: [
      { name: 'Regional Overview', path: '/', icon: LayoutDashboard },
      { name: 'Bottleneck Alerts', path: '/alerts', icon: AlertTriangle },
      { name: 'Simulation Replay', path: '/simulation', icon: PlaySquare },
    ]
  },
  {
    title: 'ANALYTICS',
    items: [
      { name: 'Multi-District Priority', path: '/priority', icon: Map },
      { name: 'Historical Backtest', path: '/backtest', icon: History },
      { name: 'Confidence & Evidence', path: '/evidence', icon: ShieldCheck },
    ]
  },
  {
    title: 'RESOURCES',
    items: [
      { name: 'Scheme Advisor', path: '/schemes', icon: BookOpen },
      { name: 'Settings', path: '/settings', icon: Settings },
    ]
  }
];

export const Sidebar = () => {
  // Real backend connectivity, not a decorative always-green dot: polls /health
  // on a light interval so the indicator reflects what the rest of the app is
  // actually seeing, including recovering automatically once the backend returns.
  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const result = await getHealth();
      if (cancelled) return;
      setBackendUp(!('error' in result && result.error));
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  return (
    <aside className="w-64 bg-[#1a1e23] text-white flex flex-col h-screen shrink-0 font-archivo transition-all duration-300 border-r border-[#2d3436]">
      {/* Header */}
      <div className="p-6 flex items-center gap-3">
        <div className="bg-[#f5b041] p-1.5 rounded-md">
          <Leaf className="w-5 h-5 text-[#1a1e23]" />
        </div>
        <h1 className="font-fraunces text-xl font-bold tracking-wide">Fasal Twin</h1>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto py-2">
        {navGroups.map((group, idx) => (
          <div key={idx} className="mb-6 px-4">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">
              {group.title}
            </h2>
            <div className="space-y-1">
              {group.items.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.path}
                  className={({ isActive }) => clsx(
                    "flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors",
                    isActive 
                      ? "bg-[#2d3436] text-[#f5b041] font-medium" 
                      : "text-gray-300 hover:bg-[#2d3436] hover:text-white"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.name}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Footer / User Profile */}
      <div className="p-4 border-t border-[#2d3436]">
        <div className="flex items-center gap-3 mb-4">
          <div className={clsx(
            'w-2 h-2 rounded-full',
            backendUp === null ? 'bg-gray-500' : backendUp ? 'bg-[#1e847f]' : 'bg-[#c0392b]'
          )}></div>
          <span className="text-xs text-gray-400">
            {backendUp === null ? 'Checking…' : backendUp ? 'Data Connected' : 'Backend Offline'}
          </span>
        </div>
        
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs font-medium">
              AO
            </div>
            <div>
              <div className="text-sm font-medium">Anjali P.</div>
              <div className="text-xs text-gray-400">Agricultural Officer</div>
            </div>
          </div>
          <button className="text-gray-400 hover:text-white transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
