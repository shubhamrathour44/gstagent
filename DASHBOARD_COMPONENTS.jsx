/**
 * GST Payment Tracking Dashboard - Complete React Components
 *
 * Usage: Copy these components into your React project
 * Install dependencies: npm install axios recharts react-router-dom
 */

import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, GaugeChart
} from 'recharts';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// ═══════════════════════════════════════════════════════════════════════════
// API SERVICE
// ═══════════════════════════════════════════════════════════════════════════

class APIService {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options
      });
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      return null;
    }
  }

  // Payment API
  getPaymentSchedule(gstin, period) {
    return this.request(`/gst-payments/schedule?gstin=${gstin}&period=${period}`);
  }

  getPaymentStatus(gstin, period) {
    return this.request(`/gst-payments/status/${gstin}/${period}`);
  }

  getPaymentSummary(gstin) {
    return this.request(`/gst-payments/summary/${gstin}`);
  }

  // Analytics API
  getPaymentTrends() {
    return this.request('/gst-features/analytics/payment-trends?months=12', { method: 'POST' });
  }

  getCashFlowForecast() {
    return this.request('/gst-features/analytics/cash-flow-forecast?forecast_months=6', { method: 'POST' });
  }

  getTaxOptimization() {
    return this.request('/gst-features/analytics/tax-optimization', { method: 'POST' });
  }

  getCompliance() {
    return this.request('/gst-features/analytics/compliance-metrics', { method: 'POST' });
  }

  getDashboardSummary() {
    return this.request('/gst-features/analytics/dashboard-summary', { method: 'POST' });
  }

  // Returns API
  getFilingCalendar(year) {
    return this.request(`/gst-features/filing-calendar/${year}`);
  }

  getReturnTypes() {
    return this.request('/gst-features/return-types/list');
  }

  // Reminders API
  getReminderSchedule(dueDate) {
    return this.request(`/gst-features/reminders/schedule/${dueDate}`);
  }

  generateEmailReminder(params) {
    return this.request(`/gst-features/reminders/generate-email?${new URLSearchParams(params).toString()}`, { method: 'POST' });
  }
}

const api = new APIService(API_BASE_URL);

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD HOME PAGE
// ═══════════════════════════════════════════════════════════════════════════

