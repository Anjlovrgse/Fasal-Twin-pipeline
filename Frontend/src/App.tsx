import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layout/MainLayout';
import { EvidenceDrawer } from './components/evidence/EvidenceDrawer';
import { Loader2 } from 'lucide-react';

// Route-level code splitting: RegionalOverview and SimulationReplay each pull in
// react-map-gl/maplibre-gl (~1MB alone), which previously loaded on every route
// (e.g. /priority, /settings) even though only two routes ever render a map.
const RegionalOverview = lazy(() => import('./pages/RegionalOverview').then(m => ({ default: m.RegionalOverview })));
const PriorityView = lazy(() => import('./pages/PriorityView').then(m => ({ default: m.PriorityView })));
const BacktestView = lazy(() => import('./pages/BacktestView').then(m => ({ default: m.BacktestView })));
const SimulationReplay = lazy(() => import('./pages/SimulationReplay').then(m => ({ default: m.SimulationReplay })));
const BottleneckAlertsView = lazy(() => import('./pages/BottleneckAlertsView').then(m => ({ default: m.BottleneckAlertsView })));
const SchemeAdvisorView = lazy(() => import('./pages/SchemeAdvisorView').then(m => ({ default: m.SchemeAdvisorView })));
const SystemStatusView = lazy(() => import('./pages/SystemStatusView').then(m => ({ default: m.SystemStatusView })));
const SowingAdvisoryView = lazy(() => import('./pages/SowingAdvisoryView').then(m => ({ default: m.SowingAdvisoryView })));
const EvidenceRedirect = lazy(() => import('./pages/EvidenceRedirect').then(m => ({ default: m.EvidenceRedirect })));
const NotFound = lazy(() => import('./pages/NotFound').then(m => ({ default: m.NotFound })));

const RouteFallback = () => (
  <div className="h-full flex items-center justify-center py-24 text-gray-400">
    <Loader2 className="w-6 h-6 animate-spin" />
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<RegionalOverview />} />
            <Route path="priority" element={<PriorityView />} />
            <Route path="backtest" element={<BacktestView />} />
            <Route path="alerts" element={<BottleneckAlertsView />} />
            <Route path="schemes" element={<SchemeAdvisorView />} />
            <Route path="settings" element={<SystemStatusView />} />
            <Route path="sowing" element={<SowingAdvisoryView />} />
            <Route path="evidence" element={<EvidenceRedirect />} />
            <Route path="*" element={<NotFound />} />
          </Route>
          {/* Simulation has its own distinct layout inside the component */}
          <Route path="/simulation" element={<SimulationReplay />} />
        </Routes>
      </Suspense>
      <EvidenceDrawer />
    </BrowserRouter>
  );
}

export default App;
