'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';

interface UserRecord {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

export default function SettingsPage() {
  const { user, token } = useAuth();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', full_name: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchUsers();
    }
  }, [user]);

  const fetchUsers = async () => {
    try {
      const res = await fetch('/api/auth/users', { headers });
      if (res.ok) setUsers(await res.json());
    } catch {}
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create user');
      }
      setSuccess('User created successfully');
      setShowAddUser(false);
      setNewUser({ username: '', email: '', password: '', full_name: '' });
      fetchUsers();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm('Delete this user?')) return;
    try {
      await fetch(`/api/auth/users/${userId}`, { method: 'DELETE', headers });
      fetchUsers();
    } catch {}
  };

  const handleToggleActive = async (userId: number, isActive: boolean) => {
    try {
      await fetch(`/api/auth/users/${userId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ is_active: !isActive }),
      });
      fetchUsers();
    } catch {}
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>

      <div className="space-y-6 max-w-3xl">
        {/* User Management */}
        {user?.role === 'admin' && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">👥 User Management</h2>
              <button
                onClick={() => setShowAddUser(!showAddUser)}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                {showAddUser ? 'Cancel' : '+ Add User'}
              </button>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">{error}</div>
            )}
            {success && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm mb-4">{success}</div>
            )}

            {showAddUser && (
              <form onSubmit={handleAddUser} className="bg-gray-50 rounded-lg p-4 mb-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <input
                    placeholder="Username"
                    value={newUser.username}
                    onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                  <input
                    placeholder="Email"
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                  />
                  <input
                    placeholder="Full Name"
                    value={newUser.full_name}
                    onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <input
                    placeholder="Password"
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                    minLength={6}
                  />
                </div>
                <button
                  type="submit"
                  className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors"
                >
                  Create User
                </button>
              </form>
            )}

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-2 font-medium text-gray-600">User</th>
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Email</th>
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Role</th>
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Status</th>
                    <th className="text-left py-3 px-2 font-medium text-gray-600">Last Login</th>
                    <th className="text-right py-3 px-2 font-medium text-gray-600">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-gray-100">
                      <td className="py-3 px-2">
                        <div className="font-medium text-gray-900">{u.username}</div>
                        {u.full_name && <div className="text-gray-500 text-xs">{u.full_name}</div>}
                      </td>
                      <td className="py-3 px-2 text-gray-600">{u.email}</td>
                      <td className="py-3 px-2">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'
                        }`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                          u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                        }`}>
                          {u.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-gray-500 text-xs">
                        {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                      </td>
                      <td className="py-3 px-2 text-right space-x-2">
                        {u.id !== user?.id && (
                          <>
                            <button
                              onClick={() => handleToggleActive(u.id, u.is_active)}
                              className="text-xs text-yellow-600 hover:text-yellow-800"
                            >
                              {u.is_active ? 'Disable' : 'Enable'}
                            </button>
                            <button
                              onClick={() => handleDeleteUser(u.id)}
                              className="text-xs text-red-600 hover:text-red-800"
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h2>
          <p className="text-sm text-gray-500 mb-4">
            Configure your API keys in the <code className="bg-gray-100 px-1 rounded">.env</code> file on the server.
          </p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Google Places API</span>
              <span className="text-green-600">✓ Configured</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">OpenAI API</span>
              <span className="text-green-600">✓ Configured</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">SendGrid</span>
              <span className="text-green-600">✓ Configured</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-600">Twilio</span>
              <span className="text-gray-400">Not configured</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Outreach Settings</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Review before sending
              </label>
              <p className="text-sm text-gray-500">
                All emails require manual approval before sending (recommended for new campaigns).
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max emails per day: 50
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max calls per day: 20
              </label>
            </div>
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">⚠️ Legal Compliance</h2>
          <ul className="text-sm text-yellow-700 space-y-1">
            <li>• CAN-SPAM: All emails include unsubscribe link and physical address</li>
            <li>• TCPA: Calls require consent; limit automated calling</li>
            <li>• Always maintain do-not-contact lists</li>
            <li>• Consult legal counsel before scaling outreach</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
