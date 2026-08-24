import json
import os
import time
import aiosqlite

import config

_connection: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    prefix TEXT,
    mod_log_channel INTEGER,
    mute_role_id INTEGER,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS antinuke_config (
    guild_id INTEGER PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    setup_done INTEGER DEFAULT 0,
    punishment TEXT DEFAULT 'strip',
    log_channel INTEGER,
    no_bypass_role_id INTEGER,
    barrier_role_id INTEGER,
    events_json TEXT DEFAULT '{}',
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS antinuke_whitelist (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS antinuke_extraowners (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS antinuke_mainroles (
    guild_id INTEGER,
    role_id INTEGER,
    PRIMARY KEY (guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS antinuke_stats (
    guild_id INTEGER,
    event_key TEXT,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, event_key)
);

CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS mod_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    action TEXT,
    reason TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS welcome_config (
    guild_id INTEGER PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    channel_id INTEGER,
    message TEXT DEFAULT 'Welcome {user} to {server}! We are now {membercount} members.'
);

CREATE TABLE IF NOT EXISTS leave_config (
    guild_id INTEGER PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    channel_id INTEGER,
    message TEXT DEFAULT '{user} has left {server}. We are now {membercount} members.'
);

CREATE TABLE IF NOT EXISTS automod_config (
    guild_id INTEGER PRIMARY KEY,
    anti_link INTEGER DEFAULT 0,
    anti_invite INTEGER DEFAULT 0,
    anti_spam INTEGER DEFAULT 0,
    spam_window_seconds INTEGER DEFAULT 6,
    spam_threshold INTEGER DEFAULT 6,
    word_filter_json TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS tickets_config (
    guild_id INTEGER PRIMARY KEY,
    category_id INTEGER,
    support_role_id INTEGER,
    log_channel_id INTEGER,
    panel_channel_id INTEGER,
    panel_message_id INTEGER
);

CREATE TABLE IF NOT EXISTS tickets_open (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS giveaways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER,
    prize TEXT,
    winner_count INTEGER DEFAULT 1,
    host_id INTEGER,
    end_time REAL,
    ended INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS giveaway_entries (
    giveaway_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (giveaway_id, user_id)
);

CREATE TABLE IF NOT EXISTS logging_config (
    guild_id INTEGER PRIMARY KEY,
    message_events_channel INTEGER,
    member_events_channel INTEGER,
    voice_events_channel INTEGER
);

CREATE TABLE IF NOT EXISTS leveling_xp (
    guild_id INTEGER,
    user_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    last_message_at REAL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS leveling_config (
    guild_id INTEGER PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    announce_channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS reaction_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    message_id INTEGER,
    emoji TEXT,
    role_id INTEGER
);

CREATE TABLE IF NOT EXISTS j2c_config (
    guild_id INTEGER PRIMARY KEY,
    trigger_channel_id INTEGER,
    category_id INTEGER
);

CREATE TABLE IF NOT EXISTS j2c_created (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    owner_id INTEGER
);

CREATE TABLE IF NOT EXISTS vanityroles_config (
    guild_id INTEGER PRIMARY KEY,
    match_text TEXT,
    role_id INTEGER
);

CREATE TABLE IF NOT EXISTS autoresponders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    trigger TEXT,
    response TEXT,
    exact_match INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    channel_id INTEGER,
    message TEXT,
    remind_at REAL,
    done INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS invite_credits (
    guild_id INTEGER,
    user_id INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS message_counts (
    guild_id INTEGER,
    user_id INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS ignore_channels (
    guild_id INTEGER,
    channel_id INTEGER,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS ignore_users (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS autoreact_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    trigger TEXT,
    emoji TEXT
);

CREATE TABLE IF NOT EXISTS autopost_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    channel_id INTEGER,
    content TEXT,
    interval_minutes INTEGER,
    last_posted_at REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS todo_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS youtube_config (
    guild_id INTEGER,
    announce_channel_id INTEGER,
    youtube_channel_id TEXT,
    last_video_id TEXT DEFAULT '',
    PRIMARY KEY (guild_id, youtube_channel_id)
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY,
    description TEXT,
    social TEXT
);

CREATE TABLE IF NOT EXISTS antiraid_config (
    guild_id INTEGER PRIMARY KEY,
    enabled INTEGER DEFAULT 0,
    join_threshold INTEGER DEFAULT 10,
    join_window_seconds INTEGER DEFAULT 15,
    lockdown_minutes INTEGER DEFAULT 15,
    auto_kick_new_accounts INTEGER DEFAULT 1,
    new_account_max_age_days INTEGER DEFAULT 3,
    alert_channel_id INTEGER
);

CREATE TABLE IF NOT EXISTS antiraid_lockdown (
    guild_id INTEGER PRIMARY KEY,
    active INTEGER DEFAULT 0,
    started_at REAL,
    backup_json TEXT
);
"""

_antinuke_cache: dict[int, dict] = {}
_prefix_cache: dict[int, str] = {}

DEFAULT_EVENTS = {key: True for key in config.ANTINUKE_EVENT_KEYS}


async def connect() -> None:
    global _connection
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    _connection = await aiosqlite.connect(config.DATABASE_PATH)
    _connection.row_factory = aiosqlite.Row
    await _connection.executescript(SCHEMA)
    await _connection.commit()


async def warm_prefix_cache() -> None:
    cur = await _conn().execute("SELECT guild_id, prefix FROM guild_settings WHERE prefix IS NOT NULL")
    async for row in cur:
        _prefix_cache[row["guild_id"]] = row["prefix"]


def get_cached_prefix(guild_id: int | None, default: str) -> str:
    if guild_id is None:
        return default
    return _prefix_cache.get(guild_id, default)


async def close() -> None:
    if _connection is not None:
        await _connection.close()


def _conn() -> aiosqlite.Connection:
    if _connection is None:
        raise RuntimeError("Database not connected yet — call connect() during startup first.")
    return _connection


async def get_guild_settings(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row is None:
        return {"guild_id": guild_id, "prefix": None, "mod_log_channel": None, "mute_role_id": None}
    return dict(row)


async def set_guild_setting(guild_id: int, **fields) -> None:
    existing = await get_guild_settings(guild_id)
    merged = {**existing, **fields, "guild_id": guild_id, "updated_at": time.time()}
    await _conn().execute(
        """INSERT INTO guild_settings (guild_id, prefix, mod_log_channel, mute_role_id, updated_at)
           VALUES (:guild_id, :prefix, :mod_log_channel, :mute_role_id, :updated_at)
           ON CONFLICT(guild_id) DO UPDATE SET
             prefix=excluded.prefix, mod_log_channel=excluded.mod_log_channel,
             mute_role_id=excluded.mute_role_id, updated_at=excluded.updated_at""",
        merged,
    )
    await _conn().commit()
    if merged.get("prefix"):
        _prefix_cache[guild_id] = merged["prefix"]


async def _load_antinuke_row(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM antinuke_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row is None:
        cfg = {
            "guild_id": guild_id,
            "enabled": 0,
            "setup_done": 0,
            "punishment": config.ANTINUKE_DEFAULT_PUNISHMENT,
            "log_channel": None,
            "no_bypass_role_id": None,
            "barrier_role_id": None,
            "events": dict(DEFAULT_EVENTS),
        }
    else:
        cfg = dict(row)
        events = {**DEFAULT_EVENTS, **json.loads(cfg.pop("events_json") or "{}")}
        cfg["events"] = events

    cur = await _conn().execute("SELECT user_id FROM antinuke_whitelist WHERE guild_id = ?", (guild_id,))
    cfg["whitelist"] = [r["user_id"] for r in await cur.fetchall()]

    cur = await _conn().execute("SELECT user_id FROM antinuke_extraowners WHERE guild_id = ?", (guild_id,))
    cfg["extraowners"] = [r["user_id"] for r in await cur.fetchall()]

    cur = await _conn().execute("SELECT role_id FROM antinuke_mainroles WHERE guild_id = ?", (guild_id,))
    cfg["mainroles"] = [r["role_id"] for r in await cur.fetchall()]

    return cfg


def get_antinuke_config(guild_id: int) -> dict:
    """Sync-looking accessor backed by an in-memory cache so hot-path event
    listeners don't hit the DB on every gateway event. Call
    warm_antinuke_cache() during startup, and refresh_antinuke() after any
    write, to keep this correct."""
    if guild_id not in _antinuke_cache:
        raise KeyError("Cache miss — call refresh_antinuke(guild_id) at least once before reading it.")
    return _antinuke_cache[guild_id]


async def refresh_antinuke(guild_id: int) -> dict:
    cfg = await _load_antinuke_row(guild_id)
    _antinuke_cache[guild_id] = cfg
    return cfg


async def warm_antinuke_cache(guild_ids: list[int]) -> None:
    for gid in guild_ids:
        await refresh_antinuke(gid)


async def save_antinuke_core(guild_id: int, **fields) -> dict:
    cfg = await _load_antinuke_row(guild_id)
    cfg.update(fields)
    events_json = json.dumps(cfg["events"])
    await _conn().execute(
        """INSERT INTO antinuke_config
             (guild_id, enabled, setup_done, punishment, log_channel, no_bypass_role_id, barrier_role_id, events_json, updated_at)
           VALUES (:guild_id, :enabled, :setup_done, :punishment, :log_channel, :no_bypass_role_id, :barrier_role_id, :events_json, :updated_at)
           ON CONFLICT(guild_id) DO UPDATE SET
             enabled=excluded.enabled, setup_done=excluded.setup_done, punishment=excluded.punishment,
             log_channel=excluded.log_channel, no_bypass_role_id=excluded.no_bypass_role_id,
             barrier_role_id=excluded.barrier_role_id, events_json=excluded.events_json, updated_at=excluded.updated_at""",
        {
            "guild_id": guild_id,
            "enabled": int(cfg["enabled"]),
            "setup_done": int(cfg["setup_done"]),
            "punishment": cfg["punishment"],
            "log_channel": cfg["log_channel"],
            "no_bypass_role_id": cfg["no_bypass_role_id"],
            "barrier_role_id": cfg["barrier_role_id"],
            "events_json": events_json,
            "updated_at": time.time(),
        },
    )
    await _conn().commit()
    return await refresh_antinuke(guild_id)


async def antinuke_list_add(guild_id: int, table: str, id_field: str, value: int) -> dict:
    await _conn().execute(
        f"INSERT OR IGNORE INTO {table} (guild_id, {id_field}) VALUES (?, ?)", (guild_id, value)
    )
    await _conn().commit()
    return await refresh_antinuke(guild_id)


async def antinuke_list_remove(guild_id: int, table: str, id_field: str, value: int) -> dict:
    await _conn().execute(f"DELETE FROM {table} WHERE guild_id = ? AND {id_field} = ?", (guild_id, value))
    await _conn().commit()
    return await refresh_antinuke(guild_id)


async def bump_antinuke_stat(guild_id: int, event_key: str) -> None:
    await _conn().execute(
        """INSERT INTO antinuke_stats (guild_id, event_key, count) VALUES (?, ?, 1)
           ON CONFLICT(guild_id, event_key) DO UPDATE SET count = count + 1""",
        (guild_id, event_key),
    )
    await _conn().commit()


async def get_antinuke_stats(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT event_key, count FROM antinuke_stats WHERE guild_id = ?", (guild_id,))
    return {r["event_key"]: r["count"] for r in await cur.fetchall()}


async def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    cur = await _conn().execute(
        "INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason, time.time()),
    )
    await _conn().commit()
    return cur.lastrowid


async def get_warnings(guild_id: int, user_id: int) -> list[dict]:
    cur = await _conn().execute(
        "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC", (guild_id, user_id)
    )
    return [dict(r) for r in await cur.fetchall()]


async def clear_warnings(guild_id: int, user_id: int) -> None:
    await _conn().execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    await _conn().commit()


async def log_mod_action(guild_id: int, user_id: int, moderator_id: int, action: str, reason: str) -> None:
    await _conn().execute(
        "INSERT INTO mod_actions (guild_id, user_id, moderator_id, action, reason, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, action, reason, time.time()),
    )
    await _conn().commit()


async def get_welcome_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM welcome_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "enabled": 0, "channel_id": None,
            "message": "Welcome {user} to {server}! We are now {membercount} members."}


async def set_welcome_config(guild_id: int, **fields) -> dict:
    cfg = await get_welcome_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO welcome_config (guild_id, enabled, channel_id, message)
           VALUES (:guild_id, :enabled, :channel_id, :message)
           ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled,
             channel_id=excluded.channel_id, message=excluded.message""",
        {"guild_id": guild_id, "enabled": int(cfg["enabled"]), "channel_id": cfg["channel_id"], "message": cfg["message"]},
    )
    await _conn().commit()
    return cfg


async def get_leave_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM leave_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "enabled": 0, "channel_id": None,
            "message": "{user} has left {server}. We are now {membercount} members."}


async def set_leave_config(guild_id: int, **fields) -> dict:
    cfg = await get_leave_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO leave_config (guild_id, enabled, channel_id, message)
           VALUES (:guild_id, :enabled, :channel_id, :message)
           ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled,
             channel_id=excluded.channel_id, message=excluded.message""",
        {"guild_id": guild_id, "enabled": int(cfg["enabled"]), "channel_id": cfg["channel_id"], "message": cfg["message"]},
    )
    await _conn().commit()
    return cfg


async def get_automod_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM automod_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row is None:
        return {"guild_id": guild_id, "anti_link": 0, "anti_invite": 0, "anti_spam": 0,
                "spam_window_seconds": 6, "spam_threshold": 6, "word_filter": []}
    cfg = dict(row)
    cfg["word_filter"] = json.loads(cfg.pop("word_filter_json") or "[]")
    return cfg


async def set_automod_config(guild_id: int, **fields) -> dict:
    cfg = await get_automod_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO automod_config
             (guild_id, anti_link, anti_invite, anti_spam, spam_window_seconds, spam_threshold, word_filter_json)
           VALUES (:guild_id, :anti_link, :anti_invite, :anti_spam, :spam_window_seconds, :spam_threshold, :word_filter_json)
           ON CONFLICT(guild_id) DO UPDATE SET anti_link=excluded.anti_link, anti_invite=excluded.anti_invite,
             anti_spam=excluded.anti_spam, spam_window_seconds=excluded.spam_window_seconds,
             spam_threshold=excluded.spam_threshold, word_filter_json=excluded.word_filter_json""",
        {
            "guild_id": guild_id, "anti_link": int(cfg["anti_link"]), "anti_invite": int(cfg["anti_invite"]),
            "anti_spam": int(cfg["anti_spam"]), "spam_window_seconds": cfg["spam_window_seconds"],
            "spam_threshold": cfg["spam_threshold"], "word_filter_json": json.dumps(cfg["word_filter"]),
        },
    )
    await _conn().commit()
    return cfg


async def get_tickets_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM tickets_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "category_id": None, "support_role_id": None,
            "log_channel_id": None, "panel_channel_id": None, "panel_message_id": None}


async def set_tickets_config(guild_id: int, **fields) -> dict:
    cfg = await get_tickets_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO tickets_config (guild_id, category_id, support_role_id, log_channel_id, panel_channel_id, panel_message_id)
           VALUES (:guild_id, :category_id, :support_role_id, :log_channel_id, :panel_channel_id, :panel_message_id)
           ON CONFLICT(guild_id) DO UPDATE SET category_id=excluded.category_id,
             support_role_id=excluded.support_role_id, log_channel_id=excluded.log_channel_id,
             panel_channel_id=excluded.panel_channel_id, panel_message_id=excluded.panel_message_id""",
        cfg,
    )
    await _conn().commit()
    return cfg


async def open_ticket(channel_id: int, guild_id: int, user_id: int) -> None:
    await _conn().execute(
        "INSERT INTO tickets_open (channel_id, guild_id, user_id, created_at) VALUES (?, ?, ?, ?)",
        (channel_id, guild_id, user_id, time.time()),
    )
    await _conn().commit()


async def get_ticket(channel_id: int) -> dict | None:
    cur = await _conn().execute("SELECT * FROM tickets_open WHERE channel_id = ?", (channel_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def close_ticket(channel_id: int) -> None:
    await _conn().execute("DELETE FROM tickets_open WHERE channel_id = ?", (channel_id,))
    await _conn().commit()


async def create_giveaway(guild_id: int, channel_id: int, message_id: int, prize: str,
                           winner_count: int, host_id: int, end_time: float) -> int:
    cur = await _conn().execute(
        """INSERT INTO giveaways (guild_id, channel_id, message_id, prize, winner_count, host_id, end_time, ended)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (guild_id, channel_id, message_id, prize, winner_count, host_id, end_time),
    )
    await _conn().commit()
    return cur.lastrowid


async def get_giveaway(giveaway_id: int) -> dict | None:
    cur = await _conn().execute("SELECT * FROM giveaways WHERE id = ?", (giveaway_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_giveaway_by_message(message_id: int) -> dict | None:
    cur = await _conn().execute("SELECT * FROM giveaways WHERE message_id = ?", (message_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_active_giveaways() -> list[dict]:
    cur = await _conn().execute("SELECT * FROM giveaways WHERE ended = 0")
    return [dict(r) for r in await cur.fetchall()]


async def get_active_giveaways_for_guild(guild_id: int) -> list[dict]:
    cur = await _conn().execute("SELECT * FROM giveaways WHERE ended = 0 AND guild_id = ?", (guild_id,))
    return [dict(r) for r in await cur.fetchall()]


async def end_giveaway(giveaway_id: int) -> None:
    await _conn().execute("UPDATE giveaways SET ended = 1 WHERE id = ?", (giveaway_id,))
    await _conn().commit()


async def add_giveaway_entry(giveaway_id: int, user_id: int) -> None:
    await _conn().execute(
        "INSERT OR IGNORE INTO giveaway_entries (giveaway_id, user_id) VALUES (?, ?)", (giveaway_id, user_id)
    )
    await _conn().commit()


async def get_giveaway_entries(giveaway_id: int) -> list[int]:
    cur = await _conn().execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id = ?", (giveaway_id,))
    return [r["user_id"] for r in await cur.fetchall()]


async def get_logging_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM logging_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "message_events_channel": None, "member_events_channel": None, "voice_events_channel": None}


async def set_logging_config(guild_id: int, **fields) -> dict:
    cfg = await get_logging_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO logging_config (guild_id, message_events_channel, member_events_channel, voice_events_channel)
           VALUES (:guild_id, :message_events_channel, :member_events_channel, :voice_events_channel)
           ON CONFLICT(guild_id) DO UPDATE SET message_events_channel=excluded.message_events_channel,
             member_events_channel=excluded.member_events_channel, voice_events_channel=excluded.voice_events_channel""",
        cfg,
    )
    await _conn().commit()
    return cfg


LEVEL_XP_BASE = 100


def xp_for_level(level: int) -> int:
    return LEVEL_XP_BASE * level * level


async def add_xp(guild_id: int, user_id: int, amount: int, cooldown_seconds: int = 60) -> tuple[int, int, bool]:
    cur = await _conn().execute(
        "SELECT xp, level, last_message_at FROM leveling_xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
    )
    row = await cur.fetchone()
    now = time.time()
    if row is None:
        xp, level, last = 0, 0, 0
    else:
        xp, level, last = row["xp"], row["level"], row["last_message_at"]

    if now - last < cooldown_seconds:
        return xp, level, False

    xp += amount
    leveled_up = False
    while xp >= xp_for_level(level + 1):
        level += 1
        leveled_up = True

    await _conn().execute(
        """INSERT INTO leveling_xp (guild_id, user_id, xp, level, last_message_at) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(guild_id, user_id) DO UPDATE SET xp=excluded.xp, level=excluded.level, last_message_at=excluded.last_message_at""",
        (guild_id, user_id, xp, level, now),
    )
    await _conn().commit()
    return xp, level, leveled_up


async def get_rank(guild_id: int, user_id: int) -> dict | None:
    cur = await _conn().execute("SELECT xp, level FROM leveling_xp WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    cur = await _conn().execute(
        "SELECT user_id, xp, level FROM leveling_xp WHERE guild_id = ? ORDER BY xp DESC LIMIT ?", (guild_id, limit)
    )
    return [dict(r) for r in await cur.fetchall()]


async def get_leveling_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM leveling_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "enabled": 0, "announce_channel_id": None}


async def set_leveling_config(guild_id: int, **fields) -> dict:
    cfg = await get_leveling_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO leveling_config (guild_id, enabled, announce_channel_id)
           VALUES (:guild_id, :enabled, :announce_channel_id)
           ON CONFLICT(guild_id) DO UPDATE SET enabled=excluded.enabled, announce_channel_id=excluded.announce_channel_id""",
        {"guild_id": guild_id, "enabled": int(cfg["enabled"]), "announce_channel_id": cfg["announce_channel_id"]},
    )
    await _conn().commit()
    return cfg


async def add_reaction_role(guild_id: int, channel_id: int, message_id: int, emoji: str, role_id: int) -> None:
    await _conn().execute(
        "INSERT INTO reaction_roles (guild_id, channel_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?, ?)",
        (guild_id, channel_id, message_id, emoji, role_id),
    )
    await _conn().commit()


async def get_reaction_role(message_id: int, emoji: str) -> dict | None:
    cur = await _conn().execute(
        "SELECT * FROM reaction_roles WHERE message_id = ? AND emoji = ?", (message_id, emoji)
    )
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_guild_reaction_roles(guild_id: int) -> list[dict]:
    cur = await _conn().execute("SELECT * FROM reaction_roles WHERE guild_id = ?", (guild_id,))
    return [dict(r) for r in await cur.fetchall()]


async def remove_reaction_role(guild_id: int, entry_id: int) -> None:
    await _conn().execute("DELETE FROM reaction_roles WHERE guild_id = ? AND id = ?", (guild_id, entry_id))
    await _conn().commit()


async def get_j2c_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM j2c_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "trigger_channel_id": None, "category_id": None}


async def set_j2c_config(guild_id: int, **fields) -> dict:
    cfg = await get_j2c_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO j2c_config (guild_id, trigger_channel_id, category_id)
           VALUES (:guild_id, :trigger_channel_id, :category_id)
           ON CONFLICT(guild_id) DO UPDATE SET trigger_channel_id=excluded.trigger_channel_id, category_id=excluded.category_id""",
        cfg,
    )
    await _conn().commit()
    return cfg


async def register_j2c_channel(channel_id: int, guild_id: int, owner_id: int) -> None:
    await _conn().execute(
        "INSERT INTO j2c_created (channel_id, guild_id, owner_id) VALUES (?, ?, ?)", (channel_id, guild_id, owner_id)
    )
    await _conn().commit()


async def get_j2c_channel(channel_id: int) -> dict | None:
    cur = await _conn().execute("SELECT * FROM j2c_created WHERE channel_id = ?", (channel_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def remove_j2c_channel(channel_id: int) -> None:
    await _conn().execute("DELETE FROM j2c_created WHERE channel_id = ?", (channel_id,))
    await _conn().commit()


async def get_vanityroles_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM vanityroles_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"guild_id": guild_id, "match_text": None, "role_id": None}


async def set_vanityroles_config(guild_id: int, **fields) -> dict:
    cfg = await get_vanityroles_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO vanityroles_config (guild_id, match_text, role_id)
           VALUES (:guild_id, :match_text, :role_id)
           ON CONFLICT(guild_id) DO UPDATE SET match_text=excluded.match_text, role_id=excluded.role_id""",
        cfg,
    )
    await _conn().commit()
    return cfg


async def add_autoresponder(guild_id: int, trigger: str, response: str, exact_match: bool) -> int:
    cur = await _conn().execute(
        "INSERT INTO autoresponders (guild_id, trigger, response, exact_match) VALUES (?, ?, ?, ?)",
        (guild_id, trigger, response, int(exact_match)),
    )
    await _conn().commit()
    return cur.lastrowid


async def get_autoresponders(guild_id: int) -> list[dict]:
    cur = await _conn().execute("SELECT * FROM autoresponders WHERE guild_id = ?", (guild_id,))
    return [dict(r) for r in await cur.fetchall()]


async def remove_autoresponder(guild_id: int, responder_id: int) -> None:
    await _conn().execute("DELETE FROM autoresponders WHERE guild_id = ? AND id = ?", (guild_id, responder_id))
    await _conn().commit()


async def add_reminder(guild_id: int, user_id: int, channel_id: int, message: str, remind_at: float) -> int:
    cur = await _conn().execute(
        "INSERT INTO reminders (guild_id, user_id, channel_id, message, remind_at, done) VALUES (?, ?, ?, ?, ?, 0)",
        (guild_id, user_id, channel_id, message, remind_at),
    )
    await _conn().commit()
    return cur.lastrowid


async def get_due_reminders() -> list[dict]:
    cur = await _conn().execute("SELECT * FROM reminders WHERE done = 0 AND remind_at <= ?", (time.time(),))
    return [dict(r) for r in await cur.fetchall()]


async def complete_reminder(reminder_id: int) -> None:
    await _conn().execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
    await _conn().commit()


async def get_user_reminders(user_id: int) -> list[dict]:
    cur = await _conn().execute("SELECT * FROM reminders WHERE user_id = ? AND done = 0 ORDER BY remind_at", (user_id,))
    return [dict(r) for r in await cur.fetchall()]


async def add_invite_credit(guild_id: int, user_id: int, delta: int = 1) -> int:
    await _conn().execute(
        """INSERT INTO invite_credits (guild_id, user_id, count) VALUES (?, ?, ?)
           ON CONFLICT(guild_id, user_id) DO UPDATE SET count = count + excluded.count""",
        (guild_id, user_id, delta),
    )
    await _conn().commit()
    cur = await _conn().execute("SELECT count FROM invite_credits WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    row = await cur.fetchone()
    return row["count"] if row else 0


async def get_invite_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    cur = await _conn().execute(
        "SELECT user_id, count FROM invite_credits WHERE guild_id = ? ORDER BY count DESC LIMIT ?", (guild_id, limit)
    )
    return [dict(r) for r in await cur.fetchall()]


async def bump_message_count(guild_id: int, user_id: int) -> None:
    await _conn().execute(
        """INSERT INTO message_counts (guild_id, user_id, count) VALUES (?, ?, 1)
           ON CONFLICT(guild_id, user_id) DO UPDATE SET count = count + 1""",
        (guild_id, user_id),
    )
    await _conn().commit()


async def get_message_leaderboard(guild_id: int, limit: int = 10) -> list[dict]:
    cur = await _conn().execute(
        "SELECT user_id, count FROM message_counts WHERE guild_id = ? ORDER BY count DESC LIMIT ?", (guild_id, limit)
    )
    return [dict(r) for r in await cur.fetchall()]


async def add_ignore(guild_id: int, table: str, id_field: str, value: int) -> None:
    await _conn().execute(f"INSERT OR IGNORE INTO {table} (guild_id, {id_field}) VALUES (?, ?)", (guild_id, value))
    await _conn().commit()


async def remove_ignore(guild_id: int, table: str, id_field: str, value: int) -> None:
    await _conn().execute(f"DELETE FROM {table} WHERE guild_id = ? AND {id_field} = ?", (guild_id, value))
    await _conn().commit()


async def get_ignored(guild_id: int, table: str, id_field: str) -> list[int]:
    cur = await _conn().execute(f"SELECT {id_field} FROM {table} WHERE guild_id = ?", (guild_id,))
    return [r[id_field] for r in await cur.fetchall()]


async def add_autoreact(guild_id: int, trigger: str, emoji: str) -> int:
    cur = await _conn().execute(
        "INSERT INTO autoreact_config (guild_id, trigger, emoji) VALUES (?, ?, ?)", (guild_id, trigger, emoji)
    )
    await _conn().commit()
    return cur.lastrowid


async def get_autoreacts(guild_id: int) -> list[dict]:
    cur = await _conn().execute("SELECT * FROM autoreact_config WHERE guild_id = ?", (guild_id,))
    return [dict(r) for r in await cur.fetchall()]


async def remove_autoreact(guild_id: int, entry_id: int) -> None:
    await _conn().execute("DELETE FROM autoreact_config WHERE guild_id = ? AND id = ?", (guild_id, entry_id))
    await _conn().commit()


async def clear_autoreacts(guild_id: int) -> None:
    await _conn().execute("DELETE FROM autoreact_config WHERE guild_id = ?", (guild_id,))
    await _conn().commit()


async def add_autopost(guild_id: int, channel_id: int, content: str, interval_minutes: int) -> int:
    cur = await _conn().execute(
        "INSERT INTO autopost_config (guild_id, channel_id, content, interval_minutes, last_posted_at) VALUES (?, ?, ?, ?, 0)",
        (guild_id, channel_id, content, interval_minutes),
    )
    await _conn().commit()
    return cur.lastrowid


async def get_autoposts(guild_id: int | None = None) -> list[dict]:
    if guild_id is None:
        cur = await _conn().execute("SELECT * FROM autopost_config")
    else:
        cur = await _conn().execute("SELECT * FROM autopost_config WHERE guild_id = ?", (guild_id,))
    return [dict(r) for r in await cur.fetchall()]


async def touch_autopost(entry_id: int) -> None:
    await _conn().execute("UPDATE autopost_config SET last_posted_at = ? WHERE id = ?", (time.time(), entry_id))
    await _conn().commit()


async def remove_autopost(guild_id: int, entry_id: int) -> None:
    await _conn().execute("DELETE FROM autopost_config WHERE guild_id = ? AND id = ?", (guild_id, entry_id))
    await _conn().commit()


async def clear_autoposts(guild_id: int) -> None:
    await _conn().execute("DELETE FROM autopost_config WHERE guild_id = ?", (guild_id,))
    await _conn().commit()


async def add_todo(user_id: int, content: str) -> int:
    cur = await _conn().execute(
        "INSERT INTO todo_items (user_id, content, created_at) VALUES (?, ?, ?)", (user_id, content, time.time())
    )
    await _conn().commit()
    return cur.lastrowid


async def get_todos(user_id: int) -> list[dict]:
    cur = await _conn().execute("SELECT * FROM todo_items WHERE user_id = ? ORDER BY created_at", (user_id,))
    return [dict(r) for r in await cur.fetchall()]


async def remove_todo(user_id: int, todo_id: int) -> None:
    await _conn().execute("DELETE FROM todo_items WHERE user_id = ? AND id = ?", (user_id, todo_id))
    await _conn().commit()


async def clear_todos(user_id: int) -> None:
    await _conn().execute("DELETE FROM todo_items WHERE user_id = ?", (user_id,))
    await _conn().commit()


async def set_youtube_config(guild_id: int, channel_id: int, youtube_channel_id: str, last_video_id: str = "") -> None:
    await _conn().execute(
        """INSERT INTO youtube_config (guild_id, announce_channel_id, youtube_channel_id, last_video_id)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(guild_id, youtube_channel_id) DO UPDATE SET announce_channel_id=excluded.announce_channel_id""",
        (guild_id, channel_id, youtube_channel_id, last_video_id),
    )
    await _conn().commit()


async def get_youtube_configs(guild_id: int | None = None) -> list[dict]:
    if guild_id is None:
        cur = await _conn().execute("SELECT * FROM youtube_config")
    else:
        cur = await _conn().execute("SELECT * FROM youtube_config WHERE guild_id = ?", (guild_id,))
    return [dict(r) for r in await cur.fetchall()]


async def update_youtube_last_video(guild_id: int, youtube_channel_id: str, video_id: str) -> None:
    await _conn().execute(
        "UPDATE youtube_config SET last_video_id = ? WHERE guild_id = ? AND youtube_channel_id = ?",
        (video_id, guild_id, youtube_channel_id),
    )
    await _conn().commit()


async def remove_youtube_config(guild_id: int, youtube_channel_id: str) -> None:
    await _conn().execute(
        "DELETE FROM youtube_config WHERE guild_id = ? AND youtube_channel_id = ?", (guild_id, youtube_channel_id)
    )
    await _conn().commit()


async def get_profile(user_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {"user_id": user_id, "description": None, "social": None}


async def set_profile(user_id: int, **fields) -> dict:
    profile = await get_profile(user_id)
    profile.update(fields)
    await _conn().execute(
        """INSERT INTO profiles (user_id, description, social) VALUES (:user_id, :description, :social)
           ON CONFLICT(user_id) DO UPDATE SET description=excluded.description, social=excluded.social""",
        profile,
    )
    await _conn().commit()
    return profile


async def reset_profile(user_id: int) -> None:
    await _conn().execute("DELETE FROM profiles WHERE user_id = ?", (user_id,))
    await _conn().commit()


async def get_antiraid_config(guild_id: int) -> dict:
    cur = await _conn().execute("SELECT * FROM antiraid_config WHERE guild_id = ?", (guild_id,))
    row = await cur.fetchone()
    if row:
        return dict(row)
    return {
        "guild_id": guild_id, "enabled": 0, "join_threshold": 10, "join_window_seconds": 15,
        "lockdown_minutes": 15, "auto_kick_new_accounts": 1, "new_account_max_age_days": 3,
        "alert_channel_id": None,
    }


async def set_antiraid_config(guild_id: int, **fields) -> dict:
    cfg = await get_antiraid_config(guild_id)
    cfg.update(fields)
    await _conn().execute(
        """INSERT INTO antiraid_config
             (guild_id, enabled, join_threshold, join_window_seconds, lockdown_minutes,
              auto_kick_new_accounts, new_account_max_age_days, alert_channel_id)
           VALUES (:guild_id, :enabled, :join_threshold, :join_window_seconds, :lockdown_minutes,
                   :auto_kick_new_accounts, :new_account_max_age_days, :alert_channel_id)
           ON CONFLICT(guild_id) DO UPDATE SET
             enabled=excluded.enabled, join_threshold=excluded.join_threshold,
             join_window_seconds=excluded.join_window_seconds, lockdown_minutes=excluded.lockdown_minutes,
             auto_kick_new_accounts=excluded.auto_kick_new_accounts,
             new_account_max_age_days=excluded.new_account_max_age_days,
             alert_channel_id=excluded.alert_channel_id""",
        {k: (int(v) if k in ("enabled", "auto_kick_new_accounts") else v) for k, v in cfg.items()},
    )
    await _conn().commit()
    return cfg


async def start_lockdown(guild_id: int, backup_json: str, started_at: float) -> None:
    await _conn().execute(
        """INSERT INTO antiraid_lockdown (guild_id, active, started_at, backup_json) VALUES (?, 1, ?, ?)
           ON CONFLICT(guild_id) DO UPDATE SET active=1, started_at=excluded.started_at, backup_json=excluded.backup_json""",
        (guild_id, started_at, backup_json),
    )
    await _conn().commit()


async def get_lockdown(guild_id: int) -> dict | None:
    cur = await _conn().execute("SELECT * FROM antiraid_lockdown WHERE guild_id = ? AND active = 1", (guild_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_active_lockdowns() -> list[dict]:
    cur = await _conn().execute("SELECT * FROM antiraid_lockdown WHERE active = 1")
    return [dict(r) for r in await cur.fetchall()]


async def end_lockdown(guild_id: int) -> None:
    await _conn().execute("UPDATE antiraid_lockdown SET active = 0 WHERE guild_id = ?", (guild_id,))
    await _conn().commit()
