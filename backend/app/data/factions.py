"""
Static faction data for the classic Dune board game (Avalon Hill / GF9 edition).

This module is the single source of truth for all fixed faction properties.
Faction-specific game logic lives in the corresponding FactionHandler subclass
in services/game/handlers/. This data layer is purely declarative.

Usage:
    from backend.app.data.factions import FACTION_DATA
    atreides = FACTION_DATA[FactionName.ATREIDES]
"""

from ..models.faction import (
    FactionAbility,
    FactionData,
    FactionName,
    SpecialForceInfo,
    StartingPosition,
)

FACTION_DATA: dict[FactionName, FactionData] = {

    # -------------------------------------------------------------------------
    # HOUSE ATREIDES
    # Starting spice : 10
    # Forces         : 20 total — 10 in Arrakeen, 10 in reserve
    # Free revival   : 2 per turn
    # Basic          : PRESCIENCE — sees each Treachery Card before it is bid
    # Advanced       : KWISATZ_HADERACH — unlocks after 7 cumulative force losses
    # -------------------------------------------------------------------------
    FactionName.ATREIDES: FactionData(
        name=FactionName.ATREIDES,
        display_name="House Atreides",
        starting_spice=10,
        total_regular_forces=20,
        starting_reserve=10,
        starting_positions=[
            StartingPosition(territory="Arrakeen", regular_forces=10),
        ],
        free_revival_per_turn=2,
        max_treachery_cards=4,
        starting_treachery_cards=1,
        traitor_cards_to_keep=1,
        basic_abilities={FactionAbility.PRESCIENCE},
        advanced_abilities={FactionAbility.KWISATZ_HADERACH},
    ),

    # -------------------------------------------------------------------------
    # HOUSE HARKONNEN
    # Starting spice : 10
    # Forces         : 20 total — 10 in Carthag, 10 in reserve
    # Free revival   : 2 per turn
    # Basic          : EXTRA_TREACHERY_CARDS — always receives 2 cards at start
    # Advanced       : CAPTURE_LEADERS — keeps all 4 traitor cards; may hold
    #                  8 Treachery Cards; captures defeated enemy leaders
    # -------------------------------------------------------------------------
    FactionName.HARKONNEN: FactionData(
        name=FactionName.HARKONNEN,
        display_name="House Harkonnen",
        starting_spice=10,
        total_regular_forces=20,
        starting_reserve=10,
        starting_positions=[
            StartingPosition(territory="Carthag", regular_forces=10),
        ],
        free_revival_per_turn=2,
        max_treachery_cards=8,
        starting_treachery_cards=2,
        traitor_cards_to_keep=4,  # Advanced: keeps all 4 traitor cards
        basic_abilities={FactionAbility.EXTRA_TREACHERY_CARDS},
        advanced_abilities={FactionAbility.CAPTURE_LEADERS},
    ),

    # -------------------------------------------------------------------------
    # BENE GESSERIT
    # Starting spice : 5
    # Forces         : 20 total — 1 in Polar Sink, 19 in reserve
    # Free revival   : 1 per turn
    # Basic          : No unique basic abilities
    # Advanced       : PREDICTION — secret alternate win condition;
    #                  ADVISORS — dual-mode Advisor/Fighter tokens
    # Note           : BG always receives 2 spice CHOAM Charity (Advanced)
    # -------------------------------------------------------------------------
    FactionName.BENE_GESSERIT: FactionData(
        name=FactionName.BENE_GESSERIT,
        display_name="Bene Gesserit",
        starting_spice=5,
        total_regular_forces=20,
        starting_reserve=19,
        starting_positions=[
            StartingPosition(territory="Polar Sink", regular_forces=1),
        ],
        free_revival_per_turn=1,
        max_treachery_cards=4,
        starting_treachery_cards=1,
        traitor_cards_to_keep=1,
        basic_abilities=set(),
        advanced_abilities={FactionAbility.PREDICTION, FactionAbility.ADVISORS},
    ),

    # -------------------------------------------------------------------------
    # FREMEN
    # Starting spice : 3
    # Forces         : 20 total — 10 on board, 10 in reserve
    #   Sietch Tabr      : 5 regular
    #   False Wall South : 3 regular
    #   False Wall West  : 2 regular
    # Free revival   : 3 per turn
    # Basic          : No unique basic abilities (sandworm immunity is inherent)
    # Advanced       : SANDWORM_RIDER, FREE_POLAR_SINK_SHIPMENT,
    #                  HALF_PRICE_SHIPMENT, FEDAYKIN (3 special forces)
    # -------------------------------------------------------------------------
    FactionName.FREMEN: FactionData(
        name=FactionName.FREMEN,
        display_name="Fremen",
        starting_spice=3,
        total_regular_forces=20,
        starting_reserve=10,
        starting_positions=[
            StartingPosition(territory="Sietch Tabr", regular_forces=5),
            StartingPosition(territory="False Wall South", regular_forces=3),
            StartingPosition(territory="False Wall West", regular_forces=2),
        ],
        free_revival_per_turn=3,
        max_treachery_cards=4,
        starting_treachery_cards=1,
        traitor_cards_to_keep=1,
        special_force_info=SpecialForceInfo(
            name="Fedaykin",
            combat_strength=2,  # Always 2, including vs Sardaukar
        ),
        total_special_forces=3,
        basic_abilities=set(),
        advanced_abilities={
            FactionAbility.SANDWORM_RIDER,
            FactionAbility.FREE_POLAR_SINK_SHIPMENT,
            FactionAbility.HALF_PRICE_SHIPMENT,
            FactionAbility.FEDAYKIN,
        },
    ),

    # -------------------------------------------------------------------------
    # SPACING GUILD
    # Starting spice : 5
    # Forces         : 20 total — 5 in Tuek's Sietch, 15 in reserve
    # Free revival   : 1 per turn
    # Basic          : CONTROLS_SHIPMENT — all factions must have Guild consent
    # Advanced       : SHIP_ANYTIME — may ship during any phase
    # -------------------------------------------------------------------------
    FactionName.SPACING_GUILD: FactionData(
        name=FactionName.SPACING_GUILD,
        display_name="Spacing Guild",
        starting_spice=5,
        total_regular_forces=20,
        starting_reserve=15,
        starting_positions=[
            StartingPosition(territory="Tuek's Sietch", regular_forces=5),
        ],
        free_revival_per_turn=1,
        max_treachery_cards=4,
        starting_treachery_cards=1,
        traitor_cards_to_keep=1,
        basic_abilities={FactionAbility.CONTROLS_SHIPMENT},
        advanced_abilities={FactionAbility.SHIP_ANYTIME},
    ),

    # -------------------------------------------------------------------------
    # THE EMPEROR
    # Starting spice : 10
    # Forces         : 20 total — all in reserve
    # Free revival   : 1 per turn
    # Basic          : RECEIVES_SHIPMENT_FEES — collects all shipment fees
    # Advanced       : SARDAUKAR — 5 special forces (count as 2 except vs Fremen)
    # -------------------------------------------------------------------------
    FactionName.EMPEROR: FactionData(
        name=FactionName.EMPEROR,
        display_name="The Emperor",
        starting_spice=10,
        total_regular_forces=20,
        starting_reserve=20,
        starting_positions=[],
        free_revival_per_turn=1,
        max_treachery_cards=4,
        starting_treachery_cards=1,
        traitor_cards_to_keep=1,
        special_force_info=SpecialForceInfo(
            name="Sardaukar",
            combat_strength=2,  # vs all factions except Fremen; exception in EmperorHandler
        ),
        total_special_forces=5,
        basic_abilities={FactionAbility.RECEIVES_SHIPMENT_FEES},
        advanced_abilities={FactionAbility.SARDAUKAR},
    ),
}
