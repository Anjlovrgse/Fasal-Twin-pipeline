# Fasal Twin - Agricultural Digital Twin Dashboard

Fasal Twin is India's Regional Crop-Flow Digital Twin & Intervention Simulator. This dashboard provides a production-quality frontend built with React, TypeScript, and Tailwind CSS.

## Features

- **Regional Overview**: Real-time crop flow monitoring with summary metrics.
- **3D Regional Twin Map**: Powered by Mapbox GL JS, visualizes farm blocks, FPOs, mandis, and capacity bottlenecks.
- **Counterfactual Simulation Replay**: Run and compare scenarios with Do Nothing vs AI Intervention.
- **Multi-District Priority View**: Government officer view to track risk across all connected regions.
- **Historical Backtest**: Transparent evaluation of predicted vs actual arrivals and prices.
- **Evidence Engine**: Drawers to explore AI confidence, factors, and relevant Government Schemes.

## Technology Stack

- **Core**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4, Lucide React icons
- **State Management**: Zustand
- **Routing**: React Router v7
- **Mapping**: Mapbox GL JS, React Map GL
- **Charts**: Recharts
- **Animations**: Framer Motion

## Setup Instructions

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Mapbox Configuration**
   To fully utilize the 3D Regional Map, you need a Mapbox Access Token.
   - Create a file named `.env` in the root of the project.
   - Add your Mapbox token:
     ```env
     VITE_MAPBOX_TOKEN=your_mapbox_public_token_here
     ```
   If no token is provided, the map will display a fallback placeholder.

3. **Run the Development Server**
   ```bash
   npm run dev
   ```

4. **Build for Production**
   ```bash
   npm run build
   ```

## Design Notes

This application uses custom typography (Fraunces for headings, Archivo for body) and a carefully crafted color palette reflecting the Fasal Twin brand (Soil-Green, Turmeric Gold, Monsoon Teal, Rust-Red). The layout is optimized for desktop usage (with a dark charcoal fixed sidebar) and gracefully collapses to a drawer menu on mobile devices.
