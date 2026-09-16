import { NetworkNode, ContributingFactor, BottleneckAlertData, DistrictPriority, BacktestDataPoint } from '@/types';

// Node coordinates are the real Alappuzha network_capacity.csv positions (Kuttanad
// backwater basin, ~9.4-9.6N / 76.3-76.5E) so markers actually fall within the map's
// initialViewState (centered 76.10, 9.49) instead of ~245km off-screen — the mock set
// previously used ~11.7N coordinates (Kozhikode-area), which put every marker outside
// the visible viewport regardless of whether basemap tiles loaded.
export const mockNodes: NetworkNode[] = [
  {
    id: 'block-c',
    name: 'Kainakary Farm Block',
    type: 'Farm Block',
    crop: 'Rice',
    forecastArrivals: 8500,
    capacity: 10000,
    occupancy: 85,
    risk: 'Medium',
    status: 'Warning',
    coordinates: [76.3833, 9.4667] // near F1 Kainakary Paddy FPO
  },
  {
    id: 'fpo-north',
    name: 'Kainakary Paddy FPO',
    type: 'FPO',
    crop: 'Rice',
    forecastArrivals: 9000,
    capacity: 12000,
    occupancy: 75,
    risk: 'Medium',
    status: 'Normal',
    coordinates: [76.3833, 9.4667] // F1
  },
  {
    id: 'mandi-a',
    name: 'Alappuzha Principal Mandi',
    type: 'Mandi',
    crop: 'Rice',
    forecastArrivals: 18400,
    capacity: 13900,
    occupancy: 132,
    risk: 'High',
    status: 'Critical',
    coordinates: [76.3388, 9.4981] // M1 — matches the Alappuzha district centroid
  },
  {
    id: 'storage-central',
    name: 'KSWC Warehouse Ambalapuzha',
    type: 'Storage',
    crop: 'Rice',
    forecastArrivals: 5000,
    capacity: 8000,
    occupancy: 62,
    risk: 'Low',
    status: 'Normal',
    coordinates: [76.36, 9.38] // S2
  },
  {
    id: 'processor-west',
    name: 'Supplyco Rice Mill Kalavoor',
    type: 'Processor',
    crop: 'Rice',
    forecastArrivals: 3000,
    capacity: 5000,
    occupancy: 60,
    risk: 'Low',
    status: 'Normal',
    coordinates: [76.33, 9.56] // P1
  },
  // Secondary example for Priority View — Harippad market, still within Alappuzha
  // district so it renders on the same regional map instead of off-screen.
  {
    id: 'block-wayanad',
    name: 'Harippad Regulated Market',
    type: 'Farm Block',
    crop: 'Tomato',
    forecastArrivals: 8500,
    capacity: 10000,
    occupancy: 85,
    risk: 'Medium',
    status: 'Warning',
    coordinates: [76.4583, 9.2783] // M2
  }
];

export const mockFactors: ContributingFactor[] = [
  {
    id: 'f1',
    nodeId: 'block-c',
    location: 'Block C',
    description: 'High expected harvest volume',
    isPositive: false,
    date: 'Oct 18-26'
  },
  {
    id: 'f2',
    nodeId: 'block-c',
    location: 'Block C',
    description: 'Sown area increased by 14%',
    isPositive: false,
    date: 'Oct 18-26',
    source: 'Satellite imagery'
  },
  {
    id: 'f3',
    nodeId: 'mandi-a',
    location: 'Mandi A',
    description: 'Expected arrivals exceed absorption capacity',
    isPositive: false,
    date: 'Oct 18-26'
  },
  {
    id: 'f4',
    nodeId: 'mandi-a',
    location: 'Mandi A',
    description: 'Storage occupancy is approaching maximum',
    isPositive: false,
    date: 'Oct 18-26'
  }
];

