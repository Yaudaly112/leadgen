'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import { useAuth } from '@/lib/auth';

const navigation = [
  { name: 'Dashboard', href: '/', icon: '📊' },
  { name: 'Pipeline Runner', href: '/pipeline', icon: '🚀' },
  { name: 'Campaigns', href: '/campaigns', icon: '🎯' },
  { name: 'Leads', href: '/leads', icon: '👥' },
  { name: 'Pending Approval', href: '/approval', icon: '✉️' },
  { name: 'Webhook Events', href: '/webhooks', icon: '📡' },
  { name: 'Suppression List', href: '/suppression', icon: '🚫' },
  { name: 'Settings', href: '/settings', icon: '⚙️' },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-xl font-bold text-gray-900">🎯 LeadGen AI</h1>
        <p className="text-sm text-gray-500 mt-1">Website Outreach Agent</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              pathname === item.href
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            )}
          >
            <span>{item.icon}</span>
            {item.name}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-200">
        {user && (
          <div className="mb-3">
            <div className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-bold">
                {(user.full_name || user.username).charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user.full_name || user.username}
                </p>
                <p className="text-xs text-gray-500 truncate">{user.role}</p>
              </div>
            </div>
          </div>
        )}
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">v0.1.0</p>
          <button
            onClick={logout}
            className="text-xs text-red-500 hover:text-red-700 font-medium"
          >
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}
