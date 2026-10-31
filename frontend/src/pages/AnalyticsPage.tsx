import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';
import { BarChart3, Database, Gauge, Zap, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { AnalyticsOverview } from '../types';
import { MetricCard } from '../components/MetricCard';

interface AnalyticsPageProps {
  onViewVehicle: (id: number) => void;
}

export const AnalyticsPage: React.FC<AnalyticsPageProps> = ({ onViewVehicle }) => {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    try {
      const res = await api.getAnalyticsOverview();
      setData(res);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load fleet analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading && !data) {
    return (
      <div className="state-container">
        <div className="spinner" />
        <div className="state-title">Aggregating Fleet Analytics...</div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="state-container">
        <AlertCircle size={40} color="#f87171" />
        <div className="state-title">Error Loading Analytics</div>
        <p>{error}</p>
        <button className="btn btn-secondary" onClick={fetchAnalytics}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    );
  }

  // 1. Status Distribution
  const pieLabels = data?.status_distribution.map((s) => `${s.status} (${s.percentage}%)`) || [];
  const pieCounts = data?.status_distribution.map((s) => s.count) || [];
  const statusPieData = {
    labels: pieLabels,
    datasets: [
      {
        data: pieCounts,
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#6366f1'],
        borderWidth: 0,
      },
    ],
  };

  // 2. Activity Over Time (Stacked Bar)
  const actLabels = data?.activity_over_time.map((a) => a.timestamp_bucket) || [];
  const actMoving = data?.activity_over_time.map((a) => a.moving_count) || [];
  const actIdle = data?.activity_over_time.map((a) => a.idle_count) || [];
  const actOffline = data?.activity_over_time.map((a) => a.offline_count) || [];

  const activityChartData = {
    labels: actLabels,
    datasets: [
      {
        label: 'Moving Units',
        data: actMoving,
        backgroundColor: '#10b981',
      },
      {
        label: 'Idle Units',
        data: actIdle,
        backgroundColor: '#f59e0b',
      },
      {
        label: 'Offline Units',
        data: actOffline,
        backgroundColor: '#ef4444',
      },
    ],
  };

  // 3. Telemetry Volume Over Time
  const volLabels = data?.telemetry_volume_over_time.map((v) => v.timestamp_bucket) || [];
  const volCounts = data?.telemetry_volume_over_time.map((v) => v.record_count) || [];

  const volumeChartData = {
    labels: volLabels,
    datasets: [
      {
        label: 'Telemetry Records Logged',
        data: volCounts,
        borderColor: '#0A0A0A',
        backgroundColor: 'rgba(10, 10, 10, 0.05)',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  const chartOptionsBase = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#0A0A0A', font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif', weight: 600 } } },
    },
    scales: {
      x: { grid: { color: '#F1F5F9' }, ticks: { color: '#64748B', font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' } } },
      y: { grid: { color: '#F1F5F9' }, ticks: { color: '#64748B', font: { family: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif' } } },
    },
  };

  return (
    <div className="page-container" data-testid="analytics-page">
      <div className="minimal-header">
        <div>
          <h1 className="minimal-title">Fleet Analytics</h1>
          <p className="minimal-subtitle">Persisted speed profiles, status distribution & telemetry volume</p>
        </div>
        <div className="minimal-actions">
          <button className="btn btn-secondary" onClick={fetchAnalytics}>
            <RefreshCw size={14} /> Refresh Analytics
          </button>
        </div>
      </div>

      {/* Top Metrics Cards */}
      <div className="metrics-grid">
        <MetricCard
          title="Total Telemetry Ingested"
          value={data?.total_records || 0}
          subtext="Persisted PostgreSQL records"
          icon={<Database size={20} color="#0A0A0A" />}
        />
        <MetricCard
          title="Active Avg Speed"
          value={`${data?.speed_analytics.active_average_kmh || 0} km/h`}
          subtext="Vehicles in transit"
          icon={<Gauge size={20} color="#059669" />}
        />
        <MetricCard
          title="Fleet Overall Avg Speed"
          value={`${data?.speed_analytics.overall_average_kmh || 0} km/h`}
          subtext="Includes idle/zero-speed readings"
          icon={<Gauge size={20} color="#0A0A0A" />}
        />
        <MetricCard
          title="Peak Recorded Speed"
          value={`${data?.speed_analytics.max_recorded_kmh || 0} km/h`}
          subtext="Upper bound telemetry point"
          icon={<Zap size={20} color="#0A0A0A" />}
        />
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* Activity Over Time */}
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Vehicle Activity Timeline</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Hourly aggregation</span>
          </div>
          <div className="panel-body" style={{ height: '300px' }}>
            <Bar data={activityChartData} options={chartOptionsBase} />
          </div>
        </div>

        {/* Telemetry Volume */}
        <div className="panel">
          <div className="panel-header">
            <h3 className="panel-title">Telemetry Volume Over Time</h3>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Ingestion throughput</span>
          </div>
          <div className="panel-body" style={{ height: '300px' }}>
            <Line data={volumeChartData} options={chartOptionsBase} />
          </div>
        </div>
      </div>

      {/* Top Vehicles Performance Summary Table */}
      <div className="panel">
        <div className="panel-header">
          <h3 className="panel-title">Vehicle Performance & Telemetry Volume Summary</h3>
        </div>
        <div className="table-responsive">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Vehicle Identifier</th>
                <th>Name</th>
                <th>Total Telemetry Points</th>
                <th>Average Speed</th>
                <th>Max Speed</th>
                <th>Power Indicator</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!data?.top_active_vehicles || data.top_active_vehicles.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)' }}>
                    No vehicle records available.
                  </td>
                </tr>
              ) : (
                data.top_active_vehicles.map((v) => (
                  <tr key={v.vehicle_id}>
                    <td>
                      <strong style={{ fontFamily: 'var(--font-family-mono)', color: 'var(--deep-obsidian)' }}>
                        {v.vehicle_identifier}
                      </strong>
                    </td>
                    <td>{v.name}</td>
                    <td>{v.total_telemetry_points} pts</td>
                    <td>{v.average_speed} km/h</td>
                    <td>{v.max_speed} km/h</td>
                    <td>{v.latest_battery_level}%</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                        onClick={() => onViewVehicle(v.vehicle_id)}
                      >
                        View Vehicle
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
