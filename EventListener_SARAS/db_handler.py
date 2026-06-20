import sqlite3
import os
import sys
from datetime import datetime, timezone

# ───────────────────────────────────────────────
# DICTIONARY DB  — stays in install directory (read-only bundled content)
# ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "Dictionary.db")


def execute_query(query, params=(), fetch=False):
    connect = sqlite3.connect(DB_PATH)
    cursor = connect.cursor()
    cursor.execute(query, params)

    if fetch:
        result = cursor.fetchall()
        connect.close()
        return result

    connect.commit()
    connect.close()


def _get_root_forms(word: str):
    """
    Returns a list of progressively simpler forms to try, in order.
    No external libraries needed.
    """
    candidates = [word]

    if word.endswith("ers"):
        candidates.append(word[:-3])
        candidates.append(word[:-2])
        candidates.append(word[:-1])
    if word.endswith("ors"):
        candidates.append(word[:-3])
        candidates.append(word[:-1])
    if word.endswith("ing"):
        candidates.append(word[:-3])
        candidates.append(word[:-3] + "e")
    if word.endswith("ies"):
        candidates.append(word[:-3] + "y")
    if word.endswith("es"):
        candidates.append(word[:-2])
    if word.endswith("s"):
        candidates.append(word[:-1])
    if word.endswith("ed"):
        candidates.append(word[:-2])
        candidates.append(word[:-1])
    if word.endswith("er"):
        candidates.append(word[:-2])

    seen = set()
    result = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result


def get_word_meaning(word: str):
    if not word or not word.strip():
        print("[DB] Empty word skipped", flush=True)
        return None

    query = '''
        SELECT definition, examples, synonm
        FROM Dictionary
        WHERE word1 = ? COLLATE NOCASE
    '''

    root_forms = _get_root_forms(word.lower())

    for candidate in root_forms:
        try:
            result = execute_query(query, (candidate,), fetch=True)
            if result and len(result) > 0:
                definition, examples_str, synonyms_str = result[0]
                examples = examples_str.split(',') if examples_str else []
                synonyms = synonyms_str.split(',') if synonyms_str else []
                print(f"[DB] '{word}' matched via '{candidate}'", flush=True)
                return {
                    'word': word,
                    'definition': definition or "No definition available",
                    'examples': [ex.strip() for ex in examples if ex.strip()],
                    'synonyms': [syn.strip() for syn in synonyms if syn.strip()]
                }
        except sqlite3.Error as e:
            print(f"[DB] Lookup failed for '{candidate}': {e}", flush=True)

    print(f"[DB] '{word}' not found even after root matching", flush=True)
    return None


# ───────────────────────────────────────────────
# PROFILE / ENTITLEMENT DB  — lives in AppData\Roaming\SARAS\
#                             survives app uninstall/reinstall
# ───────────────────────────────────────────────
def get_profile_db_path():
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    profile_dir = os.path.join(appdata, 'SARAS')
    os.makedirs(profile_dir, exist_ok=True)
    return os.path.join(profile_dir, 'profile.db')


PROFILE_DB_PATH = get_profile_db_path()

# ── Free-tier policy ──────────────────────────────────────────────
DAILY_CAP = 5          # lookups/day once the trial ends
TRIAL_DAYS = 7         # informational; trial_ends_at is authoritative (from server)
DISCOUNT_WINDOW_HOURS = 48


def _connect():
    return sqlite3.connect(PROFILE_DB_PATH)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _today_str():
    """Local calendar date — a 'day' from the user's perspective."""
    return datetime.now().strftime("%Y-%m-%d")


def _this_month_str():
    return datetime.now().strftime("%Y-%m")


