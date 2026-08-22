import React, { createContext, useContext, useState, useEffect } from 'react';
import { TenantInfo, UserInfo, getTenantsList, switchActiveTenant, registerCompany } from '../api/client';

interface TenantContextType {
  activeTenantId: string;
  activeTenantName: string;
  tenants: TenantInfo[];
  currentUser: UserInfo | null;
  isLoading: boolean;
  switchTenant: (tenantId: string) => Promise<void>;
  createCompanyTenant: (name: string, email: string, companyName: string, industry?: string) => Promise<void>;
  refreshTenants: () => Promise<void>;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export const TenantProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTenantId, setActiveTenantId] = useState<string>(
    localStorage.getItem('active_tenant_id') || 'demo'
  );
  const [activeTenantName, setActiveTenantName] = useState<string>(
    localStorage.getItem('active_tenant_name') || 'Demo Catalog (10k Products)'
  );
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshTenants = async () => {
    try {
      const list = await getTenantsList();
      setTenants(list);
      const current = list.find((t) => t.id === activeTenantId);
      if (current) {
        setActiveTenantName(current.name);
      }
    } catch (e) {
      console.error('Failed to load tenants:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshTenants();
    const handleEvents = () => {
      const storedId = localStorage.getItem('active_tenant_id') || 'demo';
      const storedName = localStorage.getItem('active_tenant_name') || 'Demo Industrial Catalog';
      setActiveTenantId(storedId);
      setActiveTenantName(storedName);
      refreshTenants();
    };
    window.addEventListener('auth-changed', handleEvents);
    window.addEventListener('tenant-changed', handleEvents);
    return () => {
      window.removeEventListener('auth-changed', handleEvents);
      window.removeEventListener('tenant-changed', handleEvents);
    };
  }, [activeTenantId]);


  const switchTenant = async (tenantId: string) => {
    try {
      setIsLoading(true);
      const res = await switchActiveTenant(tenantId);
      setActiveTenantId(res.tenant.id);
      setActiveTenantName(res.tenant.name);
      localStorage.setItem('active_tenant_id', res.tenant.id);
      localStorage.setItem('active_tenant_name', res.tenant.name);
      // Trigger a window event or re-render
      window.dispatchEvent(new Event('tenant-changed'));
    } catch (e) {
      console.error('Failed to switch tenant:', e);
      // Fallback
      setActiveTenantId(tenantId);
      localStorage.setItem('active_tenant_id', tenantId);
      window.dispatchEvent(new Event('tenant-changed'));
    } finally {
      setIsLoading(false);
    }
  };

  const createCompanyTenant = async (name: string, email: string, companyName: string, industry?: string) => {
    setIsLoading(true);
    try {
      const res = await registerCompany({
        name,
        email,
        company_name: companyName,
        industry: industry || 'Industrial Equipment',
      });
      setActiveTenantId(res.tenant.id);
      setActiveTenantName(res.tenant.name);
      setCurrentUser(res.user);
      await refreshTenants();
      window.dispatchEvent(new Event('tenant-changed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <TenantContext.Provider
      value={{
        activeTenantId,
        activeTenantName,
        tenants,
        currentUser,
        isLoading,
        switchTenant,
        createCompanyTenant,
        refreshTenants,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
};

export const useTenant = () => {
  const context = useContext(TenantContext);
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider');
  }
  return context;
};
