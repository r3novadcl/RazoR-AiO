# RazoR — Multipurpose Discord Bot

> A Simple Cv2 all-in-one Discord bot built for moderation, security, automation, utility, music, AI and community management.

**RazoR** is developed and maintained by **r3novadcl** under the **FX DEVELOPMENT TEAM**.

[![Discord](https://img.shields.io/badge/FX%20DEVELOPMENT-Join%20Server-5865F2?logo=discord&logoColor=white)](https://discord.gg/epKhYP6Y74)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![discord.py](https://img.shields.io/badge/discord.py-2.6%2B-5865F2)](https://discordpy.readthedocs.io/)

---

## Features

RazoR includes a large collection of Discord features, including:

-  **Anti-Nuke & Security**
  - Anti-ban / anti-unban
  - Anti-channel abuse
  - Anti-role abuse
  - Anti-webhook abuse
  - Anti-bot protection
  - Dangerous-permission protection
  - Selfbot/message-flood protection
-  **Moderation**
  - Moderation commands and utilities
  - Mod logging
  - Ignore system
- **Automation**
  - AutoMod
  - AutoResponder
  - AutoReact
  - AutoPost
  - Welcome / Leave
  - Vanity Roles
  - Reaction Roles
  - Join-to-Create voice channels
-  **Utilities**
  - Tickets
  - Giveaways
  - Leveling
  - Profiles
  - Invites
  - Message statistics
  - Reminders
  - Todo system
- **Music**
  - Lavalink-powered music system
- **AI & APIs [Amiro ke kamm]**
  - AI integration
  - Google integration
  - YouTube integration
  - GitHub utilities
  - Text-to-speech
- **Fun & Utility**
  - Fun commands
  - Roleplay
  - Animals
  - PFP utilities
  - Conversion utilities
  - Miscellaneous tools
-  **Slash Commands & emojis**
  - Discord application/slash commands & emojis are synced automatically when the bot starts.

---

##  Requirements

Before running RazoR, make sure you have:

- **Python 3.10 or newer**
- A **Discord Bot Application**
- The bot's **Token**
- The required Discord permissions/intents
- **Lavalink** if you want the music system
- API keys only for the optional services you want to use

The Python dependencies are already listed in `requirements.txt`.

---

##  Installation

### 1. Clone the repository

```bash
git clone https://github.com/r3novadcl/RazoR-AiO.git
cd RazoR-AIO
```

If you downloaded the project as a ZIP, simply extract it and open a terminal inside the `RazoR-AIO` folder.

### 2. Create a virtual environment (recommended)

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS / Termux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If your system uses `pip3`:

```bash
pip3 install -r requirements.txt
```

---

##  Configure `.env`

The project includes a `.env.example` file.

Create a copy named:

```text
.env
```

Then fill in the required values.

### Minimum configuration

```env
TOKEN=YOUR_DISCORD_BOT_TOKEN
CLIENT_ID=YOUR_DISCORD_APPLICATION_ID

BOT_NAME=RazoR
PREFIX=!
OWNER_IDS=YOUR_DISCORD_USER_ID
```

### What do these mean?

| Variable | Required | Description |
|---|---:|---|
| `TOKEN` | ✅ | Your Discord bot token. **Never share this publicly.** |
| `CLIENT_ID` | ✅ | Discord Application / Client ID. |
| `BOT_NAME` | ❌ | Bot display name used by the configuration. |
| `PREFIX` | ❌ | Default prefix for prefix commands. |
| `OWNER_IDS` | ❌ | Your Discord user ID(s). Multiple IDs can be comma-separated. |
| `DATABASE_PATH` | ❌ | SQLite database location. |
| `EMBED_COLOR` | ❌ | Default embed color. |
| `EMBED_FOOTER` | ❌ | Default embed footer text. |

Example:

```env
TOKEN=your_bot_token_here
CLIENT_ID=123456789012345678
BOT_NAME=RazoR
PREFIX=!
OWNER_IDS=123456789012345678
DATABASE_PATH=data/razor.sqlite3
```

### ⚠️ Important

**Never commit `.env` to GitHub.**

Your bot token is a private credential. If it is accidentally exposed, immediately regenerate/reset the token in the Discord Developer Portal.

---

##  Embed Configuration

You can customize the bot's embed colors from `.env`:

```env
EMBED_COLOR=#2B2D31
EMBED_COLOR_OK=#57F287
EMBED_COLOR_ALERT=#ED4245
EMBED_COLOR_WARN=#FEE75C
EMBED_FOOTER=RazoR
```

Colors should be written as hexadecimal values.

---

## Anti-Nuke Configuration

RazoR's anti-nuke system can be customized through `.env`.

```env
ANTINUKE_NO_BYPASS_ROLE=No-Bypass
ANTINUKE_BARRIER_ROLE=Barrier ~ Unit
ANTINUKE_DEFAULT_PUNISHMENT=strip

ANTINUKE_SELFBOT_WINDOW_SECONDS=5
ANTINUKE_SELFBOT_THRESHOLD=8
ANTINUKE_AUDIT_LOOKBACK_SECONDS=5

MOD_LOG_FALLBACK_CHANNEL_NAME=mod-logs
```

These settings control protection thresholds, role names, punishment defaults and audit-log lookback behavior.

Only change these values if you understand how your server's security setup works.

---

## Lavalink / Music Setup

The music system uses **Lavalink** through Wavelink.

Configure your Lavalink connection in `.env`:

```env
LAVALINK_HOST=YOUR_LAVALINK_HOST
LAVALINK_PORT=2333
LAVALINK_PASSWORD=YOUR_LAVALINK_PASSWORD
LAVALINK_SECURE=false
```

For a secure TLS connection:

```env
LAVALINK_SECURE=true
```

Make sure your Lavalink server is running and reachable before testing music commands.

> RazoR does not include a Lavalink server. You need to provide and maintain your own compatible Lavalink instance.

---

##  Optional AI Configuration

AI features can be configured with:

```env
AI_API_KEY=YOUR_API_KEY
AI_API_BASE=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

If you do not want to use the AI features, leave the API key empty.

```env
AI_API_KEY=
```

Do not publish API keys in your repository.

---

##  Google Configuration

If Google-powered features are enabled for your setup:

```env
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
GOOGLE_CSE_ID=YOUR_GOOGLE_CSE_ID
```

Both values should be kept private.

---

##  Start the Bot

After installing dependencies and configuring `.env`, start RazoR from the project directory:

```bash
python RazoR.py
```

On systems where `python3` is required:

```bash
python3 RazoR.py
```

If everything is configured correctly, you should see logs showing that RazoR has logged in and that slash commands have been synced.

### Example startup flow

```text
Logged in as RazoR (...)
Synced ... slash command(s).
```

Keep the terminal/process running for the bot to remain online.

---

##  Discord Developer Portal Setup

Create a bot at the **Discord Developer Portal** and copy its token and Application ID into `.env`.

RazoR uses Discord privileged gateway intents in its code, including:

- **Server Members Intent**
- **Message Content Intent**
- **Presence Intent**

If Discord requires verification/approval for your bot's privileged intents, complete the required application/verification process in the Developer Portal.

### Bot permissions

The exact permissions depend on which RazoR features you enable. Security and moderation features may require elevated permissions.

For production servers, review the bot's permissions carefully and avoid granting permissions that your deployment does not need.

---

## Emoji Assets

The repository includes emoji assets under:

```text
assets/emojis/
```

The configuration uses:

```env
EMOJIS_JSON_PATH=emojis.json
UPLOADED_EMOJIS_JSON_PATH=uploaded_emojis.json
EMOJI_ASSETS_DIR=assets/emojis
```

RazoR also contains an emoji synchronization system that runs during startup.

---

## Database

RazoR uses SQLite through `aiosqlite`.

By default:

```env
DATABASE_PATH=data/razor.sqlite3
```

The database stores bot data locally. Make sure the process has permission to create/write to the `data` directory.

For backups, periodically back up the SQLite database file.

---

## 📁 Project Structure

```text
RazoR-AIO/
├── RazoR.py
├── config.py
├── requirements.txt
├── .env.example
├── assets/
│   └── emojis/
├── Script/
│   └── upload_emojis.py
├── cogs/
├── utils/
├── data/
└── ...
```

### Important files

| File / Folder | Purpose |
|---|---|
| `RazoR.py` | Main bot entry point |
| `config.py` | Loads environment configuration |
| `.env.example` | Example environment configuration |
| `requirements.txt` | Python dependencies |
| `cogs/` | Bot feature modules |
| `utils/` | Shared utilities and systems |
| `assets/emojis/` | Emoji assets |
| `data/` | Local SQLite database data |

---

##  Troubleshooting

### `TOKEN is missing`

Check that `.env` exists in the project root and contains:

```env
TOKEN=YOUR_DISCORD_BOT_TOKEN
```

Do not put the token in `config.py`.

### `ModuleNotFoundError`

Install dependencies again:

```bash
pip install -r requirements.txt
```

### Slash commands are not appearing

Check:

1. The bot was invited with the correct application scopes.
2. The bot has been restarted.
3. `CLIENT_ID` is correct.
4. The bot has permission to use application commands.
5. Check the terminal for command-sync errors.

### Music is not working

Check:

1. Lavalink is online.
2. `LAVALINK_HOST` is correct.
3. `LAVALINK_PORT` is correct.
4. `LAVALINK_PASSWORD` matches your Lavalink configuration.
5. `LAVALINK_SECURE` matches your Lavalink connection.

### Bot starts but some features do not work

Some features require optional API keys or external services. Check the relevant `.env` variables and the terminal logs.

---

## Security

Please follow these rules when deploying RazoR:

- ❌ Never upload `.env` to GitHub.
- ❌ Never post your Discord bot token.
- ❌ Never publish API keys.
- ❌ Never publish private Lavalink credentials.
- ✅ Use `.env.example` for public configuration templates.
- ✅ Rotate exposed credentials immediately.
- ✅ Keep production credentials separate from source code.

---

##  Developer Credits

### FX DEVELOPMENT TEAM

**Developer:** `r3novadcl`

**Discord:** [Join FX DEVELOPMENT](https://discord.gg/epKhYP6Y74)

RazoR is developed and maintained as part of the **FX DEVELOPMENT TEAM**.

Please keep the developer credits intact when redistributing or modifying the project.

---

## 📜 License & Usage

This project is provided for development and educational use.

Before redistributing, rebranding or using the project commercially, check the repository's license and any applicable third-party licenses.

Third-party libraries and services used by RazoR remain subject to their own licenses and terms.

---

##  Support the Project

If you find RazoR useful:

- ⭐ Star the repository
- Report bugs with useful logs and reproduction steps
- Suggest improvements
- Join **FX DEVELOPMENT** for updates and support

**FX DEVELOPMENT TEAM**  
**Developer — r3novadcl**
