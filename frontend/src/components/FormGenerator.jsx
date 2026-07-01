import React, { useState } from 'react';
import GSTR3BForm from './forms/GSTR3BForm';
import ITR1Form from './forms/ITR1Form';
import ITR2Form from './forms/ITR2Form';
import ITR3Form from './forms/ITR3Form';

export default function FormGenerator({ client, onFormGenerated, isLoading }) {
  const [selectedForm, setSelectedForm] = useState(null);
  const [generationStatus, setGenerationStatus] = useState(null);

  const formTypes = [
    {
      id: 'gstr3b',
      name: 'GSTR-3B',
      description: 'Monthly GST Tax Summary Return',
      icon: '📋',
      color: '#1f4788',
    },
    {
      id: 'itr1',
      name: 'ITR-1 (SARAL)',
      description: 'Income Tax Return for Salaried Individuals',
      icon: '👤',
      color: '#0C6E3E',
    },
    {
      id: 'itr2',
      name: 'ITR-2',
      description: 'Income Tax Return with Capital Gains',
      icon: '📈',
      color: '#9B3E0C',
    },
    {
      id: 'itr3',
      name: 'ITR-3',
      description: 'Income Tax Return for Business Owners',
      icon: '💼',
      color: '#5B3E9B',
    },
  ];

  const handleFormSubmit = async (formData, formType) => {
    setGenerationStatus({ type: 'generating', message: `Generating ${formType}...` });

    try {
      // Call the backend API to generate the form
      const endpoint = formType === 'gstr3b' ? 'gstr3b/generate' : `itr-forms/${formType}/generate`;
      const response = await fetch(`http://localhost:8000/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const result = await response.json();
        onFormGenerated({
          type: formType.toUpperCase(),
          data: result.form || result,
          clientName: client.name,
          timestamp: new Date().toLocaleString(),
        });

        setGenerationStatus({
          type: 'success',
          message: `${formType.toUpperCase()} generated successfully!`,
        });

        setTimeout(() => {
          setSelectedForm(null);
          setGenerationStatus(null);
        }, 2000);
      } else {
        setGenerationStatus({
          type: 'error',
          message: `Failed to generate ${formType}. Please check your data.`,
        });
      }
    } catch (error) {
      console.error('Form generation error:', error);
      setGenerationStatus({
        type: 'error',
        message: `Error: ${error.message}`,
      });
    }
  };

  return (
    <div className="form-generator">
      {!selectedForm ? (
        <div className="form-selection">
          <div className="selection-header">
            <h3>Select Form Type for {client.name}</h3>
            <p>Choose the tax form you want to generate</p>
          </div>

          {generationStatus && (
            <div className={`status-message ${generationStatus.type}`}>
              {generationStatus.message}
            </div>
          )}

          <div className="form-grid">
            {formTypes.map((form) => (
              <button
                key={form.id}
                className="form-card"
                onClick={() => setSelectedForm(form.id)}
                style={{ borderLeftColor: form.color }}
              >
                <div className="form-icon">{form.icon}</div>
                <h4>{form.name}</h4>
                <p>{form.description}</p>
                <span className="action">Select Form →</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="form-container">
          <div className="form-back">
            <button
              className="btn btn-secondary"
              onClick={() => setSelectedForm(null)}
              disabled={isLoading}
            >
              ← Back to Form Selection
            </button>
          </div>

          {selectedForm === 'gstr3b' && (
            <GSTR3BForm
              client={client}
              onSubmit={(data) => handleFormSubmit(data, 'gstr3b')}
              isLoading={isLoading}
            />
          )}
          {selectedForm === 'itr1' && (
            <ITR1Form
              client={client}
              onSubmit={(data) => handleFormSubmit(data, 'itr1')}
              isLoading={isLoading}
            />
          )}
          {selectedForm === 'itr2' && (
            <ITR2Form
              client={client}
              onSubmit={(data) => handleFormSubmit(data, 'itr2')}
              isLoading={isLoading}
            />
          )}
          {selectedForm === 'itr3' && (
            <ITR3Form
              client={client}
              onSubmit={(data) => handleFormSubmit(data, 'itr3')}
              isLoading={isLoading}
            />
          )}
        </div>
      )}
    </div>
  );
}
