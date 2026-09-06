'use client';

import { useEffect, useState } from 'react';

interface PendingOutreach {
  id: number;
  lead_id: number;
  outreach_type: string;
  subject: string;
  body: string;
  template_used: string;
  created_at: string;
}

export default function ApprovalPage() {
  const [pending, setPending] = useState<PendingOutreach[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState<number | null>(null);

  const fetchPending = () => {
    fetch('/api/outreach/pending')
      .then((res) => res.json())
      .then(setPending)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleApprove = async (logId: number) => {
    setApproving(logId);
    try {
      const res = await fetch(`/api/outreach/approve/${logId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved_by: 'manual_review' }),
      });
      if (res.ok) {
        fetchPending();
      }
    } catch (err) {
      alert('Failed to approve');
    } finally {
      setApproving(null);
    }
  };

  const handleReject = async (leadId: number) => {
    try {
      await fetch(`/api/outreach/not-interested/${leadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Rejected during manual review' }),
      });
      fetchPending();
    } catch (err) {
      alert('Failed to reject');
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Pending Approval</h1>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : pending.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No emails pending approval</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pending.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-gray-200 p-6"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full">
                    {item.outreach_type}
                  </span>
                  <h3 className="text-lg font-semibold text-gray-900 mt-2">
                    {item.subject}
                  </h3>
                  <p className="text-sm text-gray-500">
                    Template: {item.template_used} • Lead #{item.lead_id}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleApprove(item.id)}
                    disabled={approving === item.id}
                    className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                  >
                    {approving === item.id ? 'Sending...' : '✓ Approve & Send'}
                  </button>
                  <button
                    onClick={() => handleReject(item.lead_id)}
                    className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-100"
                  >
                    ✕ Reject
                  </button>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
                  {item.body}
                </pre>
              </div>

              <p className="text-xs text-gray-400 mt-3">
                Created: {new Date(item.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
