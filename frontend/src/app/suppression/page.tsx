'use client';

import { useEffect, useState, useRef } from 'react';
import { clsx } from 'clsx';

interface SuppressionEntry {
  id: number;
  contact_type: string;
  value: string;
  reason: string;
  description: string;
  source: string;
  lead_id: number;
  active: boolean;
  added_by: string;
  created_at: string;
  removed_at: string;
}

interface SuppressionStats {
  total_active: number;
  by_type: Record<string, number>;
  by_reason: Record<string, number>;
  recent_7_days: number;
}

const reasonLabels: Record<string, string> = {
  unsubscribe: 'Unsubscribed',
  bounce: 'Bounced',
  spam_report: 'Spam Report',
  manual: 'Manual',
  complaint: 'Complaint',
  import: 'Imported',
};

const typeIcons: Record<string, string> = {
  email: '✉️',
  phone: '📞',
  domain: '🌐',
};

const reasonColors: Record<string, string> = {
  unsubscribe: 'bg-orange-100 text-orange-700',
  bounce: 'bg-red-100 text-red-700',
  spam_report: 'bg-red-100 text-red-700',
  manual: 'bg-gray-100 text-gray-700',
  complaint: 'bg-red-100 text-red-700',
  import: 'bg-blue-100 text-blue-700',
};

