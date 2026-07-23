import './globals.css';

export const metadata = {
  title: 'doc-sync-agent — dashboard',
  description: 'Documentation Generator & Sync Agent',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
