import React, { useState } from 'react';

export default function ITR3Form({ client, onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    pan: client.pan || '',
    financial_year: 2026,
    business: {
      gross_receipts: 0,
      cost_of_goods_sold: 0,
      operating_expenses: [],
    },
    salary_income: 0,
    house_property_income: 0,
    other_income: 0,
    tds_deducted: 0,
  });

  const [expenseInput, setExpenseInput] = useState({ expense_type: 'Salary', amount: 0 });

  const addExpense = () => {
    if (expenseInput.amount > 0) {
      setFormData({
        ...formData,
        business: {
          ...formData.business,
          operating_expenses: [...formData.business.operating_expenses, expenseInput],
        },
      });
      setExpenseInput({ expense_type: 'Salary', amount: 0 });
    }
  };

  const removeExpense = (index) => {
    setFormData({
      ...formData,
      business: {
        ...formData.business,
        operating_expenses: formData.business.operating_expenses.filter((_, i) => i !== index),
      },
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const calculateNetProfit = () => {
    const grossProfit = formData.business.gross_receipts - formData.business.cost_of_goods_sold;
    const totalExpenses = formData.business.operating_expenses.reduce((sum, exp) => sum + exp.amount, 0);
    return grossProfit - totalExpenses;
  };

  const totalExpenses = formData.business.operating_expenses.reduce((sum, exp) => sum + exp.amount, 0);

  return (
    <form onSubmit={handleSubmit} className="itr-form">
      <h3>ITR-3 - Income Tax Return for Business Owners</h3>

      <div className="form-section">
        <h4>Personal Information</h4>
        <div className="form-row">
          <div className="form-group">
            <label>PAN *</label>
            <input type="text" value={formData.pan} onChange={(e) => setFormData({ ...formData, pan: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Financial Year</label>
            <select value={formData.financial_year} onChange={(e) => setFormData({ ...formData, financial_year: parseInt(e.target.value) })}>
              <option value={2024}>2024-25</option>
              <option value={2025}>2025-26</option>
              <option value={2026}>2026-27</option>
            </select>
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>Business Income</h4>
        <div className="form-row">
          <div className="form-group">
            <label>Gross Receipts (₹) *</label>
            <input
              type="number"
              value={formData.business.gross_receipts}
              onChange={(e) => setFormData({ ...formData, business: { ...formData.business, gross_receipts: parseFloat(e.target.value) || 0 } })}
              required
            />
          </div>
          <div className="form-group">
            <label>Cost of Goods Sold (₹)</label>
            <input
              type="number"
              value={formData.business.cost_of_goods_sold}
              onChange={(e) => setFormData({ ...formData, business: { ...formData.business, cost_of_goods_sold: parseFloat(e.target.value) || 0 } })}
            />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>Operating Expenses</h4>
        {formData.business.operating_expenses.length > 0 && (
          <div className="expenses-list">
            {formData.business.operating_expenses.map((exp, idx) => (
              <div key={idx} className="expense-item">
                <span>
                  {exp.expense_type}: ₹{exp.amount.toLocaleString()}
                </span>
                <button type="button" className="btn btn-small btn-danger" onClick={() => removeExpense(idx)}>
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="add-expense">
          <select value={expenseInput.expense_type} onChange={(e) => setExpenseInput({ ...expenseInput, expense_type: e.target.value })}>
            <option>Salary</option>
            <option>Rent</option>
            <option>Utilities</option>
            <option>Depreciation</option>
            <option>Supplies</option>
            <option>Other</option>
          </select>
          <input type="number" placeholder="Amount" value={expenseInput.amount} onChange={(e) => setExpenseInput({ ...expenseInput, amount: parseFloat(e.target.value) || 0 })} />
          <button type="button" className="btn btn-secondary" onClick={addExpense}>
            Add Expense
          </button>
        </div>
      </div>

      <div className="form-section">
        <h4>Other Income Sources</h4>
        <div className="form-row">
          <div className="form-group">
            <label>Salary Income (₹)</label>
            <input type="number" value={formData.salary_income} onChange={(e) => setFormData({ ...formData, salary_income: parseFloat(e.target.value) || 0 })} />
          </div>
          <div className="form-group">
            <label>House Property Income (₹)</label>
            <input type="number" value={formData.house_property_income} onChange={(e) => setFormData({ ...formData, house_property_income: parseFloat(e.target.value) || 0 })} />
          </div>
          <div className="form-group">
            <label>Other Income (₹)</label>
            <input type="number" value={formData.other_income} onChange={(e) => setFormData({ ...formData, other_income: parseFloat(e.target.value) || 0 })} />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>TDS & Advance Tax</h4>
        <div className="form-group">
          <label>TDS Deducted (₹)</label>
          <input type="number" value={formData.tds_deducted} onChange={(e) => setFormData({ ...formData, tds_deducted: parseFloat(e.target.value) || 0 })} />
        </div>
      </div>

      <div className="form-summary">
        <h4>Business Summary</h4>
        <div className="summary-row">
          <span>Gross Receipts:</span>
          <span>₹{formData.business.gross_receipts.toLocaleString()}</span>
        </div>
        <div className="summary-row">
          <span>Less: COGS:</span>
          <span>₹{formData.business.cost_of_goods_sold.toLocaleString()}</span>
        </div>
        <div className="summary-row">
          <span>Less: Expenses:</span>
          <span>₹{totalExpenses.toLocaleString()}</span>
        </div>
        <div className="summary-row summary-total">
          <span>Net Profit:</span>
          <span>₹{calculateNetProfit().toLocaleString()}</span>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-large" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate ITR-3 Form'}
        </button>
      </div>
    </form>
  );
}
