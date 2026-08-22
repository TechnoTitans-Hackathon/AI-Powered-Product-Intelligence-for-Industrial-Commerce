import React, { useState } from 'react';
import { Bell, Search, User, ShieldCheck, Building2, Plus, Check, LogOut, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTenant } from '../context/TenantContext';
import { useAuth } from '../context/AuthContext';

interface Props {
  title?: string;
  subtitle?: string;
}

export const Header: React.FC<Props> = ({ title, subtitle }) => {
  const navigate = useNavigate();
  const { activeTenantId, activeTenantName, tenants, switchTenant, createCompanyTenant } = useTenant();
  const { user, logout } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [showTenantDropdown, setShowTenantDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showOnboardModal, setShowOnboardModal] = useState(false);


  // New company form state
  const [companyName, setCompanyName] = useState('');
  const [adminName, setAdminName] = useState('');
  const [email, setEmail] = useState('');
  const [industry, setIndustry] = useState('Industrial Equipment');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchTerm.trim()) {
      navigate(`/catalog?search=${encodeURIComponent(searchTerm.trim())}`);
    }
  };

  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName.trim() || !email.trim()) return;
    setIsSubmitting(true);
    try {
      await createCompanyTenant(adminName || companyName, email, companyName, industry);
      setShowOnboardModal(false);
      setCompanyName('');
      setAdminName('');
      setEmail('');
      navigate('/dashboard');
    } catch (err: any) {
      alert(`Failed to create company tenant: ${err.message || 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <header
        style={{
          backgroundColor: '#ffffff',
          borderBottom: '1px solid #e2e8f0',
          padding: '12px 32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div>
          {title && <h1 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#0f172a' }}>{title}</h1>}
          {subtitle && <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>{subtitle}</p>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Global Search Bar */}
          <form onSubmit={handleSearchSubmit} style={{ position: 'relative', width: '240px' }}>
            <Search
              size={15}
              style={{
                position: 'absolute',
                left: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#94a3b8',
              }}
            />
            <input
              type="search"
              placeholder="Search catalog, SKU, MPN..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                paddingLeft: '32px',
                paddingRight: '12px',
                paddingTop: '6px',
                paddingBottom: '6px',
                fontSize: '0.825rem',
                borderRadius: '6px',
                width: '100%',
              }}
            />
          </form>

          {/* Company / Tenant Selector */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowTenantDropdown(!showTenantDropdown)}
              className="btn-secondary btn-sm"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 12px',
                backgroundColor: activeTenantId === 'demo' ? '#f8fafc' : '#eff6ff',
                borderColor: activeTenantId === 'demo' ? '#cbd5e1' : '#bfdbfe',
                fontWeight: 600,
                color: activeTenantId === 'demo' ? '#334155' : '#1d4ed8',
                borderRadius: '6px',
              }}
              title="Switch Active Company / Workspace"
            >
              <Building2 size={15} color={activeTenantId === 'demo' ? '#64748b' : '#2563eb'} />
              <span style={{ maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {activeTenantName}
              </span>
            </button>

            {showTenantDropdown && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '110%',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                  width: '260px',
                  zIndex: 100,
                  overflow: 'hidden',
                }}
              >
                <div style={{ padding: '8px 12px', borderBottom: '1px solid #f1f5f9', fontSize: '0.75rem', fontWeight: 600, color: '#64748b' }}>
                  ACTIVE TENANT / WORKSPACE
                </div>

                <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  {tenants.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        switchTenant(t.id);
                        setShowTenantDropdown(false);
                      }}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: '10px 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        backgroundColor: activeTenantId === t.id ? '#f1f5f9' : 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '0.825rem',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: activeTenantId === t.id ? 600 : 500, color: '#0f172a' }}>
                          {t.name}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                          {t.id === 'demo' ? '10,005 baseline items' : t.industry || 'Workspace'}
                        </div>
                      </div>
                      {activeTenantId === t.id && <Check size={16} color="#2563eb" />}
                    </button>
                  ))}
                </div>

                <div style={{ borderTop: '1px solid #f1f5f9', padding: '6px' }}>
                  <button
                    onClick={() => {
                      setShowTenantDropdown(false);
                      setShowOnboardModal(true);
                    }}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      backgroundColor: '#2563eb',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                    }}
                  >
                    <Plus size={14} />
                    New Company Workspace
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Intelligence Mode Tag */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              backgroundColor: '#f1f5f9',
              borderRadius: '6px',
              fontSize: '0.75rem',
              color: '#334155',
              fontWeight: 500,
            }}
          >
            <ShieldCheck size={14} color="#2563eb" />
            <span>Multi-Agent Mode</span>
          </div>

          {/* Notification Bell */}
          <button
            className="btn-secondary btn-sm"
            style={{ padding: '6px 8px', borderRadius: '6px', color: '#64748b' }}
            title="System notifications"
            onClick={() => navigate('/validation')}
          >
            <Bell size={16} />
          </button>

          {/* User Profile & Logout Dropdown */}
          <div style={{ position: 'relative', paddingLeft: '8px', borderLeft: '1px solid #e2e8f0' }}>
            <button
              onClick={() => setShowUserDropdown(!showUserDropdown)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '4px 6px',
                borderRadius: '6px',
              }}
            >
              <div
                style={{
                  width: '30px',
                  height: '30px',
                  borderRadius: '50%',
                  backgroundColor: '#1e293b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#ffffff',
                }}
              >
                <User size={16} />
              </div>
              <div style={{ textAlign: 'left' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#0f172a', lineHeight: 1.2 }}>
                  {user?.name || 'Demo Employee'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748b', lineHeight: 1.2 }}>
                  {user?.email || 'employee@demo.com'}
                </div>
              </div>
              <ChevronDown size={14} color="#94a3b8" />
            </button>

            {showUserDropdown && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '115%',
                  backgroundColor: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                  width: '220px',
                  zIndex: 100,
                  overflow: 'hidden',
                }}
              >
                <div style={{ padding: '10px 14px', borderBottom: '1px solid #f1f5f9' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                    Signed in as
                  </div>
                  <div style={{ fontSize: '0.825rem', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>
                    {user?.name || 'Demo Employee'}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                    {user?.email || 'employee@demo.com'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#2563eb', marginTop: '4px', fontWeight: 500 }}>
                    Role: {user?.role || 'Specialist'} ({activeTenantName})
                  </div>
                </div>

                <div style={{ padding: '6px' }}>
                  <button
                    onClick={() => {
                      setShowUserDropdown(false);
                      logout();
                      navigate('/login');
                    }}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      background: 'none',
                      border: 'none',
                      borderRadius: '6px',
                      color: '#dc2626',
                      fontSize: '0.8rem',
                      fontWeight: 500,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      cursor: 'pointer',
                      textAlign: 'left',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#fef2f2')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <LogOut size={15} color="#dc2626" />
                    <span>Sign Out / Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>


      {/* New Company Onboarding Modal */}
      {showOnboardModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(2px)',
          }}
        >
          <div
            style={{
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              padding: '28px',
              width: '460px',
              maxWidth: '90%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  backgroundColor: '#eff6ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Building2 size={20} color="#2563eb" />
              </div>
              <div>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600, color: '#0f172a' }}>Register New Company</h2>
                <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Creates a private isolated product catalog tenant</p>
              </div>
            </div>

            <form onSubmit={handleCreateCompany} style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                  Company / Organization Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Apex Industrial Supplies"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                  Administrator Full Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Jane Doe"
                  value={adminName}
                  onChange={(e) => setAdminName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                  Work Email *
                </label>
                <input
                  type="email"
                  required
                  placeholder="e.g. admin@apexindustrial.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, color: '#334155', marginBottom: '4px' }}>
                  Primary Industry
                </label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
                >
                  <option value="Industrial Equipment">Industrial Equipment</option>
                  <option value="Pneumatics & Hydraulics">Pneumatics & Hydraulics</option>
                  <option value="Electrical & Automation">Electrical & Automation</option>
                  <option value="Fasteners & Hardware">Fasteners & Hardware</option>
                  <option value="HVAC & Refrigeration">HVAC & Refrigeration</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', marginTop: '12px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setShowOnboardModal(false)}
                  className="btn-secondary"
                  style={{ padding: '8px 16px', borderRadius: '6px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn-primary"
                  style={{ padding: '8px 20px', borderRadius: '6px' }}
                >
                  {isSubmitting ? 'Creating Workspace...' : 'Create & Switch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

