import Link from 'next/link';
import styles from './page.module.css';

export const dynamic = 'force-dynamic';

type Repo = {
  id: number;
  github_full_name: string;
  default_branch: string;
  docs_output_path: string;
  created_at: string;
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

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function getRepos(): Promise<{ repos: Repo[]; apiDown: boolean }> {
  try {
    const res = await fetch(`${API_URL}/repos/`, { cache: 'no-store' });
    if (!res.ok) return { repos: [], apiDown: true };
    return { repos: await res.json(), apiDown: false };
  } catch {
    // fetch() throws (not just a non-ok response) when the connection itself
    // fails — e.g. the FastAPI server isn't running. That's a distinct state
    // from "no repos registered yet" and deserves its own message.
    return { repos: [], apiDown: true };
  }
}

async function getLatestSync(repoId: number): Promise<SyncRun | null> {
  try {
    const res = await fetch(`${API_URL}/repos/${repoId}/syncs`, { cache: 'no-store' });
    if (!res.ok) return null;
    const runs: SyncRun[] = await res.json();
    return runs[0] ?? null;
  } catch {
    return null;
  }
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === 'success' ? 'var(--sage)' : status === 'failed' ? 'var(--terracotta)' : 'var(--text-muted)';
  return <span className={styles.statusDot} style={{ background: color }} />;
}

export default async function DashboardPage() {
  const { repos, apiDown } = await getRepos();
  const withLatest = await Promise.all(
    repos.map(async (repo) => ({ repo, latest: await getLatestSync(repo.id) }))
  );

  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>doc-sync-agent</p>
        <h1 className={styles.title}>Watched repositories</h1>
        <p className={styles.subtitle}>
          Every push is diffed at the symbol level — only signatures that actually changed get new docs.
        </p>
      </header>

      {apiDown ? (
        <div className={styles.empty}>
          <p>Can&apos;t reach the API.</p>
          <p className={styles.emptyHint}>
            Make sure it&apos;s running: <code>uvicorn app.main:app --reload</code>
          </p>
        </div>
      ) : withLatest.length === 0 ? (
        <div className={styles.empty}>
          <p>No repositories registered yet.</p>
          <p className={styles.emptyHint}>
            Register one with <code>python -m scripts.seed_repo owner/repo</code>
          </p>
        </div>
      ) : (
        <ul className={styles.repoList}>
          {withLatest.map(({ repo, latest }) => (
            <li key={repo.id} className={styles.repoCard}>
              <Link href={`/repos/${repo.id}`} className={styles.repoLink}>
                <div className={styles.repoTop}>
                  <span className={styles.repoName}>{repo.github_full_name}</span>
                  {latest && <StatusDot status={latest.status} />}
                </div>
                <div className={styles.repoMeta}>
                  <span className={styles.branch}>{repo.default_branch}</span>
                  {latest ? (
                    <>
                      <span className={styles.dividerDot}>·</span>
                      <span className={styles.hash}>{latest.commit_sha.slice(0, 7)}</span>
                      <span className={styles.dividerDot}>·</span>
                      <span
                        className={
                          latest.symbols_changed > 0 ? styles.diffPositive : styles.diffZero
                        }
                      >
                        {latest.symbols_changed > 0 ? `+${latest.symbols_changed}` : '0'} symbols
                      </span>
                    </>
                  ) : (
                    <span className={styles.dividerDot}>· no syncs yet</span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