export function DashboardHome() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDashboardSummary().then(data => {
      setSummary(data);
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingSpinner />;
  if (!summary) return <ErrorMessage message="Failed to load dashboard" />;

  const { summary: s, key_metrics: metrics } = summary;

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard
          title="Total Tax Due"
          value={`₹${s?.total_tax_due?.toLocaleString('en-IN') || '0'}`}
          icon="💰"
          color="bg-blue-500"
        />
        <MetricCard
          title="Interest Paid"
          value={`₹${s?.total_interest_paid?.toLocaleString('en-IN') || '0'}`}
          icon="📈"
          color="bg-red-500"
        />
        <MetricCard
          title="Compliance Score"
          value={`${s?.compliance_score || '0'}%`}
          icon="✅"
          color="bg-green-500"
        />
        <MetricCard
          title="On-Time Rate"
          value={s?.on_time_rate || '0%'}
          icon="⏱️"
          color="bg-purple-500"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PaymentTrendsChart />
        <ComplianceGauge score={s?.compliance_score || 0} />
      </div>

      {/* Recommendations */}
      <RecommendationsCard />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ANALYTICS PAGE
// ═══════════════════════════════════════════════════════════════════════════

export function AnalyticsPage() {
  const [trends, setTrends] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [optimization, setOptimization] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getPaymentTrends(),
      api.getCashFlowForecast(),
      api.getCompliance(),
      api.getTaxOptimization()
    ]).then(([t, f, c, o]) => {
      setTrends(t);
      setForecast(f);
      setCompliance(c);
      setOptimization(o);
      setLoading(false);
    });
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Analytics & Insights</h1>

      {/* Payment Trends */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Payment Trends</h2>
        {trends?.summary && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-50 p-4 rounded">
              <div className="text-sm text-gray-600">Total Tax Due</div>
              <div className="text-2xl font-bold">₹{trends.summary.total_tax_due?.toLocaleString('en-IN')}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <div className="text-sm text-gray-600">Average Monthly</div>
              <div className="text-2xl font-bold">₹{trends.summary.average_monthly?.toLocaleString('en-IN')}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <div className="text-sm text-gray-600">Avg Days Late</div>
              <div className="text-2xl font-bold">{trends.summary.average_days_late?.toFixed(1)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Cash Flow Forecast */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">6-Month Cash Flow Forecast</h2>
        {forecast?.forecasts && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="p-2 text-left">Month</th>
                  <th className="p-2 text-left">Forecasted Tax</th>
                  <th className="p-2 text-left">Confidence</th>
                  <th className="p-2 text-left">Interest (if 15d late)</th>
                </tr>
              </thead>
              <tbody>
                {forecast.forecasts.map((f, i) => (
                  <tr key={i} className="border-t">
                    <td className="p-2">{f.date}</td>
                    <td className="p-2">₹{f.forecasted_tax?.toLocaleString('en-IN')}</td>
                    <td className="p-2">{f.confidence}%</td>
                    <td className="p-2">₹{f.estimated_interest_if_late_15_days?.toLocaleString('en-IN')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Compliance Metrics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Compliance Metrics</h2>
        {compliance && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-600">Compliance Score</div>
              <div className="text-3xl font-bold text-green-600">{compliance.compliance_score?.toFixed(1)}%</div>
              <div className="text-sm text-gray-600 mt-2">Level: {compliance.compliance_level}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Metrics</div>
              <div className="space-y-2 mt-2">
                <div className="flex justify-between">
                  <span>On-Time Filings:</span>
                  <span className="font-bold">{compliance.metrics?.on_time_filings || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Late Filings:</span>
                  <span className="font-bold">{compliance.metrics?.late_filings || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Audit Risk:</span>
                  <span className="font-bold text-green-600">{compliance.risk_assessment?.audit_risk}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Tax Optimization */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Tax Optimization</h2>
        {optimization?.recommendations && (
          <div className="space-y-4">
            {optimization.recommendations.slice(0, 3).map((rec, i) => (
              <div key={i} className="border-l-4 border-blue-500 pl-4 py-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold text-lg">{rec.recommendation}</div>
                    <div className="text-sm text-gray-600">{rec.current_issue}</div>
                    <div className="text-sm text-green-600 mt-1">💰 Save: ₹{rec.potential_savings?.toLocaleString('en-IN')}</div>
                  </div>
                  <span className={`px-3 py-1 rounded text-white text-xs font-bold ${
                    rec.priority === 'HIGH' ? 'bg-red-500' : 'bg-yellow-500'
                  }`}>
                    {rec.priority}
                  </span>
                </div>
              </div>
            ))}
            <div className="mt-4 p-4 bg-green-50 rounded">
              <div className="text-sm text-green-800">
                <strong>Estimated Annual Savings:</strong> ₹{optimization.estimated_annual_savings?.toLocaleString('en-IN')}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// PAYMENT TRACKING PAGE
// ═══════════════════════════════════════════════════════════════════════════

export function PaymentTrackingPage() {
  const [gstin] = useState('27ABCDE1234F1Z5');
  const [period, setPeriod] = useState('042026');
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleFetch = async () => {
    setLoading(true);
    const data = await api.getPaymentStatus(gstin, period);
    setPayment(data);
    setLoading(false);
  };

  useEffect(() => {
    handleFetch();
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Payment Tracking</h1>

      {/* Search */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">GSTIN</label>
            <input type="text" value={gstin} className="w-full px-3 py-2 border rounded" disabled />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Period (MMYYYY)</label>
            <input type="text" value={period} onChange={(e) => setPeriod(e.target.value)} className="w-full px-3 py-2 border rounded" />
          </div>
          <div className="flex items-end">
            <button onClick={handleFetch} className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
              Fetch
            </button>
          </div>
        </div>
      </div>

      {/* Payment Details */}
      {payment && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Payment Status</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Tax Payable:</span>
                <span className="font-bold">₹{payment.tax_payable?.toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Amount Paid:</span>
                <span className="font-bold">₹{payment.amount_paid?.toLocaleString('en-IN')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Balance:</span>
                <span className="font-bold">₹{payment.balance?.toLocaleString('en-IN')}</span>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Due Date:</span>
                <span className="font-bold">{payment.due_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Days Overdue:</span>
                <span className="font-bold">{payment.days_overdue}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className={`font-bold px-2 py-1 rounded text-white ${
                  payment.status === 'paid' ? 'bg-green-500' : 'bg-red-500'
                }`}>
                  {payment.status?.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          {payment.interest && (
            <div className="mt-6 p-4 bg-yellow-50 rounded border border-yellow-200">
              <div className="font-bold text-yellow-900 mb-2">Interest Calculation</div>
              <div className="space-y-1 text-sm text-yellow-800">
                <div>Rate: {payment.interest.rate}</div>
                <div>Period: {payment.interest.calculation_period}</div>
                <div className="font-bold mt-2">Interest Amount: ₹{payment.interest.amount?.toLocaleString('en-IN')}</div>
                <div className="font-bold text-lg mt-2">Total Due: ₹{payment.total_due?.toLocaleString('en-IN')}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// FILING CALENDAR PAGE
// ═══════════════════════════════════════════════════════════════════════════

export function FilingCalendarPage() {
  const [calendar, setCalendar] = useState(null);
  const [year] = useState(2026);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getFilingCalendar(year).then(data => {
      setCalendar(data?.calendar);
      setLoading(false);
    });
  }, [year]);

  if (loading) return <LoadingSpinner />;
  if (!calendar) return <ErrorMessage message="Failed to load calendar" />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Filing Calendar {year}</h1>

      <div className="bg-white rounded-lg shadow p-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="p-3 text-left font-semibold">Period</th>
              <th className="p-3 text-left font-semibold">GSTR-1</th>
              <th className="p-3 text-left font-semibold">GSTR-3B</th>
              <th className="p-3 text-left font-semibold">GSTR-4</th>
              <th className="p-3 text-left font-semibold">GSTR-9</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(calendar).map(([period, returns]) => (
              <tr key={period} className="border-t hover:bg-gray-50">
                <td className="p-3 font-medium">{period}</td>
                <td className="p-3">{returns['GSTR-1']?.due_date || '-'}</td>
                <td className="p-3">{returns['GSTR-3B']?.due_date || '-'}</td>
                <td className="p-3">{returns['GSTR-4']?.due_date || '-'}</td>
                <td className="p-3">{returns['GSTR-9']?.due_date || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// REUSABLE COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════

function MetricCard({ title, value, icon, color }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-gray-600 text-sm">{title}</div>
          <div className="text-3xl font-bold mt-2">{value}</div>
        </div>
        <div className="text-4xl">{icon}</div>
      </div>
    </div>
  );
}

function PaymentTrendsChart() {
  const [data, setData] = useState([
    { month: 'Apr', tax: 100000, interest: 250 },
    { month: 'May', tax: 105000, interest: 525 },
    { month: 'Jun', tax: 95000, interest: 0 },
    { month: 'Jul', tax: 110000, interest: 825 },
  ]);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Payment Trends</h2>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="tax" stroke="#667eea" name="Tax Amount" />
          <Line type="monotone" dataKey="interest" stroke="#ef4444" name="Interest" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ComplianceGauge({ score }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Compliance Score</h2>
      <div className="flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl font-bold text-green-600">{score?.toFixed(1)}%</div>
          <div className="text-gray-600 mt-2">
            {score >= 95 ? 'Excellent' : score >= 80 ? 'Good' : 'Average'}
          </div>
        </div>
      </div>
    </div>
  );
}

function RecommendationsCard() {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Top Recommendations</h2>
      <div className="space-y-3">
        <div className="border-l-4 border-blue-500 pl-4 py-2">
          <div className="font-bold">Pay on time to eliminate interest</div>
          <div className="text-sm text-gray-600">Setting reminders 7 days before due date</div>
        </div>
        <div className="border-l-4 border-blue-500 pl-4 py-2">
          <div className="font-bold">Improve cash flow planning</div>
          <div className="text-sm text-gray-600">Forecast next 6 months using analytics</div>
        </div>
        <div className="border-l-4 border-blue-500 pl-4 py-2">
          <div className="font-bold">Review tax liability</div>
          <div className="text-sm text-gray-600">Audit GST returns for optimization opportunities</div>
        </div>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-gray-600">Loading...</div>
    </div>
  );
}

function ErrorMessage({ message }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
      {message}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN APP COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export function App() {
  const [currentPage, setCurrentPage] = useState('home');

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Navigation */}
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">GST Payment Tracking</h1>
          </div>
          <div className="flex space-x-4">
            <NavButton active={currentPage === 'home'} onClick={() => setCurrentPage('home')}>
              📊 Home
            </NavButton>
            <NavButton active={currentPage === 'payments'} onClick={() => setCurrentPage('payments')}>
              💳 Payments
            </NavButton>
            <NavButton active={currentPage === 'analytics'} onClick={() => setCurrentPage('analytics')}>
              📈 Analytics
            </NavButton>
            <NavButton active={currentPage === 'calendar'} onClick={() => setCurrentPage('calendar')}>
              📅 Calendar
            </NavButton>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {currentPage === 'home' && <DashboardHome />}
        {currentPage === 'payments' && <PaymentTrackingPage />}
        {currentPage === 'analytics' && <AnalyticsPage />}
        {currentPage === 'calendar' && <FilingCalendarPage />}
      </div>
    </div>
  );
}

function NavButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
    >
      {children}
    </button>
  );
}

export default App;
