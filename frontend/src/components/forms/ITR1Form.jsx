import React, { useState } from 'react';

export default function ITR1Form({ client, onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    pan: client.pan || '',
    financial_year: 2026,
    salary: {
      gross_salary: 0,
      allowances: 0,
      deductions: 0,
    },
    house_property: {
      annual_value: 0,
      tax_paid: 0,
      interest_paid: 0,
      other_expenditure: 0,
    },
    other_income: [],
    tds_deducted: 0,
    advance_tax_paid: 0,
  });

  const [otherIncomeInput, setOtherIncomeInput] = useState({ income_type: '', amount: 0, tax_deducted: 0 });

  const handleChange = (e, section) => {
    const { name, value } = e.target;
    if (section) {
      setFormData({
        ...formData,
        [section]: {
          ...formData[section],
          [name]: parseFloat(value) || 0,
        },
      });
    } else {
      setFormData({
        ...formData,
        [name]: name.includes('year') ? parseInt(value) : value,
      });
    }
  };

  const addOtherIncome = () => {
    if (otherIncomeInput.income_type.trim()) {
      setFormData({
        ...formData,
        other_income: [...formData.other_income, otherIncomeInput],
      });
      setOtherIncomeInput({ income_type: '', amount: 0, tax_deducted: 0 });
    }
  };

  const removeOtherIncome = (index) => {
    setFormData({
      ...formData,
      other_income: formData.other_income.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const calculateTaxableIncome = () => {
    const salaryIncome = formData.salary.gross_salary + formData.salary.allowances - 50000;
    const propertyIncome = formData.house_property.annual_value - formData.house_property.interest_paid;
    const otherIncome = formData.other_income.reduce((sum, income) => sum + income.amount, 0);
    return salaryIncome + propertyIncome + otherIncome;
  };

  return (
    <form onSubmit={handleSubmit} className="itr-form">
      <h3>ITR-1 (SARAL) - Income Tax Return for Salaried Individuals</h3>

      <div className="form-section">
        <h4>Personal Information</h4>
        <div className="form-row">
          <div className="form-group">
            <label>PAN *</label>
            <input
              type="text"
              name="pan"
              value={formData.pan}
              onChange={(e) => handleChange(e)}
              placeholder="E.g., AAAPB5055K"
              required
            />
          </div>
          <div className="form-group">
            <label>Financial Year</label>
            <select name="financial_year" value={formData.financial_year} onChange={(e) => handleChange(e)}>
              <option value={2024}>2024-25</option>
              <option value={2025}>2025-26</option>
              <option value={2026}>2026-27</option>
            </select>
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>Salary Income</h4>
        <div className="form-row">
          <div className="form-group">
            <label>Gross Salary (₹)</label>
            <input
              type="number"
              name="gross_salary"
              value={formData.salary.gross_salary}
              onChange={(e) => handleChange(e, 'salary')}
              placeholder="0"
            />
          </div>
          <div className="form-group">
            <label>Allowances (₹)</label>
            <input
              type="number"
              name="allowances"
              value={formData.salary.allowances}
              onChange={(e) => handleChange(e, 'salary')}
              placeholder="0"
            />
          </div>
          <div className="form-group">
            <label>Deductions (₹)</label>
            <input
              type="number"
              name="deductions"
              value={formData.salary.deductions}
              onChange={(e) => handleChange(e, 'salary')}
              placeholder="0"
            />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>House Property Income</h4>
        <div className="form-row">
          <div className="form-group">
            <label>Annual Value (₹)</label>
            <input
              type="number"
              name="annual_value"
              value={formData.house_property.annual_value}
              onChange={(e) => handleChange(e, 'house_property')}
              placeholder="0"
            />
          </div>
          <div className="form-group">
            <label>Tax Paid (₹)</label>
            <input
              type="number"
              name="tax_paid"
              value={formData.house_property.tax_paid}
              onChange={(e) => handleChange(e, 'house_property')}
              placeholder="0"
            />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Interest Paid (₹)</label>
            <input
              type="number"
              name="interest_paid"
              value={formData.house_property.interest_paid}
              onChange={(e) => handleChange(e, 'house_property')}
              placeholder="0"
            />
          </div>
          <div className="form-group">
            <label>Other Expenditure (₹)</label>
            <input
              type="number"
              name="other_expenditure"
              value={formData.house_property.other_expenditure}
              onChange={(e) => handleChange(e, 'house_property')}
              placeholder="0"
            />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>Other Income</h4>
        <div className="other-income-list">
          {formData.other_income.length > 0 && (
            <div className="income-items">
              {formData.other_income.map((income, index) => (
                <div key={index} className="income-item">
                  <span>{income.income_type}: ₹{income.amount.toLocaleString()}</span>
                  <button
                    type="button"
                    className="btn btn-small btn-danger"
                    onClick={() => removeOtherIncome(index)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="add-income">
            <input
              type="text"
              placeholder="Income type (e.g., Interest)"
              value={otherIncomeInput.income_type}
              onChange={(e) => setOtherIncomeInput({ ...otherIncomeInput, income_type: e.target.value })}
            />
            <input
              type="number"
              placeholder="Amount"
              value={otherIncomeInput.amount}
              onChange={(e) => setOtherIncomeInput({ ...otherIncomeInput, amount: parseFloat(e.target.value) || 0 })}
            />
            <button type="button" className="btn btn-secondary" onClick={addOtherIncome}>
              Add Income
            </button>
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>TDS & Advance Tax</h4>
        <div className="form-row">
          <div className="form-group">
            <label>TDS Deducted (₹)</label>
            <input
              type="number"
              name="tds_deducted"
              value={formData.tds_deducted}
              onChange={(e) => handleChange(e)}
              placeholder="0"
            />
          </div>
          <div className="form-group">
            <label>Advance Tax Paid (₹)</label>
            <input
              type="number"
              name="advance_tax_paid"
              value={formData.advance_tax_paid}
              onChange={(e) => handleChange(e)}
              placeholder="0"
            />
          </div>
        </div>
      </div>

      <div className="form-summary">
        <h4>Summary</h4>
        <div className="summary-row">
          <span>Estimated Taxable Income:</span>
          <span>₹{calculateTaxableIncome().toLocaleString()}</span>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-large" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate ITR-1 Form'}
        </button>
      </div>
    </form>
  );
}
