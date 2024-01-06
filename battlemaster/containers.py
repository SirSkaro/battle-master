import logging.config

from dependency_injector import containers, providers
from poke_env import AccountConfiguration, ServerConfiguration
from poke_env.player import RandomPlayer, Player

from .mind import create_agent
from .agents import BattleMasterPlayer


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


def _configure_player(config: providers.Configuration) -> PlayerSingleton:
    showdown_settings = config.showdown
    account_config = AccountConfiguration(showdown_settings.username(), showdown_settings.password())
    server_config = ServerConfiguration(showdown_settings.server_url(), showdown_settings.auth_url())
    mind, stimulus = _configure_mind()
    return PlayerSingleton(
        BattleMasterPlayer,
        mind=mind,
        stimulus=stimulus,
        account_configuration=account_config,
        server_configuration=server_config
    )


def _configure_mind():
    mind, stimulus = create_agent()
    return providers.Object(mind), providers.Object(stimulus)


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    config.from_ini('config.ini')

    logging = providers.Resource(logging.config.fileConfig, fname="logging.ini")

    player = _configure_player(config)
    opponent = providers.Object(config.opponent.username())