export default function SuppressionPage() {
  const [entries, setEntries] = useState<SuppressionEntry[]>([]);
  const [stats, setStats] = useState<SuppressionStats | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [reasonFilter, setReasonFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showCheckModal, setShowCheckModal] = useState(false);
  const [addForm, setAddForm] = useState({ contact_type: 'email', value: '', reason: 'manual', description: '' });
  const [importText, setImportText] = useState('');
  const [importResult, setImportResult] = useState<any>(null);
  const [checkEmail, setCheckEmail] = useState('');
  const [checkResult, setCheckResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchEntries = () => {
    const params = new URLSearchParams();
    if (typeFilter) params.set('contact_type', typeFilter);
    if (reasonFilter) params.set('reason', reasonFilter);
    if (search) params.set('search', search);
    params.set('limit', '100');

    fetch(`/api/suppression?${params}`)
      .then((res) => res.json())
      .then((data) => {
        setEntries(data.entries || []);
        setTotal(data.total || 0);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const fetchStats = () => {
    fetch('/api/suppression/stats')
      .then((res) => res.json())
      .then(setStats)
      .catch(console.error);
  };

  useEffect(() => {
    fetchEntries();
    fetchStats();
  }, [typeFilter, reasonFilter, search]);

  const handleAdd = async () => {
    const res = await fetch('/api/suppression', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addForm),
    });
    const data = await res.json();
    if (res.ok) {
      setShowAddModal(false);
      setAddForm({ contact_type: 'email', value: '', reason: 'manual', description: '' });
      fetchEntries();
      fetchStats();
    }
  };

  const handleRemove = async (id: number) => {
    if (!confirm('Remove this suppression entry? This will allow future contact.')) return;
    await fetch(`/api/suppression/${id}?removed_by=user`, { method: 'DELETE' });
    fetchEntries();
    fetchStats();
  };

  const handleCheck = async () => {
    if (!checkEmail) return;
    const params = new URLSearchParams({ email: checkEmail });
    const res = await fetch(`/api/suppression/check?${params}`);
    const data = await res.json();
    setCheckResult(data);
  };

  const handleImport = async () => {
    const res = await fetch('/api/suppression/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(importText),
    });
    const data = await res.json();
    setImportResult(data);
    if (data.added > 0) {
      fetchEntries();
      fetchStats();
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setImportText(ev.target?.result as string);
    };
    reader.readAsText(file);
  };

  const handleExport = async () => {
    const res = await fetch('/api/suppression/export');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'suppression_list.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Suppression List</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage do-not-contact list • {total} suppressed contacts
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCheckModal(true)}
            className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            🔍 Check Email
          </button>
          <button
            onClick={() => setShowImportModal(true)}
            className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            📥 Import CSV
          </button>
          <button
            onClick={handleExport}
            className="bg-gray-100 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            📤 Export CSV
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700"
          >
            + Add to Suppression List
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Total Suppressed</p>
            <p className="text-2xl font-bold text-gray-900">{stats.total_active}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">📧 Emails</p>
            <p className="text-2xl font-bold text-gray-900">{stats.by_type.email || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">📞 Phones</p>
            <p className="text-2xl font-bold text-gray-900">{stats.by_type.phone || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">🌐 Domains</p>
            <p className="text-2xl font-bold text-gray-900">{stats.by_type.domain || 0}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Last 7 Days</p>
            <p className="text-2xl font-bold text-gray-900">{stats.recent_7_days}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Search by email, phone, or domain..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Types</option>
            <option value="email">Email</option>
            <option value="phone">Phone</option>
            <option value="domain">Domain</option>
          </select>
          <select
            value={reasonFilter}
            onChange={(e) => setReasonFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Reasons</option>
            <option value="unsubscribe">Unsubscribed</option>
            <option value="bounce">Bounced</option>
            <option value="spam_report">Spam Report</option>
            <option value="manual">Manual</option>
            <option value="complaint">Complaint</option>
            <option value="import">Imported</option>
          </select>
        </div>
      </div>

      {/* Entries Table */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No suppression entries found</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Type</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Value</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Reason</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Source</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Added</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="text-sm">
                      {typeIcons[entry.contact_type] || '❓'} {entry.contact_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm font-mono text-gray-900">{entry.value}</td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        reasonColors[entry.reason] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {reasonLabels[entry.reason] || entry.reason}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{entry.source || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(entry.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleRemove(entry.id)}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Add to Suppression List</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select
                  value={addForm.contact_type}
                  onChange={(e) => setAddForm({ ...addForm, contact_type: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="email">Email</option>
                  <option value="phone">Phone</option>
                  <option value="domain">Domain</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Value</label>
                <input
                  type="text"
                  value={addForm.value}
                  onChange={(e) => setAddForm({ ...addForm, value: e.target.value })}
                  placeholder={
                    addForm.contact_type === 'email'
                      ? 'email@example.com'
                      : addForm.contact_type === 'phone'
                      ? '+1234567890'
                      : 'example.com'
                  }
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                <select
                  value={addForm.reason}
                  onChange={(e) => setAddForm({ ...addForm, reason: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="manual">Manual</option>
                  <option value="unsubscribe">Unsubscribed</option>
                  <option value="bounce">Bounced</option>
                  <option value="spam_report">Spam Report</option>
                  <option value="complaint">Complaint</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
                <input
                  type="text"
                  value={addForm.description}
                  onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
                  placeholder="Why is this contact suppressed?"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleAdd}
                disabled={!addForm.value}
                className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
              >
                Add to Suppression List
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <h2 className="text-lg font-semibold mb-4">Import Suppression List</h2>
            <p className="text-sm text-gray-500 mb-4">
              Paste CSV content or upload a file. Supported formats: one email per line, or CSV with
              columns: contact_type, value, reason, description.
            </p>
            <div className="space-y-4">
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.txt"
                  onChange={handleFileUpload}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
              <textarea
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
                placeholder="email1@example.com&#10;email2@example.com&#10;+1234567890&#10;..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono h-40"
              />
              {importResult && (
                <div className="bg-gray-50 rounded-lg p-3 text-sm">
                  <p>✅ Added: {importResult.added}</p>
                  <p>⏭️ Skipped (already suppressed): {importResult.skipped}</p>
                  {importResult.errors > 0 && <p>❌ Errors: {importResult.errors}</p>}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowImportModal(false);
                  setImportResult(null);
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={!importText.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Import
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Check Modal */}
      {showCheckModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Check Suppression Status</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={checkEmail}
                  onChange={(e) => setCheckEmail(e.target.value)}
                  placeholder="email@example.com"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                />
              </div>
              {checkResult && (
                <div
                  className={clsx(
                    'rounded-lg p-4 text-sm',
                    checkResult.is_suppressed ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
                  )}
                >
                  {checkResult.is_suppressed ? (
                    <>
                      <p className="font-semibold">🚫 This email IS suppressed</p>
                      {checkResult.matches?.map((m: any, i: number) => (
                        <p key={i} className="mt-2">
                          Type: {m.type} • Reason: {m.reason}
                          {m.description && <> • {m.description}</>}
                        </p>
                      ))}
                    </>
                  ) : (
                    <p className="font-semibold">✅ This email is NOT suppressed</p>
                  )}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowCheckModal(false);
                  setCheckResult(null);
                  setCheckEmail('');
                }}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Close
              </button>
              <button
                onClick={handleCheck}
                disabled={!checkEmail}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                Check
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
