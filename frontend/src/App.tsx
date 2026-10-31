import React, { useState, useEffect } from 'react';
import { TopNavbar } from './components/TopNavbar';
import { DashboardPage } from './pages/DashboardPage';
import { VehiclesPage } from './pages/VehiclesPage';
import { VehicleDetailPage } from './pages/VehicleDetailPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { IbeLabPage } from './pages/IbeLabPage';
import { SecureTransmissionLabPage } from './pages/SecureTransmissionLabPage';
import { BqcLabPage } from './pages/BqcLabPage';
import { QuboRoutingPage } from './pages/QuboRoutingPage';
import { SimulationControls } from './components/SimulationControls';
import { api } from './services/api';
import { SimulationStatus, SimulationStartParams } from './types';
import { AlertCircle } from 'lucide-react';
import { ErrorBoundary } from './components/ErrorBoundary';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | null>(null);
  const [simStatus, setSimStatus] = useState<SimulationStatus | null>(null);
  const [simLoading, setSimLoading] = useState<boolean>(false);

  const fetchSimulationState = async () => {
    try {
      const status = await api.getSimulationStatus();
      setSimStatus(status);
    } catch (e) {
      // Backend may be starting
    }
  };

  useEffect(() => {
    fetchSimulationState();
    const interval = setInterval(fetchSimulationState, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleStartSimulation = async (params: SimulationStartParams) => {
    setSimLoading(true);
    try {
      const updated = await api.startSimulation(params);
      setSimStatus(updated);
    } finally {
      setSimLoading(false);
    }
  };

  const handleStopSimulation = async () => {
    setSimLoading(true);
    try {
      const updated = await api.stopSimulation();
      setSimStatus(updated);
    } finally {
      setSimLoading(false);
    }
  };

  const handleViewVehicle = (id: number) => {
    setSelectedVehicleId(id);
    setCurrentTab('vehicle-detail');
  };

  const handleTabChange = (tab: string) => {
    setSelectedVehicleId(null);
    setCurrentTab(tab);
  };

  return (
    <div className="app-layout">
      {/* Apple Store Vibe Top Navigation Bar */}
      <TopNavbar
        currentTab={currentTab === 'vehicle-detail' ? 'vehicles' : currentTab}
        onTabChange={handleTabChange}
        isSimRunning={simStatus?.is_running ?? false}
      />

      {/* Full-Screen Main Content Area */}
      <main className="main-content">
        {/* View Router */}
        <ErrorBoundary>
          {currentTab === 'dashboard' && (
            <DashboardPage onViewVehicle={handleViewVehicle} />
          )}

          {currentTab === 'vehicles' && (
            <VehiclesPage onViewVehicle={handleViewVehicle} />
          )}

          {currentTab === 'vehicle-detail' && selectedVehicleId !== null && (
            <VehicleDetailPage
              vehicleId={selectedVehicleId}
              onBack={() => setCurrentTab('vehicles')}
            />
          )}

          {currentTab === 'analytics' && (
            <AnalyticsPage onViewVehicle={handleViewVehicle} />
          )}

          {currentTab === 'ibe' && (
            <IbeLabPage />
          )}

          {currentTab === 'secure-transmission' && (
            <SecureTransmissionLabPage />
          )}

          {currentTab === 'bqc' && (
            <BqcLabPage />
          )}

          {currentTab === 'qubo-routing' && (
            <QuboRoutingPage />
          )}


          {currentTab === 'simulation' && (
            <div className="page-container">
              <div>
                <h2 className="page-title">Simulation Control Panel</h2>
                <p className="page-description">
                  Control the background telemetry generator, select fleet scenarios, and configure deterministic random seeds.
                </p>
              </div>
              <SimulationControls
                status={simStatus}
                onStart={handleStartSimulation}
                onStop={handleStopSimulation}
                loading={simLoading}
              />
            </div>
          )}
        </ErrorBoundary>
      </main>

      {/* Modern Minimalist Footer */}
      <footer className="apple-footer">
        <div className="apple-footer-content">
          <div className="apple-footer-brand">
            <img src="/logo.png" alt="SmartFleet Logo" className="apple-footer-logo" />
            <span className="apple-footer-tagline">Connect • Monitor • Optimize</span>
          </div>
          <div className="apple-footer-copy">
            <span>© {new Date().getFullYear()} SmartFleet Operations System. All rights reserved.</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
