import React, { useState } from 'react';

export default function GSTR3BForm({ client, onSubmit, isLoading }) {
  const [formData, setFormData] = useState({
    gstin: client.gstin || '',
    month: 4,
    year: 2026,
    outward_supplies: [
      { supply_type: 'b2b', taxable_value: 0, cgst: 0, sgst: 0, igst: 0, cess: 0, invoices_count: 0 },
    ],
    inward_supplies: [
      { supply_type: 'purchases', taxable_value: 0, cgst: 0, sgst: 0, igst: 0, cess: 0, eligible_cgst: 0, eligible_sgst: 0, eligible_igst: 0, eligible_cess: 0, invoices_count: 0 },
    ],
  });

  const handleOutwardChange = (index, field, value) => {
    const updated = [...formData.outward_supplies];
    updated[index][field] = parseFloat(value) || 0;
    setFormData({ ...formData, outward_supplies: updated });
  };

  const handleInwardChange = (index, field, value) => {
    const updated = [...formData.inward_supplies];
    updated[index][field] = parseFloat(value) || 0;
    setFormData({ ...formData, inward_supplies: updated });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const calculateTotalTax = (supplies, taxType) => {
    return supplies.reduce((sum, supply) => sum + (supply[taxType] || 0), 0);
  };

  return (
    <form onSubmit={handleSubmit} className="gstr3b-form">
      <h3>GSTR-3B - Monthly Tax Summary Return</h3>

      <div className="form-section">
        <h4>Return Details</h4>
        <div className="form-row">
          <div className="form-group">
            <label>GSTIN *</label>
            <input type="text" value={formData.gstin} onChange={(e) => setFormData({ ...formData, gstin: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Month</label>
            <select value={formData.month} onChange={(e) => setFormData({ ...formData, month: parseInt(e.target.value) })}>
              {[...Array(12)].map((_, i) => (
                <option key={i + 1} value={i + 1}>
                  {new Date(2026, i).toLocaleDateString('en-IN', { month: 'long' })}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Year</label>
            <select value={formData.year} onChange={(e) => setFormData({ ...formData, year: parseInt(e.target.value) })}>
              <option value={2024}>2024</option>
              <option value={2025}>2025</option>
              <option value={2026}>2026</option>
            </select>
          </div>
        </div>
      </div>

      <div className="form-section">
        <h4>Outward Supplies (Sales)</h4>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Supply Type</th>
                <th>Taxable Value</th>
                <th>CGST</th>
                <th>SGST</th>
                <th>IGST</th>
                <th>Invoices</th>
              </tr>
            </thead>
            <tbody>
              {formData.outward_supplies.map((supply, idx) => (
                <tr key={idx}>
                  <td>
                    <select value={supply.supply_type} onChange={(e) => handleOutwardChange(idx, 'supply_type', e.target.value)}>
                      <option value="b2b">B2B</option>
                      <option value="b2c">B2C</option>
                      <option value="export">Export</option>
                    </select>
                  </td>
                  <td><input type="number" value={supply.taxable_value} onChange={(e) => handleOutwardChange(idx, 'taxable_value', e.target.value)} /></td>
                  <td><input type="number" value={supply.cgst} onChange={(e) => handleOutwardChange(idx, 'cgst', e.target.value)} /></td>
                  <td><input type="number" value={supply.sgst} onChange={(e) => handleOutwardChange(idx, 'sgst', e.target.value)} /></td>
                  <td><input type="number" value={supply.igst} onChange={(e) => handleOutwardChange(idx, 'igst', e.target.value)} /></td>
                  <td><input type="number" value={supply.invoices_count} onChange={(e) => handleOutwardChange(idx, 'invoices_count', e.target.value)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="form-section">
        <h4>Inward Supplies (Purchases)</h4>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Supply Type</th>
                <th>Taxable Value</th>
                <th>Eligible CGST</th>
                <th>Eligible SGST</th>
                <th>Invoices</th>
              </tr>
            </thead>
            <tbody>
              {formData.inward_supplies.map((supply, idx) => (
                <tr key={idx}>
                  <td>
                    <select value={supply.supply_type} onChange={(e) => handleInwardChange(idx, 'supply_type', e.target.value)}>
                      <option value="purchases">Purchases</option>
                      <option value="services">Services</option>
                    </select>
                  </td>
                  <td><input type="number" value={supply.taxable_value} onChange={(e) => handleInwardChange(idx, 'taxable_value', e.target.value)} /></td>
                  <td><input type="number" value={supply.eligible_cgst} onChange={(e) => handleInwardChange(idx, 'eligible_cgst', e.target.value)} /></td>
                  <td><input type="number" value={supply.eligible_sgst} onChange={(e) => handleInwardChange(idx, 'eligible_sgst', e.target.value)} /></td>
                  <td><input type="number" value={supply.invoices_count} onChange={(e) => handleInwardChange(idx, 'invoices_count', e.target.value)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="form-summary">
        <h4>Tax Summary</h4>
        <div className="summary-row">
          <span>Total Output Tax:</span>
          <span>
            ₹{(
              calculateTotalTax(formData.outward_supplies, 'cgst') +
              calculateTotalTax(formData.outward_supplies, 'sgst') +
              calculateTotalTax(formData.outward_supplies, 'igst')
            ).toLocaleString()}
          </span>
        </div>
        <div className="summary-row">
          <span>Total ITC Available:</span>
          <span>
            ₹{(
              calculateTotalTax(formData.inward_supplies, 'eligible_cgst') +
              calculateTotalTax(formData.inward_supplies, 'eligible_sgst')
            ).toLocaleString()}
          </span>
        </div>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-large" disabled={isLoading}>
          {isLoading ? 'Generating...' : 'Generate GSTR-3B Form'}
        </button>
      </div>
    </form>
  );
}
