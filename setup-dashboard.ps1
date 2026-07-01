# GST Payment Tracking Dashboard - Windows Setup Script
# Usage: powershell -ExecutionPolicy Bypass -File setup-dashboard.ps1

Write-Host "════════════════════════════════════════════════════════════════"
Write-Host "  GST Payment Tracking Dashboard - Setup" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════"
Write-Host ""

# Check Node.js
$nodeCheck = node --version 2>$null
if (-not $nodeCheck) {
    Write-Host "❌ Node.js is not installed. Please install Node.js 14+ first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Node.js $nodeCheck found" -ForegroundColor Green
Write-Host ""

# Create React app
Write-Host "📦 Creating React application..." -ForegroundColor Cyan
npx create-react-app gst-payment-dashboard

Set-Location gst-payment-dashboard

# Install dependencies
Write-Host ""
Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
npm install axios recharts react-router-dom

# Install Tailwind
Write-Host ""
Write-Host "🎨 Setting up Tailwind CSS..." -ForegroundColor Cyan
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Copy dashboard components
Write-Host ""
Write-Host "📋 Setting up dashboard components..." -ForegroundColor Cyan
Copy-Item ..\DASHBOARD_COMPONENTS.jsx -Destination src\App.jsx

# Create .env file
Write-Host ""
Write-Host "🔧 Creating .env file..." -ForegroundColor Cyan
@"
REACT_APP_API_URL=http://localhost:8000
"@ | Out-File -FilePath .env -Encoding UTF8

# Create tailwind config
Write-Host ""
Write-Host "🎨 Configuring Tailwind CSS..." -ForegroundColor Cyan
@"
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
"@ | Out-File -FilePath tailwind.config.js -Encoding UTF8

# Update index.css
Write-Host ""
Write-Host "🎨 Updating global styles..." -ForegroundColor Cyan
@"
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto',
    'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans',
    'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
"@ | Out-File -FilePath src\index.css -Encoding UTF8

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════"
Write-Host "  ✅ Setup Complete!" -ForegroundColor Green
Write-Host "════════════════════════════════════════════════════════════════"
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Make sure backend is running:" -ForegroundColor White
Write-Host "     python -m uvicorn backend.payment_server:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Start the dashboard:" -ForegroundColor White
Write-Host "     cd gst-payment-dashboard" -ForegroundColor Gray
Write-Host "     npm start" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Open in browser:" -ForegroundColor White
Write-Host "     http://localhost:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "  - Dashboard Guide: ..\REACT_DASHBOARD_README.md" -ForegroundColor Gray
Write-Host "  - Features API Docs: ..\FEATURES_EXPANSION_GUIDE.md" -ForegroundColor Gray
Write-Host "  - Setup Guide: ..\DASHBOARD_SETUP.md" -ForegroundColor Gray
Write-Host ""
