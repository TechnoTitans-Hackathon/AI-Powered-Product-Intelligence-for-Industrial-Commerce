import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
} from 'chart.js';
import { Bar, Doughnut, Line } from 'react-chartjs-2';
import { getAnalyticsSummary, getProcessingTrends, getProducts } from '../api/client';
import { AnalyticsSummary, ProductItem } from '../types';
import { RefreshCw, BarChart3, PieChart, TrendingUp, ShieldCheck } from 'lucide-react';
import { useTenant } from '../context/TenantContext';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

export const Analytics: React.FC = () => {
  const { activeTenantId, activeTenantName } = useTenant();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [trends, setTrends] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sumData, prodsData, trendData] = await Promise.all([
        getAnalyticsSummary(),
        getProducts({ limit: 100 }),
        getProcessingTrends(7),
      ]);
      setSummary(sumData);
      setProducts(prodsData);
      setTrends(trendData);
    } catch (err) {
      console.error('Error fetching analytics data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const handleTenantChange = () => {
      fetchData();
    };
    window.addEventListener('tenant-changed', handleTenantChange);
    return () => {
      window.removeEventListener('tenant-changed', handleTenantChange);
    };
  }, [activeTenantId]);


  // Category distribution
  const categoryCounts: Record<string, number> = {};
  products.forEach((p) => {
    const cat = p.category || 'General Industrial';
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });

  const categoryChartData = {
    labels: Object.keys(categoryCounts),
    datasets: [
      {
        label: 'Products',
        data: Object.values(categoryCounts),
        backgroundColor: '#3b82f6',
        borderRadius: 4,
      },
    ],
  };

  // Confidence distribution doughnut
  const confidenceChartData = {
    labels: ['HIGH Confidence', 'MEDIUM Confidence', 'LOW Confidence', 'CONFLICT / Discrepancy'],
    datasets: [
      {
        data: [
          summary?.confidence_distribution.HIGH ?? 0,
          summary?.confidence_distribution.MEDIUM ?? 0,
          summary?.confidence_distribution.LOW ?? 0,
          summary?.confidence_distribution.CONFLICT ?? 0,
        ],
        backgroundColor: ['#10b981', '#f59e0b', '#f97316', '#ef4444'],
        borderWidth: 1,
      },
    ],
  };

  // Status distribution
  const statusChartData = {
    labels: ['Verified', 'Needs Review', 'Conflicting', 'Processing', 'Failed'],
    datasets: [
      {
        data: [
          summary?.products.verified ?? 0,
          summary?.products.needs_review ?? 0,
          summary?.products.conflicting ?? 0,
          summary?.products.processing ?? 0,
          summary?.products.failed ?? 0,
        ],
        backgroundColor: ['#059669', '#d97706', '#dc2626', '#2563eb', '#991b1b'],
        borderWidth: 1,
      },
    ],
  };

  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#0f172a' }}>Platform Analytics & Metrics</h1>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '2px' }}>
            Empirical catalog health, confidence distribution, and validation metrics
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Catalog Products</div>
          <div className="stat-value">{summary?.products.total ?? 0}</div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #10b981' }}>
          <div className="stat-label">High Confidence Products</div>
          <div className="stat-value" style={{ color: '#059669' }}>
            {summary?.confidence_distribution.HIGH ?? 0}
          </div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #d97706' }}>
          <div className="stat-label">Unresolved Issues</div>
          <div className="stat-value" style={{ color: '#b45309' }}>
            {summary?.validation.unresolved_issues ?? 0}
          </div>
        </div>
        <div className="stat-card" style={{ borderLeft: '4px solid #2563eb' }}>
          <div className="stat-label">Multi-Agent Pipeline Success</div>
          <div className="stat-value" style={{ color: '#2563eb' }}>
            {summary?.jobs.total ? `${Math.round(((summary?.jobs.completed ?? 0) / summary.jobs.total) * 100)}%` : '100%'}
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Confidence Distribution Doughnut */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Qualitative Confidence Distribution</h3>
          </div>
          <div style={{ maxWidth: '300px', margin: '0 auto', padding: '10px' }}>
            <Doughnut
              data={confidenceChartData}
              options={{
                plugins: {
                  legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                },
              }}
            />
          </div>
        </div>

        {/* Product Status Distribution Doughnut */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Product Validation Status</h3>
          </div>
          <div style={{ maxWidth: '300px', margin: '0 auto', padding: '10px' }}>
            <Doughnut
              data={statusChartData}
              options={{
                plugins: {
                  legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                },
              }}
            />
          </div>
        </div>
      </div>

      {/* Category Breakdown Bar Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Products by Industrial Category</h3>
        </div>
        <div style={{ height: '280px' }}>
          <Bar
            data={categoryChartData}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
              },
              scales: {
                y: {
                  beginAtZero: true,
                  ticks: { stepSize: 1 },
                },
              },
            }}
          />
        </div>
      </div>
    </div>
  );
};
