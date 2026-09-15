import { create } from 'zustand';

interface AppState {
  activeState: string;
  activeDistrict: string;
  activeCrop: string;
  dateRange: string;
  selectedNodeId: string | null;
  isSimulationPlaying: boolean;
  simulationScenario: 'Baseline' | 'Weather-shift' | 'Regional shock' | 'Capacity shock';
  interventionEnabled: boolean;
  isEvidenceDrawerOpen: boolean;

  setActiveState: (state: string) => void;
  setActiveDistrict: (district: string) => void;
  setActiveCrop: (crop: string) => void;
  setDateRange: (range: string) => void;
  // selectedNodeId is ONLY for map highlighting/zoom — it does not affect the analysis context
  setSelectedNodeId: (id: string | null) => void;
  setSimulationPlaying: (playing: boolean) => void;
  setSimulationScenario: (scenario: 'Baseline' | 'Weather-shift' | 'Regional shock' | 'Capacity shock') => void;
  setInterventionEnabled: (enabled: boolean) => void;
  setEvidenceDrawerOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeState: 'Kerala',
  activeDistrict: 'Alappuzha',
  activeCrop: 'Rice',
  dateRange: 'Oct 18-26',
  selectedNodeId: null,
  isSimulationPlaying: false,
  simulationScenario: 'Baseline',
  interventionEnabled: false,
  isEvidenceDrawerOpen: false,

  setActiveState: (state) => set({ activeState: state }),
  setActiveDistrict: (district) => set({ activeDistrict: district }),
  setActiveCrop: (crop) => set({ activeCrop: crop }),
  setDateRange: (range) => set({ dateRange: range }),
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),
  setSimulationPlaying: (playing) => set({ isSimulationPlaying: playing }),
  setSimulationScenario: (scenario) => set({ simulationScenario: scenario }),
  setInterventionEnabled: (enabled) => set({ interventionEnabled: enabled }),
  setEvidenceDrawerOpen: (open) => set({ isEvidenceDrawerOpen: open }),
}));