export const mockBottleneckAlert: BottleneckAlertData = {
  nodeId: 'mandi-a',
  nodeName: 'Mandi A',
  crop: 'Rice',
  forecastArrivals: 18400,
  capacity: 13900,
  risk: 'High',
  confidence: 'High',
  harvestWindow: 'Oct 18 - 26',
  factors: mockFactors,
  recommendedAction: 'Redirect produce to Mandi B or Storage Central.',
  scheme: {
    title: 'Transport Subsidy Scheme (TSS)',
    description: 'Provides 50% transport subsidy for redirecting perishable crops to alternative mandis during glut periods.',
    source: 'Ministry of Agriculture',
    verificationNote: 'Verified active for Alappuzha district until Dec 2026.'
  }
};

export const mockPriorities: DistrictPriority[] = [
  { id: '1', district: 'Alappuzha', crop: 'Rice', risk: 'Medium', confidence: 'High', recommendedAction: 'Increase storage capacity' },
  { id: '2', district: 'Wayanad', crop: 'Tomato', risk: 'High', confidence: 'High', recommendedAction: 'Reroute to Mandi B' },
  { id: '3', district: 'Idukki', crop: 'Cardamom', risk: 'Medium', confidence: 'Medium', recommendedAction: 'Monitor arrivals' },
  { id: '4', district: 'Palakkad', crop: 'Paddy', risk: 'Medium', confidence: 'Low', recommendedAction: 'Officer review required' },
  { id: '5', district: 'Kottayam', crop: 'Rubber', risk: 'Low', confidence: 'High', recommendedAction: 'None' }
];

export const mockBacktestData: BacktestDataPoint[] = [
  { date: 'Oct 10', predictedArrivals: 4000, actualArrivals: 4200, predictedPrice: 2400, actualPrice: 2350 },
  { date: 'Oct 11', predictedArrivals: 4500, actualArrivals: 4400, predictedPrice: 2350, actualPrice: 2400 },
  { date: 'Oct 12', predictedArrivals: 5200, actualArrivals: 5500, predictedPrice: 2300, actualPrice: 2200 },
  { date: 'Oct 13', predictedArrivals: 6000, actualArrivals: 5900, predictedPrice: 2200, actualPrice: 2250 },
  { date: 'Oct 14', predictedArrivals: 7500, actualArrivals: 8000, predictedPrice: 2000, actualPrice: 1900 },
  { date: 'Oct 15', predictedArrivals: 9000, actualArrivals: 8800, predictedPrice: 1800, actualPrice: 1850 },
  { date: 'Oct 16', predictedArrivals: 11000, actualArrivals: 11500, predictedPrice: 1600, actualPrice: 1500 },
];

// Low confidence recommendation example
export const mockLowConfidenceAlert: BottleneckAlertData = {
  nodeId: 'storage-central',
  nodeName: 'Storage Central',
  crop: 'Rice',
  forecastArrivals: 5000,
  capacity: 8000,
  risk: 'Low',
  confidence: 'Low',
  confidence_label: 'LOW',
  implausible_magnitude: true,
  harvestWindow: 'Oct 18 - 26',
  factors: mockFactors,
  recommendedAction: 'estimated, pending model recalibration',
  scheme: {
    title: 'Transport Subsidy Scheme (TSS)',
    description: 'Provides 50% transport subsidy for redirecting perishable crops to alternative mandis during glut periods.',
    source: 'Ministry of Agriculture',
    verificationNote: 'Verified active for Alappuzha district.'
  }
};

// Scenario disagreement mock case
export const mockScenarioDisagreement = {
  scenarioA: 'Baseline',
  scenarioB: 'Weather-shift',
  description: 'Conflicting recommendations between scenarios, no clear winner.',
  details: {
    baseline: {
      action: 'Maintain current routing',
      confidence: 'Medium'
    },
    weatherShift: {
      action: 'Pre‑emptively shift to alternative mandi',
      confidence: 'Medium'
    }
  }
};
