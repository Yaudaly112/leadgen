'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Campaign {
  id: number;
  name: string;
  target_city: string;
  target_state: string;
  target_category: string;
  status: string;
  total_leads: number;
  emails_sent: number;
  calls_made: number;
  replies_received: number;
  conversions: number;
  created_at: string;
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/campaigns')
      .then((res) => res.json())
      .then(setCampaigns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <Link
          href="/campaigns/new"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + New Campaign
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading...</div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">No campaigns yet</p>
          <Link href="/campaigns/new" className="text-blue-600 hover:underline">
            Create your first campaign
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {campaigns.map((campaign) => (
            <Link
              key={campaign.id}
              href={`/campaigns/${campaign.id}`}
              className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900">{campaign.name}</h3>
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    campaign.status === 'active'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {campaign.status}
                </span>
              </div>
              <p className="text-sm text-gray-500 mb-4">
                📍 {campaign.target_city}, {campaign.target_state}
                <br />
                🏷️ {campaign.target_category}
              </p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-gray-600">
                  <span className="font-medium text-gray-900">{campaign.total_leads}</span> leads
                </div>
                <div className="text-gray-600">
                  <span className="font-medium text-gray-900">{campaign.emails_sent}</span> emails
                </div>
                <div className="text-gray-600">
                  <span className="font-medium text-gray-900">{campaign.replies_received}</span> replies
                </div>
                <div className="text-gray-600">
                  <span className="font-medium text-gray-900">{campaign.conversions}</span> converted
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
