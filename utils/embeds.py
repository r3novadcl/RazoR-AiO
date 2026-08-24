import discord

import config
from utils import emojis


class InfoLayout(discord.ui.LayoutView):
    def __init__(self, title: str, description: str | None, colour: int, emoji_key: str, footer_fallback: str):
        super().__init__(timeout=None)
        header = f"{emojis.get(emoji_key, footer_fallback)} **{title}**"
        body = header if not description else f"{header}\n{description}"
        container = discord.ui.Container(accent_colour=colour)
        container.add_item(discord.ui.TextDisplay(body))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# {config.EMBED_FOOTER}"))
        self.add_item(container)


def success(title: str, description: str | None = None) -> discord.ui.LayoutView:
    return InfoLayout(title, description, config.EMBED_COLOR_OK, "success", "✅")


def error(title: str, description: str | None = None) -> discord.ui.LayoutView:
    return InfoLayout(title, description, config.EMBED_COLOR_ALERT, "error", "❌")


def warning(title: str, description: str | None = None) -> discord.ui.LayoutView:
    return InfoLayout(title, description, config.EMBED_COLOR_WARN, "warning", "⚠️")


def info(title: str, description: str | None = None) -> discord.ui.LayoutView:
    return InfoLayout(title, description, config.EMBED_COLOR, "info", "ℹ️")


def alert(title: str, description: str | None = None) -> discord.ui.LayoutView:
    return InfoLayout(title, description, config.EMBED_COLOR_ALERT, "warning", "🛡️")


class ImageReveal(discord.ui.LayoutView):
    """Title line plus an actual rendered image via MediaGallery, for
    anything that fetches an image URL (avatars, pfps, animal pics,
    roleplay gifs) — a bare URL in a TextDisplay does not render inline."""

    def __init__(self, title: str, image_url: str | None, emoji_key: str, colour: int, fallback_text: str):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=colour)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get(emoji_key, 'ℹ️')} **{title}**"))
        if image_url:
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(media=image_url)))
        else:
            container.add_item(discord.ui.TextDisplay(fallback_text))
        self.add_item(container)


def image(title: str, image_url: str | None, emoji_key: str = "info", fallback_text: str = "Could not reach the image source right now.") -> discord.ui.LayoutView:
    return ImageReveal(title, image_url, emoji_key, config.EMBED_COLOR, fallback_text)


class SectionLayout(discord.ui.LayoutView):
    """A container with several distinct text blocks (e.g. a status
    dashboard), separated by thin dividers instead of one big text blob."""

    def __init__(self, title: str, blocks: list[str], colour: int = config.EMBED_COLOR, emoji_key: str = "info"):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=colour)
        container.add_item(discord.ui.TextDisplay(f"{emojis.get(emoji_key, 'ℹ️')} **{title}**"))
        for block in blocks:
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(block))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# {config.EMBED_FOOTER}"))
        self.add_item(container)


class ProfileCard(discord.ui.LayoutView):
    """A status-style layout with the subject's avatar pinned beside the
    title line via a Section+Thumbnail, for anything centered on one member
    (profile, userinfo, mod panel)."""

    def __init__(self, title: str, avatar_url: str, blocks: list[str], colour: int = config.EMBED_COLOR, emoji_key: str = "info"):
        super().__init__(timeout=180)
        container = discord.ui.Container(accent_colour=colour)
        header = discord.ui.Section(
            discord.ui.TextDisplay(f"{emojis.get(emoji_key, 'ℹ️')} **{title}**"),
            accessory=discord.ui.Thumbnail(media=avatar_url),
        )
        container.add_item(header)
        for block in blocks:
            container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
            container.add_item(discord.ui.TextDisplay(block))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(discord.ui.TextDisplay(f"-# {config.EMBED_FOOTER}"))
        self.add_item(container)
