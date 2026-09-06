import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { AuthGuard } from '@/components/AuthGuard';

export const metadata: Metadata = {
  title: 'LeadGen AI - Dashboard',
  description: 'AI-powered lead generation for businesses without websites',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50">
        <AuthProvider>
          <AuthGuard>{children}</AuthGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
