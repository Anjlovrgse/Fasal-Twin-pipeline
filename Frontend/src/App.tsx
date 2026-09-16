import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layout/MainLayout';
import { RegionalOverview } from './pages/RegionalOverview';
import { PriorityView } from './pages/PriorityView';
import { BacktestView } from './pages/BacktestView';
import { SimulationReplay } from './pages/SimulationReplay';
import { BottleneckAlertsView } from './pages/BottleneckAlertsView';
import { SchemeAdvisorView } from './pages/SchemeAdvisorView';
import { SystemStatusView } from './pages/SystemStatusView';
import { EvidenceRedirect } from './pages/EvidenceRedirect';
import { NotFound } from './pages/NotFound';
import { EvidenceDrawer } from './components/evidence/EvidenceDrawer';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<RegionalOverview />} />
          <Route path="priority" element={<PriorityView />} />
          <Route path="backtest" element={<BacktestView />} />
          <Route path="alerts" element={<BottleneckAlertsView />} />
          <Route path="schemes" element={<SchemeAdvisorView />} />
          <Route path="settings" element={<SystemStatusView />} />
          <Route path="evidence" element={<EvidenceRedirect />} />
          <Route path="*" element={<NotFound />} />
        </Route>
        {/* Simulation has its own distinct layout inside the component */}
        <Route path="/simulation" element={<SimulationReplay />} />
      </Routes>
      <EvidenceDrawer />
    </BrowserRouter>
  );
}

export default App;
