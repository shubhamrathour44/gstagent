import React, { useState } from 'react';
import './CADashboard.css';
import ClientManager from './ClientManager';
import FormGenerator from './FormGenerator';
import BulkOperations from './BulkOperations';
import ResultsViewer from './ResultsViewer';

export default function CADashboard() {
  const [activeTab, setActiveTab] = useState('clients');
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [generatedForms, setGeneratedForms] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleClientAdd = (newClient) => {
    const clientWithId = { ...newClient, id: Date.now() };
    setClients([...clients, clientWithId]);
  };

  const handleClientSelect = (client) => {
    setSelectedClient(client);
    setActiveTab('generate');
  };

  const handleFormGenerated = (formData) => {
    setGeneratedForms([...generatedForms, { ...formData, id: Date.now() }]);
  };

  const handleDownloadPDF = async (form) => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/pdf-export/${form.type.toLowerCase()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form.data),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${form.type}_${form.data.pan || form.data.gstin}_${form.data.financial_year || form.data.year}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      } else {
        alert('Failed to generate PDF');
      }
    } catch (error) {
      console.error('PDF download error:', error);
      alert('Error downloading PDF');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="ca-dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>GST Agent Professional Suite</h1>
          <p>CA Dashboard - Multi-Client Form Management</p>
        </div>
        <div className="header-stats">
          <div className="stat">
            <span className="stat-value">{clients.length}</span>
            <span className="stat-label">Clients</span>
          </div>
          <div className="stat">
            <span className="stat-value">{generatedForms.length}</span>
            <span className="stat-label">Forms Generated</span>
          </div>
        </div>
      </header>

      <nav className="dashboard-nav">
        <button
          className={`nav-item ${activeTab === 'clients' ? 'active' : ''}`}
          onClick={() => setActiveTab('clients')}
        >
          <i className="icon">👥</i> Clients
        </button>
        <button
          className={`nav-item ${activeTab === 'generate' ? 'active' : ''}`}
          onClick={() => setActiveTab('generate')}
          disabled={!selectedClient}
        >
          <i className="icon">📝</i> Generate Forms
        </button>
        <button
          className={`nav-item ${activeTab === 'bulk' ? 'active' : ''}`}
          onClick={() => setActiveTab('bulk')}
        >
          <i className="icon">⚙️</i> Bulk Operations
        </button>
        <button
          className={`nav-item ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          <i className="icon">📊</i> Results
        </button>
      </nav>

      <main className="dashboard-content">
        {activeTab === 'clients' && (
          <div className="section">
            <h2>Client Management</h2>
            <ClientManager
              clients={clients}
              onAddClient={handleClientAdd}
              onSelectClient={handleClientSelect}
              selectedClient={selectedClient}
            />
          </div>
        )}

        {activeTab === 'generate' && selectedClient && (
          <div className="section">
            <h2>Generate Forms for {selectedClient.name}</h2>
            <FormGenerator
              client={selectedClient}
              onFormGenerated={handleFormGenerated}
              isLoading={isLoading}
            />
          </div>
        )}

        {activeTab === 'bulk' && (
          <div className="section">
            <h2>Bulk Operations</h2>
            <BulkOperations
              clients={clients}
              onBulkGenerate={setGeneratedForms}
              isLoading={isLoading}
            />
          </div>
        )}

        {activeTab === 'results' && (
          <div className="section">
            <h2>Generated Forms & Results</h2>
            <ResultsViewer
              forms={generatedForms}
              onDownloadPDF={handleDownloadPDF}
              isLoading={isLoading}
            />
          </div>
        )}
      </main>

      <footer className="dashboard-footer">
        <p>GST Agent Professional Suite • Version 2.0 • CA Dashboard</p>
        <p>API: 23 Endpoints | PDF Export: 8 Forms | Database: SQLite</p>
      </footer>
    </div>
  );
}
