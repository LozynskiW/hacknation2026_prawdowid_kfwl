"""Uruchomienie: python -m discord_bot"""

import logging

from .bot import PrawdowidBot
from .config import BotSettings


def main() -> None:
    # Logujemy tylko metadane (ID rozmowy, czasy) – nigdy treści wiadomości użytkowników.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = BotSettings()  # type: ignore[call-arg]
    bot = PrawdowidBot(settings)
    bot.run(settings.discord_token.get_secret_value(), log_handler=None)


if __name__ == "__main__":
    main()
