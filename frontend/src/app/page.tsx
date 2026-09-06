'use client';

import { useEffect, useState } from 'react';
import { StatsCard } from '@/components/StatsCard';

interface DashboardStats {
  total_leads: number;
  total_campaigns: number;
  pending_approval: number;
  emails_sent: number;
  suppressed_contacts: number;
  running_pipelines: number;
  status_counts: Record<string, number>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/stats/dashboard')
      .then((res) => res.json())
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Dashboard</h1>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Total Leads"
          value={stats?.total_leads ?? 0}
          icon="👥"
          color="blue"
        />
        <StatsCard
          title="Campaigns"
          value={stats?.total_campaigns ?? 0}
          icon="🎯"
          color="green"
        />
        <StatsCard
          title="Pending Approval"
          value={stats?.pending_approval ?? 0}
          icon="✉️"
          color="yellow"
        />
        <StatsCard
          title="Emails Sent"
          value={stats?.emails_sent ?? 0}
          icon="📧"
          color="purple"
        />
        <StatsCard
          title="Suppressed"
          value={stats?.suppressed_contacts ?? 0}
          icon="🚫"
          color="red"
        />
        <StatsCard
          title="Running Pipelines"
          value={stats?.running_pipelines ?? 0}
          icon="🚀"
          color="blue"
        />
      </div>

      {/* Pipeline Status */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Status</h2>
        <div className="space-y-3">
          {Object.entries(stats?.status_counts ?? {}).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between">
              <span className="text-sm text-gray-600 capitalize">
                {status.replace(/_/g, ' ')}
              </span>
              <div className="flex items-center gap-3">
                <div className="w-48 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all"
                    style={{
                      width: `${Math.min(
                        100,
                        ((count as number) / Math.max(stats?.total_leads ?? 1, 1)) * 100
                      )}%`,
                    }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900 w-8 text-right">
                  {count as number}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <a
            href="/pipeline"
            className="flex items-center gap-3 p-4 border-2 border-blue-200 rounded-lg hover:bg-blue-50 transition-colors"
          >
            <span className="text-2xl">🚀</span>
            <div>
              <div className="font-medium text-gray-900">Run Pipeline</div>
              <div className="text-sm text-gray-500">Full pipeline: discover → enrich → demo → email</div>
            </div>
          </a>
          <a
            href="/campaigns/new"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl">➕</span>
            <div>
              <div className="font-medium text-gray-900">New Campaign</div>
              <div className="text-sm text-gray-500">Start a new discovery campaign</div>
            </div>
          </a>
          <a
            href="/leads"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl">🔍</span>
            <div>
              <div className="font-medium text-gray-900">Review Leads</div>
              <div className="text-sm text-gray-500">Approve or edit leads</div>
            </div>
          </a>
          <a
            href="/approval"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl">✉️</span>
            <div>
              <div className="font-medium text-gray-900">Pending Emails</div>
              <div className="text-sm text-gray-500">Review emails before sending</div>
            </div>
          </a>
          <a
            href="/suppression"
            className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <span className="text-2xl">🚫</span>
            <div>
              <div className="font-medium text-gray-900">Suppression List</div>
              <div className="text-sm text-gray-500">Manage do-not-contact list</div>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}
