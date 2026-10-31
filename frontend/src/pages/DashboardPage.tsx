import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Doughnut } from 'react-chartjs-2';
import { Truck, Activity, Gauge, BatteryCharging, AlertCircle, RefreshCw, Radio } from 'lucide-react';
import { api } from '../services/api';
import { DashboardSummary, Vehicle } from '../types';
import { MetricCard } from '../components/MetricCard';
import { SimulatedMap } from '../components/SimulatedMap';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface DashboardPageProps {
  onViewVehicle: (id: number) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onViewVehicle }) => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [sumRes, vehRes] = await Promise.all([
        api.getDashboardSummary(),
        api.getVehicles(1, 100),
      ]);
      setSummary(sumRes);
      setVehicles(vehRes.items);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Poll updates every 4 seconds for live demonstration
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !summary) {
    return (
      <div className="state-container">
        <div className="spinner" />
        <div className="state-title">Loading Fleet Telemetry...</div>
        <p>Connecting to backend simulation database</p>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="state-container">
        <AlertCircle size={40} color="#ef4444" />
        <div className="state-title">Unable to Connect to Backend</div>
        <p>{error}</p>
        <button className="btn btn-secondary" onClick={loadData}>
          <RefreshCw size={14} /> Retry Connection
        </button>
      </div>
    );
  }

  // Charts configuration in Ink Wash high-contrast palette
  const trendLabels = summary?.recent_trend.map((t) => t.time_label) || [];
  const trendCounts = summary?.recent_trend.map((t) => t.record_count) || [];
  const trendSpeeds = summary?.recent_trend.map((t) => t.avg_speed) || [];

  const trendChartData = {
    labels: trendLabels,
    datasets: [
      {
        label: 'Avg Speed (km/h)',
        data: trendSpeeds,
        borderColor: '#0A0A0A',
        backgroundColor: 'rgba(10, 10, 10, 0.05)',
        tension: 0.35,
        fill: true,
        borderWidth: 2,
        yAxisID: 'y',
      },
      {
        label: 'Telemetry Volume',
        data: trendCounts,
        borderColor: '#64748B',
        backgroundColor: 'rgba(100, 116, 139, 0.04)',
        tension: 0.35,
        borderWidth: 1.8,
        yAxisID: 'y1',
      },
    ],
  };

  const trendChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: '#0A0A0A',
          font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif', size: 12, weight: 600 }
        }
      },
    },
    scales: {
      x: {
        grid: { color: '#F1F5F9' },
        ticks: { color: '#64748B', font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' } }
      },
      y: {
        type: 'linear' as const,
        position: 'left' as const,
        grid: { color: '#F1F5F9' },
        ticks: { color: '#64748B' },
        title: { display: true, text: 'km/h', color: '#64748B' },
      },
      y1: {
        type: 'linear' as const,
        position: 'right' as const,
        grid: { drawOnChartArea: false },
        ticks: { color: '#64748B' },
        title: { display: true, text: 'Records', color: '#64748B' },
      },
    },
  };

  const doughnutData = {
    labels: ['Moving', 'Idle', 'Offline'],
    datasets: [
      {
        data: [
          summary?.status_breakdown.moving || 0,
          summary?.status_breakdown.idle || 0,
          summary?.status_breakdown.offline || 0,
        ],
        backgroundColor: ['#059669', '#D97706', '#E2E8F0'],
        borderColor: '#FFFFFF',
        borderWidth: 2,
      },
    ],
  };

  const lastUpdateStr = summary?.latest_telemetry_at
    ? new Date(summary.latest_telemetry_at).toLocaleTimeString()
    : 'No telemetry yet';

  return (
    <div className="page-container" data-testid="dashboard-page">
      {/* Minimalist Page Header */}
      <div className="minimal-header">
        <div>
          <h1 className="minimal-title">Fleet Operations</h1>
          <p className="minimal-subtitle">Real-time IoT telemetry, tracking & vehicle metrics</p>
        </div>
        <div className="minimal-actions">
          <button className="apple-btn-pill" onClick={loadData}>
            <RefreshCw size={13} /> Sync Telemetry
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <MetricCard
          title="Total Vehicles"
          value={summary?.total_vehicles || 0}
          subtext="Registered units"
          icon={<Truck size={20} color="#0A0A0A" />}
        />
        <MetricCard
          title="Active (Moving)"
          value={summary?.status_breakdown.moving || 0}
          subtext="In transit"
          icon={<Activity size={20} color="#059669" />}
        />
        <MetricCard
          title="Idle / Standby"
          value={summary?.status_breakdown.idle || 0}
          subtext="Stationary"
          icon={<BatteryCharging size={20} color="#D97706" />}
        />
        <MetricCard
          title="Average Speed"
          value={`${summary?.speed_stats.average_speed_active_kmh || 0} km/h`}
          subtext={`Peak: ${summary?.speed_stats.max_speed_kmh || 0} km/h`}
          icon={<Gauge size={20} color="#0A0A0A" />}
        />
      </div>

      {/* Map & Distribution Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">
              <span>Live Fleet Map</span>
            </h3>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              Updated {lastUpdateStr}
            </span>
          </div>
          <div className="panel-body" style={{ padding: 0 }}>
            <SimulatedMap
              vehicles={vehicles}
              onSelectVehicle={onViewVehicle}
            />
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Status Breakdown</h3>
          </div>
          <div className="panel-body" style={{ height: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: '230px', height: '230px' }}>
              <Doughnut
                data={doughnutData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      position: 'bottom',
                      labels: {
                        color: '#0A0A0A',
                        font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif', size: 12 }
                      }
                    },
                  },
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Telemetry Trends */}
      <div className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Telemetry Trends & Speed Profile</h3>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Recent intervals
          </span>
        </div>
        <div className="panel-body" style={{ height: '300px' }}>
          <Line data={trendChartData} options={trendChartOptions} />
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
