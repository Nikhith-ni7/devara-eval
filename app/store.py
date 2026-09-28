import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS versions (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,
              payload TEXT NOT NULL, error TEXT);
            CREATE TABLE IF NOT EXISTS results (
              run_id TEXT NOT NULL REFERENCES runs(id), case_id TEXT NOT NULL,
              payload TEXT NOT NULL, PRIMARY KEY(run_id, case_id));
            CREATE TABLE IF NOT EXISTS reviews (
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, case_id TEXT NOT NULL,
              created_at TEXT NOT NULL, payload TEXT NOT NULL,
              FOREIGN KEY(run_id, case_id) REFERENCES results(run_id, case_id));
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE runs SET status='interrupted', error='Process stopped before run completed' WHERE status IN ('queued','running')")

    def add_version(self, version):
        with self.connect() as db:
            db.execute('INSERT INTO versions VALUES (?,?)', (version['id'], json.dumps(version)))

    def versions(self):
        with self.connect() as db:
            return [json.loads(r['payload']) for r in db.execute('SELECT payload FROM versions ORDER BY id')]

    def version(self, version_id):
        return next((v for v in self.versions() if v['id'] == version_id), None)

    def add_run(self, payload):
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?,NULL)', (payload['id'], payload['created_at'], 'queued', json.dumps(payload)))

    def status(self, run_id, status, error=None):
        with self.connect() as db:
            db.execute('UPDATE runs SET status=?,error=? WHERE id=?', (status, error, run_id))

    def add_result(self, run_id, result):
        with self.connect() as db:
            db.execute('INSERT INTO results VALUES (?,?,?)', (run_id, result['case_id'], json.dumps(result)))

    def get_run(self, run_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run_id,)).fetchone()
            if not row:
                return None
            run = json.loads(row['payload'])
            run.update(status=row['status'], error=row['error'])
            run['results'] = [json.loads(r['payload']) for r in db.execute('SELECT payload FROM results WHERE run_id=? ORDER BY case_id', (run_id,))]
            return run

    def runs(self):
        with self.connect() as db:
            rows = db.execute('SELECT id FROM runs ORDER BY created_at DESC LIMIT 100').fetchall()
        output = []
        for row in rows:
            run = self.get_run(row['id'])
            run['completed_cases'] = len(run.pop('results'))
            run['total_cases'] = len(run.pop('dataset')['cases'])
            output.append(run)
        return output

    def add_review(self, run_id, case_id, payload):
        with self.connect() as db:
            cursor = db.execute('INSERT INTO reviews(run_id,case_id,created_at,payload) VALUES (?,?,?,?)',
                                (run_id, case_id, now(), json.dumps(payload)))
            return cursor.lastrowid

    def reviews(self, run_id):
        with self.connect() as db:
            return [dict(id=r['id'], case_id=r['case_id'], created_at=r['created_at'], **json.loads(r['payload']))
                    for r in db.execute('SELECT * FROM reviews WHERE run_id=? ORDER BY id', (run_id,))]
