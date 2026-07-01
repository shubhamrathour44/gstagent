# Quick Start Guide - GST Payment Tracking System

Get the complete system running in under 10 minutes.

---

## ⚡ 5-Minute Backend Start

### Step 1: Start the Server

```bash
cd backend
python -m uvicorn payment_server:app --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

### Step 2: Verify It's Working

Open in browser or curl:
```bash
# Option A: Browser
http://localhost:8000/health

# Option B: Terminal
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "payment-tracking",
  "database": "sqlite"
}
```

---

## 📊 Test All Features (2 minutes)

Run these curl commands to verify all features:

### Test 1: Payment Interest Calculator
```bash
curl "http://localhost:8000/demo/interest-calculator?tax_amount=100000&due_date=2026-05-20&payment_date=2026-06-05"
```
**Expected:** Interest amount: ₹800

### Test 2: GST Return Types
```bash
curl "http://localhost:8000/gst-features/return-types/list"
```
**Expected:** List of all 9 return types (GSTR-1 through GSTR-9)

### Test 3: Filing Calendar
```bash
curl "http://localhost:8000/gst-features/filing-calendar/2026"
```
**Expected:** Full year calendar with all due dates

### Test 4: Payment Trends
```bash
curl -X POST "http://localhost:8000/gst-features/analytics/payment-trends?months=12"
```
**Expected:** Trend analysis with summary statistics

### Test 5: Tax Optimization
```bash
curl -X POST "http://localhost:8000/gst-features/analytics/tax-optimization"
```
**Expected:** Recommendations with savings potential

### Test 6: Cash Flow Forecast
```bash
curl -X POST "http://localhost:8000/gst-features/analytics/cash-flow-forecast?forecast_months=6"
```
**Expected:** 6-month predictions with confidence levels

---

## 🎨 Dashboard Setup (3 minutes)

### Option A: Automated (Recommended)

**Windows:**
```bash
powershell -ExecutionPolicy Bypass -File setup-dashboard.ps1
```

**Linux/Mac:**
```bash
bash setup-dashboard.sh
```

Then:
```bash
cd gst-payment-dashboard
npm start
```

### Option B: Manual

```bash
npx create-react-app gst-payment-dashboard
cd gst-payment-dashboard
npm install axios recharts react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
cp ../DASHBOARD_COMPONENTS.jsx src/App.jsx
npm start
```

**Expected:** Dashboard opens at http://localhost:3000

---

## 🎯 First Look - What You'll See

### Backend (http://localhost:8000)

1. **Home Page** - Health check
2. **Demo Endpoints** - 4 interactive endpoints
3. **15+ Feature Endpoints** - Full GST suite

### Dashboard (http://localhost:3000)

**Home Page**
- 4 metric cards (Tax Due, Interest, Compliance, On-Time Rate)
- Payment trends chart
- Compliance gauge
- Top recommendations

**Payment Tracking**
- Search by GSTIN and period
- Real-time payment status
- Interest calculation
- Payment details

**Analytics**
- Payment trends (12 months)
- Cash flow forecast (6 months)
- Compliance metrics
- Tax optimization recommendations

**Filing Calendar**
- Year-long GST return schedule
- All 9 return types
- Due dates for each period

---

## 🧪 Demo Credentials & Data

### GSTIN (for testing)
```
27ABCDE1234F1Z5
```

### Period Format (MMYYYY)
```
042026 = April 2026
052026 = May 2026
```

### Demo Tax Amounts
```
₹100,000 - Basic example
₹105,000 - Increased amount
₹110,000 - Peak amount
```

---

## ✅ Success Checklist

- [ ] Backend started successfully on port 8000
- [ ] `/health` endpoint returns `healthy`
- [ ] All 6 API test commands return data
- [ ] Dashboard created successfully
- [ ] Dashboard started on port 3000
- [ ] Dashboard loads without errors
- [ ] Can see all 4 pages (Home, Payments, Analytics, Calendar)
- [ ] Charts display correctly
- [ ] Metrics cards show data

---

## 🔧 Troubleshooting

### Port Already in Use

**Port 8000 in use:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows
```

**Port 3000 in use:**
```bash
# Start on different port
PORT=3001 npm start
```

### CORS Error in Dashboard

**Check:**
1. Backend running on http://localhost:8000
2. `.env` has correct `REACT_APP_API_URL`
3. Network tab in DevTools shows correct URL

**Fix:**
```bash
# Restart backend
cd backend
python -m uvicorn payment_server:app --reload
```

### Dependencies Missing

```bash
# Install missing packages
npm install axios recharts
npm install -D tailwindcss postcss autoprefixer
```

### Build Error

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 Next Steps

### Learn the APIs
Read: `FEATURES_EXPANSION_GUIDE.md`
- All 20 endpoints documented
- Request/response examples
- Use cases for each feature

### Customize Dashboard
Edit: `DASHBOARD_COMPONENTS.jsx`
- Add more charts
- Customize colors
- Add new pages

### Connect to Database
Next: Database integration guide
- PostgreSQL setup
- Data persistence
- Real data loading

### Deploy to Production
See: `REACT_DASHBOARD_README.md`
- Vercel deployment
- Docker setup
- Environment configuration

---

## 💡 Tips

1. **Keep both servers running** - Backend on 8000, Frontend on 3000
2. **Check console errors** - DevTools > Console tab
3. **Watch network tab** - DevTools > Network to see API calls
4. **Refresh browser** - Sometimes needed after backend restart
5. **Clear cache** - Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

---

## 📊 Quick API Reference

| Feature | Method | URL | Status |
|---------|--------|-----|--------|
| Health Check | GET | `/health` | ✅ |
| Payment Status | GET | `/demo/payment-status` | ✅ |
| Interest Calculator | GET | `/demo/interest-calculator` | ✅ |
| Return Types | GET | `/gst-features/return-types/list` | ✅ |
| Filing Calendar | GET | `/gst-features/filing-calendar/2026` | ✅ |
| Trends | POST | `/gst-features/analytics/payment-trends` | ✅ |
| Forecast | POST | `/gst-features/analytics/cash-flow-forecast` | ✅ |
| Recommendations | POST | `/gst-features/analytics/tax-optimization` | ✅ |
| Compliance | POST | `/gst-features/analytics/compliance-metrics` | ✅ |
| Dashboard | POST | `/gst-features/analytics/dashboard-summary` | ✅ |

---

## 🎉 You're All Set!

Backend: http://localhost:8000  
Dashboard: http://localhost:3000

Start testing the complete GST Payment Tracking System!

---

**Questions?** Check the detailed guides:
- Backend: `FEATURES_EXPANSION_GUIDE.md`
- Frontend: `REACT_DASHBOARD_README.md`
- Architecture: `PROJECT_SUMMARY.md`
