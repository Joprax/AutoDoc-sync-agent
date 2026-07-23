import Link from 'next/link';
import { notFound } from 'next/navigation';
import styles from './page.module.css';

export const dynamic = 'force-dynamic';

type Repo = {
  id: number;
  github_full_name: string;
  default_branch: string;
  docs_output_path: string;
};

type SyncRun = {
  id: number;
  commit_sha: string;
  status: string;
  symbols_changed: number;
  pr_url: string | null;
  error_message: string | null;
  created_at: string;
  finished_at: string | null;
};

type Symbol = {
  id: number;
  file_path: string;
  symbol_name: string;
  signature_hash: string;
  last_doc_content: string | null;
  last_synced_commit_sha: string | null;
  updated_at: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getRepo(id: string): Promise<Repo | null> {
  try {
    const res = await fetch(`${API_URL}/repos/`, { cache: 'no-store' });
    if (!res.ok) return null;
    const repos: Repo[] = await res.json();
    return repos.find((r) => String(r.id) === id) ?? null;
  } catch {
    return null;
  }
}

async function getSyncs(id: string): Promise<SyncRun[]> {
  try {
    const res = await fetch(`${API_URL}/repos/${id}/syncs`, { cache: 'no-store' });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

async function getSymbols(id: string): Promise<Symbol[]> {
  try {
    const res = await fetch(`${API_URL}/repos/${id}/symbols`, { cache: 'no-store' });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

function statusColor(status: string) {
  if (status === 'success') return 'var(--sage)';
  if (status === 'failed') return 'var(--terracotta)';
  return 'var(--text-muted)';
}

function timeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default async function RepoDetailPage({ params }: { params: { id: string } }) {
  const repo = await getRepo(params.id);
  if (!repo) notFound();

  const [syncs, symbols] = await Promise.all([getSyncs(params.id), getSymbols(params.id)]);

  return (
    <main className={styles.main}>
      <Link href="/" className={styles.back}>
        ← all repos
      </Link>

      <header className={styles.header}>
        <p className={styles.eyebrow}>{repo.default_branch}</p>
        <h1 className={styles.title}>{repo.github_full_name}</h1>
      </header>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Sync history</h2>
        {syncs.length === 0 ? (
          <p className={styles.emptyText}>No pushes synced yet — waiting for the first webhook.</p>
        ) : (
          <ul className={styles.runList}>
            {syncs.map((run) => (
              <li key={run.id} className={styles.runItem}>
                <div className={styles.runLine}>
                  <span
                    className={styles.runDot}
                    style={{ background: statusColor(run.status) }}
                  />
                  <span className={styles.runHash}>{run.commit_sha.slice(0, 7)}</span>
                  <span className={styles.runStatus} style={{ color: statusColor(run.status) }}>
                    {run.status}
                  </span>
                  <span className={styles.runSymbols}>
                    {run.symbols_changed > 0 ? `+${run.symbols_changed} symbols` : 'no signature changes'}
                  </span>
                  <span className={styles.runTime}>{timeAgo(run.created_at)}</span>
                </div>
                {run.pr_url && (
                  <a href={run.pr_url} target="_blank" rel="noreferrer" className={styles.prLink}>
                    view pull request →
                  </a>
                )}
                {run.error_message && (
                  <p className={styles.errorText}>{run.error_message.split('\n')[0]}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Documented symbols ({symbols.length})</h2>
        {symbols.length === 0 ? (
          <p className={styles.emptyText}>Nothing documented yet.</p>
        ) : (
          <ul className={styles.symbolList}>
            {symbols.map((sym) => (
              <li key={sym.id} className={styles.symbolItem}>
                <div className={styles.symbolPath}>
                  {sym.file_path} <span className={styles.symbolSep}>::</span> {sym.symbol_name}
                </div>
                <p className={styles.symbolDoc}>{sym.last_doc_content || '(no description generated)'}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
