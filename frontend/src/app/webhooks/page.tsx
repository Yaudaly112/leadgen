'use client';

import { useEffect, useState } from 'react';
import { clsx } from 'clsx';

interface WebhookEvent {
  id: number;
  event_type: string;
  message_id: string;
  email: string;
  outreach_log_id: number;
  campaign_id: number;
  reason: string;
  url: string;
  ip_address: string;
  user_agent: string;
  raw_event: Record<string, any>;
  event_timestamp: string;
  created_at: string;
}

const eventColors: Record<string, string> = {
  delivered: 'bg-green-100 text-green-700',
  open: 'bg-blue-100 text-blue-700',
  click: 'bg-purple-100 text-purple-700',
  bounce: 'bg-red-100 text-red-700',
  dropped: 'bg-red-100 text-red-700',
  spamreport: 'bg-red-100 text-red-700',
  unsubscribe: 'bg-orange-100 text-orange-700',
  deferred: 'bg-yellow-100 text-yellow-700',
  processed: 'bg-gray-100 text-gray-700',
  test: 'bg-gray-100 text-gray-500',
};

export default function WebhooksPage() {
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<WebhookEvent | null>(null);
  const [testPayload, setTestPayload] = useState('');
  const [testResult, setTestResult] = useState<string | null>(null);

  const fetchEvents = () => {
    const params = new URLSearchParams();
    if (typeFilter) params.set('event_type', typeFilter);
    params.set('limit', '100');

    fetch(`/api/webhooks/events?${params}`)
      .then((res) => res.json())
      .then(setEvents)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchEvents();
  }, [typeFilter]);

  const handleTestWebhook = async () => {
    try {
      const events = JSON.parse(testPayload);
      const res = await fetch('/api/webhooks/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events: Array.isArray(events) ? events : [events] }),
      });
      const data = await res.json();
      setTestResult(JSON.stringify(data, null, 2));
      fetchEvents();
    } catch (err) {
      setTestResult('Error: Invalid JSON or network error');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Webhook Events</h1>
          <p className="text-sm text-gray-500 mt-1">
            SendGrid event webhook log — tracks delivery, opens, clicks, bounces, and replies
          </p>
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Events</option>
          <option value="delivered">Delivered</option>
          <option value="open">Opened</option>
          <option value="click">Clicked</option>
          <option value="bounce">Bounced</option>
          <option value="dropped">Dropped</option>
          <option value="spamreport">Spam Report</option>
          <option value="unsubscribe">Unsubscribed</option>
        </select>
      </div>

      {/* Test Webhook */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Test Webhook</h2>
        <p className="text-sm text-gray-500 mb-3">
          Paste a SendGrid event payload to test processing locally.
        </p>
        <div className="flex gap-4">
          <textarea
            value={testPayload}
            onChange={(e) => setTestPayload(e.target.value)}
            placeholder='[{"event":"open","email":"test@example.com","sg_message_id":"abc123.filter000","timestamp":1700000000,"custom_args":{"outreach_log_id":"1"}}]'
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono h-24"
          />
          <div className="flex flex-col gap-2">
            <button
              onClick={handleTestWebhook}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              Send Test
            </button>
            {testResult && (
              <pre className="text-xs bg-gray-50 rounded-lg p-2 max-h-32 overflow-auto">
                {testResult}
              </pre>
            )}
          </div>
        </div>
      </div>

      {/* Events Table */}
      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading events...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No webhook events yet</p>
          <p className="text-sm text-gray-400 mt-2">
            Configure your SendGrid Event Webhook to point to:{' '}
            <code className="bg-gray-100 px-1 rounded">/api/webhooks/sendgrid</code>
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Event</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Email</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Log ID</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Message ID</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Details</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {events.map((event) => (
                <tr
                  key={event.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedEvent(selectedEvent?.id === event.id ? null : event)}
                >
                  <td className="px-4 py-3">
                    <span
                      className={clsx(
                        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                        eventColors[event.event_type] || 'bg-gray-100 text-gray-700'
                      )}
                    >
                      {event.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{event.email}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {event.outreach_log_id ? `#${event.outreach_log_id}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400 font-mono">
                    {event.message_id?.substring(0, 16)}...
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {event.reason && <span className="text-red-600">{event.reason}</span>}
                    {event.url && (
                      <span className="text-purple-600 truncate max-w-[200px] block">
                        🔗 {event.url}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {new Date(event.event_timestamp || event.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Expanded raw event detail */}
          {selectedEvent && (
            <div className="border-t border-gray-200 p-4 bg-gray-50">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Raw Event Payload</h3>
              <pre className="text-xs bg-white rounded-lg p-4 overflow-auto max-h-64 border border-gray-200">
                {JSON.stringify(selectedEvent.raw_event, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
