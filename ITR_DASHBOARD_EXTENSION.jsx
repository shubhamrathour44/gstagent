/**
 * ITR Dashboard Extension Components
 * Add these components to your main App.jsx to enable ITR features
 *
 * Add to App.jsx:
 * 1. Add ITR methods to APIService class (copy from below)
 * 2. Add ITRFilingCalendarPage component
 * 3. Add ITRTrackerPage component
 * 4. Update navigation to include ITR tabs
 * 5. Update main App render to show ITR pages
 */

// ═══════════════════════════════════════════════════════════════════════════
// ADD THESE METHODS TO APIService CLASS
// ═══════════════════════════════════════════════════════════════════════════

// Copy this code into the existing APIService class:

/*
  // ITR APIs
  getITRTypes() {
    return this.request('/itr-features/return-types/list');
  }

  getITRFilingCalendar(financialYear) {
    return this.request(`/itr-features/filing-calendar/${financialYear}`);
  }

  getITRDueDates(financialYear) {
    return this.request(`/itr-features/due-dates/${financialYear}`);
  }

  calculateITRPenalty(amount, daysLate) {
    return this.request(
      `/itr-features/penalty-calculator?amount=${amount}&days_late=${daysLate}`,
      { method: 'POST' }
    );
  }

  getApplicableITRs(incomeSources, entityType) {
    const sources = incomeSources.map(s => `income_sources=${s}`).join('&');
    return this.request(
      `/itr-features/applicable-itrs?${sources}&entity_type=${entityType}`,
      { method: 'POST' }
    );
  }

  getITRChecklist(returnType) {
    return this.request(`/itr-features/filing-checklist/${returnType}`);
  }

  getITRFeaturesStatus() {
    return this.request('/itr-features/features-status');
  }
*/

// ═══════════════════════════════════════════════════════════════════════════
// ITR FILING CALENDAR PAGE
// ═══════════════════════════════════════════════════════════════════════════

