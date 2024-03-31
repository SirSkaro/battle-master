from enum import Enum

import pyClarion as cl
from pyClarion import feature


class drive(feature, Enum):
    KEEP_POKEMON_ALIVE = 'keep_pokemon_alive'
    HAVE_MORE_POKEMON_THAN_OPPONENT = 'have_more_pokemon_than_opponent'
    KO_OPPONENT = 'ko_opponent'
    DO_DAMAGE = 'do_damage'
    KEEP_HEALTHY = 'keep_healthy'
    BUFF_SELF = 'buff_self'
    DEBUFF_OPPONENT = 'debuff_opponent'
    PREVENT_OPPONENT_BUFF = 'prevent_opponent_buff'
    KEEP_TYPE_ADVANTAGE = 'keep_type_advantage'
    PREVENT_TYPE_DISADVANTAGE = 'prevent_type_disadvantage'
    HAVE_SUPER_EFFECTIVE_MOVE_AVAILABLE = 'have_super_effective_move_available'
    REVEAL_HIDDEN_INFORMATION = 'reveal_hidden_information'

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super(Enum, self).__setattr__(key, value)
        else:
            super(feature, self).__setattr__(key, value)


class goal(cl.chunk):
    pass


DRIVE_DOMAIN = cl.Domain(features=tuple([d for d in drive]))

