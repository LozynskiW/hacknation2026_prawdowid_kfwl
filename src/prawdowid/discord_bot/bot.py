"""Bot Discorda – adapter kanału. Zero logiki merytorycznej: zbiera zgłoszenie, woła API, pokazuje wynik."""

import hashlib
import hmac
import logging
import re
import time
from collections import defaultdict, deque

import discord
from discord import app_commands

from . import render
from .api_client import PrawdowidClient
from .config import BotSettings

log = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 5000
URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


class PrawdowidBot(discord.Client):
    def __init__(self, settings: BotSettings) -> None:
        intents = discord.Intents.default()
        intents.message_content = settings.message_content_intent
        super().__init__(intents=intents)
        self.settings = settings
        self.api = PrawdowidClient(settings)
        self.tree = app_commands.CommandTree(self)
        self._recent: dict[int, deque[float]] = defaultdict(deque)
        self._register_commands()

    # ── cykl życia ──────────────────────────────────────────────────────────

    async def setup_hook(self) -> None:
        if self.settings.discord_guild_id:
            guild = discord.Object(id=self.settings.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        log.info("bot ready as %s (id=%s)", self.user, self.user.id if self.user else "?")

    async def close(self) -> None:
        await self.api.aclose()
        await super().close()

    # ── komendy ─────────────────────────────────────────────────────────────

    def _register_commands(self) -> None:
        @self.tree.command(name="sprawdz", description="Sprawdź informację w wiarygodnych źródłach")
        @app_commands.describe(
            tresc="Tekst do sprawdzenia (np. wiadomość, którą dostałeś)",
            link="Adres strony do sprawdzenia (opcjonalnie)",
            prywatnie="Pokaż wynik tylko mnie",
        )
        async def sprawdz(
            interaction: discord.Interaction,
            tresc: str | None = None,
            link: str | None = None,
            prywatnie: bool = False,
        ) -> None:
            # Discord wymaga reakcji w ciągu 3 s – od razu "Bot myśli…", wynik dosyłamy (token ważny 15 min).
            await interaction.response.defer(ephemeral=prywatnie, thinking=True)
            embeds = await self._handle(
                user_id=interaction.user.id,
                raw_text=tresc,
                raw_url=link,
                conversation_id=f"{interaction.channel_id}:{interaction.id}",
            )
            await interaction.followup.send(embeds=embeds, ephemeral=prywatnie)

        @self.tree.command(name="pomoc", description="Jak działa Prawdowid")
        async def pomoc(interaction: discord.Interaction) -> None:
            await interaction.response.send_message(embed=render.help_embed(), ephemeral=True)

    # ── wiadomości prywatne i oznaczenia bota ───────────────────────────────

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or self.user is None:
            return
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user in message.mentions
        if not (is_dm or is_mention):
            return

        text = message.content.replace(self.user.mention, "").replace(f"<@!{self.user.id}>", "").strip()
        async with message.channel.typing():
            embeds = await self._handle(
                user_id=message.author.id,
                raw_text=text,
                raw_url=None,
                conversation_id=f"{message.channel.id}:{message.id}",
            )
        await message.reply(embeds=embeds, mention_author=False)

    # ── wspólna obsługa ─────────────────────────────────────────────────────

    async def _handle(
        self, *, user_id: int, raw_text: str | None, raw_url: str | None, conversation_id: str
    ) -> list[discord.Embed]:
        if not self._allow(user_id):
            return [render.input_error_embed("Zbyt wiele zapytań. Spróbuj ponownie za minutę.")]

        text, url, error = _normalize_input(raw_text, raw_url)
        if error:
            return [render.input_error_embed(error)]

        outcome = await self.api.check(
            text=text, url=url, user_ref=self._user_ref(user_id), conversation_id=conversation_id
        )
        full_url = None
        if outcome.report and outcome.report.check_id and self.settings.web_result_url_template:
            full_url = self.settings.web_result_url_template.format(check_id=outcome.report.check_id)
        return render.render(outcome, full_url)

    def _user_ref(self, user_id: int) -> str:
        """Pseudonim użytkownika: HMAC-SHA256 z solą – surowe ID Discorda nie opuszcza bota."""
        salt = self.settings.user_ref_salt.get_secret_value().encode()
        return hmac.new(salt, str(user_id).encode(), hashlib.sha256).hexdigest()

    def _allow(self, user_id: int) -> bool:
        now = time.monotonic()
        window = self._recent[user_id]
        while window and now - window[0] > self.settings.rate_limit_window_s:
            window.popleft()
        if len(window) >= self.settings.rate_limit_count:
            return False
        window.append(now)
        return True


def _normalize_input(raw_text: str | None, raw_url: str | None) -> tuple[str | None, str | None, str | None]:
    """Zwraca (tekst, url, komunikat_błędu). Pierwszy link z tekstu trafia do pola url."""
    text = (raw_text or "").strip() or None
    url = (raw_url or "").strip() or None

    if url is None and text:
        found = URL_RE.search(text)
        if found:
            url = found.group(0).rstrip(").,;!?\"'")

    if url is not None and not URL_RE.fullmatch(url):
        return None, None, "Link musi zaczynać się od http:// lub https://."
    if text is None and url is None:
        return None, None, (
            "Wklej tekst lub link do sprawdzenia, np.\n"
            "`/sprawdz tresc: Czy w Warszawie wprowadzono alert RCB o skażeniu?`"
        )
    if text and len(text) > MAX_TEXT_LENGTH:
        return None, None, f"Tekst jest za długi (maks. {MAX_TEXT_LENGTH} znaków). Skróć go do najważniejszej części."
    return text, url, None