function ITRFilingCalendarPage() {
  const [year, setYear] = React.useState(2026);
  const [calendar, setCalendar] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    loadCalendar();
  }, [year]);

  async function loadCalendar() {
    setLoading(true);
    const api = new APIService(API_BASE_URL);
    const data = await api.getITRFilingCalendar(year);
    if (data) {
      setCalendar(data.calendar);
    }
    setLoading(false);
  }

  if (loading) return <div className="text-center py-8">Loading...</div>;

  const fy = `FY ${year - 1}-${year}`;
  const fyCalendar = calendar?.[fy] || {};

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">ITR Filing Calendar</h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setYear(year - 1)}
              className="px-3 py-2 bg-gray-100 rounded hover:bg-gray-200"
            >
              ← Previous
            </button>
            <span className="px-4 py-2 font-semibold">{fy}</span>
            <button
              onClick={() => setYear(year + 1)}
              className="px-3 py-2 bg-gray-100 rounded hover:bg-gray-200"
            >
              Next →
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  ITR Type
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Description
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Due Date
                </th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                  Applicable To
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {Object.entries(fyCalendar).map(([itrCode, details]) => {
                const daysUntilDue = Math.ceil(
                  (new Date(details.due_date) - new Date()) / (1000 * 60 * 60 * 24)
                );
                const isDue = daysUntilDue <= 7 && daysUntilDue > 0;
                const isOverdue = daysUntilDue <= 0;

                return (
                  <tr key={itrCode} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <span className="font-semibold text-gray-900">{details.return_type}</span>
                    </td>
                    <td className="px-6 py-4 text-gray-600 text-sm">{details.name}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <span>{details.due_date}</span>
                        {isDue && (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded">
                            Due Soon
                          </span>
                        )}
                        {isOverdue && (
                          <span className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                            Overdue
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-600 text-sm">{details.applicable_to}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded border border-blue-200">
          <h3 className="font-semibold text-blue-900 mb-2">ITR Filing Deadlines for {fy}</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• ITR-1, ITR-2: <strong>31 July {year}</strong> (Salary, Capital Gains)</li>
            <li>• ITR-3, ITR-4, ITR-5, ITR-6, ITR-7: <strong>30 September {year}</strong> (Business, Partnerships, Companies)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// ITR TRACKER PAGE
// ═══════════════════════════════════════════════════════════════════════════

function ITRTrackerPage() {
  const [entityType, setEntityType] = React.useState('individual');
  const [incomeSources, setIncomeSources] = React.useState(['salary']);
  const [applicableITRs, setApplicableITRs] = React.useState([]);
  const [selectedITR, setSelectedITR] = React.useState(null);
  const [checklist, setChecklist] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  const incomeOptions = {
    individual: ['salary', 'pension', 'house_property', 'capital_gains', 'business', 'profession'],
    partnership: ['business'],
    company: ['corporate'],
    trust: ['trust_income']
  };

  async function findApplicableITRs() {
    setLoading(true);
    const api = new APIService(API_BASE_URL);

    // Construct query string
    const sourcesQuery = incomeSources.map(s => `income_sources=${s}`).join('&');
    const response = await fetch(
      `${API_BASE_URL}/itr-features/applicable-itrs?${sourcesQuery}&entity_type=${entityType}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' } }
    );
    const data = await response.json();

    setApplicableITRs(data.applicable_itrs || []);
    setSelectedITR(null);
    setLoading(false);
  }

  async function loadChecklist(itrType) {
    setLoading(true);
    const api = new APIService(API_BASE_URL);
    const data = await api.getITRChecklist(itrType);
    setChecklist(data);
    setLoading(false);
  }

  const handleSelectITR = (itr) => {
    setSelectedITR(itr);
    loadChecklist(itr);
  };

  return (
    <div className="space-y-6">
      {/* Finder Section */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">ITR Finder</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Entity Type</label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded"
            >
              <option value="individual">Individual</option>
              <option value="partnership">Partnership</option>
              <option value="company">Company</option>
              <option value="trust">Trust/NGO</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Income Sources</label>
          <div className="space-y-2">
            {incomeOptions[entityType].map((source) => (
              <label key={source} className="flex items-center">
                <input
                  type="checkbox"
                  checked={incomeSources.includes(source)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setIncomeSources([...incomeSources, source]);
                    } else {
                      setIncomeSources(incomeSources.filter(s => s !== source));
                    }
                  }}
                  className="mr-2"
                />
                <span className="text-gray-700 capitalize">{source.replace(/_/g, ' ')}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          onClick={findApplicableITRs}
          disabled={loading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Find Applicable ITRs
        </button>
      </div>

      {/* Results Section */}
      {applicableITRs.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Recommended ITRs</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {applicableITRs.map((itr) => (
              <button
                key={itr}
                onClick={() => handleSelectITR(itr)}
                className={`p-4 border-2 rounded-lg cursor-pointer transition ${
                  selectedITR === itr
                    ? 'border-blue-600 bg-blue-50'
                    : 'border-gray-200 hover:border-blue-300'
                }`}
              >
                <div className="font-bold text-lg">{itr}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Checklist Section */}
      {checklist && selectedITR && (
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            {selectedITR} - Required Documents
          </h3>
          <ul className="space-y-2">
            {checklist.documents_required.map((doc, idx) => (
              <li key={idx} className="flex items-center space-x-2">
                <span className="text-green-600">✓</span>
                <span className="text-gray-700">{doc}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// UPDATED NAVIGATION WITH ITR TABS
// ═══════════════════════════════════════════════════════════════════════════

/*
Update the navigation in App component to include ITR tabs:

<div className="flex space-x-4">
  <NavButton active={currentPage === 'home'} onClick={() => setCurrentPage('home')}>
    📊 Home
  </NavButton>
  <NavButton active={currentPage === 'payments'} onClick={() => setCurrentPage('payments')}>
    💳 Payments
  </NavButton>
  <NavButton active={currentPage === 'analytics'} onClick={() => setCurrentPage('analytics')}>
    📈 Analytics
  </NavButton>
  <NavButton active={currentPage === 'calendar'} onClick={() => setCurrentPage('calendar')}>
    📅 GST Calendar
  </NavButton>

  {/* New ITR Tabs */}
  <NavButton active={currentPage === 'itr-calendar'} onClick={() => setCurrentPage('itr-calendar')}>
    📋 ITR Calendar
  </NavButton>
  <NavButton active={currentPage === 'itr-tracker'} onClick={() => setCurrentPage('itr-tracker')}>
    📌 ITR Tracker
  </NavButton>
</div>

And update the main content:

{currentPage === 'itr-calendar' && <ITRFilingCalendarPage />}
{currentPage === 'itr-tracker' && <ITRTrackerPage />}
*/

export { ITRFilingCalendarPage, ITRTrackerPage };
