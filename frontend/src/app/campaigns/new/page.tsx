'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

const US_CITIES = [
  { city: 'New York', state: 'NY' },
  { city: 'Los Angeles', state: 'CA' },
  { city: 'Chicago', state: 'IL' },
  { city: 'Houston', state: 'TX' },
  { city: 'Phoenix', state: 'AZ' },
  { city: 'Philadelphia', state: 'PA' },
  { city: 'San Antonio', state: 'TX' },
  { city: 'San Diego', state: 'CA' },
  { city: 'Dallas', state: 'TX' },
  { city: 'Austin', state: 'TX' },
];

const BUSINESS_CATEGORIES = [
  'Plumber',
  'Dentist',
  'Electrician',
  'HVAC',
  'Landscaping',
  'Auto Repair',
  'Hair Salon',
  'Restaurant',
  'Gym',
  'Pet Grooming',
  'Cleaning Service',
  'Roofing',
  'Painter',
  'Locksmith',
  'Pest Control',
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    target_city: '',
    target_state: '',
    target_category: '',
    custom_city: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const city = form.custom_city || form.target_city;
    const data = {
      name: form.name || `${form.target_category} - ${city}`,
      target_city: city,
      target_state: form.target_state,
      target_category: form.target_category,
    };

    try {
      const res = await fetch('/api/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (res.ok) {
        const campaign = await res.json();
        router.push(`/campaigns/${campaign.id}`);
      } else {
        alert('Failed to create campaign');
      }
    } catch (err) {
      alert('Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">New Campaign</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Campaign Name (optional)
          </label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g., Plumbers in Austin - Q4 2024"
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Business Category *
          </label>
          <select
            required
            value={form.target_category}
            onChange={(e) => setForm({ ...form, target_category: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          >
            <option value="">Select a category...</option>
            {BUSINESS_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target City *
          </label>
          <select
            value={form.target_city}
            onChange={(e) => setForm({ ...form, target_city: e.target.value })}
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          >
            <option value="">Select a city...</option>
            {US_CITIES.map((c) => (
              <option key={c.city} value={c.city}>
                {c.city}, {c.state}
              </option>
            ))}
            <option value="custom">Other (enter below)</option>
          </select>
        </div>

        {form.target_city === 'custom' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              City Name
            </label>
            <input
              type="text"
              required
              value={form.custom_city}
              onChange={(e) => setForm({ ...form, custom_city: e.target.value })}
              placeholder="Enter city name"
              className="w-full border border-gray-300 rounded-lg px-4 py-2"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            State *
          </label>
          <input
            type="text"
            required
            value={form.target_state}
            onChange={(e) => setForm({ ...form, target_state: e.target.value.toUpperCase() })}
            placeholder="e.g., TX"
            maxLength={2}
            className="w-full border border-gray-300 rounded-lg px-4 py-2"
          />
        </div>

        <div className="bg-blue-50 rounded-lg p-4 text-sm text-blue-700">
          <strong>What happens next:</strong>
          <ol className="mt-2 space-y-1 list-decimal list-inside">
            <li>We'll discover {form.target_category || 'businesses'} in {form.target_city || 'the target city'} without websites</li>
            <li>AI will enrich each lead with descriptions and content</li>
            <li>A demo website will be generated for each lead</li>
            <li>You'll review and approve personalized emails before they're sent</li>
          </ol>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating Campaign...' : 'Create Campaign'}
        </button>
      </form>
    </div>
  );
}
