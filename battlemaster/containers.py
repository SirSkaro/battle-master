import logging.config

from dependency_injector import containers, providers
from poke_env import AccountConfiguration, LocalhostServerConfiguration
from poke_env.player import RandomPlayer, Player


def _configure_player(config: providers.Configuration) -> providers.Singleton[Player]:
    auth = config.showdown_auth
    account_config = AccountConfiguration(auth.username(), auth.password())
    return providers.Singleton(
        RandomPlayer,
        account_configuration=account_config,
        server_configuration=LocalhostServerConfiguration
    )


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    config.from_ini('config.ini')

    logging = providers.Resource(logging.config.fileConfig, fname="logging.ini")

    player = _configure_player(config)
    opponent = providers.Object(config.opponent.username())
