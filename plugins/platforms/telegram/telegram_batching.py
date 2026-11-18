"""Telegram inbound album and photo-burst event merging."""

from typing import Optional

from gateway.platforms.event import MessageEvent
from gateway.platforms.helpers import caption_is_command
from plugins.platforms.telegram.telegram_media_group import CAPTION_TEXT_ATTR, caption_text, item_notes


def pad_inline_flags(event: MessageEvent) -> list[Optional[bool]]:
    """Represent unspecified legacy flags as None before appending media.

    Local twin of core's private ``gateway.platforms.base_media_flags`` helper: plugins may only
    import the published plugin API.
    """
    flags = list(getattr(event, "media_text_inlined", []) or [])
    return flags + [None] * (len(event.media_urls) - len(flags))


def merge_batched_event(pending: dict, key: str, event: MessageEvent, *, merge_caption) -> None:
    """Retain each attachment's inlining semantics when combining album items."""
    existing = pending.get(key)
    if existing is None:
        pending[key] = event
        return
    existing.absorb_reply_expected(event)
    existing.media_text_inlined = pad_inline_flags(existing) + pad_inline_flags(event)
    existing.extend_media(event)
    captions = command_first(caption_text(existing), caption_text(event), merge_caption) \
        or merged_text(caption_text(existing), event, caption_text(event), merge_caption) or ""
    existing.text = merged_text(existing.text, event, event.text, merge_caption)
    if CAPTION_TEXT_ATTR in existing.__dict__ or CAPTION_TEXT_ATTR in event.__dict__:  # an item inlined file text
        existing.__dict__[CAPTION_TEXT_ATTR] = captions  # refreshed on every merge, so it never lags the text
        if caption_is_command(captions):
            # An album is judged by its ONE caption, which only one item carries. The uncaptioned siblings
            # inlined their text, which would become the command's arguments or hide the command; the files
            # stay attached and the agent is told to read them.
            existing.text = captions
            existing.media_text_inlined = [False if flag else flag for flag in pad_inline_flags(existing)]
    return key


def command_first(captions: str, incoming: str, merge_caption) -> Optional[str]:
    """The album's captions when a later item carries its command caption and an earlier one holds text
    (the comment absorbed by the first file): the command leads so it still parses. Else ``None``."""
    if captions and caption_is_command(incoming) and not caption_is_command(captions):
        return merge_caption(incoming, captions)
    return None


def merged_text(text: Optional[str], event: MessageEvent, incoming: Optional[str], merge_caption) -> Optional[str]:
    """``text`` with ``incoming`` (one album item's text) merged in: its caption deduped, its own notes kept."""
    caption, notes = incoming or "", []
    for note in reversed(item_notes(event)):
        if caption.endswith(note):  # two same-name or unnamed same-size items both keep their note
            caption, notes = caption[:-len(note)].rstrip("\n"), [note, *notes]
    if caption:
        text = merge_caption(text, caption)
    for note in notes:
        text = f"{text}\n\n{note}" if text else note
    return text
