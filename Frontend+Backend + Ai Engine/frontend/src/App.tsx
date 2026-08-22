import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { TenantProvider } from './context/TenantContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { UploadProduct } from './pages/UploadProduct';
import { ProductCatalog } from './pages/ProductCatalog';
import { ProductIntelligence } from './pages/ProductIntelligence';
import { BatchProcessing } from './pages/BatchProcessing';
import { ValidationCenter } from './pages/ValidationCenter';
import { Explainability } from './pages/Explainability';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { HelpSupport } from './pages/HelpSupport';
import AITraceConsole from './pages/admin/AITraceConsole';

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="app-container">
      {/* Left Sidebar Navigation */}
      <Sidebar />

      {/* Right Main Content */}
      <div className="main-content">
        <Header />
        <main style={{ flex: 1 }}>{children}</main>
      </div>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <TenantProvider>
        <Router>
          <Routes>
            {/* Public Login Route */}
            <Route path="/login" element={<Login />} />

            {/* Protected Routes guarded by ProtectedRoute and wrapped in AppLayout */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Navigate to="/dashboard" replace />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Dashboard />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/upload"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <UploadProduct />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/catalog"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ProductCatalog />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/product-intelligence"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ProductIntelligence />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/batch-processing"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <BatchProcessing />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/validation"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ValidationCenter />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/explainability"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Explainability />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Analytics />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Settings />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/help"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <HelpSupport />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/ai-trace"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <AITraceConsole />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="*"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Navigate to="/dashboard" replace />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
          </Routes>
        </Router>
      </TenantProvider>
    </AuthProvider>
  );
}

export default App;
