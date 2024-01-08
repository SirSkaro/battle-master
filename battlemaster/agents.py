from typing import Optional
from random import shuffle

from pyClarion import chunk
from poke_env.player import Player
from poke_env.environment import Battle
from poke_env.ps_client.account_configuration import AccountConfiguration
from poke_env.ps_client.server_configuration import ServerConfiguration
from pyClarion import Structure, Construct, subsystem, flow_tt


class BattleMasterPlayer(Player):

    def __init__(self, mind: Structure, stimulus: Construct, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mind = mind
        self.stimulus = stimulus

    def choose_move(self, battle: Battle):
        type1, type2 = battle.opponent_active_pokemon.types
        stimulus = {chunk(type1.name.lower()): 1.}
        if type2 is not None:
            stimulus[chunk(type2.name.lower())] = 1.

        self.stimulus.process.input(stimulus)
        self.mind.step()
        associations = self.mind.output[(subsystem('nacs'), flow_tt('associations'))]

        move_type_priority_list = [symbol.cid for symbol in sorted(associations, key=associations.get, reverse=True) if isinstance(symbol, chunk)]
        shuffle(battle.available_moves)

        self.logger.info(f'I see {stimulus}')
        self.logger.info(f'I know these types are super-effective: {move_type_priority_list}, and I have {[move.id for move in battle.available_moves]}')

        for move_type_to_choose in move_type_priority_list:
            for available_move in battle.available_moves:
                if available_move.type.name.lower() == move_type_to_choose:
                    self.logger.info(f'I am picking on of my super-effective moves: {available_move.id}')
                    return self.create_order(available_move)

        self.logger.info(f"I don't have a super-effective move. Picking a random action...")
        return self.choose_random_move(battle)
