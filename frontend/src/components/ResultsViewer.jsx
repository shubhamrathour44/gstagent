import React, { useState } from 'react';

export default function ResultsViewer({ forms, onDownloadPDF, isLoading }) {
  const [filterType, setFilterType] = useState('all');
  const [sortBy, setSortBy] = useState('newest');

  const filteredForms = forms.filter((form) => filterType === 'all' || form.type === filterType);

  const sortedForms = [...filteredForms].sort((a, b) => {
    if (sortBy === 'newest') {
      return new Date(b.timestamp) - new Date(a.timestamp);
    } else if (sortBy === 'oldest') {
      return new Date(a.timestamp) - new Date(b.timestamp);
    } else if (sortBy === 'name') {
      return a.clientName.localeCompare(b.clientName);
    }
    return 0;
  });

  const stats = {
    total: forms.length,
    gstr3b: forms.filter((f) => f.type === 'GSTR-3B').length,
    itr1: forms.filter((f) => f.type === 'ITR-1').length,
    itr2: forms.filter((f) => f.type === 'ITR-2').length,
    itr3: forms.filter((f) => f.type === 'ITR-3').length,
  };

  const handleBulkDownload = () => {
    sortedForms.forEach((form, index) => {
      setTimeout(() => onDownloadPDF(form), index * 500);
    });
  };

  return (
    <div className="results-viewer">
      <div className="results-header">
        <h3>Generated Forms Results</h3>
        <p>View and download all generated tax forms</p>
      </div>

      <div className="results-stats">
        <div className="stat-card">
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Total Forms</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.gstr3b}</div>
          <div className="stat-label">GSTR-3B</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.itr1}</div>
          <div className="stat-label">ITR-1</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.itr2}</div>
          <div className="stat-label">ITR-2</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.itr3}</div>
          <div className="stat-label">ITR-3</div>
        </div>
      </div>

      <div className="results-controls">
        <div className="control-group">
          <label>Filter by Type:</label>
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="all">All Forms</option>
            <option value="GSTR-3B">GSTR-3B Only</option>
            <option value="ITR-1">ITR-1 Only</option>
            <option value="ITR-2">ITR-2 Only</option>
            <option value="ITR-3">ITR-3 Only</option>
          </select>
        </div>

        <div className="control-group">
          <label>Sort by:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="name">Client Name</option>
          </select>
        </div>

        {filteredForms.length > 0 && (
          <button className="btn btn-success" onClick={handleBulkDownload} disabled={isLoading}>
            Download All ({filteredForms.length})
          </button>
        )}
      </div>

      {sortedForms.length === 0 ? (
        <div className="empty-results">
          <p>No forms generated yet</p>
          <p>Generate forms to see them here</p>
        </div>
      ) : (
        <div className="results-grid">
          {sortedForms.map((form) => (
            <div key={form.id} className="result-card">
              <div className="result-header">
                <div className="form-type-badge">{form.type}</div>
                <span className="result-time">{form.timestamp}</span>
              </div>

              <div className="result-content">
                <h4>{form.clientName}</h4>
                <div className="form-details">
                  {form.data.pan && <span className="detail">PAN: {form.data.pan}</span>}
                  {form.data.gstin && <span className="detail">GSTIN: {form.data.gstin}</span>}
                  {form.data.financial_year && <span className="detail">FY: {form.data.financial_year}-{form.data.financial_year + 1}</span>}
                  {form.data.period && <span className="detail">Period: {form.data.period}</span>}
                </div>
              </div>

              <div className="result-actions">
                <button
                  className="btn btn-primary btn-small"
                  onClick={() => onDownloadPDF(form)}
                  disabled={isLoading}
                >
                  Download PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
