# Warzone 2100 12P test build

This branch exists only to build an experimental 12-player Warzone 2100 4.7.0 Windows client.

It clones upstream 4.7.0, changes MAX_PLAYERS from 11 to 13 (12 human positions + scavenger slot), assigns a separate experimental network protocol ID (0x12A0/1), and converts WaterLoop to 12 positions.

The workflow output is intentionally incompatible with stock Warzone 2100 4.7.0 and is for testing only.