def _parse_iso(s):
    if not s:
        return None
    try:
        s = s.replace('Z', '+00:00')
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _ensure_column(cursor, table, col, decl):
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [r[1] for r in cursor.fetchall()]
    if col not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_profile_db():
    """
    Creates / migrates the profile DB.
    Safe to run on every launch. Existing paid installs are migrated in place:
    new columns are added and any row that already has a license_key is
    backfilled to tier='paid'.
    """
    connect = _connect()
    cursor = connect.cursor()

    # Base table (original shape kept so old installs ALTER cleanly)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id            INTEGER PRIMARY KEY,
            first_name    TEXT NOT NULL,
            last_name     TEXT NOT NULL,
            email         TEXT NOT NULL,
            license_key   TEXT NOT NULL,
            activated_at  TEXT NOT NULL
        )
    ''')

    # New entitlement columns
    _ensure_column(cursor, 'user_profile', 'tier',           "TEXT")
    _ensure_column(cursor, 'user_profile', 'trial_ends_at',  "TEXT")
    _ensure_column(cursor, 'user_profile', 'has_license',    "INTEGER DEFAULT 0")
    _ensure_column(cursor, 'user_profile', 'last_synced_at', "TEXT")
    _ensure_column(cursor, 'user_profile', 'access_token',   "TEXT")
    _ensure_column(cursor, 'user_profile', 'refresh_token',  "TEXT")

    # One-time backfill: existing paid installs → tier=paid
    cursor.execute('''
        UPDATE user_profile
           SET tier = 'paid', has_license = 1
         WHERE (tier IS NULL OR tier = '')
           AND license_key IS NOT NULL AND license_key != ''
    ''')

    # Per-day usage counter (drives the cap AND the monthly vanity counter)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_daily (
            day   TEXT PRIMARY KEY,
            count INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Small key/value store (first_cap_hit_at, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    connect.commit()
    connect.close()
    print("[DB] Profile DB initialised (entitlement schema ready)", flush=True)


# ── Identity persistence ──────────────────────────────────────────
def _upsert_profile(first_name, last_name, email, license_key, tier,
                    trial_ends_at, has_license, access_token, refresh_token):
    """Single-row profile table. Inserts if empty, otherwise updates row 1.
    license_key / tokens are preserved if a blank/None is passed (protects
    a paid user when a later free-sync comes through)."""
    connect = _connect()
    cur = connect.cursor()
    now = _now_iso()

    cur.execute("SELECT id FROM user_profile LIMIT 1")
    row = cur.fetchone()
    if row:
        cur.execute('''
            UPDATE user_profile
               SET first_name=?, last_name=?, email=?,
                   license_key=COALESCE(NULLIF(?, ''), license_key),
                   tier=?, trial_ends_at=?, has_license=?,
                   access_token=COALESCE(?, access_token),
                   refresh_token=COALESCE(?, refresh_token),
                   last_synced_at=?
             WHERE id=?
        ''', (first_name, last_name, email, license_key, tier, trial_ends_at,
              1 if has_license else 0, access_token, refresh_token, now, row[0]))
    else:
        cur.execute('''
            INSERT INTO user_profile
                (first_name, last_name, email, license_key, activated_at,
                 tier, trial_ends_at, has_license, access_token, refresh_token, last_synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (first_name, last_name, email, license_key or '', now,
              tier, trial_ends_at, 1 if has_license else 0,
              access_token, refresh_token, now))

    connect.commit()
    connect.close()


def save_user_profile(first_name: str, last_name: str, email: str, license_key: str):
    """Paid activation path (license key submitted). Marks the profile PAID."""
    _upsert_profile(
        first_name=first_name, last_name=last_name, email=email,
        license_key=license_key, tier='paid', trial_ends_at=None,
        has_license=1, access_token=None, refresh_token=None,
    )
    print(f"[DB] Paid profile saved for {first_name} {last_name}", flush=True)


def save_identity(first_name, last_name, email, tier, trial_ends_at,
                  has_license=False, access_token=None, refresh_token=None):
    """Free / login path (no license key). Persists identity + cached entitlement."""
    _upsert_profile(
        first_name=first_name or '', last_name=last_name or '', email=email,
        license_key='', tier=tier, trial_ends_at=trial_ends_at,
        has_license=has_license, access_token=access_token, refresh_token=refresh_token,
    )
    print(f"[DB] Identity saved for {email} (tier={tier})", flush=True)


def update_entitlement(tier, trial_ends_at, has_license):
    """Lightweight re-sync — refresh tier/trial without touching name or tokens."""
    connect = _connect()
    cur = connect.cursor()
    cur.execute('''
        UPDATE user_profile
           SET tier=?, trial_ends_at=?, has_license=?, last_synced_at=?
         WHERE id IN (SELECT id FROM user_profile LIMIT 1)
    ''', (tier, trial_ends_at, 1 if has_license else 0, _now_iso()))
    connect.commit()
    connect.close()


