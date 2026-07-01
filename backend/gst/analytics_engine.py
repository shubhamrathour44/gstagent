"""
Advanced Analytics Engine

Provides:
- Payment trends analysis
- Cash flow forecasting
- Tax optimization recommendations
- GST compliance analytics
- Industry benchmarking
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import statistics


@dataclass
class PaymentTrend:
    """Payment trend data"""
    period: str
    tax_amount: float
    amount_paid: float
    days_late: int
    interest_paid: float
    status: str


@dataclass
class CashFlowForecast:
    """Cash flow forecast"""
    period: str
    forecasted_tax: float
    confidence: float
    trend: str


class AnalyticsEngine:
    """Advanced analytics for GST payments"""

    @staticmethod
    def analyze_payment_trends(
        payments: List[Dict],
        months: int = 12
    ) -> Dict:
        """
        Analyze payment trends over time.

        Args:
            payments: List of payment records
            months: Number of months to analyze

        Returns:
            Trend analysis with insights
        """
        if not payments:
            return {"error": "No payment data available"}

        # Extract trends
        amounts = [p.get("tax_amount", 0) for p in payments]
        days_late_list = [p.get("days_late", 0) for p in payments]
        interest_paid_list = [p.get("interest_paid", 0) for p in payments]

        total_tax = sum(amounts)
        average_tax = total_tax / len(amounts) if amounts else 0
        average_days_late = statistics.mean(days_late_list) if days_late_list else 0
        average_interest = statistics.mean(interest_paid_list) if interest_paid_list else 0

        # Calculate trend direction
        if len(amounts) >= 2:
            recent_avg = statistics.mean(amounts[-3:]) if len(amounts) >= 3 else amounts[-1]
            earlier_avg = statistics.mean(amounts[:3]) if len(amounts) >= 3 else amounts[0]
            trend = "increasing" if recent_avg > earlier_avg else "decreasing"
            trend_percentage = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
        else:
            trend = "stable"
            trend_percentage = 0

        # On-time payment rate
        on_time_count = sum(1 for d in days_late_list if d <= 0)
        on_time_rate = (on_time_count / len(days_late_list) * 100) if days_late_list else 0

        return {
            "period_analyzed": f"Last {months} months",
            "summary": {
                "total_tax_due": total_tax,
                "average_monthly": average_tax,
                "total_interest_paid": sum(interest_paid_list),
                "average_days_late": round(average_days_late, 1),
                "on_time_payment_rate": round(on_time_rate, 1)
            },
            "trend": {
                "direction": trend,
                "percentage_change": round(trend_percentage, 1),
                "insight": f"Tax liability is {trend} by {abs(round(trend_percentage, 1))}%"
            },
            "payment_behavior": {
                "average_days_late": round(average_days_late, 1),
                "average_interest_per_month": round(average_interest, 0),
                "monthly_payments_on_time": on_time_count,
                "monthly_payments_late": len(days_late_list) - on_time_count
            }
        }

    @staticmethod
    def forecast_cash_flow(
        historical_payments: List[Dict],
        forecast_months: int = 6
    ) -> Dict:
        """
        Forecast future cash flow requirements.

        Args:
            historical_payments: Historical payment data
            forecast_months: Months to forecast

        Returns:
            Cash flow forecast
        """
        if not historical_payments:
            return {"error": "No historical data available"}

        amounts = [p.get("tax_amount", 0) for p in historical_payments]

        # Calculate statistics
        avg_amount = statistics.mean(amounts)
        std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0

        # Generate forecast
        forecasts = []
        current_date = datetime.now()

        for month in range(1, forecast_months + 1):
            forecast_date = current_date + timedelta(days=30 * month)

            # Simple forecast (can be enhanced with machine learning)
            forecasted_tax = avg_amount
            confidence = 85 - (month * 2)  # Confidence decreases further out
            trend = "stable" if std_dev < avg_amount * 0.2 else "volatile"

            forecasts.append({
                "month": month,
                "date": forecast_date.strftime("%Y-%m-%d"),
                "forecasted_tax": round(forecasted_tax, 0),
                "confidence": max(50, confidence),  # Min 50% confidence
                "trend": trend,
                "estimated_interest_if_late_15_days": round(forecasted_tax * 0.0005 * 15, 0)
            })

        # Summary forecast
        total_forecasted = sum(f["forecasted_tax"] for f in forecasts)
        cash_required = round(total_forecasted, 0)

        return {
            "forecast_period": f"Next {forecast_months} months",
            "forecasts": forecasts,
            "summary": {
                "total_tax_forecasted": cash_required,
                "average_monthly": round(cash_required / forecast_months, 0),
                "peak_month": max(forecasts, key=lambda x: x["forecasted_tax"]),
                "minimum_cash_buffer": round(max(f["forecasted_tax"] for f in forecasts) * 1.1, 0)
            }
        }

    @staticmethod
    def get_tax_optimization_recommendations(
        payments: List[Dict]
    ) -> Dict:
        """
        Get recommendations to optimize tax payments and reduce interest.

        Args:
            payments: Payment history

        Returns:
            Optimization recommendations
        """
        if not payments:
            return {"error": "No payment data available"}

        days_late_list = [p.get("days_late", 0) for p in payments]
        interest_list = [p.get("interest_paid", 0) for p in payments]

        total_interest = sum(interest_list)
        average_days_late = statistics.mean(days_late_list) if days_late_list else 0

        recommendations = []

        # Recommendation 1: On-time payment
        if average_days_late > 0:
            potential_savings = total_interest
            recommendations.append({
                "priority": "HIGH",
                "recommendation": "Pay GST on or before due date",
                "current_issue": f"Average {round(average_days_late, 1)} days late",
                "potential_savings": round(potential_savings, 0),
                "action": "Set payment reminders 7 days before due date",
                "impact": "Eliminate 18% interest charges completely"
            })

        # Recommendation 2: Partial payments
        if average_days_late > 10:
            potential_savings = round(total_interest * 0.5, 0)
            recommendations.append({
                "priority": "HIGH",
                "recommendation": "Make partial payments early in the month",
                "current_issue": f"Paying {round(average_days_late, 1)} days late causes high interest",
                "potential_savings": potential_savings,
                "action": "Pay 50% of estimated tax by 15th, balance by 20th",
                "impact": "Reduce average days late to <5 days"
            })

        # Recommendation 3: Cash flow planning
        if len(payments) >= 3:
            amount_variance = statistics.stdev([p.get("tax_amount", 0) for p in payments[-3:]])
            if amount_variance > 0:
                recommendations.append({
                    "priority": "MEDIUM",
                    "recommendation": "Implement monthly cash flow forecasting",
                    "current_issue": "Irregular payment patterns may indicate cash flow issues",
                    "action": "Forecast next 6 months of tax liability",
                    "impact": "Better budgeting and payment planning"
                })

        # Recommendation 4: GST liability reduction
        recommendations.append({
            "priority": "MEDIUM",
            "recommendation": "Audit GST liability to identify optimization opportunities",
            "current_issue": f"Total interest paid: ₹{round(total_interest, 0)}",
            "action": "Review input tax credit claims and supply documentation",
            "impact": "Reduce tax liability through legitimate claims"
        })

        return {
            "analysis_period": f"{len(payments)} months",
            "total_interest_paid": round(total_interest, 0),
            "recommendations": recommendations,
            "estimated_annual_savings": round(total_interest / len(payments) * 12 * 0.5, 0)
        }

    @staticmethod
    def get_compliance_analytics(
        payments: List[Dict]
    ) -> Dict:
        """
        Analyze GST compliance metrics.

        Args:
            payments: Payment records

        Returns:
            Compliance analytics
        """
        if not payments:
            return {"error": "No payment data available"}

        # Calculate compliance metrics
        on_time = sum(1 for p in payments if p.get("days_late", 0) <= 0)
        late = len(payments) - on_time

        compliance_rate = (on_time / len(payments) * 100) if payments else 0

        # Categorize compliance
        if compliance_rate >= 95:
            compliance_status = "EXCELLENT"
            compliance_level = "A+"
        elif compliance_rate >= 80:
            compliance_status = "GOOD"
            compliance_level = "A"
        elif compliance_rate >= 60:
            compliance_status = "AVERAGE"
            compliance_level = "B"
        else:
            compliance_status = "POOR"
            compliance_level = "C"

        return {
            "compliance_score": round(compliance_rate, 1),
            "compliance_level": compliance_level,
            "compliance_status": compliance_status,
            "metrics": {
                "on_time_filings": on_time,
                "late_filings": late,
                "total_filings": len(payments),
                "on_time_rate_percentage": round(compliance_rate, 1),
                "late_rate_percentage": round(100 - compliance_rate, 1)
            },
            "risk_assessment": {
                "audit_risk": "LOW" if compliance_rate >= 95 else "MEDIUM" if compliance_rate >= 80 else "HIGH",
                "penalty_risk": "LOW" if compliance_rate >= 90 else "MEDIUM",
                "recommended_action": "Continue current practice" if compliance_rate >= 95 else "Improve payment timeliness"
            }
        }

    @staticmethod
    def get_industry_benchmark(
        user_tax_amount: float,
        business_type: str = "B2B",
        state: str = "National"
    ) -> Dict:
        """
        Compare with industry benchmarks.

        Args:
            user_tax_amount: User's monthly tax amount
            business_type: Type of business (B2B, B2C, etc)
            state: State for regional comparison

        Returns:
            Benchmark comparison
        """
        # Industry benchmarks (example data)
        benchmarks = {
            "B2B": {
                "small": 50000,      # < 1Cr turnover
                "medium": 500000,    # 1-10Cr turnover
                "large": 2000000     # > 10Cr turnover
            },
            "B2C": {
                "small": 25000,
                "medium": 250000,
                "large": 1000000
            }
        }

        # Categorize user
        if user_tax_amount < 100000:
            user_category = "small"
            benchmark = benchmarks.get(business_type, benchmarks["B2B"])["small"]
        elif user_tax_amount < 1000000:
            user_category = "medium"
            benchmark = benchmarks.get(business_type, benchmarks["B2B"])["medium"]
        else:
            user_category = "large"
            benchmark = benchmarks.get(business_type, benchmarks["B2B"])["large"]

        percentile = (user_tax_amount / benchmark * 100) if benchmark > 0 else 0

        return {
            "user_analysis": {
                "monthly_tax": round(user_tax_amount, 0),
                "business_type": business_type,
                "category": user_category,
                "percentile": round(percentile, 1)
            },
            "benchmark": {
                "category_benchmark": round(benchmark, 0),
                "comparison": "above_average" if percentile > 100 else "below_average",
                "vs_benchmark_percentage": round(percentile - 100, 1)
            },
            "insights": {
                "your_position": f"In the {user_category} business category for {business_type}",
                "relative_to_industry": f"{'Higher' if percentile > 100 else 'Lower'} than industry average by {abs(round(percentile - 100, 1))}%",
                "implication": "Consider tax planning" if percentile > 150 else "Normal tax liability"
            }
        }

    @staticmethod
    def get_dashboard_summary(
        payments: List[Dict],
        forecast_data: Dict = None
    ) -> Dict:
        """
        Get complete dashboard summary for a quick overview.

        Args:
            payments: Payment records
            forecast_data: Forecast data (optional)

        Returns:
            Dashboard summary
        """
        if not payments:
            return {"error": "No data available"}

        # Get all analytics
        trends = AnalyticsEngine.analyze_payment_trends(payments)
        compliance = AnalyticsEngine.get_compliance_analytics(payments)
        recommendations = AnalyticsEngine.get_tax_optimization_recommendations(payments)

        return {
            "summary": {
                "total_tax_due": trends["summary"]["total_tax_due"],
                "total_interest_paid": trends["summary"]["total_interest_paid"],
                "compliance_score": compliance["compliance_score"],
                "on_time_rate": f"{compliance['metrics']['on_time_rate_percentage']}%"
            },
            "key_metrics": {
                "average_monthly_tax": round(trends["summary"]["average_monthly"], 0),
                "average_days_late": trends["summary"]["average_days_late"],
                "average_interest_cost": round(trends["summary"]["average_monthly"] * 0.0005 * trends["summary"]["average_days_late"], 0) if trends["summary"]["average_days_late"] > 0 else 0
            },
            "health_status": compliance["compliance_status"],
            "top_recommendation": recommendations["recommendations"][0] if recommendations["recommendations"] else None,
            "estimated_savings": recommendations["estimated_annual_savings"]
        }
