import json
import os

import aiohttp

import config

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
API_BASE = "https://discord.com/api/v10"

MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _load_uploaded() -> dict:
    if not os.path.exists(config.UPLOADED_EMOJIS_JSON_PATH):
        return {}
    with open(config.UPLOADED_EMOJIS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_uploaded(data: dict) -> None:
    with open(config.UPLOADED_EMOJIS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


async def sync_application_emojis(client_id: str, token: str, log=print) -> dict:
    """Uploads every image in EMOJI_ASSETS_DIR as an application emoji (named
    after its filename) unless it's already present, then persists the
    name->id map to uploaded_emojis.json so utils.emojis can resolve tags
    at runtime without ever hardcoding an emoji ID."""
    if not os.path.isdir(config.EMOJI_ASSETS_DIR):
        return _load_uploaded()

    files = sorted(
        f for f in os.listdir(config.EMOJI_ASSETS_DIR)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
    )
    if not files:
        return _load_uploaded()

    headers = {"Authorization": f"Bot {token}"}
    uploaded = _load_uploaded()

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(f"{API_BASE}/applications/{client_id}/emojis") as resp:
            existing = []
            if resp.status == 200:
                payload = await resp.json()
                existing = payload.get("items", payload if isinstance(payload, list) else [])
            existing_by_name = {e["name"]: e for e in existing}

        for filename in files:
            name = os.path.splitext(filename)[0]
            animated = os.path.splitext(filename)[1].lower() == ".gif"

            if name in existing_by_name:
                uploaded[name] = {
                    "id": existing_by_name[name]["id"],
                    "name": name,
                    "animated": existing_by_name[name].get("animated", False),
                }
                continue
            if name in uploaded:
                continue

            path = os.path.join(config.EMOJI_ASSETS_DIR, filename)
            with open(path, "rb") as f:
                raw = f.read()
            import base64

            mime = "image/gif" if animated else ("image/png" if filename.lower().endswith(".png") else "image/jpeg")
            data_uri = f"data:{mime};base64,{base64.b64encode(raw).decode()}"

            async with session.post(
                f"{API_BASE}/applications/{client_id}/emojis",
                json={"name": name, "image": data_uri},
            ) as create_resp:
                if create_resp.status not in (200, 201):
                    body = await create_resp.text()
                    log(f"[emoji-sync] failed to upload '{name}': {create_resp.status} {body}")
                    continue
                created = await create_resp.json()
                uploaded[name] = {"id": created["id"], "name": name, "animated": animated}
                log(f"[emoji-sync] uploaded '{name}'")

    _save_uploaded(uploaded)
    return uploaded
