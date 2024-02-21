import asyncio
import logging
import argparse
from argparse import Namespace
from typing import Dict

from dependency_injector.wiring import Provide, inject
from poke_env.player import Player

from .containers import Container


def _parse_command_line_args() -> Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode")
    subparsers.required = True

    challenge_parser = subparsers.add_parser('challenge', help='Challenge the specified player.')
    challenge_parser.add_argument("opponent_username", help='The name of the user')

    benchmark_parser = subparsers.add_parser('benchmark', help='Run Battle Master against a benchmark agent')
    benchmark_parser.add_argument("agent", type=str, help='Which benchmark agent to use',
                                  choices=['random', 'max_damage', 'simple_heuristic', 'exp_minmax'])
    benchmark_parser.add_argument("num_battles", type=int, help='The number of battles to play')

    ladder_parser = subparsers.add_parser('ladder', help='Play against opponents on the ladder')
    ladder_parser.add_argument("num_games", type=int, help='The number of games to play on the ladder')

    args = parser.parse_args()
    return args


@inject
async def challenge_opponent(opponent: str, agent: Player = Provide[Container.player]):
    logger = logging.getLogger(f"{__name__}")
    logger.info(f"Logged into Showdown as {agent.username}")
    logger.info(f"Challenging {opponent}")
    await agent.send_challenges(opponent, n_challenges=1)


@inject
async def benchmark(number_battles: int, benchmark_agent: str,
                    agent: Player = Provide[Container.player],
                    benchmark_agents: Dict[str, Player] = Provide[Container.benchmark_agents]):
    logger = logging.getLogger(f"{__name__}")
    logger.info(f"Benchmarking {agent.username} against {benchmark_agent}")
    await agent.battle_against(benchmark_agents[benchmark_agent], number_battles)
    logger.info(f'Agent won {agent.n_won_battles} / {number_battles} battles {agent.n_won_battles/number_battles}%')


@inject
async def play_ladder(num_games: int, agent: Player = Provide[Container.player]):
    logger = logging.getLogger(f"{__name__}")
    logger.info(f"Playing {num_games} games on the ladder as {agent.username}")
    await agent.ladder(num_games)


if __name__ == "__main__":
    cli_args = _parse_command_line_args()

    ioc_container = Container()
    ioc_container.init_resources()
    ioc_container.wire(modules=[__name__])

    if cli_args.mode == 'challenge':
        asyncio.run(challenge_opponent(cli_args.opponent_username))
    elif cli_args.mode == 'benchmark':
        asyncio.run(benchmark(cli_args.num_battles, cli_args.agent))
    elif cli_args.mode == 'ladder':
        asyncio.run(play_ladder(cli_args.num_games))
