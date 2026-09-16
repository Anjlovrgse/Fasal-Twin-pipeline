export type RiskLevel = 'Low' | 'Medium' | 'High';
export type ConfidenceTier = 'Low' | 'Medium' | 'High';
export type NodeStatus = 'Normal' | 'Warning' | 'Critical';
export type NodeType = 'Farm Block' | 'FPO' | 'Mandi' | 'Storage' | 'Processor';

export interface NetworkNode {
  id: string;
  name: string;
  type: NodeType;
  crop: string;
  forecastArrivals: number;
  capacity: number;
  occupancy: number; // percentage 0-100
  risk: RiskLevel;
  status: NodeStatus;
  coordinates: [number, number]; // [longitude, latitude]
}

export interface Metric {
  label: string;
  value: string;
  subLabel?: string;
  isRisk?: boolean;
}

export interface ContributingFactor {
  id: string;
  nodeId: string;
  location: string;
  description: string;
  isPositive: boolean;
  date: string;
  source?: string;
}

export interface SchemeInfo {
  title: string;
  description: string;
  source: string;
  verificationNote: string;
}

export interface BottleneckAlertData {
  nodeId: string;
  nodeName: string;
  crop: string;
  forecastArrivals: number;
  capacity: number;
  risk: RiskLevel;
  confidence: ConfidenceTier;
  // Optional real-API-shaped fields — present on mocks that mirror a LOW-confidence
  // or implausible-magnitude backend response for offline preview/demo purposes.
  confidence_label?: 'HIGH' | 'MEDIUM' | 'MODERATE' | 'LOW';
  implausible_magnitude?: boolean;
  harvestWindow: string;
  factors: ContributingFactor[];
  recommendedAction: string;
  scheme?: SchemeInfo;
}

export interface DistrictPriority {
  id: string;
  district: string;
  crop: string;
  risk: RiskLevel;
  confidence: ConfidenceTier;
  recommendedAction: string;
}

export interface BacktestDataPoint {
  date: string;
  predictedArrivals: number;
  actualArrivals: number;
  predictedPrice: number;
  actualPrice: number;
}
