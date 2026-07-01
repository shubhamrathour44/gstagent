import React, { useState } from 'react';

export default function BulkOperations({ clients, onBulkGenerate, isLoading }) {
  const [selectedClients, setSelectedClients] = useState([]);
  const [formTypes, setFormTypes] = useState([]);
  const [status, setStatus] = useState(null);

  const handleClientToggle = (clientId) => {
    setSelectedClients((prev) =>
      prev.includes(clientId) ? prev.filter((id) => id !== clientId) : [...prev, clientId]
    );
  };

  const handleFormTypeToggle = (type) => {
    setFormTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]));
  };

  const handleBulkGenerate = async () => {
    if (selectedClients.length === 0 || formTypes.length === 0) {
      setStatus({ type: 'error', message: 'Please select at least one client and one form type' });
      return;
    }

    setStatus({ type: 'generating', message: `Generating ${selectedClients.length * formTypes.length} forms...` });

    try {
      const results = [];
      for (const clientId of selectedClients) {
        const client = clients.find((c) => c.id === clientId);
        for (const formType of formTypes) {
          // Generate demo forms for bulk operation
          try {
            const endpoint =
              formType === 'gstr3b'
                ? `gstr3b/demo/${client.gstin || '27ABCDE1234F1Z5'}/4/2026`
                : `itr-forms/${formType}/demo/${client.pan || 'AAAPB5055K'}`;

            const response = await fetch(`http://localhost:8000/${endpoint}`);
            if (response.ok) {
              const data = await response.json();
              results.push({
                id: Date.now() + Math.random(),
                type: formType.toUpperCase(),
                client: client.name,
                data: data.form || data,
                timestamp: new Date().toLocaleString(),
              });
            }
          } catch (error) {
            console.error(`Error generating ${formType} for ${client.name}:`, error);
          }
        }
      }

      onBulkGenerate(results);
      setStatus({
        type: 'success',
        message: `Successfully generated ${results.length} forms!`,
      });

      setTimeout(() => {
        setSelectedClients([]);
        setFormTypes([]);
        setStatus(null);
      }, 2000);
    } catch (error) {
      setStatus({ type: 'error', message: `Error: ${error.message}` });
    }
  };

  return (
    <div className="bulk-operations">
      <div className="bulk-header">
        <h3>Generate Multiple Forms at Once</h3>
        <p>Select clients and form types to generate forms in bulk</p>
      </div>

      {status && <div className={`status-message ${status.type}`}>{status.message}</div>}

      <div className="bulk-selection">
        <div className="selection-section">
          <h4>Select Clients ({selectedClients.length})</h4>
          <div className="client-list">
            {clients.length === 0 ? (
              <p>No clients available. Add clients first.</p>
            ) : (
              clients.map((client) => (
                <label key={client.id} className="checkbox-item">
                  <input
                    type="checkbox"
                    checked={selectedClients.includes(client.id)}
                    onChange={() => handleClientToggle(client.id)}
                  />
                  <span>
                    {client.name}
                    <small>({client.type})</small>
                  </span>
                </label>
              ))
            )}
          </div>
        </div>

        <div className="selection-section">
          <h4>Select Form Types ({formTypes.length})</h4>
          <div className="form-types-list">
            {[
              { id: 'gstr3b', name: 'GSTR-3B (GST Return)' },
              { id: 'itr1', name: 'ITR-1 (Salary)' },
              { id: 'itr2', name: 'ITR-2 (Capital Gains)' },
              { id: 'itr3', name: 'ITR-3 (Business)' },
            ].map((form) => (
              <label key={form.id} className="checkbox-item">
                <input
                  type="checkbox"
                  checked={formTypes.includes(form.id)}
                  onChange={() => handleFormTypeToggle(form.id)}
                />
                <span>{form.name}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="bulk-summary">
        <div className="summary-stat">
          <span className="stat-label">Clients:</span>
          <span className="stat-value">{selectedClients.length}</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Form Types:</span>
          <span className="stat-value">{formTypes.length}</span>
        </div>
        <div className="summary-stat">
          <span className="stat-label">Total Forms:</span>
          <span className="stat-value">{selectedClients.length * formTypes.length}</span>
        </div>
      </div>

      <div className="bulk-actions">
        <button
          className="btn btn-primary btn-large"
          onClick={handleBulkGenerate}
          disabled={isLoading || selectedClients.length === 0 || formTypes.length === 0}
        >
          {isLoading ? 'Generating...' : 'Generate All Forms'}
        </button>
      </div>
    </div>
  );
}
