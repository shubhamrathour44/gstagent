import React, { useState } from 'react';

export default function ITR2Form({ client, onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    pan: client.pan || '',
    financial_year: 2026,
    salary_income: 0,
    house_property_income: 0,
    capital_gains: [],
    other_income: 0,
    tds_deducted: 0,
  });

  const [capGainInput, setCapGainInput] = useState({
    asset_type: 'Shares',
    cost_of_acquisition: 0,
    selling_price: 0,
    holding_period: 1,
    selling_date: '',
  });

  const addCapitalGain = () => {
    if (capGainInput.cost_of_acquisition > 0 && capGainInput.selling_price > 0) {
      setFormData({
        ...formData,
        capital_gains: [...formData.capital_gains, capGainInput],
      });
      setCapGainInput({ asset_type: 'Shares', cost_of_acquisition: 0, selling_price: 0, holding_period: 1, selling_date: '' });
    }
  };

  const removeCapitalGain = (index) => {
    setFormData({
      ...formData,
      capital_gains: formData.capital_gains.filter((_, i) => i !== index),
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const calculateTotalGains = () => {
    return formData.capital_gains.reduce((sum, gain) => sum + (gain.selling_price - gain.cost_of_acquisition), 0);
  };

  return (
    <form onSubmit={handleSubmit} className="itr-form">
      <h3>ITR-2 - Income Tax Return with Capital Gains</h3>

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
        <h4>Income Sources</h4>
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
        <h4>Capital Gains</h4>
        {formData.capital_gains.length > 0 && (
          <div className="gains-list">
            {formData.capital_gains.map((gain, idx) => (
              <div key={idx} className="gain-item">
                <span>
                  {gain.asset_type}: ₹{(gain.selling_price - gain.cost_of_acquisition).toLocaleString()} {gain.holding_period >= 2 ? '(LT)' : '(ST)'}
                </span>
                <button type="button" className="btn btn-small btn-danger" onClick={() => removeCapitalGain(idx)}>
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="add-gain">
          <select value={capGainInput.asset_type} onChange={(e) => setCapGainInput({ ...capGainInput, asset_type: e.target.value })}>
            <option>Shares</option>
            <option>Property</option>
            <option>Mutual Funds</option>
            <option>Bonds</option>
          </select>
          <input type="number" placeholder="Cost" value={capGainInput.cost_of_acquisition} onChange={(e) => setCapGainInput({ ...capGainInput, cost_of_acquisition: parseFloat(e.target.value) || 0 })} />
          <input type="number" placeholder="Sale Price" value={capGainInput.selling_price} onChange={(e) => setCapGainInput({ ...capGainInput, selling_price: parseFloat(e.target.value) || 0 })} />
          <input type="number" placeholder="Holding Years" min="1" value={capGainInput.holding_period} onChange={(e) => setCapGainInput({ ...capGainInput, holding_period: parseInt(e.target.value) || 1 })} />
          <button type="button" className="btn btn-secondary" onClick={addCapitalGain}>
            Add Gain
          </button>
        </div>
      </div>

      <div className="form-section">
        <h4>TDS & Advance Tax</h4>
        <div className="form-row">
          <div className="form-group">
            <label>TDS Deducted (₹)</label>
            <input type="number" value={formData.tds_deducted} onChange={(e) => setFormData({ ...formData, tds_deducted: parseFloat(e.target.value) || 0 })} />
          </div>
        </div>
      </div>

      <div className="form-summary">
        <h4>Summary</h4>
        <div className="summary-row">
          <span>Total Capital Gains:</span>
          <span>₹{calculateTotalGains().toLocaleString()}</span>
        </div>
        <div className="summary-row">
          <span>Total Income:</span>
          <span>₹{(formData.salary_income + formData.house_property_income + calculateTotalGains() + formData.other_income).toLocaleString()}</span>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-large" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate ITR-2 Form'}
        </button>
      </div>
    </form>
  );
}
