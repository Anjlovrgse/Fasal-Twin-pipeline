import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layout/MainLayout';
import { RegionalOverview } from './pages/RegionalOverview';
import { PriorityView } from './pages/PriorityView';
import { BacktestView } from './pages/BacktestView';
import { SimulationReplay } from './pages/SimulationReplay';
import { EvidenceDrawer } from './components/evidence/EvidenceDrawer';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<RegionalOverview />} />
          <Route path="priority" element={<PriorityView />} />
          <Route path="backtest" element={<BacktestView />} />
        </Route>
        {/* Simulation has its own distinct layout inside the component */}
        <Route path="/simulation" element={<SimulationReplay />} />
        {/* Mock other routes */}
        <Route path="*" element={<MainLayout />} />
      </Routes>
      <EvidenceDrawer />
    </BrowserRouter>
  );
}

export default App;
