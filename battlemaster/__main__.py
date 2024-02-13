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
                                  choices=['random', 'max_damage', 'simple_heuristic'])
    benchmark_parser.add_argument("num_battles", type=int, help='The number of battles to play')

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


if __name__ == "__main__":
    cli_args = _parse_command_line_args()

    ioc_container = Container()
    ioc_container.init_resources()
    ioc_container.wire(modules=[__name__])

    if cli_args.mode == 'challenge':
        asyncio.get_event_loop().run_until_complete(challenge_opponent(cli_args.opponent_username))
    elif cli_args.mode == 'benchmark':
        asyncio.get_event_loop().run_until_complete(benchmark(cli_args.num_battles, cli_args.agent))
