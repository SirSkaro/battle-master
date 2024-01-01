import asyncio
import logging

from dependency_injector.wiring import Provide, inject
from poke_env.player import Player

from .containers import Container


@inject
async def main(player: Player = Provide[Container.player], opponent: str = Provide[Container.opponent]):
    logger = logging.getLogger(f"{__name__}")
    logger.info(f"Logged into Showdown as {player.username}")

    logger.info(f"Challenging {opponent}")
    await player.send_challenges(opponent, n_challenges=1)


if __name__ == "__main__":
    ioc_container = Container()
    ioc_container.init_resources()
    ioc_container.wire(modules=[__name__])

    asyncio.get_event_loop().run_until_complete(main())
