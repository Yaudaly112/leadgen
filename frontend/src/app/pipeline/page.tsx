'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { clsx } from 'clsx';

interface PipelineRun {
  id: number;
  campaign_id: number;
  status: string;
  started_at: string;
  completed_at: string;
  discovery_status: string;
  discovery_new: number;
  enrichment_status: string;
  enrichment_total: number;
  enrichment_done: number;
  enrichment_errors: number;
  demo_status: string;
  demo_total: number;
  demo_done: number;
  demo_errors: number;
  email_status: string;
  email_total: number;
  email_sent: number;
  email_queued: number;
  email_suppressed: number;
  email_errors: number;
  error_log: Array<{ step: string; lead_id?: number; error: string }> | null;
  created_at: string;
  updated_at: string;
}

interface Campaign {
  id: number;
  name: string;
  target_city: string;
  target_state: string;
  target_category: string;
}

const statusConfig: Record<string, { color: string; label: string; icon: string }> = {
  pending: { color: 'bg-gray-100 text-gray-600', label: 'Pending', icon: '⏳' },
  running: { color: 'bg-blue-100 text-blue-700', label: 'Running', icon: '🔄' },
  completed: { color: 'bg-green-100 text-green-700', label: 'Completed', icon: '✅' },
  completed_with_errors: { color: 'bg-yellow-100 text-yellow-700', label: 'Done (with errors)', icon: '⚠️' },
  failed: { color: 'bg-red-100 text-red-700', label: 'Failed', icon: '❌' },
  cancelled: { color: 'bg-gray-100 text-gray-500', label: 'Cancelled', icon: '🚫' },
  skipped: { color: 'bg-gray-100 text-gray-400', label: 'Skipped', icon: '⏭️' },
};

const PIPELINE_STEPS = [
  { key: 'discovery', label: 'Discover Leads', icon: '🔍', description: 'Find businesses without websites' },
  { key: 'enrichment', label: 'Enrich Leads', icon: '✨', description: 'Generate AI descriptions & content' },
  { key: 'demo', label: 'Generate Demos', icon: '🎨', description: 'Build one-page demo websites' },
  { key: 'email', label: 'Send Emails', icon: '📧', description: 'Personalized cold outreach' },
];

