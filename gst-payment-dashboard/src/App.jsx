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

  // ITR API
  getITRTypes() {
    return this.request('/itr-features/return-types/list');
  }

  getITRFilingCalendar(financialYear) {
    return this.request(`/itr-features/filing-calendar/${financialYear}`);
  }

  getITRDueDates(financialYear) {
    return this.request(`/itr-features/due-dates/${financialYear}`);
  }

  calculateITRPenalty(amount, daysLate) {
    return this.request(
      `/itr-features/penalty-calculator?amount=${amount}&days_late=${daysLate}`,
      { method: 'POST' }
    );
  }

  getApplicableITRs(incomeSources, entityType) {
    const sources = incomeSources.map(s => `income_sources=${s}`).join('&');
    return this.request(
      `/itr-features/applicable-itrs?${sources}&entity_type=${entityType}`,
      { method: 'POST' }
    );
  }

  getITRChecklist(returnType) {
    return this.request(`/itr-features/filing-checklist/${returnType}`);
  }

  getITRFeaturesStatus() {
    return this.request('/itr-features/features-status');
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
// ITR FILING CALENDAR PAGE
// ═══════════════════════════════════════════════════════════════════════════

function ITRFilingCalendarPage() {
  const [year, setYear] = useState(2026);
  const [calendar, setCalendar] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadCalendar();
  }, [year]);

  async function loadCalendar() {
    setLoading(true);
    const data = await api.getITRFilingCalendar(year);
    if (data) {
      setCalendar(data.calendar);
    }
    setLoading(false);
  }

  if (loading) return <div className="text-center py-8">Loading...</div>;

  const fy = `FY ${year - 1}-${year}`;
  const fyCalendar = calendar?.[fy] || {};

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">ITR Filing Calendar</h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setYear(year - 1)}
              className="px-3 py-2 bg-gray-100 rounded hover:bg-gray-200"
            >
              ← Previous
            </button>
            <span className="px-4 py-2 font-semibold">{fy}</span>
            <button
              onClick={() => setYear(year + 1)}
              className="px-3 py-2 bg-gray-100 rounded hover:bg-gray-200"
            >
              Next →
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">ITR Type</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Name</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Due Date</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">For</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {Object.entries(fyCalendar).map(([itrCode, details]) => {
                const daysUntilDue = Math.ceil((new Date(details.due_date) - new Date()) / (1000 * 60 * 60 * 24));
                const isDue = daysUntilDue <= 7 && daysUntilDue > 0;
                const isOverdue = daysUntilDue <= 0;

                return (
                  <tr key={itrCode} className="hover:bg-gray-50">
                    <td className="px-6 py-4"><span className="font-semibold">{details.return_type}</span></td>
                    <td className="px-6 py-4 text-sm text-gray-600">{details.name}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <span>{details.due_date}</span>
                        {isDue && <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">Due Soon</span>}
                        {isOverdue && <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">Overdue</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{details.applicable_to}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded border border-blue-200">
          <h3 className="font-semibold text-blue-900 mb-2">ITR Filing Deadlines for {fy}</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• ITR-1, ITR-2: <strong>31 July {year}</strong> (Salary, Capital Gains)</li>
            <li>• ITR-3, ITR-4, ITR-5, ITR-6, ITR-7: <strong>30 September {year}</strong> (Business, Partnerships, Companies)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ITR TRACKER PAGE
// ═══════════════════════════════════════════════════════════════════════════

function ITRTrackerPage() {
  const [entityType, setEntityType] = useState('individual');
  const [incomeSources, setIncomeSources] = useState(['salary']);
  const [applicableITRs, setApplicableITRs] = useState([]);
  const [selectedITR, setSelectedITR] = useState(null);
  const [checklist, setChecklist] = useState(null);
  const [loading, setLoading] = useState(false);

  const incomeOptions = {
    individual: ['salary', 'pension', 'house_property', 'capital_gains', 'business', 'profession'],
    partnership: ['business'],
    company: ['corporate'],
    trust: ['trust_income']
  };

  async function findApplicableITRs() {
    setLoading(true);
    const data = await api.getApplicableITRs(incomeSources, entityType);
    setApplicableITRs(data?.applicable_itrs || []);
    setSelectedITR(null);
    setLoading(false);
  }

  async function loadChecklist(itrType) {
    setLoading(true);
    const data = await api.getITRChecklist(itrType);
    setChecklist(data);
    setLoading(false);
  }

  const handleSelectITR = (itr) => {
    setSelectedITR(itr);
    loadChecklist(itr);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">ITR Finder</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Entity Type</label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded"
            >
              <option value="individual">Individual</option>
              <option value="partnership">Partnership</option>
              <option value="company">Company</option>
              <option value="trust">Trust/NGO</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Income Sources</label>
          <div className="space-y-2">
            {incomeOptions[entityType].map((source) => (
              <label key={source} className="flex items-center">
                <input
                  type="checkbox"
                  checked={incomeSources.includes(source)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setIncomeSources([...incomeSources, source]);
                    } else {
                      setIncomeSources(incomeSources.filter(s => s !== source));
                    }
                  }}
                  className="mr-2"
                />
                <span className="text-gray-700 capitalize">{source.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={findApplicableITRs}
          disabled={loading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Find Applicable ITRs
        </button>
      </div>

      {applicableITRs.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Recommended ITRs</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {applicableITRs.map((itr) => (
              <button
                key={itr}
                onClick={() => handleSelectITR(itr)}
                className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                  selectedITR === itr
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-blue-300'
                }`}
              >
                <div className="font-bold text-lg">{itr}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {checklist && selectedITR && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold text-gray-900 mb-4">{selectedITR} - Required Documents</h3>
          <ul className="space-y-2">
            {checklist.documents_required?.map((doc, idx) => (
              <li key={idx} className="flex items-center space-x-2">
                <span className="text-green-600">✓</span>
                <span className="text-gray-700">{doc}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
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
          <div className="flex flex-wrap space-x-2 gap-2">
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
              📅 GST Calendar
            </NavButton>
            <NavButton active={currentPage === 'itr-calendar'} onClick={() => setCurrentPage('itr-calendar')}>
              📋 ITR Calendar
            </NavButton>
            <NavButton active={currentPage === 'itr-tracker'} onClick={() => setCurrentPage('itr-tracker')}>
              📌 ITR Tracker
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
        {currentPage === 'itr-calendar' && <ITRFilingCalendarPage />}
        {currentPage === 'itr-tracker' && <ITRTrackerPage />}
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
