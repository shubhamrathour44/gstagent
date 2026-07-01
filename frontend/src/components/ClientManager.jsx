import React, { useState } from 'react';

export default function ClientManager({ clients, onAddClient, onSelectClient, selectedClient }) {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    type: 'individual',
    pan: '',
    gstin: '',
    email: '',
    phone: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.name.trim()) {
      onAddClient(formData);
      setFormData({ name: '', type: 'individual', pan: '', gstin: '', email: '', phone: '' });
      setShowForm(false);
    }
  };

  return (
    <div className="client-manager">
      <div className="clients-section">
        <div className="section-header">
          <h3>Your Clients ({clients.length})</h3>
          <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? '✕ Cancel' : '+ Add Client'}
          </button>
        </div>

        {showForm && (
          <form className="client-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Client Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="E.g., Acme Corp or John Doe"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Type</label>
                <select name="type" value={formData.type} onChange={handleChange}>
                  <option value="individual">Individual</option>
                  <option value="business">Business</option>
                  <option value="professional">Professional</option>
                </select>
              </div>
              <div className="form-group">
                <label>PAN</label>
                <input
                  type="text"
                  name="pan"
                  value={formData.pan}
                  onChange={handleChange}
                  placeholder="E.g., AAAPB5055K"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>GSTIN</label>
                <input
                  type="text"
                  name="gstin"
                  value={formData.gstin}
                  onChange={handleChange}
                  placeholder="E.g., 27ABCDE1234F1Z5"
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="client@example.com"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Phone</label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="+91 9876543210"
              />
            </div>

            <button type="submit" className="btn btn-success">
              Add Client
            </button>
          </form>
        )}

        <div className="clients-grid">
          {clients.length === 0 ? (
            <div className="empty-state">
              <p>No clients added yet</p>
              <p>Click "Add Client" to get started</p>
            </div>
          ) : (
            clients.map((client) => (
              <div
                key={client.id}
                className={`client-card ${selectedClient?.id === client.id ? 'selected' : ''}`}
                onClick={() => onSelectClient(client)}
              >
                <div className="client-header">
                  <h4>{client.name}</h4>
                  <span className="client-type">{client.type}</span>
                </div>
                <div className="client-details">
                  {client.pan && (
                    <div className="detail-row">
                      <span className="label">PAN:</span>
                      <span className="value">{client.pan}</span>
                    </div>
                  )}
                  {client.gstin && (
                    <div className="detail-row">
                      <span className="label">GSTIN:</span>
                      <span className="value">{client.gstin}</span>
                    </div>
                  )}
                  {client.email && (
                    <div className="detail-row">
                      <span className="label">Email:</span>
                      <span className="value">{client.email}</span>
                    </div>
                  )}
                  {client.phone && (
                    <div className="detail-row">
                      <span className="label">Phone:</span>
                      <span className="value">{client.phone}</span>
                    </div>
                  )}
                </div>
                {selectedClient?.id === client.id && (
                  <div className="client-actions">
                    <button className="btn btn-small">Selected ✓</button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
