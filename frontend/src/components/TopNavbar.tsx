import React, { useState, useRef, useEffect } from 'react';
import {
  LayoutDashboard,
  Truck,
  BarChart3,
  Cpu,
  Radio,
  Shield,
  Atom,
  Compass,
  ChevronDown,
  Check,
  LucideIcon
} from 'lucide-react';

interface TopNavbarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  isSimRunning: boolean;
}

interface DropdownItem {
  id: string;
  label: string;
  sublabel: string;
  domId: string;
  icon: LucideIcon;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({ currentTab, onTabChange, isSimRunning }) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const primaryNavItems = [
    { id: 'dashboard', label: 'Fleet Dashboard', domId: 'nav-dashboard', icon: LayoutDashboard },
    { id: 'vehicles', label: 'Vehicle Fleet', domId: 'nav-vehicles', icon: Truck },
    { id: 'analytics', label: 'Fleet Analytics', domId: 'nav-analytics', icon: BarChart3 },
  ];

  const securityItems: DropdownItem[] = [
    {
      id: 'ibe',
      label: 'Identity Encryption',
      sublabel: 'IBE Security Lab & Key Auth',
      domId: 'nav-ibe',
      icon: Shield,
    },
    {
      id: 'secure-transmission',
      label: 'Secure Transmission',
      sublabel: 'Encrypted Vehicle Data Tunnel',
      domId: 'nav-secure-transmission',
      icon: Radio,
    },
    {
      id: 'bqc',
      label: 'Quantum Privacy',
      sublabel: 'Universal BFK09 MBQC Lab',
      domId: 'nav-bqc',
      icon: Atom,
    },
    {
      id: 'qubo-routing',
      label: 'QUBO Route Optimizer',
      sublabel: 'Simulated Annealing Scheduling',
      domId: 'nav-qubo-routing',
      icon: Compass,
    },
  ];


  const isSecurityActive = securityItems.some((item) => item.id === currentTab);
  const activeSecurityItem = securityItems.find((item) => item.id === currentTab);

  // Close dropdown on click outside or escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setDropdownOpen(false);
      }
    };

    if (dropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [dropdownOpen]);

  const handleSelectSecurity = (id: string) => {
    onTabChange(id);
    setDropdownOpen(false);
  };

  return (
    <header className="apple-top-navbar" role="navigation">
      <div className="apple-navbar-container">
        {/* Brand Section */}
        <div className="apple-navbar-brand" onClick={() => onTabChange('dashboard')} style={{ cursor: 'pointer' }} title="SmartFleet">
          <img
            src="/logo.png"
            alt="SmartFleet Logo"
            className="apple-brand-logo-img"
          />
        </div>

        <div className="apple-navbar-divider" />

        {/* Center Navigation Links */}
        <nav className="apple-navbar-links" aria-label="Main Navigation">
          {primaryNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id || (item.id === 'vehicles' && currentTab === 'vehicle-detail');
            return (
              <button
                key={item.id}
                id={item.domId}
                type="button"
                className={`apple-nav-button ${isActive ? 'active' : ''}`}
                onClick={() => onTabChange(item.id)}
              >
                <Icon size={15} className="apple-nav-icon" />
                <span>{item.label}</span>
                {isActive && <div className="apple-nav-indicator" />}
              </button>
            );
          })}

          {/* Security & Privacy Dropdown */}
          <div className="apple-nav-dropdown-wrapper" ref={dropdownRef}>
            <button
              id="nav-security-dropdown"
              type="button"
              className={`apple-nav-button apple-dropdown-trigger ${isSecurityActive ? 'active' : ''} ${dropdownOpen ? 'menu-open' : ''}`}
              onClick={() => setDropdownOpen((prev) => !prev)}
              aria-expanded={dropdownOpen}
              aria-haspopup="true"
            >
              <Shield size={15} className="apple-nav-icon" />
              <span>{activeSecurityItem ? `Security: ${activeSecurityItem.label}` : 'Security & Privacy'}</span>
              <ChevronDown
                size={13}
                className={`apple-nav-chevron ${dropdownOpen ? 'rotated' : ''}`}
              />
              {isSecurityActive && <div className="apple-nav-indicator" />}
            </button>

            {dropdownOpen && (
              <div className="apple-dropdown-menu" role="menu">
                <div className="apple-dropdown-header">
                  <span>Security & Quantum Optimization Labs</span>
                </div>
                {securityItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = currentTab === item.id;
                  return (
                    <button
                      key={item.id}
                      id={item.domId}
                      type="button"
                      role="menuitem"
                      className={`apple-dropdown-item ${isActive ? 'active' : ''}`}
                      onClick={() => handleSelectSecurity(item.id)}
                    >
                      <div className="apple-dropdown-item-icon">
                        <Icon size={16} />
                      </div>
                      <div className="apple-dropdown-item-content">
                        <div className="apple-dropdown-item-title">
                          {item.label}
                          {isActive && <span className="apple-dropdown-current-dot" />}
                        </div>
                        <div className="apple-dropdown-item-desc">{item.sublabel}</div>
                      </div>
                      {isActive && <Check size={14} className="apple-dropdown-check" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Simulator Control */}
          <button
            id="nav-simulation"
            type="button"
            className={`apple-nav-button ${currentTab === 'simulation' ? 'active' : ''}`}
            onClick={() => onTabChange('simulation')}
          >
            <Cpu size={15} className="apple-nav-icon" />
            <span>Simulator Control</span>
            {currentTab === 'simulation' && <div className="apple-nav-indicator" />}
          </button>
        </nav>
      </div>
    </header>
  );
};

export default TopNavbar;
