import logging.config

from dependency_injector import containers, providers
from poke_env import AccountConfiguration, ServerConfiguration
from poke_env.player import RandomPlayer, Player


def _configure_player(config: providers.Configuration) -> providers.Singleton[Player]:
    showdown_settings = config.showdown
    account_config = AccountConfiguration(showdown_settings.username(), showdown_settings.password())
    server_config = ServerConfiguration(showdown_settings.server_url(), showdown_settings.auth_url())
    return providers.Singleton(
        RandomPlayer,
        account_configuration=account_config,
        server_configuration=server_config
    )


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    config.from_ini('config.ini')

    logging = providers.Resource(logging.config.fileConfig, fname="logging.ini")

    player = _configure_player(config)
    opponent = providers.Object(config.opponent.username())
