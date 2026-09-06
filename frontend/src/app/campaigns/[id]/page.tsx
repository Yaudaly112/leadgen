'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

interface CampaignStats {
  campaign: {
    id: number;
    name: string;
    target_city: string;
    target_state: string;
    target_category: string;
    status: string;
  };
  total_leads: number;
  leads_by_status: Record<string, number>;
  outreach: {
    total: number;
    emails_sent: number;
    calls_made: number;
    replies: number;
    pending_approval: number;
  };
}

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id;

  const [stats, setStats] = useState<CampaignStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [runningAction, setRunningAction] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/stats/campaign/${campaignId}`)
      .then((res) => res.json())
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [campaignId]);

  const runPipelineStep = async (action: string) => {
    setRunningAction(action);
    try {
      let url = '';
      let body: any = {};

      switch (action) {
        case 'discover':
          url = `/api/discover/${campaignId}`;
          break;
        case 'enrich':
          url = `/api/tasks/enrich-batch/${campaignId}`;
          break;
        case 'generate-demos':
          url = `/api/tasks/generate-demos-batch/${campaignId}`;
          break;
      }

      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      const data = await res.json();
      alert(data.status || data.detail || 'Action started');
    } catch (err) {
      alert('Failed to start action');
    } finally {
      setRunningAction(null);
    }
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Loading...</div>;
  }

  if (!stats) {
    return <div className="text-center py-12 text-gray-500">Campaign not found</div>;
  }

  const { campaign } = stats;

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
          <p className="text-gray-500 mt-1">
            📍 {campaign.target_city}, {campaign.target_state} • 🏷️ {campaign.target_category}
          </p>
        </div>
        <span
          className={`text-sm px-3 py-1 rounded-full ${
            campaign.status === 'active'
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {campaign.status}
        </span>
      </div>

      {/* Pipeline Actions */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Actions</h2>
        <div className="flex flex-wrap gap-3">
          <a
            href={`/pipeline?campaign=${campaignId}`}
            className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            🚀 Run Full Pipeline
          </a>
          <button
            onClick={() => runPipelineStep('discover')}
            disabled={runningAction === 'discover'}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            {runningAction === 'discover' ? '⏳ Discovering...' : '🔍 Discover Only'}
          </button>
          <button
            onClick={() => runPipelineStep('enrich')}
            disabled={runningAction === 'enrich' || stats.total_leads === 0}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            {runningAction === 'enrich' ? '⏳ Enriching...' : '✨ Enrich Only'}
          </button>
          <button
            onClick={() => runPipelineStep('generate-demos')}
            disabled={runningAction === 'generate-demos'}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
          >
            {runningAction === 'generate-demos' ? '⏳ Generating...' : '🎨 Generate Demos Only'}
          </button>
          <a
            href={`/leads?campaign=${campaignId}`}
            className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-200"
          >
            👥 View Leads
          </a>
          <a
            href="/approval"
            className="bg-yellow-100 text-yellow-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-yellow-200"
          >
            ✉️ Review Emails ({stats.outreach.pending_approval})
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Leads by Status</h3>
          <div className="space-y-2">
            {Object.entries(stats.leads_by_status).map(([status, count]) => (
              count > 0 && (
                <div key={status} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 capitalize">{status.replace(/_/g, ' ')}</span>
                  <span className="font-medium">{count as number}</span>
                </div>
              )
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Outreach Stats</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Total Outreach</span>
              <span className="font-medium">{stats.outreach.total}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Emails Sent</span>
              <span className="font-medium">{stats.outreach.emails_sent}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Calls Made</span>
              <span className="font-medium">{stats.outreach.calls_made}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Replies</span>
              <span className="font-medium">{stats.outreach.replies}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Pending Approval</span>
              <span className="font-medium text-yellow-600">
                {stats.outreach.pending_approval}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
