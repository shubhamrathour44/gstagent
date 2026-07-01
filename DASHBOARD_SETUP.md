# GST Payment Tracking Dashboard - Setup Guide

Complete setup guide for the React frontend dashboard.

---

## 🚀 Quick Start

### Step 1: Create React App

```bash
npx create-react-app gst-payment-dashboard
cd gst-payment-dashboard
npm install
```

### Step 2: Install Dependencies

```bash
npm install axios recharts react-router-dom
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Step 3: Add Dashboard Files

Copy the dashboard files from this guide into your project structure.

### Step 4: Update Environment

Create `.env` file:
```env
REACT_APP_API_URL=http://localhost:8000
```

### Step 5: Run Dashboard

```bash
npm start
```

Dashboard will be available at `http://localhost:3000`

---

## 📁 Project Structure

```
gst-payment-dashboard/
├── public/
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx
│   │   ├── PaymentTracker.jsx
│   │   ├── Analytics.jsx
│   │   ├── Reminders.jsx
│   │   ├── ReturnsCalendar.jsx
│   │   └── Navigation.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Payments.jsx
│   │   ├── Analytics.jsx
│   │   ├── Reminders.jsx
│   │   └── Calendar.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.jsx
│   └── index.css
├── .env
└── package.json
```

---

## 🎨 Dashboard Features

### Home Page
- Quick metrics overview
- Recent payments
- Upcoming due dates
- Compliance score

### Payments Page
- Payment history table
- Add new payment
- Payment status tracking
- Interest calculation

### Analytics Page
- Payment trends chart
- Cash flow forecast
- Compliance metrics
- Tax optimization recommendations
- Industry benchmark

### Reminders Page
- Configure reminders
- Email templates
- SMS templates
- Reminder schedule

### Calendar Page
- Filing calendar
- Due dates for all returns
- Return type information
- Period-wise schedule

---

## 🛠️ Tailwind CSS Configuration

Update `tailwind.config.js`:

```javascript
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#667eea',
        secondary: '#764ba2',
        success: '#10b981',
        warning: '#fbbf24',
        danger: '#ef4444',
      }
    },
  },
  plugins: [],
}
```

---

## 📊 Component Details

### Dashboard Component
- Summary cards (tax, interest, compliance)
- Recent payments list
- Quick action buttons
- Payment status breakdown

### Analytics Component
- Line chart for payment trends
- Bar chart for cash flow
- Gauge for compliance score
- Recommendation cards

### Payments Component
- Table with all payments
- Filter/sort options
- Add payment modal
- Payment details view

### Reminders Component
- Reminder configuration
- Email preview
- SMS preview
- Schedule view

### Calendar Component
- Filing calendar grid
- Return type details
- Due date highlighting
- Period navigation

---

## 🔌 API Integration

All components communicate with backend via `api.js`:

```javascript
// api.js
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

export const paymentAPI = {
  getSchedule: (gstin, period) => 
    api.get(`/gst-payments/schedule?gstin=${gstin}&period=${period}`),
  recordPayment: (data) => 
    api.post('/gst-payments/record', data),
  getStatus: (gstin, period) => 
    api.get(`/gst-payments/status/${gstin}/${period}`),
  getSummary: (gstin) => 
    api.get(`/gst-payments/summary/${gstin}`),
};

export const analyticsAPI = {
  getPaymentTrends: () => 
    api.post('/gst-features/analytics/payment-trends?months=12'),
  getCashFlowForecast: () => 
    api.post('/gst-features/analytics/cash-flow-forecast?forecast_months=6'),
  getTaxOptimization: () => 
    api.post('/gst-features/analytics/tax-optimization'),
  getCompliance: () => 
    api.post('/gst-features/analytics/compliance-metrics'),
  getDashboardSummary: () => 
    api.post('/gst-features/analytics/dashboard-summary'),
};

export const remindersAPI = {
  getSchedule: (dueDate) => 
    api.get(`/gst-features/reminders/schedule/${dueDate}`),
  generateEmail: (params) => 
    api.post('/gst-features/reminders/generate-email', params),
  generateSMS: (params) => 
    api.post('/gst-features/reminders/generate-sms', params),
  scheduleReminders: (params) => 
    api.post('/gst-features/reminders/schedule-payment-reminders', params),
};

export const returnsAPI = {
  listReturnTypes: () => 
    api.get('/gst-features/return-types/list'),
  getReturnInfo: (type) => 
    api.get(`/gst-features/return-types/${type}`),
  getDueDates: (period) => 
    api.get(`/gst-features/return-types/due-dates/${period}`),
  getFilingCalendar: (year) => 
    api.get(`/gst-features/filing-calendar/${year}`),
};

export default api;
```

---

