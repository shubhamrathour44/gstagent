#!/bin/bash

# GST Payment Tracking Dashboard - One Command Setup
# Usage: bash setup-dashboard.sh

set -e

echo "════════════════════════════════════════════════════════════════"
echo "  GST Payment Tracking Dashboard - Setup"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 14+ first."
    exit 1
fi

echo "✅ Node.js $(node --version) found"

# Create React app
echo ""
echo "📦 Creating React application..."
npx create-react-app gst-payment-dashboard

cd gst-payment-dashboard

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install axios recharts react-router-dom

# Install Tailwind
echo ""
echo "🎨 Setting up Tailwind CSS..."
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Copy dashboard components
echo ""
echo "📋 Setting up dashboard components..."
cp ../DASHBOARD_COMPONENTS.jsx src/App.jsx

# Create .env file
echo ""
echo "🔧 Creating .env file..."
cat > .env << 'EOF'
REACT_APP_API_URL=http://localhost:8000
EOF

# Create tailwind config
echo ""
echo "🎨 Configuring Tailwind CSS..."
cat > tailwind.config.js << 'EOF'
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
EOF

# Update index.css
echo ""
echo "🎨 Updating global styles..."
cat > src/index.css << 'EOF'
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
EOF

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  ✅ Setup Complete!"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📝 Next Steps:"
echo "  1. Make sure backend is running:"
echo "     python -m uvicorn backend.payment_server:app --reload"
echo ""
echo "  2. Start the dashboard:"
echo "     cd gst-payment-dashboard"
echo "     npm start"
echo ""
echo "  3. Open in browser:"
echo "     http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "  - Dashboard Guide: ../REACT_DASHBOARD_README.md"
echo "  - Features API Docs: ../FEATURES_EXPANSION_GUIDE.md"
echo "  - Setup Guide: ../DASHBOARD_SETUP.md"
echo ""