def get_user_profile():
    """Returns the stored profile dict, or None if not identified yet."""
    try:
        connect = _connect()
        cur = connect.cursor()
        cur.execute('''
            SELECT first_name, last_name, email, license_key, activated_at,
                   tier, trial_ends_at, has_license, last_synced_at,
                   access_token, refresh_token
            FROM user_profile
            LIMIT 1
        ''')
        row = cur.fetchone()
        connect.close()
        if not row:
            return None
        return {
            'first_name':    row[0],
            'last_name':     row[1],
            'email':         row[2],
            'license_key':   row[3],
            'activated_at':  row[4],
            'tier':          row[5],
            'trial_ends_at': row[6],
            'has_license':   bool(row[7]),
            'last_synced_at': row[8],
            'access_token':  row[9],
            'refresh_token': row[10],
        }
    except sqlite3.Error as e:
        print(f"[DB] Could not read profile: {e}", flush=True)
        return None


# ── Gates ─────────────────────────────────────────────────────────
def is_identified():
    """We know who the user is (free or paid). The real 'can use the app' gate."""
    return get_user_profile() is not None


def is_activated():
    """Back-compat: True only for PAID users (have a license)."""
    p = get_user_profile()
    return bool(p and (p['has_license'] or (p['license_key'] or '').strip()))


def resolve_tier():
    """Local tier decision: paid > trial (by server date) > capped."""
    p = get_user_profile()
    if not p:
        return None
    if p['has_license'] or (p['license_key'] or '').strip():
        return 'paid'
    ends = _parse_iso(p.get('trial_ends_at'))
    if ends and datetime.now(timezone.utc) < ends:
        return 'trial'
    return 'capped'


# ── Usage counters ────────────────────────────────────────────────
def get_daily_count(day=None):
    day = day or _today_str()
    connect = _connect()
    cur = connect.cursor()
    cur.execute("SELECT count FROM usage_daily WHERE day=?", (day,))
    row = cur.fetchone()
    connect.close()
    return row[0] if row else 0


def increment_daily_count(day=None):
    day = day or _today_str()
    connect = _connect()
    cur = connect.cursor()
    cur.execute('''
        INSERT INTO usage_daily (day, count) VALUES (?, 1)
        ON CONFLICT(day) DO UPDATE SET count = count + 1
    ''', (day,))
    connect.commit()
    cur.execute("SELECT count FROM usage_daily WHERE day=?", (day,))
    row = cur.fetchone()
    connect.close()
    return row[0] if row else 1


def get_month_count(yyyymm=None):
    yyyymm = yyyymm or _this_month_str()
    connect = _connect()
    cur = connect.cursor()
    cur.execute("SELECT COALESCE(SUM(count), 0) FROM usage_daily WHERE day LIKE ?",
                (yyyymm + '%',))
    row = cur.fetchone()
    connect.close()
    return row[0] if row else 0


# ── Key/value state ───────────────────────────────────────────────
def get_state(key, default=None):
    connect = _connect()
    cur = connect.cursor()
    cur.execute("SELECT value FROM app_state WHERE key=?", (key,))
    row = cur.fetchone()
    connect.close()
    return row[0] if row else default


def set_state(key, value):
    connect = _connect()
    cur = connect.cursor()
    cur.execute('''
        INSERT INTO app_state (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    ''', (key, str(value)))
    connect.commit()
    connect.close()


# ── Policy: the only two functions saras_app needs per-lookup ──────
def can_lookup(daily_cap=DAILY_CAP):
    """Decide whether THIS lookup is allowed. Does NOT mutate any counter.
    'remaining' is what's left AFTER this lookup (capped tier only)."""
    tier = resolve_tier()
    month = get_month_count()
    if tier in ('paid', 'trial'):
        return {'allow': True, 'tier': tier, 'remaining': None, 'month_count': month}
    used = get_daily_count()
    return {
        'allow': used < daily_cap,
        'tier': 'capped',
        'remaining': max(daily_cap - used - 1, 0),
        'month_count': month,
    }


def record_lookup():
    """Count one successful lookup (drives both the daily cap and monthly counter)."""
    increment_daily_count()
    return {'daily_used': get_daily_count(), 'month_count': get_month_count()}


def resolve_offer(discount_window_hours=DISCOUNT_WINDOW_HOURS):
    """First time the cap is hit → 'discount' for N hours, then 'standard'.
    Anchors the discount window on first call (the 6th-click block)."""
    first = get_state('first_cap_hit_at')
    now = datetime.now(timezone.utc)
    if not first:
        set_state('first_cap_hit_at', now.isoformat())
        return 'discount'
    started = _parse_iso(first) or now
    hours = (now - started).total_seconds() / 3600.0
    return 'discount' if hours < discount_window_hours else 'standard'