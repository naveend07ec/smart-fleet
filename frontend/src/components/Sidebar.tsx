import { LayoutDashboard, Truck, BarChart3, Cpu, Radio, Shield, Atom, Compass } from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  isSimRunning: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onTabChange, isSimRunning }) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-badge">
          <Radio size={12} className={isSimRunning ? 'text-emerald-400 animate-pulse' : ''} />
          <span>Research Platform</span>
        </div>
        <h1 className="brand-title">Smart Fleet IoT</h1>
        <p className="brand-subtitle">Quantum-Safe Fleet Platform</p>
      </div>

      <nav className="sidebar-nav">
        <button
          className={`nav-link ${currentTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onTabChange('dashboard')}
          id="nav-dashboard"
        >
          <LayoutDashboard size={18} />
          <span>Fleet Dashboard</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'vehicles' ? 'active' : ''}`}
          onClick={() => onTabChange('vehicles')}
          id="nav-vehicles"
        >
          <Truck size={18} />
          <span>Vehicle Fleet</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'analytics' ? 'active' : ''}`}
          onClick={() => onTabChange('analytics')}
          id="nav-analytics"
        >
          <BarChart3 size={18} />
          <span>Fleet Analytics</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'ibe' ? 'active' : ''}`}
          onClick={() => onTabChange('ibe')}
          id="nav-ibe"
        >
          <Shield size={18} />
          <span>IBE Security Lab</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'secure-transmission' ? 'active' : ''}`}
          onClick={() => onTabChange('secure-transmission')}
          id="nav-secure-transmission"
        >
          <Radio size={18} />
          <span>Secure Transmission Lab</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'bqc' ? 'active' : ''}`}
          onClick={() => onTabChange('bqc')}
          id="nav-bqc"
        >
          <Atom size={18} />
          <span>BQC Privacy Lab</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'qubo-routing' ? 'active' : ''}`}
          onClick={() => onTabChange('qubo-routing')}
          id="nav-qubo-routing-sidebar"
        >
          <Compass size={18} />
          <span>QUBO Fleet Routing</span>
        </button>

        <button
          className={`nav-link ${currentTab === 'simulation' ? 'active' : ''}`}
          onClick={() => onTabChange('simulation')}
          id="nav-simulation"
        >
          <Cpu size={18} />
          <span>Simulator Control</span>
        </button>
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span>Simulator Status</span>
          <span style={{
            fontSize: '0.72rem',
            padding: '2px 6px',
            borderRadius: '4px',
            fontWeight: 600,
            background: isSimRunning ? 'rgba(16, 185, 129, 0.2)' : 'rgba(100, 116, 139, 0.2)',
            color: isSimRunning ? '#34d399' : '#94a3b8'
          }}>
            {isSimRunning ? 'Active' : 'Idle'}
          </span>
        </div>
        <div>v5.0.0-full • Multi-Phase Platform</div>
      </div>
    </aside>
  );
};

