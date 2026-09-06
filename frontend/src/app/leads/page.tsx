'use client';

import { useEffect, useState } from 'react';
import { clsx } from 'clsx';

interface Lead {
  id: number;
  business_name: string;
  business_type: string;
  city: string;
  state: string;
  phone: string;
  email: string;
  rating: number;
  review_count: number;
  status: string;
  demo_url: string;
  lead_score: number;
  created_at: string;
}

const statusColors: Record<string, string> = {
  discovered: 'bg-gray-100 text-gray-700',
  enriched: 'bg-blue-100 text-blue-700',
  demo_created: 'bg-purple-100 text-purple-700',
  outreach_queued: 'bg-yellow-100 text-yellow-700',
  email_sent: 'bg-green-100 text-green-700',
  followup_sent: 'bg-green-100 text-green-700',
  interested: 'bg-emerald-100 text-emerald-700',
  not_interested: 'bg-red-100 text-red-700',
  converted: 'bg-green-100 text-green-700',
  do_not_contact: 'bg-red-100 text-red-700',
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [cityFilter, setCityFilter] = useState('');
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchLeads = () => {
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    if (cityFilter) params.set('city', cityFilter);
    params.set('limit', '100');

    fetch(`/api/leads?${params}`)
      .then((res) => res.json())
      .then(setLeads)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLeads();
  }, [statusFilter, cityFilter]);

  const handleAction = async (leadId: number, action: string) => {
    setActionLoading(leadId);
    try {
      const res = await fetch(`/api/${action}/${leadId}`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        fetchLeads(); // Refresh the list
      } else {
        alert(data.detail || 'Action failed');
      }
    } catch (err) {
      alert('Network error');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
        <div className="flex gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Statuses</option>
            <option value="discovered">Discovered</option>
            <option value="enriched">Enriched</option>
            <option value="demo_created">Demo Created</option>
            <option value="email_sent">Email Sent</option>
            <option value="interested">Interested</option>
            <option value="not_interested">Not Interested</option>
          </select>
          <input
            type="text"
            placeholder="Filter by city..."
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading leads...</div>
      ) : leads.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No leads found</p>
          <a
            href="/campaigns/new"
            className="mt-4 inline-block text-blue-600 hover:underline"
          >
            Create a campaign to start finding leads
          </a>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Business</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Location</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Contact</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Reviews</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Status</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{lead.business_name}</div>
                    <div className="text-sm text-gray-500">{lead.business_type}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {lead.city}, {lead.state}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {lead.phone && <div className="text-gray-600">📞 {lead.phone}</div>}
                    {lead.email && <div className="text-gray-600">✉️ {lead.email}</div>}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {lead.rating ? `⭐ ${lead.rating}` : '—'}{' '}
                    {lead.review_count ? `(${lead.review_count})` : ''}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        statusColors[lead.status] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {lead.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      {lead.status === 'discovered' && (
                        <button
                          onClick={() => handleAction(lead.id, 'enrich')}
                          disabled={actionLoading === lead.id}
                          className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded hover:bg-blue-100"
                        >
                          Enrich
                        </button>
                      )}
                      {lead.status === 'enriched' && (
                        <button
                          onClick={() => handleAction(lead.id, 'demo')}
                          disabled={actionLoading === lead.id}
                          className="text-xs bg-purple-50 text-purple-600 px-2 py-1 rounded hover:bg-purple-100"
                        >
                          Generate Demo
                        </button>
                      )}
                      {lead.status === 'demo_created' && (
                        <button
                          onClick={() => handleAction(lead.id, 'outreach/cold-email')}
                          disabled={actionLoading === lead.id}
                          className="text-xs bg-green-50 text-green-600 px-2 py-1 rounded hover:bg-green-100"
                        >
                          Send Email
                        </button>
                      )}
                      {lead.demo_url && (
                        <a
                          href={lead.demo_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs bg-gray-50 text-gray-600 px-2 py-1 rounded hover:bg-gray-100"
                        >
                          View Demo
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
