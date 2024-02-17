from poke_env.environment import Battle, Pokemon, Effect, Field
from poke_engine import Battle as BattleSimulation, Battler, Pokemon as PokemonSimulation, constants
from poke_engine.battle_modifier import check_speed_ranges
from poke_engine.helpers import normalize_name


def convert_battle(battle: Battle) -> BattleSimulation:
    simulation = BattleSimulation('')
    simulation.user = convert_player(battle)
    simulation.opponent = convert_opponent(battle)
    check_speed_ranges(battle, '')

    if len(battle.weather) > 0:
        weather = next(iter(battle.weather))
        simulation.weather = normalize_name(weather).replace("_", "")

    if len(battle.fields) > 0:
        field_effect = next(iter(battle.fields))
        simulation.field = normalize_name(field_effect).replace("_", "")

    simulation.trick_room = Field.TRICK_ROOM in battle.fields
    simulation.turn = battle.turn
    simulation.force_switch = battle.force_switch
    simulation.wait = battle._wait

    return simulation


def convert_player(battle: Battle) -> Battler:
    user = Battler()
    user.name = battle.player_username
    user.account_name = battle.player_username
    user.active = convert_player_pokemon(battle.active_pokemon) if battle.active_pokemon is not None else None
    user.reserve = [convert_player_pokemon(pokemon) for pokemon in battle.available_switches]
    user.trapped = Effect.TRAPPED in battle.active_pokemon.effects if battle.active_pokemon is not None else False
    user.future_sight = Effect.FUTURE_SIGHT in battle.active_pokemon.effects if battle.active_pokemon is not None else False
    user.side_conditions = {normalize_name(condition).replace("_", ""): value for condition, value in battle.side_conditions.items()}

    return user


def convert_opponent(battle: Battle) -> Battler:
    user = Battler()
    user.name = battle.opponent_username
    user.account_name = battle.opponent_username
    user.active = convert_opponent_pokemon(battle.opponent_active_pokemon) if battle.opponent_active_pokemon is not None else None
    user.reserve = [convert_opponent_pokemon(pokemon) for pokemon in battle.opponent_team.values() if not pokemon.active]
    user.trapped = Effect.TRAPPED in battle.opponent_active_pokemon.effects if battle.opponent_active_pokemon is not None else False
    user.future_sight = Effect.FUTURE_SIGHT in battle.opponent_active_pokemon.effects if battle.opponent_active_pokemon is not None else False
    user.side_conditions = {normalize_name(condition).replace("_", ""): value for condition, value in battle.opponent_side_conditions.items()}

    return user


def convert_player_pokemon(pokemon: Pokemon) -> PokemonSimulation:
    simulated = PokemonSimulation(pokemon.species, pokemon.level)
    simulated.fainted = pokemon.fainted
    simulated.status = pokemon.status.value.lower() if pokemon.status is not None else None
    simulated.stats = {
        constants.ATTACK: pokemon.stats['atk'],
        constants.DEFENSE: pokemon.stats['def'],
        constants.SPECIAL_ATTACK: pokemon.stats['spa'],
        constants.SPECIAL_DEFENSE: pokemon.stats['spd'],
        constants.SPEED: pokemon.stats['spe']
    }
    simulated.hp = pokemon.current_hp
    simulated.max_hp = pokemon.max_hp
    simulated.item = pokemon.item
    simulated.ability = pokemon.ability
    for move in pokemon.moves.values():
        simulated.add_move(move.id)
    simulated.volatile_statuses = [normalize_name(effect.value).replace("_", "") for effect, count in pokemon.effects.items() if count > 0]
    simulated.boosts = {
        constants.ACCURACY: pokemon.boosts['accuracy'],
        constants.EVASION: pokemon.boosts['evasion'],
        constants.ATTACK: pokemon.boosts['atk'],
        constants.DEFENSE: pokemon.stats['def'],
        constants.SPECIAL_ATTACK: pokemon.stats['spa'],
        constants.SPECIAL_DEFENSE: pokemon.stats['spd'],
        constants.SPEED: pokemon.stats['spe']
    }
    simulated.terastallized = pokemon.terastallized
    simulated.types = [normalize_name(type.value) for type in pokemon.types if type is not None]

    return simulated


def convert_opponent_pokemon(pokemon: Pokemon) -> PokemonSimulation:
    simulated = PokemonSimulation(pokemon.species, pokemon.level)
    simulated.fainted = pokemon.fainted
    simulated.status = pokemon.status.value.lower() if pokemon.status is not None else None
    simulated.set_most_likely_spread()
    simulated.hp = (pokemon.current_hp / 100.0) * simulated.max_hp

    if pokemon.ability is not None:
        simulated.ability = pokemon.ability
    else:
        simulated.set_most_likely_ability_unless_revealed()

    if pokemon.item is not None:
        simulated.item = pokemon.item
    else:
        simulated.set_most_likely_item_unless_revealed()

    for move in pokemon.moves.values():
        simulated.add_move(move.id)
    if len(simulated.moves) < 4:
        simulated.set_likely_moves_unless_revealed()

    simulated.volatile_statuses = [normalize_name(effect.value).replace("_", "") for effect, count in pokemon.effects.items() if count > 0]

    simulated.boosts = {
        constants.ACCURACY: pokemon.boosts['accuracy'],
        constants.EVASION: pokemon.boosts['evasion'],
        constants.ATTACK: pokemon.boosts['atk'],
        constants.DEFENSE: pokemon.stats['def'],
        constants.SPECIAL_ATTACK: pokemon.stats['spa'],
        constants.SPECIAL_DEFENSE: pokemon.stats['spd'],
        constants.SPEED: pokemon.stats['spe']
    }

    simulated.terastallized = pokemon.terastallized
    simulated.types = [normalize_name(type.value) for type in pokemon.types if type is not None]

    return simulated


