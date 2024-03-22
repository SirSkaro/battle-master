import logging
import logging.config
from typing import Type, List
import re

from dependency_injector import containers, providers
from poke_env import AccountConfiguration, ServerConfiguration
from poke_env.player import RandomPlayer, Player, SimpleHeuristicsPlayer

from .mind import create_agent
from .agents import BattleMasterPlayer, MaxDamagePlayer, ExpectiminimaxPlayer
from .adapters.clarion_adapter import MindAdapter, PerceptionFactory


class ShowdownEventFilter(logging.Filter):
    def __init__(self, events_to_ignore: List[str] = []):
        super().__init__()
        regex = '|'.join(events_to_ignore)
        self._record_regex = re.compile(f'\\|{regex}\\|')

    def filter(self, record: logging.LogRecord) -> bool:
        log_message = record.getMessage()
        return self._record_regex.search(log_message) is None


class PlayerSingleton(providers.Provider):

    __slots__ = ("_factory", "_config")

    def __init__(self, provides, config: providers.Configuration, *args, **kwargs):
        self._factory = providers.Singleton(provides, *args, **kwargs)
        super().__init__()
        self._config = config

    def __deepcopy__(self, memo):
        copied = memo.get(id(self))
        if copied is not None:
            return copied

        copied = self.__class__(
            self._factory.provides,
            self._config,
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
        log_ignore = self._config.log.showdown_event_ignore().split(',')

        player: Player = self._factory(*args, **kwargs)
        player.logger.handlers.clear()
        player.logger.addFilter(ShowdownEventFilter(log_ignore))
        return player


def _get_showdown_config(config: providers.Configuration):
    showdown_settings = config.showdown
    account_config = AccountConfiguration(showdown_settings.username(), showdown_settings.password())
    server_config = ServerConfiguration(showdown_settings.server_url(), showdown_settings.auth_url())
    return account_config, server_config


def _configure_player(config: providers.Configuration) -> PlayerSingleton:
    account_config, server_config = _get_showdown_config(config)
    mind = _configure_mind()
    return PlayerSingleton(
        BattleMasterPlayer,
        config,
        mind=mind,
        account_configuration=account_config,
        server_configuration=server_config,
        max_concurrent_battles=config.agent.max_concurrent_battles.as_int()()
    )


def _configure_benchmark_player(config: providers.Configuration, provides: Type) -> PlayerSingleton:
    _, server_config = _get_showdown_config(config)
    return PlayerSingleton(
        provides,
        config,
        server_configuration=server_config,
        max_concurrent_battles=config.agent.max_concurrent_battles.as_int()(),
        start_listening=False
    )


def _configure_mind():
    mind, stimulus = create_agent()
    factory = PerceptionFactory()
    return providers.Object(MindAdapter(mind, stimulus, factory))


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    config.from_ini('config.ini')

    logging = providers.Resource(logging.config.fileConfig, fname="logging.ini")

    player = _configure_player(config)
    benchmark_agents = providers.Dict(
        random=_configure_benchmark_player(config, RandomPlayer),
        max_damage=_configure_benchmark_player(config, MaxDamagePlayer),
        simple_heuristic=_configure_benchmark_player(config, SimpleHeuristicsPlayer),
        exp_minmax=_configure_benchmark_player(config, ExpectiminimaxPlayer)
    )
