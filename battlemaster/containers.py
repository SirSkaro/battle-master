import logging.config
from typing import Type

from dependency_injector import containers, providers
from poke_env import AccountConfiguration, ServerConfiguration
from poke_env.player import RandomPlayer, Player

from .mind import create_agent
from .agents import BattleMasterPlayer, MaxDamagePlayer


class PlayerSingleton(providers.Provider):

    __slots__ = ("_factory",)

    def __init__(self, provides, *args, **kwargs):
        self._factory = providers.Singleton(provides, *args, **kwargs)
        super().__init__()

    def __deepcopy__(self, memo):
        copied = memo.get(id(self))
        if copied is not None:
            return copied

        copied = self.__class__(
            self._factory.provides,
            *providers.deepcopy(self._factory.args, memo),
            **providers.deepcopy(self._factory.kwargs, memo),
        )
        self._copy_overridings(copied, memo)

        return copied

    @property
    def related(self):
        """Return related providers generator."""
        yield from [self._factory]
        yield from super().related

    def _provide(self, args, kwargs):
        player: Player = self._factory(*args, **kwargs)
        player.logger.handlers.clear()
        return player


def _get_showdown_config(config: providers.Configuration):
    showdown_settings = config.showdown
    account_config = AccountConfiguration(showdown_settings.username(), showdown_settings.password())
    server_config = ServerConfiguration(showdown_settings.server_url(), showdown_settings.auth_url())
    return account_config, server_config


def _configure_player(config: providers.Configuration) -> PlayerSingleton:
    account_config, server_config = _get_showdown_config(config)
    mind, stimulus = _configure_mind()
    return PlayerSingleton(
        BattleMasterPlayer,
        mind=mind,
        stimulus=stimulus,
        account_configuration=account_config,
        server_configuration=server_config,
        max_concurrent_battles=config.agent.max_concurrent_battles.as_int()()
    )


def _configure_benchmark_player(config: providers.Configuration, provides: Type) -> PlayerSingleton:
    _, server_config = _get_showdown_config(config)
    return PlayerSingleton(
        provides,
        server_configuration=server_config,
        max_concurrent_battles=config.agent.max_concurrent_battles.as_int()()
    )


def _configure_mind():
    mind, stimulus = create_agent()
    return providers.Object(mind), providers.Object(stimulus)


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    config.from_ini('config.ini')

    logging = providers.Resource(logging.config.fileConfig, fname="logging.ini")

    player = _configure_player(config)
    benchmark_agents = providers.Dict(
        random=_configure_benchmark_player(config, RandomPlayer),
        max_damage=_configure_benchmark_player(config, MaxDamagePlayer)
    )