export default function PipelinePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [runs, setRuns] = useState<PipelineRun[]>([]);
  const [activeRun, setActiveRun] = useState<PipelineRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCampaign, setSelectedCampaign] = useState<number | null>(null);
  const [options, setOptions] = useState({
    skip_discovery: false,
    skip_enrichment: false,
    skip_demo: false,
    skip_email: false,
  });
  const [starting, setStarting] = useState(false);
  const [startTime, setStartTime] = useState<string>('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const fetchCampaigns = () => {
    fetch('/api/campaigns')
      .then((res) => res.json())
      .then(setCampaigns)
      .catch(console.error);
  };

  const fetchRuns = () => {
    fetch('/api/pipeline/runs?limit=20')
      .then((res) => res.json())
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCampaigns();
    fetchRuns();
  }, []);

  // Auto-refresh runs list every 10s
  useEffect(() => {
    const interval = setInterval(fetchRuns, 10000);
    return () => clearInterval(interval);
  }, []);

  const connectSSE = useCallback((runId: number) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(`/api/pipeline/runs/${runId}/stream`);
    eventSourceRef.current = es;

    es.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setActiveRun((prev) => (prev ? { ...prev, ...data } : null));
    });

    es.addEventListener('done', (e) => {
      const data = JSON.parse(e.data);
      setActiveRun((prev) => (prev ? { ...prev, ...data } : null));
      es.close();
      fetchRuns();
    });

    es.addEventListener('error', () => {
      es.close();
      fetchRuns();
    });
  }, []);

  // Connect SSE when viewing an active run
  useEffect(() => {
    if (activeRun && (activeRun.status === 'running' || activeRun.status === 'pending')) {
      connectSSE(activeRun.id);
    }
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [activeRun?.id, activeRun?.status, connectSSE]);

  const handleStartPipeline = async () => {
    if (!selectedCampaign) return;
    setStarting(true);
    try {
      const res = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign_id: selectedCampaign,
          ...options,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        // Fetch the run details
        const runRes = await fetch(`/api/pipeline/runs/${data.run_id}`);
        const runData = await runRes.json();
        setActiveRun(runData);
        setStartTime(new Date().toLocaleTimeString());
        fetchRuns();
      } else {
        const err = await res.json();
        alert(err.detail || 'Failed to start pipeline');
      }
    } catch (err) {
      alert('Network error');
    } finally {
      setStarting(false);
    }
  };

  const handleViewRun = async (runId: number) => {
    const res = await fetch(`/api/pipeline/runs/${runId}`);
    const data = await res.json();
    setActiveRun(data);
    setStartTime(new Date(data.started_at || data.created_at).toLocaleTimeString());
  };

  const handleCancel = async (runId: number) => {
    if (!confirm('Cancel this pipeline run?')) return;
    await fetch(`/api/pipeline/runs/${runId}`, { method: 'DELETE' });
    fetchRuns();
    if (activeRun?.id === runId) {
      setActiveRun((prev) => (prev ? { ...prev, status: 'cancelled' } : null));
    }
  };

  const getStepProgress = (run: PipelineRun, step: string) => {
    const s = step === 'discovery' ? 'discovery' : step === 'enrichment' ? 'enrichment' : step === 'demo' ? 'demo' : 'email';
    const status = run[`${s}_status` as keyof PipelineRun] as string;
    const total = run[`${s}_total` as keyof PipelineRun] as number;
    const done = run[`${s}_done` as keyof PipelineRun] as number || run[`${s}_new` as keyof PipelineRun] as number || run[`${s}_sent` as keyof PipelineRun] as number || run[`${s}_queued` as keyof PipelineRun] as number || 0;

    if (status === 'skipped') return { percent: 100, status: 'skipped', done: 0, total: 0 };
    if (status === 'completed') return { percent: 100, status: 'completed', done: total, total };
    if (status === 'failed') return { percent: 100, status: 'failed', done, total };
    if (total > 0) return { percent: Math.round((done / total) * 100), status: 'running', done, total };
    return { percent: 0, status: status === 'running' ? 'starting' : 'pending', done: 0, total: 0 };
  };

  const isRunning = activeRun?.status === 'running' || activeRun?.status === 'pending';

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pipeline Runner</h1>
          <p className="text-sm text-gray-500 mt-1">
            Run the full pipeline: discover → enrich → generate demos → send emails
          </p>
        </div>
      </div>

      {/* Start New Pipeline */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">🚀 Start New Pipeline</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Campaign</label>
            <select
              value={selectedCampaign || ''}
              onChange={(e) => setSelectedCampaign(Number(e.target.value) || null)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="">Select a campaign...</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} — {c.target_city}, {c.target_state}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Steps to run</label>
            <div className="space-y-2">
              {[
                { key: 'skip_discovery', label: '🔍 Discovery' },
                { key: 'skip_enrichment', label: '✨ Enrichment' },
                { key: 'skip_demo', label: '🎨 Demo Generation' },
                { key: 'skip_email', label: '📧 Email Outreach' },
              ].map((step) => (
                <label key={step.key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={!options[step.key as keyof typeof options]}
                    onChange={(e) =>
                      setOptions({ ...options, [step.key]: !e.target.checked })
                    }
                    className="rounded"
                  />
                  {step.label}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-4">
          <button
            onClick={handleStartPipeline}
            disabled={!selectedCampaign || starting || isRunning}
            className={clsx(
              'px-6 py-3 rounded-lg text-sm font-medium transition-colors',
              selectedCampaign && !starting && !isRunning
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-200 text-gray-500 cursor-not-allowed'
            )}
          >
            {starting ? '⏳ Starting...' : isRunning ? '🔄 Pipeline Running' : '🚀 Run Pipeline'}
          </button>
          {isRunning && (
            <span className="text-sm text-gray-500">
              Started at {startTime} — check progress below
            </span>
          )}
        </div>
      </div>

      {/* Active Run Progress */}
      {activeRun && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Run #{activeRun.id} — Campaign #{activeRun.campaign_id}
              </h2>
              <p className="text-sm text-gray-500">
                {statusConfig[activeRun.status]?.icon}{' '}
                {statusConfig[activeRun.status]?.label || activeRun.status}
              </p>
            </div>
            {isRunning && (
              <button
                onClick={() => handleCancel(activeRun.id)}
                className="bg-red-50 text-red-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-100"
              >
                Cancel Run
              </button>
            )}
          </div>

          {/* Pipeline Steps */}
          <div className="space-y-4">
            {PIPELINE_STEPS.map((step, idx) => {
              const progress = getStepProgress(activeRun, step.key);
              const config = statusConfig[progress.status] || statusConfig.pending;

              return (
                <div key={step.key} className="flex items-center gap-4">
                  {/* Step number */}
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm font-medium text-gray-600">
                    {idx + 1}
                  </div>

                  {/* Step info */}
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">
                          {step.icon} {step.label}
                        </span>
                        <span className={clsx('text-xs px-2 py-0.5 rounded-full', config.color)}>
                          {config.label}
                        </span>
                      </div>
                      <span className="text-xs text-gray-500">
                        {progress.done > 0 && `${progress.done}/${progress.total}`}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mb-2">{step.description}</p>

                    {/* Progress bar */}
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className={clsx(
                          'h-2 rounded-full transition-all duration-500',
                          progress.status === 'completed'
                            ? 'bg-green-500'
                            : progress.status === 'failed'
                            ? 'bg-red-500'
                            : progress.status === 'skipped'
                            ? 'bg-gray-300'
                            : 'bg-blue-500'
                        )}
                        style={{ width: `${progress.percent}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Error Log */}
          {activeRun.error_log && activeRun.error_log.length > 0 && (
            <div className="mt-6 bg-red-50 rounded-lg p-4">
              <h3 className="text-sm font-medium text-red-700 mb-2">
                ⚠️ Errors ({activeRun.error_log.length})
              </h3>
              <div className="max-h-40 overflow-auto space-y-1">
                {activeRun.error_log.map((err, i) => (
                  <p key={i} className="text-xs text-red-600">
                    <span className="font-medium">{err.step}</span>
                    {err.lead_id && ` (lead #${err.lead_id})`}: {err.error}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Summary when done */}
          {activeRun.status === 'completed' || activeRun.status === 'completed_with_errors' ? (
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">{activeRun.discovery_new}</p>
                <p className="text-xs text-gray-500">Leads Found</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">{activeRun.enrichment_done}</p>
                <p className="text-xs text-gray-500">Enriched</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-900">{activeRun.demo_done}</p>
                <p className="text-xs text-gray-500">Demos Created</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{activeRun.email_sent}</p>
                <p className="text-xs text-gray-500">Emails Sent</p>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* Run History */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Run History</h2>
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No pipeline runs yet</div>
        ) : (
          <div className="space-y-3">
            {runs.map((run) => {
              const config = statusConfig[run.status] || statusConfig.pending;
              return (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-4 border border-gray-100 rounded-lg hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleViewRun(run.id)}
                >
                  <div className="flex items-center gap-4">
                    <span className={clsx('text-xs px-2.5 py-1 rounded-full font-medium', config.color)}>
                      {config.icon} {config.label}
                    </span>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Campaign #{run.campaign_id}</p>
                      <p className="text-xs text-gray-500">
                        {new Date(run.created_at).toLocaleString()}
                        {run.completed_at && ` → ${new Date(run.completed_at).toLocaleTimeString()}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-xs text-gray-500">
                    <span>🔍 {run.discovery_new}</span>
                    <span>✨ {run.enrichment_done}</span>
                    <span>🎨 {run.demo_done}</span>
                    <span className="text-green-600">📧 {run.email_sent + run.email_queued}</span>
                    {(run.status === 'running' || run.status === 'pending') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancel(run.id);
                        }}
                        className="text-red-500 hover:text-red-700 font-medium"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