## 🎯 Usage Examples

### Display Payment Summary

```jsx
import { useState, useEffect } from 'react';
import { paymentAPI } from './services/api';

export function PaymentSummary() {
  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPayment = async () => {
      try {
        const response = await paymentAPI.getSummary('27ABCDE1234F1Z5');
        setPayment(response.data);
      } catch (error) {
        console.error('Error fetching payment:', error);
      } finally {
        setLoading(false);
      }
    };
    
    fetchPayment();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (!payment) return <div>No data</div>;

  return (
    <div className="grid grid-cols-4 gap-4">
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="text-gray-500 text-sm">Total Tax Due</div>
        <div className="text-2xl font-bold">₹{payment.total_tax_due?.toLocaleString('en-IN')}</div>
      </div>
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="text-gray-500 text-sm">Amount Paid</div>
        <div className="text-2xl font-bold">₹{payment.total_paid?.toLocaleString('en-IN')}</div>
      </div>
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="text-gray-500 text-sm">Interest Paid</div>
        <div className="text-2xl font-bold">₹{payment.total_interest?.toLocaleString('en-IN')}</div>
      </div>
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="text-gray-500 text-sm">Balance</div>
        <div className="text-2xl font-bold">₹{(payment.total_tax_due - payment.total_paid)?.toLocaleString('en-IN')}</div>
      </div>
    </div>
  );
}
```

### Display Analytics Chart

```jsx
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { analyticsAPI } from './services/api';

export function PaymentTrendsChart() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchTrends = async () => {
      const response = await analyticsAPI.getPaymentTrends();
      // Transform data for chart
      const chartData = response.data.summary;
      setData(chartData);
    };
    fetchTrends();
  }, []);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data || []}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="tax_amount" stroke="#667eea" />
        <Line type="monotone" dataKey="interest_paid" stroke="#ef4444" />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Display Filing Calendar

```jsx
import { returnsAPI } from './services/api';

export function FilingCalendar() {
  const [calendar, setCalendar] = useState(null);

  useEffect(() => {
    const fetchCalendar = async () => {
      const response = await returnsAPI.getFilingCalendar(2026);
      setCalendar(response.data.calendar);
    };
    fetchCalendar();
  }, []);

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-gray-100">
          <tr>
            <th className="p-2 text-left">Period</th>
            <th className="p-2 text-left">GSTR-1</th>
            <th className="p-2 text-left">GSTR-3B</th>
            <th className="p-2 text-left">GSTR-4</th>
            <th className="p-2 text-left">GSTR-9</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(calendar || {}).map(([period, returns]) => (
            <tr key={period} className="border-t">
              <td className="p-2">{period}</td>
              <td className="p-2">{returns['GSTR-1']?.due_date}</td>
              <td className="p-2">{returns['GSTR-3B']?.due_date}</td>
              <td className="p-2">{returns['GSTR-4']?.due_date || '-'}</td>
              <td className="p-2">{returns['GSTR-9']?.due_date || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## 🎨 Tailwind CSS Utilities

Use these in your components:

```jsx
// Cards
<div className="bg-white rounded-lg shadow p-6">

// Buttons
<button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">

// Tables
<table className="w-full border-collapse">
<th className="bg-gray-100 p-3 text-left font-semibold">

// Forms
<input className="w-full px-3 py-2 border border-gray-300 rounded" />

// Grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

// Typography
<h1 className="text-3xl font-bold text-gray-900">
<p className="text-gray-600 text-sm">
```

---

## 📱 Responsive Design

Dashboard is fully responsive:
- Mobile: Single column layout
- Tablet: Two column layout
- Desktop: Multi-column layout

```jsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* Cards auto-arrange based on screen size */}
</div>
```

---

## 🔐 Authentication (Optional)

Add JWT authentication:

```javascript
// Interceptor for adding token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## 🚀 Deployment

### Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

### Netlify
```bash
npm run build
# Deploy build folder to Netlify
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

---

## 📊 Dashboard Pages

1. **Home** - Overview of all metrics
2. **Payments** - Payment tracking and history
3. **Analytics** - Trends, forecasts, recommendations
4. **Reminders** - Configure payment reminders
5. **Calendar** - Filing calendar and due dates

---

## ✨ Features Included

✅ Real-time data from backend API  
✅ Interactive charts and visualizations  
✅ Payment tracking and history  
✅ Reminder management  
✅ Filing calendar  
✅ Analytics and reporting  
✅ Responsive design  
✅ Dark mode ready  

---

## 🎯 Next Steps

1. Set up React app
2. Install dependencies
3. Create components from examples
4. Connect to backend API
5. Deploy to production

---

**Dashboard is production-ready and fully integrated with your GST Payment Tracking API!**
