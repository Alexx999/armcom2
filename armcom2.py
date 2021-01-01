# -*- coding: UTF-8 -*-
# Python 3.6.8 x64
# Libtcod 1.6.4 x64
##########################################################################################
#                                                                                        #
#                                Armoured Commander II                                   #
#                                                                                        #
##########################################################################################
#             Project Started February 23, 2016; Restarted July 25, 2016                 #
#          Restarted again January 11, 2018; Restarted again January 2, 2019             #
#                           First stable release March 14, 2020                          #
#          Private Beta Steam release May 9, 2020; Early Access May 14, 2020             #
#                             Full Steam release ???                                     #
##########################################################################################
#
#    Copyright (c) 2016-2020 Gregory Adam Scott
#    (armouredcommander@gmail.com)
#
#    This file is part of Armoured Commander II.
#
#    Armoured Commander II is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Armoured Commander II is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Armoured Commander II, in the form of a file named "gpl.txt".
#    If not, see <https://www.gnu.org/licenses/>.
#
#    xp_loader.py is covered under a MIT License (MIT) and is Copyright (c) 2015
#    Sean Hagar; see XpLoader_LICENSE.txt for more info.
#
#    Some sound samples from the C64 sample pack by Odo:
#    <https://howtomakeelectronicmusic.com/270mb-of-free-c64-samples-made-by-odo/>
#
#    Steam integration thanks to SteamworksPy, covered under a MIT License (MIT)
#    Copyright (c) 2016 GP Garcia, CoaguCo Industries
#    https://github.com/Gramps/SteamworksPy
#
##########################################################################################

DEBUG = False						# debug flag - set to False in all distribution versions

##### Libraries #####
import os, sys						# OS-related stuff
from shutil import copyfile
from pathlib import Path				# to find the user's home directory
import libtcodpy as libtcod
os.environ['PYSDL2_DLL_PATH'] = os.getcwd() + '/lib'.replace('/', os.sep)	# set sdl2 dll path
from configparser import ConfigParser			# saving and loading configuration settings
from random import choice, shuffle, sample		# for the illusion of randomness
from math import floor, cos, sin, sqrt, degrees, atan2, ceil	# math and heading calculations
from astral import LocationInfo, moon
from astral.sun import sun
import xp_loader, gzip					# loading xp image files
import json						# for loading JSON data
import time
from datetime import date, datetime, timedelta		# for timestamping logs, date calculations
from textwrap import wrap				# breaking up strings
import shelve						# saving and loading games
import sdl2.sdlmixer as mixer				# sound effects
from calendar import monthrange				# for date calculations
import traceback					# for error reporting
from steamworks import STEAMWORKS			# main steamworks library


##########################################################################################
#                                        Constants                                       #
##########################################################################################

NAME = 'Armoured Commander II'				# game name
VERSION = '7.1.3'					# game version
DISCLAIMER = 'This is a work of fiction and no endorsement of any historical ideologies or events depicted within is intended.'
DATAPATH = 'data/'.replace('/', os.sep)			# path to data files
SAVEPATH = 'saved_campaigns/'.replace('/', os.sep)	# path to saved campaign folder
BACKUP_PATH = 'backups/'.replace('/', os.sep)		# path to backup campaign folders
SOUNDPATH = 'sounds/'.replace('/', os.sep)		# path to sound samples
CAMPAIGNPATH = 'campaigns/'.replace('/', os.sep)	# path to campaign files
MODPATH = 'unit_mods/'.replace('/', os.sep)		# path to modded unit files

if os.name == 'posix':				# linux (and OS X?) has to use SDL for some reason
	RENDERER = libtcod.RENDERER_SDL
else:
	RENDERER = libtcod.RENDERER_SDL2

LIMIT_FPS = 50						# maximum screen refreshes per second
SCREEN_WIDTH, SCREEN_HEIGHT = 120, 68			# size of screen in character cells for fullscreen mode
WINDOW_WIDTH, WINDOW_HEIGHT = 90, 60			# size of game window in character cells
WINDOW_XM, WINDOW_YM = int(WINDOW_WIDTH/2), int(WINDOW_HEIGHT/2)	# center of game window
KEYBOARDS = ['QWERTY', 'AZERTY', 'QWERTZ', 'Dvorak', 'Custom']	# list of possible keyboard layout settings
MAX_TANK_NAME_LENGTH = 20				# maximum length of tank names
MAX_CREW_NAME_LENGTH = 17				# maximum total length of crew names, including space
MAX_NICKNAME_LENGTH = 10				# " for crew nicknames

DEBUG_OPTIONS  = [
	'Regenerate CD Map Roads & Rivers', 'Regenerate Objectives', 'Spawn Enemy', 'Remove Enemy',
	'Attack Selected Crewman (Scenario)', 'Set Crewman Injury', 'Set Time to End of Day',
	'End Current Scenario', 'Export Campaign Log', 'Regenerate Weather'
]

# defintions for campaign options
CAMPAIGN_OPTIONS = [
	('Player Commander', 'permadeath', 'You take on the role of the tank commander. If you are seriously ' +
		'injured, you may miss a number of days of the campaign. If you ' +
		'are killed, your campaign ends.', 0.25),
	('Fate Points', 'fate_points', 'You are protected by fate, giving you the option of negating ' +
		'a few incoming attacks per day that might otherwise destroy ' +
		'your tank.', -0.15),
	('Realistic Explosions', 'explosion_kills', "If your tank is destroyed there's a chance that " +
		"gun ammo or fuel will ignite, igniting an explosion inside the tank. If this option is " +
		"active, all crewmen inside the tank are killed by such an explosion (no fate point use allowed), " +
		"otherwise they have a small chance of survival.", 0.10),
	('Random Tank Model', 'random_tank', 'At the start of a new campaign and whenever replacing ' +
		'a lost tank, you will be assigned a random tank model, based on its historical availability ' +
		'for that date in the calendar. During a refit period, you can still select any available tank ' +
		'model.', 0.10),
	('Ahistorical Availability', 'ahistorical', 'Unit rarity factors will be ignored for player and enemy units, ' +
		'meaning that tanks, guns, and other unit types may appear before or after they were ' +
		'historically available.', -0.15),
	('Realistic Injuries', 'realistic_injuries', 'Crewmen will be injured more often from incoming small ' +
		'arms attacks and spalling.', 0.10),
	('Realistic Enemies', 'realistic_ai', 'Enemies will be more aggressive, dangerous, and will react ' +
		'in a more realistic way.', 0.20)
]

##### Hex geometry definitions #####

# directional and positional constants
DESTHEX = [(0,-1), (1,-1), (1,0), (0,1), (-1,1), (-1,0)]	# change in hx, hy values for hexes in each direction
CD_DESTHEX = [(1,-1), (1,0), (0,1), (-1,1), (-1,0), (0,-1)]	# same for pointy-top
PLOT_DIR = [(0,-1), (1,-1), (1,1), (0,1), (-1,1), (-1,-1)]	# position of direction indicator
TURRET_CHAR = [254, 47, 92, 254, 47, 92]			# characters to use for turret display

# relative locations of edge cells in a given direction for a map hex
HEX_EDGE_CELLS = {
	0: [(-1,-2),(0,-2),(1,-2)],
	1: [(1,-2),(2,-1),(3,0)],
	2: [(3,0),(2,1),(1,2)],
	3: [(1,2),(0,2),(-1,2)],
	4: [(-1,2),(-2,1),(-3,0)],
	5: [(-3,0),(-2,-1),(-1,-2)]
}

# same for campaign day hexes (pointy-topped)
CD_HEX_EDGE_CELLS = {
	0: [(0,-4),(1,-3),(2,-2),(3,-1)],
	1: [(3,-1),(3,0),(3,1)],
	2: [(3,1),(2,2),(1,3),(0,4)],
	3: [(0,4),(-1,3),(-2,2),(-3,1)],
	4: [(-3,1),(-3,0),(-3,-1)],
	5: [(-3,-1),(-2,-2),(-1,-3),(0,-4)]
}

# one cell smaller
CD_HEX_EDGE_CELLS2 = {
	0: [(0,-3),(1,-2),(2,-1)],
	1: [(2,-1),(2,0),(2,1)],
	2: [(2,1),(1,2),(0,3)],
	3: [(0,3),(-1,2),(-2,1)],
	4: [(-2,1),(-2,0),(-2,-1)],
	5: [(-2,-1), (-1,-2), (0,-3)]
}

# list of hexes on campaign day map
CAMPAIGN_DAY_HEXES = [
	(0,0),(1,0),(2,0),(3,0),(4,0),
	(0,1),(1,1),(2,1),(3,1),
	(-1,2),(0,2),(1,2),(2,2),(3,2),
	(-1,3),(0,3),(1,3),(2,3),
	(-2,4),(-1,4),(0,4),(1,4),(2,4),
	(-2,5),(-1,5),(0,5),(1,5),
	(-3,6),(-2,6),(-1,6),(0,6),(1,6),
	(-3,7),(-2,7),(-1,7),(0,7),
	(-4,8),(-3,8),(-2,8),(-1,8),(0,8)
]


##### Colour Definitions #####
KEY_COLOR = libtcod.Color(255, 0, 255)			# key color for transparency
ACTION_KEY_COL = libtcod.Color(51, 153, 255)		# colour for key commands
HIGHLIGHT_MENU_COL = libtcod.Color(30, 70, 130)		# background highlight colour for selected menu option
TITLE_COL = libtcod.Color(102, 178, 255)		# menu titles
PORTRAIT_BG_COL = libtcod.Color(217, 108, 0)		# background color for unit portraits
UNKNOWN_UNIT_COL = libtcod.grey				# unknown enemy unit display colour
ENEMY_UNIT_COL = libtcod.Color(255, 20, 20)		# known "
ALLIED_UNIT_COL = libtcod.Color(120, 120, 255)		# allied unit display colour
GOLD_COL = libtcod.Color(255, 255, 100)			# golden colour for awards
DIRT_ROAD_COL = libtcod.Color(80, 50, 20)		# dirt roads on campaign day map
STONE_ROAD_COL = libtcod.Color(110, 110, 110)		# stone "
RIVER_COL = libtcod.Color(0, 0, 140)			# rivers "
BRIDGE_COL = libtcod.Color(40, 20, 10)			# bridges/fords "

# text names for months
MONTH_NAMES = [
	'', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
	'October', 'November', 'December'
]

# order of turn phases
PHASE_COMMAND = 0
PHASE_SPOTTING = 1
PHASE_CREW_ACTION = 2
PHASE_MOVEMENT = 3
PHASE_SHOOTING = 4
PHASE_ALLIED_ACTION = 5
PHASE_ENEMY_ACTION = 6

# text names for scenario turn phases
SCEN_PHASE_NAMES = [
	'Command', 'Spotting', 'Crew Action', 'Movement', 'Shooting', 'Allied Action',
	'Enemy Action'
]

# colour associated with phases
SCEN_PHASE_COL = [
	libtcod.yellow, libtcod.purple, libtcod.light_blue, libtcod.green, libtcod.red,
	ALLIED_UNIT_COL, ENEMY_UNIT_COL 
]

# list of campaign calendar menus and their highlight colours
CC_MENU_LIST = [
	('Proceed', 1, libtcod.Color(70, 140, 0)),
	('Crew and Tank', 2, libtcod.Color(140, 140, 0)),
	('Journal', 3, libtcod.Color(0, 0, 150)),
	('Field Hospital', 4, libtcod.Color(200, 0, 0))
]

# list of campaign day menus and their highlight colours
CD_MENU_LIST = [
	('Supply', 1, libtcod.Color(128, 100, 64)),
	('Crew', 2, libtcod.Color(140, 140, 0)),
	('Travel', 3, libtcod.Color(70, 140, 0)),
	('Group', 4, libtcod.Color(180, 0, 45))
]

# directional arrows for directions on the campaign day map
CD_DIR_ARROW = [228,26,229,230,27,231]

# list of key commands for travel in campaign day
DIRECTION_KEYS = ['e', 'd', 'c', 'z', 'a', 'q']
CD_TRAVEL_CMDS = [
	('e',2,-2,228), ('d',2,0,26), ('c',2,2,229), ('z',-2,2,230), ('a',-2,0,27), ('q',-2,-2,231)
]

# order to display ammo types
AMMO_TYPES = ['HE', 'AP', 'APCR', 'APDS', 'HEAT', 'Smoke']

# anti-armour only ammo types, no effect otherwise
AP_AMMO_TYPES = ['AP', 'APCR', 'APDS']

# descriptions for ammo load menu
AMMO_DESCRIPTIONS = {
	'HE' : ('High Explosive', 'Explodes on contact, used against guns, infantry, and unarmoured vehicles.'),
	'AP' : ('Armour-Piercing', 'A solid or capped projectile, used against armoured targets.'),
	'APCR' : ('Armour-Piercing Composite Rigid', 'Has a dense core surrounded by a lighter material for better armour penetration, but loses velocity more quickly and is thus less effective at long ranges.'),
	'APDS' : ('Armour-Piercing Discarding Sabot', 'Uses a fin-stabilized dart of very dense material for excellent armour penetration, but is usually less accurate at long ranges.'),
	'HEAT' : ('High-Explosive Anti-Tank', 'Uses a shaped explosive charge to penetrate armour, also potentially causing damage to exposed crewmen.'),
	'Smoke' : ('Smoke Round', 'Emits concealing smoke for a short period of time. Not harmful to personnel.')
}

# display colours for ammo types (FUTURE: store text descriptions here too)
AMMO_TYPE_COLOUR = {
	'HE' : libtcod.lighter_grey,
	'AP' : libtcod.yellow,
	'APCR' : libtcod.light_blue,
	'APDS' : libtcod.lighter_blue,
	'HEAT' : libtcod.light_red,
	'Smoke' : libtcod.darker_grey
}

# list of MG-type weapons
MG_WEAPONS = ['Co-ax MG', 'Turret MG', 'Hull MG', 'AA MG', 'HMG']

# types of records to store for each combat day and for entire campaign
# also order in which they are displayed
RECORD_LIST = [
	'Battles Fought', 'Map Areas Captured', 'Gun Hits', 'Vehicles Destroyed',
	'Guns Destroyed', 'Infantry Destroyed'
]

# text descriptions for different types of Campaign Day missions
MISSION_DESC = {
	'Advance' : 'Enemy resistance is scattered and we are pushing forward. Advance into enemy territory and destroy any resistance.',
	'Battle' : 'Your group has been posted to the front line where there is heavy resistance. Break through the enemy defenses and destroy enemy units.',
	'Counterattack' : 'Enemy forces have mounted a counterattack against our lines. Hold as much territory as possible and attack the enemy wherever you can.',
	'Fighting Withdrawal' : 'The enemy is mounting a strong attack against our lines. Destroy enemy units but withdraw into friendly territory if necessary.',
	'Spearhead' : 'You must pierce the enemy lines, driving forward as far as possible before the end of the day.',
	'Patrol' : 'Scattered enemy forces are operating in this area, but their strength and whereabouts are unknown. Scout as much territory as you can, and engage any enemy forces discovered.'
}

##########################################################################################
#                                Game Engine Definitions                                 #
##########################################################################################

# base chances of partial effect for area fire attacks: infantry/gun and vehicle targets
INF_FP_BASE_CHANCE = 50.0
VEH_FP_BASE_CHANCE = 40.0

FP_CHANCE_STEP = 5.0		# each additional firepower beyond 1 adds this additional chance
FP_CHANCE_STEP_MOD = 0.95	# additional firepower modifier reduced by this much beyond 1
FP_FULL_EFFECT = 0.8		# multiplier for full effect
FP_CRIT_EFFECT = 0.15		# multipler for critical effect

RESOLVE_FP_BASE_CHANCE = 3.0	# base chance of a 1 firepower attack destroying a unit
RESOLVE_FP_CHANCE_STEP = 3.0	# each additional firepower beyond 1 adds this additional chance
RESOLVE_FP_CHANCE_MOD = 1.02	# additional firepower modifier increased by this much beyond 1

# list of anti-tank close combat weapons
AT_CC_WEAPONS = ['Bazooka', 'PIAT', 'Panzerfaust Klein', 'Panzerschreck', 'Panzerfaust']

# base fatigue level for personnel
BASE_FATIGUE = -2

# definition for panzerfaust, only added randomly to German infantry squads
PF_WEAPON = {
	"type" : "Close Combat",
	"name" : "Panzerfaust",
	"fp" : "16",
	"max_range" : "1"
}

# definition for demolition charge, added randomly to infantry squads
DC_WEAPON = {
	"type" : "Close Combat",
	"name" : "Demolition Charge",
	"fp" : "30",
	"max_range" : "1"
}

# defintion for molotov cocktails, added randomly to infantry squads
MOL_WEAPON = {
	"type" : "Close Combat",
	"name" : "Molotovs",
	"fp" : "2",
	"max_range" : "1"
}

# chance that an ineffective firepower attack will still increase the odds of a concealed target being easier to spot
MISSED_FP_REVEAL_CHANCE = 20.0

# AI units won't execute an action with a final score of this or lower
AI_ACTION_MIN = 3.0
# chance after every failed action roll that unit will simply do nothing that activation
AI_PASS_TURN_CHANCE = 10.0

# ballistic attack (eg. mortars) to-hit chance modifier, HE fp effect modifier
BALLISTIC_TO_HIT_MOD = 0.25
BALLISTIC_HE_FP_MOD = 0.5

# crewman will receive one automatic level up and advance per this many days between campaigns
CONTINUE_CAMPAIGN_LEVEL_UP_DAYS = 140

# chance upon every move or reposition action that a landmine will be hit, and chance that
# vehicle will be immobilized
LANDMINE_CHANCE = 5.0
LANDMINE_KO_CHANCE = 10.0

# descriptions for different Campaign Day objective types
CD_OBJECTIVES = {
	'Capture' : 'Destroy any enemy presence in this zone and capture it for our side.',
	'Hold' : 'Maintain friendly control of this zone, and remain in the same map area, at the end of the combat day.',
	'Recon' : 'Recon this zone to determine the level of enemy strength here.',
	'Rescue' : 'Allied forces are pinned down here, go to their aid and rescue them from destruction.'
}

# multipliers for different campaign length options
CAMPAIGN_LENGTH_MULTIPLIERS = [1.0, 0.8, 0.5, 0.2]

# terrain types in desert that can be captured by either side
DESERT_CAPTURE_ZONES = ['Villages', 'Oasis', 'Fortress']

# amount that unit destruction and zone capture VP is multipled by in North Africa
DESERT_DESTROY_MULTIPLER = 2.25
DESERT_CAPTURE_MULTIPLIER = 3

# each surviving crewman receives the day's VP times this amount in experience points
EXP_MULTIPLIER = 0.5

# base chance of CD hex zone capture per enemy-held adjacent hex zone
CD_ZONE_CAPTURE_CHANCE = 5.0

# base chance that a unit not in LoS of any enemy units will regain concealment after its side's activation
BASE_RECONCEAL_CHANCE = 20.0

# percent chance per day after minimum stay that a crewman in the Field Hospital will be released
# to active duty
FIELD_HOSPITAL_RELEASE_CHANCE = 4.0

# Spearhead mission zone capture VP values: adds one per this many hexrows reached
SPEARHEAD_HEXROW_LEVELS = 4

# level at which crew become eligible for promotion to the next rank
LEVEL_RANK_LIST = {
	'2' : 1,
	'4' : 2,
	'10' : 3,
	'15' : 4,
	'20' : 5,
	'25' : 6
}

# chance that eligible crew will receive a promotion
PROMOTION_CHANCE = 18.0

# chance that a weapon will jam upon use, chance that it will be unjammed if crewman is operating it
WEAPON_JAM_CHANCE = 0.5
WEAPON_UNJAM_CHANCE = 75.0

# chance of a direct hit during air or artillery attacks
DIRECT_HIT_CHANCE = 4.0

# base crew experience point and level system
BASE_EXP_REQUIRED = 12.0
EXP_EXPONENT = 1.2

# region definitions: set by campaigns, determine terrain odds on the campaign day map,
# types and odds of weather conditions at different times during the calendar year
REGIONS = {
	'Northeastern Europe' : {
		
		# campaign day map terrain type odds, can be modified by campaign weeks
		'cd_terrain_odds' : {
			'Flat' : 50,
			'Forest' : 10,
			'Hills' : 15,
			'Fields' : 10,
			'Marsh' : 5,
			'Villages' : 10,
			'Lake' : 2
		},
		
		# odds of dirt road network being present on the map
		'dirt_road_odds' : 40.0,
		
		# odds of stone/improved road "
		'stone_road_odds' : 10.0,
		
		# odds of 1+ rivers being spawned (with crossing points)
		'river_odds' : 50.0,
		
		# seasons, end dates, and weather odds for each season
		'season_weather_odds' : {
			'Winter' : {
				'end_date' : '03.31',
				'ground_conditions' : {
					'Dry' : 20.0, 'Wet' : 0.0, 'Muddy' : 5.0,
					'Snow' : 60.0, 'Deep Snow' : 15.0
				},
				'temperature' : {
					'Extreme Cold' : 30.0, 'Cold' : 60.0,
					'Mild' : 10.0, 'Warm' : 0.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 20.0
				},
				'precipitation' : {
					'None' : 35.0, 'Mist' : 10.0,
					'Rain' : 10.0, 'Heavy Rain' : 5.0,
					'Light Snow' : 10.0, 'Snow' : 20.0,
					'Blizzard' : 10.0
				}
			},
			'Spring' : {
				'end_date' : '06.14',
				'ground_conditions' : {
					'Dry' : 50.0, 'Wet' : 20.0, 'Muddy' : 25.0,
					'Snow' : 5.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 10.0,
					'Mild' : 70.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 30.0, 'Mist' : 10.0,
					'Rain' : 30.0, 'Heavy Rain' : 20.0,
					'Light Snow' : 10.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Summer' : {
				'end_date' : '09.31',
				'ground_conditions' : {
					'Dry' : 75.0, 'Wet' : 10.0, 'Muddy' : 15.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 25.0, 'Warm' : 60.0,
					'Hot' : 10.0, 'Extreme Hot' : 5.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 60.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}	
			},
			'Autumn' : {
				'end_date' : '12.01',
				'ground_conditions' : {
					'Dry' : 65.0, 'Wet' : 10.0, 'Muddy' : 15.0,
					'Snow' : 10.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 10.0,
					'Mild' : 70.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 50.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 10.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			}
		}
	},
	
	'Western Russia' : {
		'cd_terrain_odds' : {
			'Flat' : 45,
			'Forest' : 5,
			'Hills' : 10,
			'Fields' : 15,
			'Marsh' : 10,
			'Villages' : 10,
			'Lake' : 5
		},
		'dirt_road_odds' : 10.0,
		'stone_road_odds' : 0.0,
		'poor_quality_roads' : True,
		'river_odds' : 50.0,
		'season_weather_odds' : {
			'Winter' : {
				'end_date' : '04.31',
				'ground_conditions' : {
					'Dry' : 5.0, 'Wet' : 0.0, 'Muddy' : 15.0,
					'Snow' : 60.0, 'Deep Snow' : 20.0
				},
				'temperature' : {
					'Extreme Cold' : 50.0, 'Cold' : 30.0,
					'Mild' : 10.0, 'Warm' : 0.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 20.0
				},
				'precipitation' : {
					'None' : 35.0, 'Mist' : 10.0,
					'Rain' : 10.0, 'Heavy Rain' : 5.0,
					'Light Snow' : 10.0, 'Snow' : 20.0,
					'Blizzard' : 10.0
				}
			},
			'Spring' : {
				'end_date' : '06.14',
				'ground_conditions' : {
					'Dry' : 25.0, 'Wet' : 20.0, 'Muddy' : 50.0,
					'Snow' : 5.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 10.0,
					'Mild' : 70.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 30.0, 'Mist' : 10.0,
					'Rain' : 30.0, 'Heavy Rain' : 20.0,
					'Light Snow' : 10.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Summer' : {
				'end_date' : '09.31',
				'ground_conditions' : {
					'Dry' : 75.0, 'Wet' : 10.0, 'Muddy' : 15.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 25.0, 'Warm' : 60.0,
					'Hot' : 10.0, 'Extreme Hot' : 5.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 60.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}	
			},
			'Autumn' : {
				'end_date' : '11.01',
				'ground_conditions' : {
					'Dry' : 20.0, 'Wet' : 25.0, 'Muddy' : 45.0,
					'Snow' : 10.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 20.0,
					'Mild' : 60.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 50.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 10.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			}
		}
	},
	
	'Northwestern Europe' : {
		'cd_terrain_odds' : {
			'Flat' : 40,
			'Forest' : 20,
			'Hills' : 10,
			'Fields' : 15,
			'Marsh' : 5,
			'Villages' : 10,
			'Lake' : 2
		},
		
		'dirt_road_odds' : 80.0,
		'stone_road_odds' : 50.0,
		'river_odds' : 20.0,

		'season_weather_odds' : {
			
			'Winter' : {
				'end_date' : '03.31',
				'ground_conditions' : {
					'Dry' : 25.0, 'Wet' : 0.0, 'Muddy' : 5.0,
					'Snow' : 60.0, 'Deep Snow' : 10.0
				},
				'temperature' : {
					'Extreme Cold' : 30.0, 'Cold' : 60.0,
					'Mild' : 10.0, 'Warm' : 0.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 20.0
				},
				'precipitation' : {
					'None' : 35.0, 'Mist' : 10.0,
					'Rain' : 10.0, 'Heavy Rain' : 5.0,
					'Light Snow' : 15.0, 'Snow' : 20.0,
					'Blizzard' : 5.0
				}
			},
			'Spring' : {
				'end_date' : '06.14',
				'ground_conditions' : {
					'Dry' : 50.0, 'Wet' : 20.0, 'Muddy' : 25.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 10.0,
					'Mild' : 70.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 30.0, 'Mist' : 10.0,
					'Rain' : 30.0, 'Heavy Rain' : 20.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
				
			},
			'Summer' : {
				'end_date' : '09.31',
				'ground_conditions' : {
					'Dry' : 75.0, 'Wet' : 10.0, 'Muddy' : 15.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 25.0, 'Warm' : 60.0,
					'Hot' : 10.0, 'Extreme Hot' : 5.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 60.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
				
			},
			'Autumn' : {
				'end_date' : '12.01',
				'ground_conditions' : {
					'Dry' : 65.0, 'Wet' : 10.0, 'Muddy' : 15.0,
					'Snow' : 10.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 10.0,
					'Mild' : 70.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 50.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 10.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			}
		}
	},
	
	'Nordic' : {
		'cd_terrain_odds' : {
			'Flat' : 20,
			'Forest' : 40,
			'Hills' : 20,
			'Fields' : 10,
			'Marsh' : 5,
			'Villages' : 5,
			'Lake' : 5
		},
		
		'dirt_road_odds' : 20.0,
		'stone_road_odds' : 2.0,
		'river_odds' : 30.0,

		'season_weather_odds' : {
			
			'Winter' : {
				'end_date' : '03.31',
				'ground_conditions' : {
					'Dry' : 0.0, 'Wet' : 0.0, 'Muddy' : 0.0,
					'Snow' : 70.0, 'Deep Snow' : 30.0
				},
				'temperature' : {
					'Extreme Cold' : 60.0, 'Cold' : 40.0,
					'Mild' : 0.0, 'Warm' : 0.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 20.0, 'Scattered' : 10.0,
					'Heavy' : 10.0, 'Overcast' : 60.0
				},
				'precipitation' : {
					'None' : 40.0, 'Mist' : 0.0,
					'Rain' : 0.0, 'Heavy Rain' : 0.0,
					'Light Snow' : 25.0, 'Snow' : 25.0,
					'Blizzard' : 10.0
				}
				
			},
			'Spring' : {
				'end_date' : '06.14',
				'ground_conditions' : {
					'Dry' : 55.0, 'Wet' : 15.0, 'Muddy' : 5.0,
					'Snow' : 15.0, 'Deep Snow' : 10.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 35.0,
					'Mild' : 45.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 30.0, 'Mist' : 15.0,
					'Rain' : 10.0, 'Heavy Rain' : 5.0,
					'Light Snow' : 20.0, 'Snow' : 15.0,
					'Blizzard' : 5.0
				}
				
			},
			'Summer' : {
				'end_date' : '09.31',
				'ground_conditions' : {
					'Dry' : 75.0, 'Wet' : 10.0, 'Muddy' : 15.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 25.0, 'Warm' : 60.0,
					'Hot' : 10.0, 'Extreme Hot' : 5.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 60.0, 'Mist' : 10.0,
					'Rain' : 20.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Autumn' : {
				'end_date' : '12.01',
				'ground_conditions' : {
					'Dry' : 10.0, 'Wet' : 20.0, 'Muddy' : 20.0,
					'Snow' : 40.0, 'Deep Snow' : 10.0
				},
				'temperature' : {
					'Extreme Cold' : 10.0, 'Cold' : 40.0,
					'Mild' : 40.0, 'Warm' : 10.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 20.0, 'Scattered' : 10.0,
					'Heavy' : 30.0, 'Overcast' : 40.0
				},
				'precipitation' : {
					'None' : 15.0, 'Mist' : 10.0,
					'Rain' : 15.0, 'Heavy Rain' : 10.0,
					'Light Snow' : 25.0, 'Snow' : 20.0,
					'Blizzard' : 5.0
				}
			}
		}
	},
	
	'North Africa' : {
		'cd_terrain_odds' : {
			'Flat' : 120,
			'Scrub' : 5,
			'Hamada' : 10,
			'Sand' : 20,
			'Hills' : 5,
			'Oasis' : 1,
			'Mountains' : 3,
			'Fortress' : 3,
			'Villages' : 7
		},
		'dirt_road_odds' : 40.0,
		'stone_road_odds' : 0.0,
		'river_odds' : 0.0,
		'season_weather_odds' : {
			'Winter' : {
				'end_date' : '03.31',
				'ground_conditions' : {
					'Dry' : 85.0, 'Wet' : 10.0, 'Muddy' : 5.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 20.0,
					'Mild' : 50.0, 'Warm' : 30.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 5.0
				},
				'precipitation' : {
					'None' : 95.0, 'Mist' : 2.0,
					'Rain' : 3.0, 'Heavy Rain' : 0.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Spring' : {
				'end_date' : '06.14',
				'ground_conditions' : {
					'Dry' : 50.0, 'Wet' : 20.0, 'Muddy' : 15.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 20.0, 'Warm' : 40.0,
					'Hot' : 20.0, 'Extreme Hot' : 20.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 5.0
				},
				'precipitation' : {
					'None' : 90.0, 'Mist' : 5.0,
					'Rain' : 5.0, 'Heavy Rain' : 0.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Summer' : {
				'end_date' : '09.31',
				'ground_conditions' : {
					'Dry' : 95.0, 'Wet' : 5.0, 'Muddy' : 0.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 0.0, 'Warm' : 10.0,
					'Hot' : 10.0, 'Extreme Hot' : 80.0
				},
				'cloud_cover' : {
					'Clear' : 90.0, 'Scattered' : 10.0,
					'Heavy' : 0.0, 'Overcast' : 0.0
				},
				'precipitation' : {
					'None' : 100.0, 'Mist' : 0.0,
					'Rain' : 0.0, 'Heavy Rain' : 0.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}	
			},
			'Autumn' : {
				'end_date' : '12.01',
				'ground_conditions' : {
					'Dry' : 50.0, 'Wet' : 20.0, 'Muddy' : 15.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 10.0, 'Warm' : 40.0,
					'Hot' : 20.0, 'Extreme Hot' : 30.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 5.0
				},
				'precipitation' : {
					'None' : 95.0, 'Mist' : 3.0,
					'Rain' : 2.0, 'Heavy Rain' : 0.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			}
		}
	},
	
	'Asian Steppes' : {
		'cd_terrain_odds' : {
			'Flat' : 62,
			'Forest' : 1,
			'Hills' : 10,
			'Fields' : 15,
			'Marsh' : 0,
			'Villages' : 10,
			'Lake' : 2
		},
		'dirt_road_odds' : 3.0,
		'stone_road_odds' : 0.0,
		'poor_quality_roads' : True,
		'river_odds' : 20.0,
		'season_weather_odds' : {
			'Winter' : {
				'end_date' : '04.31',
				'ground_conditions' : {
					'Dry' : 85.0, 'Wet' : 0.0, 'Muddy' : 10.0,
					'Snow' : 5.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 50.0, 'Cold' : 30.0,
					'Mild' : 10.0, 'Warm' : 0.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 40.0, 'Scattered' : 20.0,
					'Heavy' : 20.0, 'Overcast' : 20.0
				},
				'precipitation' : {
					'None' : 95.0, 'Mist' : 0.0,
					'Rain' : 0.0, 'Heavy Rain' : 0.0,
					'Light Snow' : 5.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Spring' : {
				'end_date' : '06.14',
				'ground_conditions' : {
					'Dry' : 70.0, 'Wet' : 10.0, 'Muddy' : 20.0,
					'Snow' : 2.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 10.0,
					'Mild' : 70.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 72.0, 'Mist' : 10.0,
					'Rain' : 10.0, 'Heavy Rain' : 5.0,
					'Light Snow' : 3.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			},
			'Summer' : {
				'end_date' : '09.31',
				'ground_conditions' : {
					'Dry' : 95.0, 'Wet' : 5.0, 'Muddy' : 0.0,
					'Snow' : 0.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 0.0,
					'Mild' : 25.0, 'Warm' : 60.0,
					'Hot' : 10.0, 'Extreme Hot' : 5.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 90.0, 'Mist' : 3.0,
					'Rain' : 5.0, 'Heavy Rain' : 2.0,
					'Light Snow' : 0.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}	
			},
			'Autumn' : {
				'end_date' : '11.01',
				'ground_conditions' : {
					'Dry' : 70.0, 'Wet' : 10.0, 'Muddy' : 20.0,
					'Snow' : 2.0, 'Deep Snow' : 0.0
				},
				'temperature' : {
					'Extreme Cold' : 0.0, 'Cold' : 20.0,
					'Mild' : 60.0, 'Warm' : 20.0,
					'Hot' : 0.0, 'Extreme Hot' : 0.0
				},
				'cloud_cover' : {
					'Clear' : 50.0, 'Scattered' : 15.0,
					'Heavy' : 20.0, 'Overcast' : 15.0
				},
				'precipitation' : {
					'None' : 72.0, 'Mist' : 10.0,
					'Rain' : 10.0, 'Heavy Rain' : 5.0,
					'Light Snow' : 3.0, 'Snow' : 0.0,
					'Blizzard' : 0.0
				}
			}
		}
	}
}

# base chance of a ground conditions change during weather update
GROUND_CONDITION_CHANGE_CHANCE = 20.0
# modifier for heavy rain/snow
HEAVY_PRECEP_MOD = 15.0

# list of crew stats
CREW_STATS = ['Perception', 'Morale', 'Grit', 'Knowledge']

# list of positions that player character can be (Commander, etc.)
PLAYER_POSITIONS = ['Commander', 'Commander/Gunner']

# length of scenario turn in minutes
TURN_LENGTH = 2

# maximum visible distance when buttoned up
MAX_BU_LOS = 1

# base chance to spot unit at distances 0-6
SPOT_BASE_CHANCE = [95.0, 85.0, 70.0, 50.0, 40.0, 35.0, 32.5]

# each point of Perception increases chance to spot enemy unit by this much
PERCEPTION_SPOTTING_MOD = 5.0

# base chance of moving forward/backward into next hex
BASE_FORWARD_MOVE_CHANCE = 50.0
BASE_REVERSE_MOVE_CHANCE = 20.0

# bonus per unsuccessful move attempt
BASE_MOVE_BONUS = 15.0

# base critical hit and miss thresholds
CRITICAL_HIT = 3.0
CRITICAL_MISS = 99.5

# maximum range at which MG attacks have a chance to penetrate armour
MG_AP_RANGE = 1

# base success chances for point fire attacks
# first column is for vehicle targets, second is everything else
PF_BASE_CHANCE = [
	[98.0, 88.0],			# same hex
	[83.0, 78.0],			# 1 hex range
	[70.0, 68.0],			# 2 "
	[59.0, 58.0],			# 3 "
	[49.0, 48.0],			# 4 "
	[40.0, 38.0],			# 5 "
	[32.0, 28.0]			# 6 "
]

# base success chance for a close combat attack
CC_BASE_CHANCE = [90.0, 80.0]

# acquired target bonus for level 1 and level 2 for point fire
AC_BONUS = [
	[8.0, 15.0],	# same hex 0
	[10.0, 25.0],	# 1 hex range
	[10.0, 25.0],	# 2 "
	[20.0, 35.0],	# 3 "
	[25.0, 45.0],	# 4 "
	[25.0, 45.0],	# 5 "
	[25.0, 45.0]	# 6 "
]

# modifier for target size if target is known
PF_SIZE_MOD = {
	'Very Small' : -28.0,
	'Small' : -12.0,
	'Large' : 12.0,
	'Very Large' : 28.0
}

MORALE_CHECK_BASE_CHANCE = 70.0	# base chance of passing a morale check

# effective FP of an HE hit from different weapon calibres
HE_FP_EFFECT = [
	(200, 36),(183, 34),(170, 32),(160, 31),(150, 30),(140, 28),(128, 26),(120, 24),
	(107, 22),(105, 22),(100, 20),(95, 19),(88, 18),(85, 17),(80, 16),(75, 14),
	(70, 12),(65, 10),(60, 8),(57, 7),(50, 6),(45, 5),(37, 4),(30, 2),(25, 2),(20, 1)
]

# odds of unarmoured vehicle destruction when resolving FP
VEH_FP_TK = [
	(36, 110.0),(30, 100.0),(24, 97.0),(20, 92.0),(16, 83.0),(12, 72.0),(8, 58.0),(6, 42.0),
	(4, 28.0),(2, 17.0),(1, 8.0)
]

# amount within an AFV armour save that will result in Stun tests for crew/unit
AP_STUN_MARGIN = 10.0

# amount within an AFV armour save that will result in recall test for an enemy unit
# chance of it being recalled
AP_RECALL_MARGIN = 10.0
AP_RECALL_CHANCE = 20.0

# definitions for terrain types on the Campaign Day map
CD_TERRAIN_TYPES = {
	'Flat' : {
		'description' : 'Mostly flat terrain with few features.',
		'travel_time' : 30,
		'scenario_terrain_odds' : {
			'Open Ground' : 60.0,
			'Broken Ground' : 20.0,
			'Brush' : 10.0,
			'Woods' : 5.0,
			'Wooden Buildings' : 4.0,
			'Rubble' : 1.0
		}
	},
	'Forest' : {
		'description' : 'Dense areas of trees and brush, difficult and time-consuming to traverse.',
		'travel_time' : 45,
		'scenario_terrain_odds' : {
			'Open Ground' : 10.0,
			'Broken Ground' : 15.0,
			'Brush' : 25.0,
			'Woods' : 45.0,
			'Wooden Buildings' : 4.0,
			'Rubble' : 1.0
		}
	},
	'Hills' : {
		'description' : 'Rolling hills, not impassible but can make travel slower.',
		'travel_time' : 40,
		'scenario_terrain_odds' : {
			'Open Ground' : 15.0,
			'Broken Ground' : 10.0,
			'Brush' : 5.0,
			'Woods' : 5.0,
			'Hills' : 50.0,
			'Wooden Buildings' : 4.0,
			'Rubble' : 1.0
		}
	},
	'Fields' : {
		'description' : 'Fields of crops.',
		'travel_time' : 35,
		'scenario_terrain_odds' : {
			'Open Ground' : 20.0,
			'Broken Ground' : 5.0,
			'Brush' : 5.0,
			'Woods' : 5.0,
			'Fields' : 50.0,
			'Wooden Buildings' : 4.0,
			'Rubble' : 1.0
		}
	},
	'Marsh' : {
		'description' : 'Marshy area with standing water, not impassible but risky.',
		'travel_time' : 40,
		'scenario_terrain_odds' : {
			'Open Ground' : 10.0,
			'Broken Ground' : 5.0,
			'Brush' : 5.0,
			'Woods' : 4.0,
			'Marsh' : 60.0,
			'Wooden Buildings' : 5.0,
			'Rubble' : 1.0
		}
	},
	'Villages' : {
		'description' : 'Clusters of small settlements with fields nearby.',
		'travel_time' : 30,
		'scenario_terrain_odds' : {
			'Open Ground' : 5.0,
			'Broken Ground' : 5.0,
			'Brush' : 10.0,
			'Fields' : 15.0,
			'Wooden Buildings' : 45.0,
			'Stone Buildings' : 20.0
		}
	},
	'Scrub' : {
		'description' : 'Small patches of hardy vegetation, sufficient for infantry to find some cover.',
		'travel_time' : 30,
		'scenario_terrain_odds' : {
			'Open Ground' : 45.0,
			'Broken Ground' : 20.0,
			'Brush' : 30.0,
			'Wooden Buildings' : 4.0,
			'Rubble' : 1.0
		}
	},
	'Hamada' : {
		'description' : 'Flat and featureless rocky plateau, covered in a layer of sharp stones.',
		'travel_time' : 20,
		'scenario_terrain_odds' : {
			'Hamada' : 70.0,
			'Open Ground' : 10.0,
			'Broken Ground' : 10.0,
			'Rubble' : 10.0
		}
	},
	'Sand' : {
		'description' : 'A shifting sea of sand and sand dunes.',
		'travel_time' : 30,
		'scenario_terrain_odds' : {
			'Sand' : 70.0,
			'Open Ground' : 15.0,
			'Broken Ground' : 10.0,
			'Hamada' : 5.0
		}
	},
	'Oasis' : {
		'description' : 'A rare green and lush place, built over a natural well.',
		'travel_time' : 30,
		'max_per_map' : 1,
		'scenario_terrain_odds' : {
			'Open Ground' : 70.0,
			'Broken Ground' : 10.0,
			'Stone Buildings' : 15.0,
			'Hills' : 5.0,
		}
	},
	'Fortress' : {
		'description' : 'An ancient stone fortress, a perfect defensive position.',
		'travel_time' : 30,
		'max_per_map' : 2,
		'scenario_terrain_odds' : {
			'Stone Buildings' : 60.0,
			'Open Ground' : 20.0,
			'Broken Ground' : 10.0,
			'Sand' : 10.0
		}
	},
	'Mountains' : {
		'description' : 'High, impassible mountains.',
		'impassible' : True,
		'max_per_map' : 3
	},
	'Lake' : {
		'description' : 'An inland lake, impassible.',
		'impassible' : True,
		'max_per_map' : 2,
		'no_adjacent' : ['Ocean', 'Lake']
	},
	'Ocean' : {
		'description' : 'The coast, impassible to tanks.',
		'impassible' : True
	}
}


# modifiers and effects for different types of terrain on the scenario layer
SCENARIO_TERRAIN_EFFECTS = {
	'Open Ground' : {
		'HD Chance' : 5.0,
		'los_mod' : 0.0
	},
	'Broken Ground' : {
		'TEM' : {
			'Vehicle' : -10.0,
			'Infantry' : -15.0,
			'Deployed Gun' : -15.0
		},
		'HD Chance' : 10.0,
		'Movement Mod' : -5.0,
		'Bog Mod' : 1.0,
		'los_mod' : 3.0
	},
	'Brush': {
		'TEM' : {
			'All' : -15.0
		},
		'HD Chance' : 10.0,
		'Movement Mod' : -15.0,
		'Bog Mod' : 2.0,
		'Burnable' : True,			# not used yet
		'los_mod' : 5.0
	},
	'Woods': {
		'TEM' : {
			'All' : -25.0
		},
		'HD Chance' : 20.0,
		'Movement Mod' : -30.0,
		'Bog Mod' : 5.0,
		'Double Bog Check' : True,		# player must test to bog before moving out of this terrain type
		'Burnable' : True,
		'los_mod' : 10.0
	},
	'Fields': {
		'TEM' : {
			'All' : -10.0
		},
		'HD Chance' : 5.0,
		'Burnable' : True,
		'los_mod' : 5.0
	},
	'Hills': {
		'TEM' : {
			'All' : -20.0
		},
		'HD Chance' : 40.0,
		'los_mod' : 15.0
	},
	'Wooden Buildings': {
		'TEM' : {
			'Vehicle' : -20.0,
			'Infantry' : -30.0,
			'Deployed Gun' : -30.0
		},
		'HD Chance' : 20.0,
		'los_mod' : 10.0,
		'Burnable' : True
	},
	'Stone Buildings': {
		'TEM' : {
			'Vehicle' : -20.0,
			'Infantry' : -50.0,
			'Deployed Gun' : -50.0
		},
		'HD Chance' : 30.0,
		'los_mod' : 15.0
	},
	'Marsh': {
		'TEM' : {
			'All' : -10.0
		},
		'HD Chance' : 15.0,
		'Movement Mod' : -30.0,
		'Bog Mod' : 10.0,
		'Double Bog Check' : True,
		'los_mod' : 3.0,
		'dug_in_na' : True
	},
	'Rubble': {
		'TEM' : {
			'Vehicle' : -15.0,
			'Infantry' : -30.0,
			'Deployed Gun' : -30.0
		},
		'HD Chance' : 30.0,
		'los_mod' : 10.0,
		'Bog Mod' : 10.0,
		'Double Bog Check' : True
	},
	'Hamada': {
		'los_mod' : 0.0,
		'HD Chance' : 2.0,
		'Movement Mod' : -15.0,
		'Bog Mod' : 10.0,
		'Double Bog Check' : True,
		'dug_in_na' : True
	},
	'Sand': {
		'los_mod' : 0.0,
		'HD Chance' : 2.0,
		'Movement Mod' : -5.0,
		'Bog Mod' : 15.0,
		'dug_in_na' : True
	}
}

# relative locations to draw greebles for terrain on scenario map
GREEBLE_LOCATIONS = [(-1,-1), (0,-1), (1,-1), (-1,0), (1,0), (-1,1), (0,1), (1,1)]

# modifier for base HD chance
HD_SIZE_MOD = {
	'Very Small' : 12.0, 'Small' : 6.0, 'Normal' : 0.0, 'Large' : -6.0, 'Very Large' : -12.0
}

# base chance of a sniper attack being effective
BASE_SNIPER_TK_CHANCE = 45.0

# base chance of a random event in a scenario
BASE_RANDOM_EVENT_CHANCE = 5.0
# base chance of a random event in a campaign day
BASE_CD_RANDOM_EVENT_CHANCE = 3.0

# base number of minutes between weather update checks
BASE_WEATHER_UPDATE_CLOCK = 30


# Campaign: stores data about a campaign and calendar currently in progress
class Campaign:
	def __init__(self):
		
		self.filename = ''		# record filename of campaign definitions
		
		self.options = {
			'permadeath' : True,
			'fate_points' : True,
			'explosion_kills' : False,
			'random_tank' : False,
			'ahistorical' : False,
			'realistic_injuries' : False,
			'realistic_ai' : False
		}
		
		self.vp_modifier = 0.0		# total effect on VP from campaign options
		
		# load skills from JSON file - they won't change over the course of a campaign
		with open(DATAPATH + 'skill_defs.json', encoding='utf8') as data_file:
			self.skills = json.load(data_file)
		
		self.logs = {}			# dictionary of campaign logs for each combat day
		self.journal = {}		# dictionary of events for each combat day
		self.player_unit = None		# placeholder for player unit
		self.player_squad_max = 0	# maximum units in player squad in addition to player
		self.player_vp = 0		# total player victory points
		self.stats = {}			# local copy of campaign stats
		self.combat_calendar = []	# list of combat days
		self.today = None		# pointer to current day in calendar
		self.current_week = None	# " week
		
		self.latitude = 55.95		# current location in world
		self.longitude = -3.18		# these are placeholder values, will be set by each campaign week
		
		self.hospital = []		# holds crewmen currently in the field hospital
		
		self.active_calendar_menu = 1	# currently active menu in the campaign calendar interface
		self.active_journal_day = None	# currently displayed journal day
		self.journal_scroll_line = 0	# current level of scroll on the journal display
		self.ended = False		# campaign has ended due to player serious injury or death
		self.player_oob = False		# player was seriously injured or killed
		
		self.decoration = ''		# decoration awarded to player at end of campaign
		
		# records for end-of-campaign summary
		self.records = {}
		for text in RECORD_LIST:
			self.records[text] = 0
		# only recorded for entire campaign, not each campaign day
		self.records['Combat Days'] = 0
	
	
	# do a rarity check for spawning a given type of unit today
	def DoRarityCheck(self, unit_id):
		
		# no rarity factor in unit type def, select automatically
		if 'rarity' not in session.unit_types[unit_id]:
			return True
		
		# roll against rarity for current date
		rarity = None
		for date, chance in session.unit_types[unit_id]['rarity'].items():
			
			# select the earliest rarity factor
			if rarity is None:
				
				# if the earliest rarity factor is still later than current date, do not spawn
				if date > self.today:
					return False
				
				rarity = int(chance)
				continue
			
			# break if this date is later than current date
			if date > self.today: break
				
			# earlier than or equal to today's date, use this rarity factor 
			rarity = int(chance)
		
		# not able to get a rarity factor for today, don't spawn
		if rarity is None:
			return False
		
		# roll againt rarity rating
		if GetPercentileRoll() <= float(rarity):
			return True
		return False
		
	
	# do post-init modifier checks, these need to wait until the player unit is generated, etc.
	def DoPostInitChecks(self):
		# if current campaign region is north africa, german and italian vehicles are all unreliable before Oct. 1941
		if self.stats['region'] == 'North Africa' and self.player_unit.nation in ['Germany', 'Italy']:
			if self.today < '1941.10.01' and self.player_unit.GetStat('category') == 'Vehicle':
				self.player_unit.stats['unreliable'] = True
		
	
	# check for the start of a new campaign week given the current date, apply any modifiers
	def CheckForNewWeek(self):
		week_index = self.stats['calendar_weeks'].index(self.current_week)
		if week_index < len(self.stats['calendar_weeks']) - 1:
			week_index += 1
			if self.today >= self.stats['calendar_weeks'][week_index]['start_date'] or 'refitting' in self.current_week:
				
				# start of new week
				self.current_week = self.stats['calendar_weeks'][week_index]
				
				# check for modified class spawn odds
				if 'enemy_class_odds_modifier' in self.current_week:
					for k, v in self.current_week['enemy_class_odds_modifier'].items():
						if k in self.stats['enemy_unit_class_odds']:
							self.stats['enemy_unit_class_odds'][k] = v
				
				# check for promotions
				for position in self.player_unit.positions_list:
					if position.crewman is None: continue
					position.crewman.PromotionCheck()
				
				session.ModifySteamStat('weeks_passed', 1)
	
	
	# handle a Player Commander heading to the field hospital for a period of time
	def CommanderInAComa(self, crewman):
		
		# roll for actual length of hospital stay
		(days_min, days_max) = crewman.field_hospital
		hospital_days = days_min
		for i in range(days_max-days_min):
			if GetPercentileRoll() <= FIELD_HOSPITAL_RELEASE_CHANCE:
				break
			hospital_days += 1
		
		# check to see if this would take the player beyond the end of the campaign
		(year, month, day) = self.today.split('.')
		a = datetime(int(year), int(month), int(day), 0, 0, 0) + timedelta(days=hospital_days)
		release_day = str(a.year) + '.' + str(a.month).zfill(2) + '.' + str(a.day).zfill(2)
		
		if release_day > self.combat_calendar[-1]:
		
			ShowMessage('While you are still recovering in the field hospital, you receive word that your campaign has ended.')
			
			# set today to end of campaign
			self.today = self.combat_calendar[-1]
			
			# temporarily return crewman to original position
			self.player_unit.positions_list[0].crewman = crewman
			crewman.current_position = self.player_unit.positions_list[0]
			return True
		
		# clear all remaining crewmen from current player tank
		for position in self.player_unit.positions_list:
			position.crewman = None
		
		# we're still in the campaign, set the current day to the next possible combat day
		i = self.combat_calendar.index(self.today)
		for combat_day in self.combat_calendar[i+1:]:
			
			self.CheckForNewWeek()
			
			# recalculate commander age
			crewman.CalculateAge()
			
			# ignore refitting weeks
			if 'refitting' in self.current_week:
				continue
			
			# found a suitable day
			if combat_day >= release_day:
				self.today = combat_day
				self.CheckForNewWeek()
				crewman.CalculateAge()
				break
			
		else:
			# unable to find a combat day on or after the release date, campaign ends
			ShowMessage('While you are still recovering in the field hospital, you receive word that your campaign has ended.')
			self.today = self.combat_calendar[-1]
			self.player_unit.positions_list[0].crewman = crewman
			crewman.current_position = self.player_unit.positions_list[0]
			return True
		
		ShowMessage('After ' + str(hospital_days) + ' days in the field hospital, you recover and return to active duty on ' +
			GetDateText(self.today), longer_pause=True)
		self.hospital.remove(crewman)
		self.hospital.sort(key=lambda x: x.field_hospital)
		crewman.field_hospital = None
		
		# player selects a new tank, and generate a crew for it
		(unit_id, tank_name) = self.TankSelectionMenu()
		self.player_unit = Unit(unit_id, is_player=True)
		self.player_unit.unit_name = tank_name
		self.player_unit.nation = campaign.stats['player_nation']
		
		# put the player commander in the new unit
		for position in self.player_unit.positions_list:
			if position.name in PLAYER_POSITIONS:
				position.crewman = crewman
				crewman.current_position = position
				crewman.unit = self.player_unit
				crewman.SetCEStatus()
				break
		
		# generate rest of crew and set up the main gun
		self.player_unit.GenerateNewPersonnel()
		self.player_unit.ClearGunAmmo()
		
		return False
	
	
	# show a menu to handle assigning returning crewmen to a tank position, or crewmen to
	# new positions in a new tank
	def ShowAssignPositionsMenu(self, unassigned_crewmen=[]):
		
		def DrawMenu():
			
			libtcod.console_clear(con)
			
			# left and right column headings
			libtcod.console_set_default_background(con, libtcod.dark_blue)
			libtcod.console_rect(con, 1, 13, 28, 2, True, libtcod.BKGND_SET)
			libtcod.console_rect(con, 61, 13, 28, 2, True, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			
			libtcod.console_set_default_foreground(con, libtcod.red)
			libtcod.console_print(con, 9, 13, 'Unassigned')
			libtcod.console_print(con, 11, 14, 'Crewmen')
			libtcod.console_set_default_foreground(con, libtcod.cyan)
			libtcod.console_print(con, 70, 13, 'Selected')
			if crewman_highlight:
				text = 'Crewman'
			else:
				text = 'Crewman in Position'
			libtcod.console_print_ex(con, 74, 14, libtcod.BKGND_NONE,
				libtcod.CENTER, text)
			
			# list of unassigned crewmen
			y = 18
			i = 0
			libtcod.console_set_default_foreground(con, libtcod.white)
			for crewman in unassigned_crewmen:
				# highlight if selected
				if i == selected_crewman:
					if crewman_highlight:
						libtcod.console_set_default_background(con, libtcod.darker_blue)
					else:
						libtcod.console_set_default_background(con, libtcod.darkest_blue)
					libtcod.console_rect(con, 1, y, 28, 3, True, libtcod.BKGND_SET)
					libtcod.console_set_default_background(con, libtcod.black)
				PrintExtended(con, 1, y+1, crewman.GetName(), first_initial=True)
				y += 3
				i += 1
			
			# player unit and crew
			libtcod.console_set_default_foreground(con, libtcod.white)
			DrawFrame(con, 32, 0, 27, 17)
			DrawFrame(con, 32, 16, 27, 34)
			DisplayUnitInfo(con, 33, 1, self.player_unit.unit_id, self.player_unit, status=False)
			DisplayCrew(self.player_unit, con, 33, 18, selected_position, darken_highlight=crewman_highlight)
			
			# currently selected crewman or position
			crewman = None
			if crewman_highlight:
				if len(unassigned_crewmen) > 0:
					crewman = unassigned_crewmen[selected_crewman]
			else:
				crewman = campaign.player_unit.positions_list[selected_position].crewman
			
			if crewman is None:
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				libtcod.console_print_ex(con, 74, 18, libtcod.BKGND_NONE,
					libtcod.CENTER, 'None')
			else:
				x = 60
				libtcod.console_set_default_foreground(con, libtcod.dark_grey)
				libtcod.console_hline(con, x, 18, 28)
				libtcod.console_hline(con, x, 20, 28)
				libtcod.console_hline(con, x, 23, 28)
				libtcod.console_hline(con, x, 28, 28)
				
				libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
				libtcod.console_print(con, x, 17, 'Name')
				libtcod.console_print(con, x, 19, 'Rank')
				libtcod.console_print(con, x, 21, 'Current')
				libtcod.console_print(con, x, 22, 'Position')
				libtcod.console_print(con, x, 24, 'Stats')
				libtcod.console_print(con, x, 29, 'Skills')
				libtcod.console_print(con, x+5, 55, 'Level')
				libtcod.console_print(con, x+5, 56, 'Experience')
				libtcod.console_print(con, x+5, 57, 'Advance Points')
				
				libtcod.console_set_default_foreground(con, libtcod.white)
				PrintExtended(con, x+9, 17, crewman.GetName())
				libtcod.console_print(con, x+9, 19, session.nations[crewman.nation]['rank_names'][str(crewman.rank)])
				
				if crewman.current_position is None:
					text = 'None'
				else:
					if crewman.current_position.name is None:
						text = 'None'
					else:
						text = crewman.current_position.name
				libtcod.console_print(con, x+9, 21, text)
				
				# stats
				libtcod.console_put_char_ex(con, x+9, 24, chr(4), libtcod.yellow, libtcod.black)
				libtcod.console_put_char_ex(con, x+9, 25, chr(3), libtcod.red, libtcod.black)
				libtcod.console_put_char_ex(con, x+9, 26, chr(5), libtcod.blue, libtcod.black)
				libtcod.console_put_char_ex(con, x+9, 27, chr(6), libtcod.green, libtcod.black)
				y = 24
				for t in CREW_STATS:
					libtcod.console_set_default_foreground(con, libtcod.white)
					libtcod.console_print(con, x+11, y, t)
					libtcod.console_set_default_foreground(con, libtcod.light_grey)
					libtcod.console_print_ex(con, x+23, y, libtcod.BKGND_NONE,
						libtcod.RIGHT, str(crewman.stats[t]))
					y += 1
				
				# skills
				y = 29
				libtcod.console_set_default_foreground(con, libtcod.white)
				for skill in crewman.skills:
					libtcod.console_print(con, x+9, y, skill)
					y += 1
				
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print_ex(con, x+22, 55, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(crewman.level))
				libtcod.console_print_ex(con, x+22, 56, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(crewman.exp))
				libtcod.console_print_ex(con, x+22, 57, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(crewman.adv))
			
			# display commands
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, 31, 52, EnKey('q').upper() + '/' + EnKey('a').upper())
			libtcod.console_print(con, 31, 53, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(con, 31, 54, 'Tab')
			libtcod.console_print(con, 31, 55, EnKey('e').upper())
			libtcod.console_print(con, 31, 57, 'Enter')
			
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			libtcod.console_print(con, 37, 52, 'Select Crewman')
			libtcod.console_print(con, 37, 53, 'Select Position')
			libtcod.console_print(con, 37, 54, 'Display Crewman/Position')
			libtcod.console_print(con, 37, 55, 'Assign/Unassign Crewman')
			libtcod.console_print(con, 37, 56, ' to/from Position')
			libtcod.console_print(con, 37, 57, 'Finish')
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		selected_crewman = 0
		selected_position = 0
		crewman_highlight = False
		
		# draw menu screen for the first time
		DrawMenu()
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# confirm and finish
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER]:
				
				# make sure no player commanders would be reassigned
				for crewman in unassigned_crewmen:
					if crewman.is_player_commander:
						ShowNotification('You cannot reassign yourself! Your character must be assigned to a position.')
						continue
				
				# if any crewmen remain unassigned, confirm exit first
				if len(unassigned_crewmen) > 0:
					if not ShowNotification(str(len(unassigned_crewmen)) + ' crewmen will permanently leave your crew.', confirm=True):
						continue
				exit_menu = True
				continue
			
			elif key.vk == libtcod.KEY_TAB:
				crewman_highlight = not crewman_highlight
				DrawMenu()
				continue
			
			key_char = DeKey(chr(key.c).lower())
			
			# select unassigned crewman if any
			if key_char in ['q', 'a']:
				if len(unassigned_crewmen) <= 1: continue
				if key_char == 'q':
					selected_crewman -= 1
					if selected_crewman < 0:
						selected_crewman = len(unassigned_crewmen) - 1
			
				else:
					selected_crewman += 1
					if selected_crewman == len(unassigned_crewmen):
						selected_crewman = 0
				DrawMenu()
				continue
			
			# select tank position
			elif key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					selected_position -= 1
					if selected_position < 0:
						selected_position = len(campaign.player_unit.positions_list) - 1
			
				else:
					selected_position += 1
					if selected_position == len(campaign.player_unit.positions_list):
						selected_position = 0
				DrawMenu()
				continue
			
			# assign/unassign crewmen
			elif key_char == 'e':
				
				# move a crewman out of a position into unassigned
				crewman = campaign.player_unit.positions_list[selected_position].crewman
				if crewman is not None:
					unassigned_crewmen.append(crewman)
					crewman.current_position = None
					campaign.player_unit.positions_list[selected_position].crewman = None
				
				# assign a crewman from the unassigned list to a position on the tank
				if len(unassigned_crewmen) > 0:
					crewman = unassigned_crewmen[selected_crewman]
					unassigned_crewmen.remove(crewman)
					campaign.player_unit.positions_list[selected_position].crewman = crewman
					crewman.current_position = campaign.player_unit.positions_list[selected_position]
					crewman.SetCEStatus()
					crewman.unit = campaign.player_unit
					
					# need to select a new crewman
					if selected_crewman > len(unassigned_crewmen) - 1:
						selected_crewman = 0
				
				DrawMenu()
				continue
	
	
	# add an entry to the journal
	def AddJournal(self, text):
		if campaign_day is None: return
		time = str(campaign_day.day_clock['hour']).zfill(2) + ':' + str(campaign_day.day_clock['minute']).zfill(2)
		# create a new day entry if none exists already
		if self.today not in self.journal:
			self.journal[self.today] = []
		self.journal[self.today].append((time, text))
	
	
	# end the campaign
	def DoEnd(self):
		self.ended = True
		self.AwardDecorations()
		self.DisplayCampaignSummary()
		ExportLog()
		EraseGame(campaign.filename)
			
	
	# randomly generate a list of combat days for this campaign
	def GenerateCombatCalendar(self, campaign_length):
		
		self.combat_calendar = []
		
		# build a list of possible combat days
		possible_days = []
		for week in self.stats['calendar_weeks']:
			
			# skip refitting weeks for now
			if 'refitting' in week:
				continue
			
			# build list of possible dates this week: add the first date, then the following 6
			possible_days.append((week['start_date'], week['combat_chance']))
			day_text = week['start_date']
			(year, month, day) = day_text.split('.')
			
			for i in range(6):
				
				# this could be done with datetime now, but it works!
				# find the next day in the calendar
				
				# last day of month
				if int(day) == monthrange(int(year), int(month))[1]:
					
					# also last day of year
					if int(month) == 12:
						year = str(int(year) + 1)
						month = '01'
						day = '01'
					else:
						month = str(int(month) + 1)
						day = '01'
				
				else:
					day = str(int(day) + 1)
				
				day_text = year + '.' + month.zfill(2) + '.' + day.zfill(2)
				
				# if day is past end of calendar week, stop checking week
				if 'end_date' in week:
					if day_text > week['end_date']:
						break
				
				# check that day is not past end of campaign
				if day_text > self.stats['end_date']:
					break
				
				possible_days.append((day_text, week['combat_chance']))
		
		# calculate total number of desired days
		total_days = self.stats['combat_days']
		total_days = int(float(total_days) * CAMPAIGN_LENGTH_MULTIPLIERS[campaign_length])
		
		# keep rolling until combat calendar is full
		while len(self.combat_calendar) < total_days and len(possible_days) > 0:
			(day_text, combat_chance) = choice(possible_days)
			if libtcod.random_get_int(0, 1, 100) <= combat_chance:
				self.combat_calendar.append(day_text)
				possible_days.remove((day_text, combat_chance))
		
		# calculate total number of refit days, use final day of refit period
		# if we're playing a shorter campaign, remove some refit days
		refit_days = []
		for week in self.stats['calendar_weeks']:
			if 'refitting' in week:
				refit_days.append(week['end_date'])
		
		if CAMPAIGN_LENGTH_MULTIPLIERS[campaign_length] != 1.0:
			new_length = int(ceil(len(refit_days) * CAMPAIGN_LENGTH_MULTIPLIERS[campaign_length]))
			refit_days = sample(refit_days, new_length)
		
		#print('DEBUG: Adding ' + str(len(refit_days)) + ' refit days')
		self.combat_calendar += refit_days

		self.combat_calendar.sort()
		
		# sanity check to remove multiple dates in the calendar
		new_list = []
		for day_text in self.combat_calendar:
			if day_text not in new_list:
				new_list.append(day_text)
			else:
				print('DEBUG: Found and removed a repeated date in the combat calendar: ' + day_text)
		self.combat_calendar = new_list.copy()
		
		# if the final date in the combat calendar is a refit day, remove it
		if self.combat_calendar[-1] in refit_days:
			#print('DEBUG: Removing a refit day at the end of the combat calendar')
			self.combat_calendar.pop(-1)
		
		#print('DEBUG: Generated a combat calendar of ' + str(len(self.combat_calendar)) + ' days:')
		#print(str(self.combat_calendar))
	
	
	# copy over day's records to a new entry in the campaign record log
	def LogDayRecords(self):
		self.logs[self.today] = campaign_day.records.copy()
	
	
	# award VP to the player
	def AwardVP(self, vp_to_add):
		campaign_day.day_vp += vp_to_add
	
	
	# menu to select a campaign
	def CampaignSelectionMenu(self, campaign_list=None):
		
		# update screen with info about the currently selected campaign
		def UpdateCampaignSelectionScreen(active_list, selected_campaign_list, selected_campaign):
			libtcod.console_clear(con)
			
			# list of campaigns if any
			libtcod.console_set_default_foreground(con, libtcod.light_yellow)
			libtcod.console_set_default_background(con, libtcod.darkest_yellow)
			libtcod.console_rect(con, 3, 1, 20, 3, True, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			libtcod.console_print_ex(con, 13, 2, libtcod.BKGND_NONE, libtcod.CENTER,
				active_list)
			
			
			
			# display scroll arrows
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_put_char(con, 1, 2, 27)
			libtcod.console_put_char(con, 24, 2, 26)
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_set_default_background(con, libtcod.dark_blue)
			
			if len(selected_campaign_list) == 0:
				libtcod.console_print(con, 2, 26, 'None Yet Available')
			else:
				y = 5
				s = selected_campaign_list.index(selected_campaign)
				for i in range(s-7, s+10):
					if i < 0:
						y += 3
						continue
					elif i > len(selected_campaign_list) - 1:
						break
					
					if i == selected_campaign_list.index(selected_campaign):
						libtcod.console_rect(con, 1, y, 24, 2, True, libtcod.BKGND_SET)
					lines = wrap(selected_campaign_list[i]['name'], 23)
					y1 = 0
					for line in lines[:2]:
						libtcod.console_print(con, 2, y+y1, line)
						y1 += 1
					
					y += 3
			
			libtcod.console_set_default_background(con, libtcod.black)
			
			# menu title
			DrawFrame(con, 26, 0, 62, 60)
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			if campaign_list is None:
				text = 'Campaign Selection'
			else:
				text = 'Campaign Continuation'
			libtcod.console_print_ex(con, 57, 1, libtcod.BKGND_NONE, libtcod.CENTER,
				text)
			
			libtcod.console_set_default_foreground(con, libtcod.grey)
			libtcod.console_print_ex(con, 57, 3, libtcod.BKGND_NONE, libtcod.CENTER,
				str(total_campaigns) + ' Campaigns Available')
			
			# selected campaign info if any
			if selected_campaign is not None:
				
				libtcod.console_set_default_background(con, libtcod.darker_grey)
				libtcod.console_rect(con, 27, 5, 60, 4, True, libtcod.BKGND_SET)
				libtcod.console_set_default_background(con, libtcod.black)
				libtcod.console_set_default_foreground(con, PORTRAIT_BG_COL)
				lines = wrap(selected_campaign['name'], 33)
				y = 6
				for line in lines:
					libtcod.console_print_ex(con, 57, y, libtcod.BKGND_NONE, libtcod.CENTER, line)
					y += 1
				
				# player nation flag
				if selected_campaign['player_nation'] in session.flags:
					libtcod.console_blit(session.flags[selected_campaign['player_nation']],
						0, 0, 0, 0, con, 43, 10)
				
				# campaign start and end dates
				libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
				text = GetDateText(selected_campaign['start_date']) + ' to ' + GetDateText(selected_campaign['end_date'])
				libtcod.console_print_ex(con, 57, 25, libtcod.BKGND_NONE, libtcod.CENTER, text)
				
				# wrapped description text
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				y = 27
				lines = wrap(selected_campaign['desc'], 33)
				for line in lines[:6]:
					libtcod.console_print(con, 41, y, line)
					y+=1
				
				# player and enemy forces
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print_ex(con, 43, 36, libtcod.BKGND_NONE, libtcod.CENTER, 'PLAYER FORCE')
				libtcod.console_print_ex(con, 72, 36, libtcod.BKGND_NONE, libtcod.CENTER, 'ENEMY FORCES')
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				libtcod.console_print_ex(con, 43, 37, libtcod.BKGND_NONE, libtcod.CENTER, selected_campaign['player_nation'])
				text = ''
				for nation_name in selected_campaign['enemy_nations']:
					if selected_campaign['enemy_nations'].index(nation_name) != 0:
						text += ', '
					text += nation_name
				# handle longer lists of enemy nations
				y = 37
				lines = wrap(text, 30)
				for line in lines[:3]:
					libtcod.console_print_ex(con, 72, y, libtcod.BKGND_NONE, libtcod.CENTER, line)
					y += 1
				
				# region, and total combat days
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print_ex(con, 43, 41, libtcod.BKGND_NONE, libtcod.CENTER, 'REGION')
				libtcod.console_print_ex(con, 72, 41, libtcod.BKGND_NONE, libtcod.CENTER, 'COMBAT DAYS')
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				libtcod.console_print_ex(con, 43, 42, libtcod.BKGND_NONE, libtcod.CENTER,
					selected_campaign['region'])
				libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
				i = selected_campaign['combat_days']
				i = int(float(i) * CAMPAIGN_LENGTH_MULTIPLIERS[campaign_length])
				libtcod.console_print_ex(con, 72, 42, libtcod.BKGND_NONE, libtcod.CENTER,
					str(i))
				
				# display creator if any given
				if selected_campaign['creator'] is not None:
					libtcod.console_set_default_foreground(con, libtcod.white)
					libtcod.console_print_ex(con, 43, 44, libtcod.BKGND_NONE, libtcod.CENTER, 'CREATOR')
					libtcod.console_set_default_foreground(con, libtcod.light_grey)
					libtcod.console_print_ex(con, 43, 45, libtcod.BKGND_NONE, libtcod.CENTER,
						selected_campaign['creator'])
			
			# key commands
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, 46, 51, EnKey('q').upper() + '/' + EnKey('e').upper())
			libtcod.console_print(con, 46, 52, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(con, 46, 53, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_print(con, 46, 55, 'Tab')			
			libtcod.console_print(con, 46, 56, 'R')
			libtcod.console_print(con, 46, 57, 'Esc')
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 52, 51, 'Select Time Period')
			libtcod.console_print(con, 52, 52, 'Select Campaign')
			libtcod.console_print(con, 52, 53, 'Select Length')
			libtcod.console_print(con, 52, 55, 'Proceed')
			libtcod.console_print(con, 52, 56, 'Proceed with Random')
			libtcod.console_print(con, 52, 57, 'Return to Main Menu')
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# load basic information of campaigns into a list of dictionaries
		BASIC_INFO = [
			'name', 'start_date', 'end_date', 'player_nation',
			'enemy_nations', 'region', 'desc', 'combat_days',
			'creator'
		]
		
		# create separate lists for each time period
		# default category list
		CATEGORIES = [
			'Great War 1914-1918', 'Interwar 1919-1938', 'Early War 1939-1941',
			'Mid War 1942-1943', 'Late War 1944-1945', 'Cold War 1946-1989',
			'Contemporary 1990-'
		]
		campaigns = {}
		for k in CATEGORIES:
			campaigns[k] = []
		all_campaigns = []
		total_campaigns = 0
		
		for filename in os.listdir(CAMPAIGNPATH):
			if not filename.endswith('.json'): continue
			
			# campaign list has already been defined (for continuing after a completed campaign)
			if campaign_list is not None:
				if filename not in campaign_list: continue
			
			# players might create their own campaigns, so add a check in case json parsing fails
			try:
				with open(CAMPAIGNPATH + filename, encoding='utf8') as data_file:
					campaign_data = json.load(data_file)
			except Exception as e:
				ShowNotification('Error: Unable to parse campaign file ' + filename + ': ' +
					str(e))
				continue
			new_campaign = {}
			new_campaign['filename'] = filename
			for k in BASIC_INFO:
				# some data is optional (eg. creator)
				if k not in campaign_data:
					new_campaign[k] = None
				else:
					new_campaign[k] = campaign_data[k]
			
			# add to the appropriate list
			year = int(new_campaign['start_date'].split('.')[0])
			if 1914 <= year <= 1918:
				campaigns['Great War 1914-1918'].append(new_campaign)
			elif 1919 <= year <= 1938:
				campaigns['Interwar 1919-1938'].append(new_campaign)
			elif 1939 <= year <= 1941:
				campaigns['Early War 1939-1941'].append(new_campaign)
			elif 1942 <= year <= 1943:
				campaigns['Mid War 1942-1943'].append(new_campaign)
			elif 1944 <= year <= 1945:
				campaigns['Late War 1944-1945'].append(new_campaign)
			elif 1946 <= year <= 1989:
				campaigns['Cold War 1946-1989'].append(new_campaign)
			elif year > 1989:
				campaigns['Contemporary 1990-'].append(new_campaign)
			else:
				continue
			all_campaigns.append(new_campaign)
			total_campaigns += 1
			
			del campaign_data
		
		# no campaign files!
		if total_campaigns == 0:
			ShowNotification('Error: No compatible campaign files available!')
			return False
		
		# prune any categories with 0 campaigns and create a new list of categories
		category_list = []
		for k in CATEGORIES:
			if len(campaigns[k]) == 0:
				del campaigns[k]
			else:
				category_list.append(k)
		
		# sort campaigns in each list by start date
		for k, v in campaigns.items():
			campaigns[k] = sorted(v, key = lambda x : (x['start_date']))
		
		# select first available campaign category and first campaign
		active_list = category_list[0]
		selected_campaign = campaigns[active_list][0]
		
		# campaign length selection
		campaign_length = 0
		
		# draw menu screen for first time
		UpdateCampaignSelectionScreen(active_list, campaigns[active_list], selected_campaign)
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# exit without starting a new campaign if escape is pressed
			if key.vk == libtcod.KEY_ESCAPE:
				
				# if we're continuing a campaign, confirm with the player
				if campaign_list is not None:
					if not ShowNotification('Cancel new campaign? Your current crew will be lost forever!', confirm=True, add_pause=True):
						continue
				
				return False
			
			# proceed with selected campaign
			elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				
				if selected_campaign is None: continue
				
				# check to see whether there's already a saved game for this campaign
				if os.path.isdir(SAVEPATH + selected_campaign['filename'].rsplit('.', 1)[0]):
					if not ShowNotification('WARNING: Saved campaign already exists for this campaign, erase and start a new one?', confirm=True):
						UpdateCampaignSelectionScreen(active_list, campaigns[active_list], selected_campaign)
						continue
				
				exit_menu = True
			
			key_char = DeKey(chr(key.c).lower())
			
			# change selected category
			if key_char in ['q', 'e']:
				i = category_list.index(active_list)
				if key_char == 'e':
					if i == len(category_list) - 1:
						active_list = category_list[0]
					else:
						active_list = category_list[i+1]
				else:
					if i == 0:
						active_list = category_list[-1]
					else:
						active_list = category_list[i-1]
				selected_campaign = None
				if len(campaigns[active_list]) > 0:
					selected_campaign = campaigns[active_list][0]
				PlaySoundFor(None, 'menu_select')
				UpdateCampaignSelectionScreen(active_list, campaigns[active_list], selected_campaign)
			
			# change selected campaign
			elif key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				if selected_campaign is None: continue
				i = campaigns[active_list].index(selected_campaign)
				if key_char == 's' or key.vk == libtcod.KEY_DOWN:
					if i == len(campaigns[active_list]) - 1:
						selected_campaign = campaigns[active_list][0]
					else:
						selected_campaign = campaigns[active_list][i+1]
				else:
					if i == 0:
						selected_campaign = campaigns[active_list][-1]
					else:
						selected_campaign = campaigns[active_list][i-1]
				PlaySoundFor(None, 'menu_select')
				UpdateCampaignSelectionScreen(active_list, campaigns[active_list], selected_campaign)
			
			# cycle campaign length
			elif key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
				if selected_campaign is None: continue
				if key_char == 'a' or key.vk == libtcod.KEY_LEFT:
					m = 1
				else:
					m = -1
				campaign_length += m
				if campaign_length < 0:
					campaign_length = len(CAMPAIGN_LENGTH_MULTIPLIERS) - 1
				elif campaign_length >= len(CAMPAIGN_LENGTH_MULTIPLIERS):
					campaign_length = 0
				PlaySoundFor(None, 'menu_select')
				UpdateCampaignSelectionScreen(active_list, campaigns[active_list], selected_campaign)
			
			# select a random campaign (not keymapped)
			elif chr(key.c).lower() == 'r':
				old_campaign = selected_campaign
				selected_campaign = choice(all_campaigns)
				
				# check to see whether there's already a saved game for this campaign
				if os.path.isdir(SAVEPATH + selected_campaign['filename'].rsplit('.', 1)[0]):
					if not ShowNotification('WARNING: Saved campaign already exists for ' +
						selected_campaign['name'] + ', erase and start a new one?',
						confirm=True):
						selected_campaign = old_campaign
						UpdateCampaignSelectionScreen(active_list, campaigns[active_list], selected_campaign)
						continue
				
				exit_menu = True
		
		# create a local copy of selected campaign stats
		with open(CAMPAIGNPATH + selected_campaign['filename'], encoding='utf8') as data_file:
			self.filename = selected_campaign['filename'].rsplit('.', 1)[0]
			self.stats = json.load(data_file)
		
		# DEBUG - check that all enemy unit IDs are present in unit defs
		if DEBUG:
			for nation_name, unit_list in self.stats['enemy_unit_list'].items():
				for unit_name in unit_list:
					if unit_name not in session.unit_types:
						print('Unit ID not found: ' + unit_name)
		
		# generate list of combat days
		self.GenerateCombatCalendar(campaign_length)
		
		# set current date and week
		self.today = self.combat_calendar[0]
		self.current_week = self.stats['calendar_weeks'][0]
		
		return True
	
	
	# menu to set campaign options
	def CampaignOptionsMenu(self):
		
		# update menu screen
		def UpdateCampaignOptionsScreen(selected_option):
			libtcod.console_clear(con)
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			DrawFrame(con, 24, 2, 42, 7)
			libtcod.console_set_default_background(con, libtcod.dark_grey)
			libtcod.console_rect(con, 25, 3, 40, 5, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			
			libtcod.console_set_default_foreground(con, libtcod.light_green)
			libtcod.console_print_ex(con, 45, 5, libtcod.BKGND_NONE, libtcod.CENTER,
				'Campaign Options')
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 54, 11, 'Victory Point')
			libtcod.console_print(con, 57, 12, 'Modifier')
			
			i = 0
			y = 15
			vp_mod = 0.00
			for (name, k, desc, mod) in CAMPAIGN_OPTIONS:
				
				if i == selected_option:
					libtcod.console_set_default_background(con, libtcod.darker_blue)
					libtcod.console_rect(con, 27, y-1, 36, 3, False, libtcod.BKGND_SET)
					libtcod.console_set_default_background(con, libtcod.black)
					
					lines = wrap(desc, 23)
					y1 = 27 - int(len(lines) / 2)
					libtcod.console_set_default_foreground(con, libtcod.white)
					for line in lines:
						libtcod.console_print(con, 2, y1, line)
						y1 += 1
				
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print(con, 28, y, name)
				
				if self.options[k]:
					libtcod.console_set_default_foreground(con, libtcod.white)
					libtcod.console_print(con, 53, y, 'ON')
				else:
					libtcod.console_set_default_foreground(con, libtcod.dark_grey)
					libtcod.console_print(con, 53, y, 'OFF')
				
				# display VP modifier as a percentage
				if not self.options[k]:
					col = libtcod.grey
				else:
					vp_mod += mod
					vp_mod = round(vp_mod, 2)
					if mod < 0.0:
						col = libtcod.light_red
					else:
						col = libtcod.light_green
				libtcod.console_set_default_foreground(con, col)
				text = ''
				if mod > 0.0: text += '+'
				text += str(int(mod * 100.0)) + '%' 
				libtcod.console_print(con, 58, y, text)
				
				y += 3
				i += 1
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 28, 45, 'Total VP Modifier:')
			
			text = ''
			if vp_mod == 0.0:
				col = libtcod.grey
				text = '--'
			else:
				if vp_mod < 0.0:
					col = libtcod.light_red
				else:
					col = libtcod.light_green
					text += '+'
				libtcod.console_set_default_foreground(con, col)
				text += str(int(vp_mod * 100.0)) + '%'
			libtcod.console_print(con, 58, 45, text)
			
			# key commands
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, 33, 52, 'W/S')
			libtcod.console_print(con, 33, 53, 'Space')
			libtcod.console_print(con, 33, 54, 'Tab')
			libtcod.console_print(con, 33, 55, 'Esc')
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 40, 52, 'Select Option')
			libtcod.console_print(con, 40, 53, 'Toggle Option')
			libtcod.console_print(con, 40, 54, 'Proceed with Campaign')
			libtcod.console_print(con, 40, 55, 'Return to Main Menu')
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		selected_option = 0
		
		# draw menu screen for first time
		UpdateCampaignOptionsScreen(selected_option)
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# exit if escape is pressed
			if key.vk == libtcod.KEY_ESCAPE:
				if not ShowNotification('Cancel new campaign and return to the main menu?', confirm=True, add_pause=True):
					continue
				return False
			
			# proceed with current options
			elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				
				# calculate total vp modifier and store
				vp_mod = 0.0
				for (name, k, desc, mod) in CAMPAIGN_OPTIONS:
					if self.options[k]:
						vp_mod += mod
						vp_mod = round(vp_mod, 2)
				
				self.vp_modifier = vp_mod
				return True
			
			# toggle selected option
			elif key.vk == libtcod.KEY_SPACE:
				(name, k, desc, req) = CAMPAIGN_OPTIONS[selected_option]
				self.options[k] = not self.options[k]
				PlaySoundFor(None, 'menu_select')
				UpdateCampaignOptionsScreen(selected_option)
				continue
			
			key_char = chr(key.c).lower()
			
			if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if selected_option > 0:
						selected_option -= 1
					else:
						selected_option = len(CAMPAIGN_OPTIONS) - 1
				else:
					if selected_option < len(CAMPAIGN_OPTIONS) - 1:
						selected_option += 1
					else:
						selected_option = 0
				PlaySoundFor(None, 'menu_select')
				UpdateCampaignOptionsScreen(selected_option)
				continue
	
	
	# menu to select player tank
	# also allows input/generation of tank name, and return both
	# can be used when replacing a tank mid-campaign as well
	def TankSelectionMenu(self, replacing_tank=False, starting_campaign=False):
		
		def UpdateTankSelectionScreen():
			libtcod.console_clear(con)
			
			if replacing_tank and campaign.player_unit.alive:
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print_ex(con, 77, 32, libtcod.BKGND_NONE, libtcod.CENTER,
					'Current Tank')
				DisplayUnitInfo(con, 64, 34, campaign.player_unit.unit_id,
					campaign.player_unit, status=False)
				
			libtcod.console_set_default_foreground(con, libtcod.white)
			DrawFrame(con, 26, 1, 37, 58)
			
			libtcod.console_set_default_background(con, libtcod.darker_blue)
			libtcod.console_rect(con, 27, 2, 35, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print_ex(con, 45, 3, libtcod.BKGND_NONE, libtcod.CENTER,
				'Player Tank Selection')
			libtcod.console_set_default_foreground(con, libtcod.white)
			
			libtcod.console_print_ex(con, 45, 6, libtcod.BKGND_NONE, libtcod.CENTER,
				'Select a tank type to command')
			
			# list of tank types
			y = WINDOW_YM - len(unit_list)
			if y < 2: y = 2
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			for unit_type in unit_list:
				if unit_type == selected_unit_id:
					libtcod.console_set_default_background(con, libtcod.darker_blue)
					libtcod.console_rect(con, 2, y, 22, 1, False, libtcod.BKGND_SET)
					libtcod.console_set_default_background(con, libtcod.black)
				libtcod.console_print(con, 2, y, unit_type)
				y += 2
			
			# add note if list was restricted
			if more_to_come:
				y += 2
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				libtcod.console_print(con, 2, y, 'More options will be')
				libtcod.console_print(con, 2, y+1, 'availible later in')
				libtcod.console_print(con, 2, y+2, 'the campaign')
			
			# details on currently selected tank type
			libtcod.console_set_default_foreground(con, libtcod.white)
			DrawFrame(con, 32, 10, 27, 18)
			DisplayUnitInfo(con, 33, 11, selected_unit_id, None)
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 33, 13, player_tank_name)
			
			if 'tank_vp_modifiers' in campaign.stats:
				if selected_unit_id in campaign.stats['tank_vp_modifiers']:
					libtcod.console_set_default_foreground(con, libtcod.light_purple)
					libtcod.console_print(con, 35, 29, 'VP Modifier: ')
					modifier = campaign.stats['tank_vp_modifiers'][selected_unit_id]
					if modifier > 1.0:
						libtcod.console_set_default_foreground(con, libtcod.light_green)
						text = '+' + str(int(round((modifier - 1.0) * 100.0, 0))) + '%'
					else:
						libtcod.console_set_default_foreground(con, libtcod.light_red)
						text = '-' + str(int(round((1.0 - modifier) * 100.0, 0))) + '%'
					libtcod.console_print(con, 48, 29, text)
			
			if 'description' in session.unit_types[selected_unit_id]:
				text = ''
				for t in session.unit_types[selected_unit_id]['description']:
					text += t
				lines = wrap(text, 33)
				y = 32
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				for line in lines[:20]:
					libtcod.console_print(con, 28, y, line)
					y+=1
			
			# display list of tank positions
			if 'crew_positions' in session.unit_types[selected_unit_id]:
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print(con, 65, 13, 'Crew: ' + str(len(session.unit_types[selected_unit_id]['crew_positions'])))
				y = 15
				for position in session.unit_types[selected_unit_id]['crew_positions']:
					libtcod.console_print(con, 66, y, position['name'])
					y += 2
			
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, 32, 52, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(con, 32, 53, 'N')
			if (replacing_tank and campaign.player_unit.alive) or starting_campaign:
				libtcod.console_print(con, 32, 54, 'Esc')
			if len(unit_list) > 1:
				libtcod.console_print(con, 32, 55, 'R')
			libtcod.console_print(con, 32, 56, 'Tab')
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 38, 52, 'Select Unit Type')
			libtcod.console_print(con, 38, 53, 'Set Tank Name')
			if replacing_tank and campaign.player_unit.alive:
				libtcod.console_print(con, 38, 54, 'Keep Current Tank')
			elif starting_campaign:
				libtcod.console_print(con, 38, 54, 'Return to Main Menu')
			if len(unit_list) > 1:
				libtcod.console_print(con, 38, 55, 'Proceed with Random Tank')
			libtcod.console_print(con, 38, 56, 'Proceed')
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# generate temporary list of units, one per possible unit type
		unit_list = []
		more_to_come = False
		
		for unit_id in self.stats['player_unit_list']:
			
			# check that unit is available at current point in calendar
			if unit_id not in session.unit_types: continue
			if 'rarity' in session.unit_types[unit_id]:
				rarity_ok = True
				for date, chance in session.unit_types[unit_id]['rarity'].items():
					# not yet available at this time
					if date > campaign.today:
						rarity_ok = False
						break
					# earliest rarity date is on or before current date, proceed
					break
			
			if not campaign.options['ahistorical']:
				if not rarity_ok:
					more_to_come = True
					continue
			
			# check to see if some player tanks are restricted to a certain date (used for captured tanks)
			if 'player_unit_dates' in self.stats and not campaign.options['ahistorical']:
				if unit_id in self.stats['player_unit_dates']:
					if campaign.today < self.stats['player_unit_dates'][unit_id]:
						more_to_come = True
						continue
			
			unit_list.append(unit_id)
		
		# if random_tank campaign option is active, limit choices to one tank model
		if campaign.options['random_tank'] and 'refitting' not in campaign.current_week:
			unit_id = choice(unit_list)
			unit_list = [unit_id]
			
		# select first tank type by default
		selected_unit_id = unit_list[0]
		
		# placeholder for tank name if any
		player_tank_name = ''
		
		# draw menu screen for first time
		UpdateTankSelectionScreen()
		
		exit_loop = False
		while not exit_loop:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# proceed with selected tank
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				exit_loop = True
			
			# cancel new campaign
			elif key.vk in [libtcod.KEY_BACKSPACE, libtcod.KEY_ESCAPE] and starting_campaign:
				return (None, None)
			
			# don't choose a new model
			elif key.vk in [libtcod.KEY_BACKSPACE, libtcod.KEY_ESCAPE] and replacing_tank and campaign.player_unit.alive:
				return (None, None)
			
			# unmapped keys
			key_char = chr(key.c).lower()
			
			# change/generate player tank name
			if key_char == 'n':				
				player_tank_name = ShowTextInputMenu('Enter a name for your tank', player_tank_name, MAX_TANK_NAME_LENGTH, [])
				UpdateTankSelectionScreen()
			
			# choose random tank type and proceed
			elif key_char == 'r':
				
				if len(unit_list) <= 1: continue
				
				if not ShowNotification('Be assigned a random tank type? You cannot reverse this choice.', confirm=True):
					UpdateTankSelectionScreen()
					continue
				
				selected_unit_id = choice(unit_list)
				ShowNotification('You are assigned a ' + selected_unit_id + ' tank.')
				exit_loop = True
			
			# mapped keys
			key_char = DeKey(chr(key.c).lower())
			
			# change selected tank
			if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				
				i = unit_list.index(selected_unit_id)
				if key_char == 's'  or key.vk == libtcod.KEY_DOWN:
					if i == len(unit_list) - 1:
						selected_unit_id = unit_list[0]
					else:
						selected_unit_id = unit_list[i+1]
				else:
					if i == 0:
						selected_unit_id = unit_list[-1]
					else:
						selected_unit_id = unit_list[i-1]
				PlaySoundFor(None, 'menu_select')
				UpdateTankSelectionScreen()
			
		return (selected_unit_id, player_tank_name)
	
	
	# allow player to choose a new tank after losing one or during a refit period
	def ReplacePlayerTank(self):
		
		# clear any dead crewmen from old positions
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			if not position.crewman.alive:
				position.crewman = None
		
		exit_menu = False
		while not exit_menu:
			
			# allow player to choose a new tank model
			(unit_id, tank_name) = self.TankSelectionMenu(replacing_tank=True)
			
			# did not choose a new model
			if unit_id is None:
				return
			
			# run through each current crewmen and see if anyone cannot fit in new model
			positions_open = len(session.unit_types[unit_id]['crew_positions'])
			all_dead = True
			for position in self.player_unit.positions_list:
				if position.crewman is None: continue
				all_dead = False
				positions_open -= 1
			
			if positions_open < 0:
				text = 'You will need to reassign ' + str(abs(positions_open)) + ' crewmen who will leave your crew.'
			elif all_dead:
				text = 'Choose this tank model?'
			else:
				text = 'All current crew can be assigned to this new tank.'
			if not ShowNotification(text, confirm=True):
				continue
			
			exit_menu = True
			
		new_unit = Unit(unit_id, is_player=True)
		new_unit.unit_name = tank_name
		new_unit.nation = self.stats['player_nation']
		
		# transfer crew over to new tank
		
		# do an initial pass, trying to place crewman into a position for which they are trained
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			for new_position in new_unit.positions_list:
				if new_position.crewman is not None: continue
				
				position.crewman.current_position = new_position
				if position.crewman.UntrainedPosition():
					position.crewman.current_position = position
					continue
				
				# move the crewman
				new_position.crewman = position.crewman
				new_position.crewman.unit = new_unit
				new_position.crewman.SetCEStatus()
				position.crewman = None
				break
		
		# go through remaining crewman and fit them in the new tank from lowest position upward
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			for new_position in reversed(new_unit.positions_list):
				if new_position.crewman is not None: continue
				
				# move the crewman
				position.crewman.current_position = new_position
				new_position.crewman = position.crewman
				new_position.crewman.unit = new_unit
				new_position.crewman.SetCEStatus()
				position.crewman = None
				break
		
		# some crewmen may not be able to be assigned to the new tank 
		extra_crewmen = []
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			extra_crewmen.append(position.crewman)
		
		# set the player unit to the new unit
		self.player_unit = new_unit
		self.player_unit.ClearGunAmmo()
		self.AddJournal('We transferred to a new tank: ' + self.player_unit.unit_id)
		
		# need to reassign 1+ crewmen
		if len(extra_crewmen) > 0:
			ShowNotification(str(len(extra_crewmen)) + ' crewmen must now be reassigned.')
			campaign.ShowAssignPositionsMenu(unassigned_crewmen=extra_crewmen)
		
		# give player a chance to swap crewmen around
		ShowNotification('You can now assign your crew to new positions if required.')
		ShowSwapPositionMenu()
		
		# generate new crewmen to fill vacant positions if required
		for position in self.player_unit.positions_list:
			if position.crewman is None:
				position.crewman = Personnel(self.player_unit, self.player_unit.nation, position)
				ShowMessage('A new crewman joins your crew in the ' + position.name + ' position:',
					crewman=position.crewman)
				campaign.AddJournal('Start of day')

	
	# display an animated screen for the start of a new combat day
	def ShowStartOfDay(self):
		
		libtcod.console_clear(con)
		
		# background gradient
		for y in range(WINDOW_HEIGHT):
			col = libtcod.Color(int(255 * (y / WINDOW_HEIGHT)), int(170 * (y / WINDOW_HEIGHT)), 0)
			libtcod.console_set_default_background(con, col)
			libtcod.console_rect(con, 0, y, WINDOW_WIDTH, 1, True, libtcod.BKGND_SET)
		
		# text box
		libtcod.console_set_default_background(con, libtcod.black)
		libtcod.console_rect(con, 30, 15, 30, 20, True, libtcod.BKGND_SET)
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		DrawFrame(con, 30, 15, 30, 20)
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_print_ex(con, WINDOW_XM, 17, libtcod.BKGND_NONE, libtcod.CENTER,
			GetDateText(self.today))
		
		if 'refitting' in self.current_week:
			libtcod.console_print_ex(con, WINDOW_XM, 19, libtcod.BKGND_NONE, libtcod.CENTER,
				'Refitting')
		else:
			libtcod.console_print_ex(con, WINDOW_XM, 19, libtcod.BKGND_NONE, libtcod.CENTER,
				str(campaign_day.start_of_day['hour']).zfill(2) + ':' + str(campaign_day.start_of_day['minute']).zfill(2))
			
			lines = wrap(self.current_week['week_title'], 20)
			y = 24
			for line in lines:
				PrintExtended(con, WINDOW_XM, y, line, center=True)
				y += 1
		
		# fade in from black
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		for i in range(100, 0, -5):
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			libtcod.console_blit(darken_con, 0, 0, 0, 0, 0, window_x, window_y, 0.0, (i * 0.01))
			libtcod.console_flush()
			Wait(5, ignore_animations=True)
		Wait(95, ignore_animations=True)
	
	
	# determine and show results of a completed campaign day: injury results and level ups
	def ShowEndOfDay(self):
		
		# create background console
		libtcod.console_clear(con)
		
		# starfield
		for i in range(18):
			x = libtcod.random_get_int(0, 0, WINDOW_WIDTH)
			y = libtcod.random_get_int(0, 0, 18)
			libtcod.console_put_char_ex(con, x, y, 250, libtcod.white, libtcod.black)
		
		# moon phase display
		if campaign_day.moon_phase in ['First Quarter', 'Full Moon']:
			libtcod.console_put_char_ex(con, 7, 3, 236, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 7, 4, 219, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 7, 5, 238, libtcod.white, libtcod.black)
		if campaign_day.moon_phase in ['Last Quarter', 'Full Moon']:
			libtcod.console_put_char_ex(con, 9, 3, 237, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 9, 4, 219, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 9, 5, 239, libtcod.white, libtcod.black)
		if campaign_day.moon_phase == 'First Quarter':
			libtcod.console_put_char_ex(con, 8, 3, 17, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 8, 5, 31, libtcod.white, libtcod.black)
		elif campaign_day.moon_phase == 'Last Quarter':
			libtcod.console_put_char_ex(con, 8, 3, 30, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 8, 5, 16, libtcod.white, libtcod.black)
		elif campaign_day.moon_phase == 'Full Moon':
			libtcod.console_put_char_ex(con, 8, 3, 219, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 8, 4, 219, libtcod.white, libtcod.black)
			libtcod.console_put_char_ex(con, 8, 5, 219, libtcod.white, libtcod.black)
		
		# gradient
		for y in range(19, WINDOW_HEIGHT):
			col = libtcod.Color(int(180 * (y / WINDOW_HEIGHT)), 0, 0)
			libtcod.console_set_default_background(con, col)
			libtcod.console_rect(con, 0, y, WINDOW_WIDTH, 1, True, libtcod.BKGND_SET)
		
		# window
		libtcod.console_set_default_background(con, libtcod.black)
		libtcod.console_rect(con, 15, 6, 60, 50, True, libtcod.BKGND_SET)
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		DrawFrame(con, 15, 6, 60, 50)
		
		libtcod.console_set_default_background(con, libtcod.darker_blue)
		libtcod.console_rect(con, 39, 7, 12, 3, True, libtcod.BKGND_SET)
		libtcod.console_set_default_background(con, libtcod.black)
		libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
		libtcod.console_print_ex(con, WINDOW_XM, 8, libtcod.BKGND_NONE, libtcod.CENTER,
			'End of Day')
		
		# column titles
		libtcod.console_set_default_foreground(con, libtcod.red)
		libtcod.console_print(con, 42, 12, 'Injury/KIA')
		libtcod.console_set_default_foreground(con, libtcod.light_blue)
		libtcod.console_print(con, 60, 12, 'Level Up')
		
		y = 15
		for position in campaign.player_unit.positions_list:
			if position.crewman is None: continue
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 18, y, position.name)
			PrintExtended(con, 18, y+1, position.crewman.GetName(), first_initial=True)
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			for x in range(18, 72):
				libtcod.console_put_char(con, x, y+3, '.')
			y += 6
		
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		for y1 in range(13, y-3):
			libtcod.console_put_char(con, 38, y1, '.')
			libtcod.console_put_char(con, 56, y1, '.')
		
		# fade in from black
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		for i in range(100, 0, -5):
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			libtcod.console_blit(darken_con, 0, 0, 0, 0, 0, 0, 0, 0.0, (i * 0.01))
			Wait(5, ignore_animations=True)
		
		# award exp for entire day, roll for crew injury resolution, apply results
		for position in campaign.player_unit.positions_list:
			if position.crewman is None: continue
			if not position.crewman.alive: continue
			position.crewman.AwardExp(campaign_day.day_vp)
			position.crewman.ResolveInjuries()
		
		# add day VP to campaign total
		campaign.player_vp += campaign_day.day_vp
		
		# save now to fix these results in place
		SaveGame()
		
		# display results of crew injury resolution and level ups
		y = 15
		for position in campaign.player_unit.positions_list:
			if position.crewman is None: continue
			
			# KIA or field hospital result
			if not position.crewman.alive:
				libtcod.console_set_default_foreground(con, libtcod.red)
				libtcod.console_print(con, 45, y+1, 'KIA')
			else:
				if position.crewman.field_hospital is None:
					libtcod.console_set_default_foreground(con, libtcod.light_grey)
					libtcod.console_print_ex(con, 47, y, libtcod.BKGND_NONE, libtcod.CENTER,
						'None')
				else:
					libtcod.console_set_default_foreground(con, libtcod.dark_red)
					libtcod.console_print_ex(con, 47, y, libtcod.BKGND_NONE, libtcod.CENTER,
						'Field Hospital')
					(days_min, days_max) = position.crewman.field_hospital
					text = str(days_min) + '-' + str(days_max) + ' days'
					libtcod.console_print_ex(con, 47, y+1, libtcod.BKGND_NONE, libtcod.CENTER,
						text)
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(30, ignore_animations=True)
			
			if not position.crewman.alive:
				libtcod.console_set_default_foreground(con, libtcod.red)
				libtcod.console_print(con, 62, y+1, 'N/A')
			
			else:
			
				# reset fatigue points if any
				position.crewman.fatigue = BASE_FATIGUE
				
				# grant random additional exp
				position.crewman.exp += libtcod.random_get_int(0, 0, 5)
				
				# check for level up
				levels_up = 0
				for level in range(position.crewman.level+1, 31):
					if position.crewman.exp >= GetExpRequiredFor(level):
						levels_up += 1
					else:
						break
				
				if levels_up == 0:
					libtcod.console_set_default_foreground(con, libtcod.light_grey)
					text = 'None'
				else:
					position.crewman.level += levels_up
					position.crewman.adv += levels_up
					libtcod.console_set_default_foreground(con, libtcod.white)
					text = '+' + str(levels_up)
				libtcod.console_print_ex(con, 64, y, libtcod.BKGND_NONE,
					libtcod.CENTER, text)
			
			# crewmen recover from any negative condition (except for death)
			if position.crewman.alive: 
				position.crewman.condition = 'Good Order'
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(30, ignore_animations=True)
			y += 6
		
		# remove dead crewmen
		for position in campaign.player_unit.positions_list:
			if position.crewman is None: continue
			if not position.crewman.alive:
				text = 'The body of your ' + position.name + ' is taken away.'
				ShowMessage(text)
				position.crewman = None
				continue
		
		# move crewmen to field hospital where required
		for position in campaign.player_unit.positions_list:
			if position.crewman is None: continue
			if position.crewman.field_hospital is None: continue
			campaign.hospital.append(position.crewman)
			position.crewman = None
		
		# sort current field hospital crewman
		campaign.hospital.sort(key=lambda x: x.field_hospital)
		
		# repair tank if required
		if campaign.player_unit.immobilized:
			campaign.player_unit.immobilized = False
		
		# add to campaign records
		self.records['Combat Days'] += 1
		
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 38, 53, 'Tab')
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		libtcod.console_print(con, 45, 53, 'Continue')
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				exit_menu = True

	
	# calculate decorations to be awarded at the end of a campaign
	def AwardDecorations(self):
		
		# no decorations set
		if 'decorations_list' not in self.stats:
			return
		
		# generate an ordered list of required VP scores and decoration names for this campaign
		deco_list = []
		
		for key, value in self.stats['decorations_list'].items():
			deco_list.append((int(key), value))
		deco_list.sort(key = lambda x: x[0], reverse=True)
		
		# see if player has enough VP for a decoration
		for (vp_req, decoration) in deco_list:
			if self.player_vp >= vp_req:
				self.decoration = decoration
				return
	
	
	# display a summary of a completed campaign
	def DisplayCampaignSummary(self):
		
		# add a line of text to the screen one character at a time
		def DisplayLine(x, y, text):
			x1 = x
			for char in text:
				libtcod.console_put_char(con, x1, y, char)
				x1 += 1
				libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
				Wait(2, ignore_animations=True)
		
		# draw background to screen
		libtcod.console_blit(LoadXP('final_report.xp'), 0, 0, 0, 0, con, 0, 0)
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		libtcod.console_flush()
		Wait(70, ignore_animations=True)
		
		# titles
		libtcod.console_set_default_foreground(con, libtcod.black)
		DisplayLine(35, 3, 'Armoured Commander')
		Wait(20, ignore_animations=True)
		DisplayLine(38, 4, 'Final Report')
		Wait(20, ignore_animations=True)
		DisplayLine(25, 6, '. . . . . . . . . . . . . . . . . . . .')
		Wait(60, ignore_animations=True)
		
		# display current date
		text = GetDateText(self.today)
		x = 64 - len(text)
		DisplayLine(x, 8, text)
		Wait(60, ignore_animations=True)
		
		# commander info
		crewman = self.player_unit.positions_list[0].crewman
		
		if crewman is not None:
		
			DisplayLine(25, 11, 'Name:')
			Wait(20, ignore_animations=True)
			PrintExtended(con, 31, 11, crewman.GetName())
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(60, ignore_animations=True)
			
			DisplayLine(25, 15, 'Rank:')
			Wait(20, ignore_animations=True)
			text = session.nations[crewman.nation]['rank_names'][str(crewman.rank)]
			libtcod.console_print(con, 31, 15, text)
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(60, ignore_animations=True)
			
			DisplayLine(25, 19, 'VP Earned:')
			Wait(20, ignore_animations=True)
			libtcod.console_print(con, 36, 19, str(self.player_vp))
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(60, ignore_animations=True)
			
			# campaign stats
			DisplayLine(25, 24, 'Statistics:')
			Wait(20, ignore_animations=True)

			y = 26
			record_list = RECORD_LIST.copy()
			record_list.append('Combat Days')
			for text in record_list:
				libtcod.console_print(con, 32, y, text + ':')
				libtcod.console_print_ex(con, 55, y, libtcod.BKGND_NONE, libtcod.RIGHT,
					str(self.records[text]))
				libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
				Wait(20, ignore_animations=True)
				y += 1
				if y == 39:
					break
		
			# award if any
			DisplayLine(25, 41, 'Awarded:')
			Wait(20, ignore_animations=True)
			if self.decoration == '':
				text = 'No Award'
			else:
				text = self.decoration
			libtcod.console_print_ex(con, 45, 42, libtcod.BKGND_NONE, libtcod.CENTER,
				text)
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(60, ignore_animations=True)
			
			# fate
			DisplayLine(25, 48, 'Fate:')
			Wait(30, ignore_animations=True)
			if not crewman.alive:
				fate_text = 'KIA'
			else:
				fate_text = 'Survived'
			libtcod.console_print_ex(con, 45, 48, libtcod.BKGND_NONE, libtcod.CENTER,
				fate_text)
			libtcod.console_set_default_foreground(con, libtcod.light_red)
			DrawFrame(con, 36, 46, 18, 5)
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			Wait(60, ignore_animations=True)
		
		libtcod.console_set_default_foreground(con, libtcod.black)
		libtcod.console_print(con, 25, 54, '. . . . . . . . . . . . . . . . . . . .')
		
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 38, 56, 'Esc')
		libtcod.console_set_default_foreground(con, libtcod.black)
		libtcod.console_print(con, 43, 56, 'Continue')
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# get input from player
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# end menu
			if key.vk == libtcod.KEY_ESCAPE:
				exit_menu = True
		
		# add an entry to the morgue file
		session.UpdateMorguefile((crewman.GetName(), crewman.level, self.player_vp,
			fate_text, self.records['Combat Days'], self.stats['name'], VERSION))
	
	
	#######################################
	#     Campaign Calendar Interface     #
	#######################################
	
	# update the day outline console, 24x22
	def UpdateDayOutlineCon(self):
		libtcod.console_clear(day_outline)
		
		# campaign name, max 2 lines
		libtcod.console_set_default_foreground(day_outline, PORTRAIT_BG_COL)
		lines = wrap(campaign.stats['name'], 20)
		y = 2
		for line in lines[:3]:
			libtcod.console_print_ex(day_outline, 12, y, libtcod.BKGND_NONE,
				libtcod.CENTER, line)
			y += 1
		
		# current date
		libtcod.console_set_default_foreground(day_outline, libtcod.light_grey)
		libtcod.console_print_ex(day_outline, 12, 6, libtcod.BKGND_NONE, libtcod.CENTER,
			GetDateText(campaign.today))
		
		# display days passed and days remaining
		libtcod.console_set_default_background(day_outline, libtcod.darker_yellow)
		libtcod.console_rect(day_outline, 0, 8, 24, 1, True, libtcod.BKGND_SET)
		days = campaign.combat_calendar.index(campaign.today) + 1
		total_days = len(campaign.combat_calendar)
		x = int(24.0 * float(days) / float(total_days))
		libtcod.console_set_default_background(day_outline, libtcod.dark_yellow)
		libtcod.console_rect(day_outline, 0, 8, x, 1, True, libtcod.BKGND_SET)
		libtcod.console_set_default_background(day_outline, libtcod.black)
		libtcod.console_set_default_foreground(day_outline, libtcod.white)
		text = 'Day ' + str(days) + '/' + str(total_days)
		libtcod.console_print_ex(day_outline, 12, 8, libtcod.BKGND_NONE, libtcod.CENTER,
			text)
		
		if 'refitting' not in campaign.current_week:
			libtcod.console_set_default_foreground(day_outline, libtcod.light_grey)
			libtcod.console_print(day_outline, 1, 30, 'Start of Day:')
			libtcod.console_print(day_outline, 3, 31, 'End of Day:')
			
			libtcod.console_set_default_foreground(day_outline, libtcod.white)
			libtcod.console_print_ex(day_outline, 19, 30, libtcod.BKGND_NONE, libtcod.RIGHT,
				str(campaign_day.start_of_day['hour']).zfill(2) + ':' + str(campaign_day.start_of_day['minute']).zfill(2))
			libtcod.console_print_ex(day_outline, 19, 31, libtcod.BKGND_NONE, libtcod.RIGHT,
				str(campaign_day.end_of_day['hour']).zfill(2) + ':' + str(campaign_day.end_of_day['minute']).zfill(2))
	
		libtcod.console_set_default_foreground(day_outline, libtcod.white)
		libtcod.console_print(day_outline, 2, 34, 'Campaign VP: ' + str(campaign.player_vp))
	
	
	# update the command menu for the campaign calendar interface, 24x21
	def UpdateCalendarCmdCon(self):
		libtcod.console_clear(calendar_cmd_con)
		
		libtcod.console_set_default_foreground(calendar_cmd_con, TITLE_COL)
		libtcod.console_print(calendar_cmd_con, 6, 0, 'Command Menu')
		libtcod.console_set_default_foreground(calendar_cmd_con, libtcod.light_grey)
		libtcod.console_print(calendar_cmd_con, 0, 19, 'Use highlighted keys')
		libtcod.console_print(calendar_cmd_con, 0, 20, 'to navigate interface')
		
		x = 0
		for (text, num, col) in CC_MENU_LIST:
			libtcod.console_set_default_background(calendar_cmd_con, col)
			libtcod.console_rect(calendar_cmd_con, x, 1, 2, 1, True, libtcod.BKGND_SET)
			
			# display menu activation key, use darker bg colour for visibility
			col2 = col * libtcod.light_grey
			libtcod.console_put_char_ex(calendar_cmd_con, x, 1, str(num), ACTION_KEY_COL, col2)
			x += 2
			
			# display menu text if active
			if self.active_calendar_menu == num:
				libtcod.console_rect(calendar_cmd_con, x, 1, len(text)+2, 1,
					True, libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(calendar_cmd_con, libtcod.white)
				libtcod.console_print(calendar_cmd_con, x, 1, text)
				x += len(text) + 2
		
		# fill in rest of menu line with final colour
		libtcod.console_rect(calendar_cmd_con, x, 1, 25-x, 1, True, libtcod.BKGND_SET)
		libtcod.console_set_default_background(calendar_cmd_con, libtcod.black)
		
		# proceed - start day or continue to next day, summary of expected day
		if self.active_calendar_menu == 1:
			
			libtcod.console_set_default_foreground(calendar_cmd_con, ACTION_KEY_COL)
			if DEBUG:
				libtcod.console_print(calendar_cmd_con, 2, 9, 'S')
			libtcod.console_print(calendar_cmd_con, 2, 10, 'Tab')
			
			libtcod.console_set_default_foreground(calendar_cmd_con, libtcod.light_grey)
			if DEBUG:
				libtcod.console_print(calendar_cmd_con, 9, 9, 'Skip Day')
			
			# day has not yet started
			if not campaign_day.started:
				libtcod.console_print(calendar_cmd_con, 9, 10, 'Start Day')
			
			# day has finished
			else:
				libtcod.console_print(calendar_cmd_con, 9, 10, 'Next Day')
		
		# crew and tank menu
		elif self.active_calendar_menu == 2:
			
			libtcod.console_set_default_foreground(calendar_cmd_con, ACTION_KEY_COL)
			libtcod.console_print(calendar_cmd_con, 2, 7, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(calendar_cmd_con, 2, 8, EnKey('p').upper())
			libtcod.console_print(calendar_cmd_con, 2, 9, EnKey('e').upper())
			libtcod.console_print(calendar_cmd_con, 2, 10, EnKey('t').upper())
			
			libtcod.console_set_default_foreground(calendar_cmd_con, libtcod.light_grey)
			libtcod.console_print(calendar_cmd_con, 6, 7, 'Select Position')
			libtcod.console_print(calendar_cmd_con, 6, 8, 'Swap Position')
			libtcod.console_print(calendar_cmd_con, 6, 9, 'Crewman Menu')
			libtcod.console_print(calendar_cmd_con, 6, 10, 'Tank Name')
		
		# day log
		elif self.active_calendar_menu == 3:
			
			libtcod.console_set_default_foreground(calendar_cmd_con, ACTION_KEY_COL)
			libtcod.console_print(calendar_cmd_con, 2, 9, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(calendar_cmd_con, 2, 10, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_set_default_foreground(calendar_cmd_con, libtcod.light_grey)
			libtcod.console_print(calendar_cmd_con, 7, 9, 'Scroll Log')
			libtcod.console_print(calendar_cmd_con, 7, 10, 'Select Day')
		
		# field hospital
		elif self.active_calendar_menu == 4:
			
			# no possible commands
			if len(self.hospital) == 0: return
			
			libtcod.console_set_default_foreground(calendar_cmd_con, ACTION_KEY_COL)
			libtcod.console_print(calendar_cmd_con, 2, 9, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(calendar_cmd_con, 2, 10, EnKey('e').upper())
			libtcod.console_set_default_foreground(calendar_cmd_con, libtcod.light_grey)
			libtcod.console_print(calendar_cmd_con, 7, 9, 'Select Crewman')
			libtcod.console_print(calendar_cmd_con, 7, 10, 'Crewman Menu')
	
	
	# update the main calendar display panel 63x58
	def UpdateCCMainPanel(self, selected_position, selected_hospital_crewman):
		libtcod.console_clear(calendar_main_panel)
		
		# proceed menu - show summary of expected day
		if self.active_calendar_menu == 1:
			
			# sunrise gradient
			for y in range(0, 58):
				if campaign_day.ended:
					col = libtcod.Color(0, int(50 * (y / WINDOW_HEIGHT)), int(210 * (y / WINDOW_HEIGHT)))
				else:
					col = libtcod.Color(int(210 * (y / WINDOW_HEIGHT)), int(50 * (y / WINDOW_HEIGHT)), 0)
				libtcod.console_set_default_background(calendar_main_panel, col)
				libtcod.console_rect(calendar_main_panel, 0, y, 63, 1, True, libtcod.BKGND_SET)
			
			x = 17
			y = 13
			
			# box and frame
			libtcod.console_set_default_background(calendar_main_panel, libtcod.black)
			libtcod.console_rect(calendar_main_panel, 15, 8, 36, 41, False, libtcod.BKGND_SET)
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.dark_yellow)
			DrawFrame(calendar_main_panel, 15, 8, 36, 41)
			
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.white)
			# refitting week
			if 'refitting' in campaign.current_week:
				libtcod.console_print_ex(calendar_main_panel, 33, 10, libtcod.BKGND_NONE,
					libtcod.CENTER, 'Refitting')
			else:
			
				# week title - max 4 lines
				lines = wrap(campaign.current_week['week_title'], 20)
				y = 10
				for line in lines[:4]:
					PrintExtended(calendar_main_panel, 33, y, line, center=True)
					y += 1
			
			# check for week description and display wrapped text if any
			if 'week_description' in campaign.current_week:
				libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_grey)
				
				text = campaign.current_week['week_description']
				lines = wrap(text, 32)
				y = 16
				for line in lines[:10]:
					PrintExtended(calendar_main_panel, 17, y, line)
					y += 1
			
			# day mission type and description
			libtcod.console_set_default_background(calendar_main_panel, libtcod.darker_blue)
			libtcod.console_rect(calendar_main_panel, 19, 28, 30, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(calendar_main_panel, libtcod.black)
			
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_yellow)
			
			# day has finished
			if campaign_day.ended:
				libtcod.console_print_ex(calendar_main_panel, 33, 29, libtcod.BKGND_NONE,
					libtcod.CENTER,	"Day has Ended")
				return
			
			libtcod.console_print_ex(calendar_main_panel, 33, 29, libtcod.BKGND_NONE,
				libtcod.CENTER,	"Today's Mission")
			
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_blue)
			libtcod.console_print_ex(calendar_main_panel, 33, 33, libtcod.BKGND_NONE,
				libtcod.CENTER,	campaign_day.mission)
			
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_grey)
			lines = wrap(MISSION_DESC[campaign_day.mission], 32)
			y = 35
			for line in lines[:5]:
				libtcod.console_print(calendar_main_panel, 17, y, line)
				y+=1
			
			# player support
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.white)
			libtcod.console_print(calendar_main_panel, 21, 44, 'Air Support:')
			libtcod.console_print(calendar_main_panel, 21, 45, 'Artillery Support:')
			libtcod.console_print(calendar_main_panel, 21, 46, 'Unit Support:')
			
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_grey)
			if 'air_support_level' not in campaign.current_week:
				text = 'None'
			else:
				text = str(campaign.current_week['air_support_level'])
			libtcod.console_print(calendar_main_panel, 41, 44, text)
			if 'arty_support_level' not in campaign.current_week:
				text = 'None'
			else:
				text = str(campaign.current_week['arty_support_level'])
			libtcod.console_print(calendar_main_panel, 41, 45, text)
			if 'unit_support_level' not in campaign.current_week:
				text = 'None'
			else:
				text = str(campaign.current_week['unit_support_level'])
			libtcod.console_print(calendar_main_panel, 41, 46, text)
		
		# crew and tank menu
		elif self.active_calendar_menu == 2:
			
			# frame
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.dark_blue)
			DrawFrame(calendar_main_panel, 1, 8, 61, 45)
			
			# show list of crewmen
			libtcod.console_set_default_foreground(calendar_main_panel, TITLE_COL)
			libtcod.console_print(calendar_main_panel, 3, 10, 'Tank Positions and Crewmen')
			libtcod.console_print(calendar_main_panel, 41, 10, 'Player Tank')
			
			DisplayCrew(campaign.player_unit, calendar_main_panel, 4, 13, selected_position)
			
			# show info on player tank if still alive
			if campaign.player_unit.alive:
				DisplayUnitInfo(calendar_main_panel, 34, 13, campaign.player_unit.unit_id,
					campaign.player_unit, status=False)
				
				# description of tank
				text = ''
				for t in campaign.player_unit.GetStat('description'):
					text += t
				lines = wrap(text, 27)
				y = 29
				libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_grey)
				for line in lines[:20]:
					libtcod.console_print(calendar_main_panel, 33, y, line)
					y+=1
			
			else:
				libtcod.console_print(calendar_main_panel, 41, 13, 'None')
		
		# journal menu
		elif self.active_calendar_menu == 3:
			
			# if no day selected yet, select the first one
			if self.active_journal_day is None:
				for (k, v) in self.journal.items():
					self.active_journal_day = k
					break
			
			libtcod.console_set_default_background(calendar_main_panel, libtcod.darker_grey)
			libtcod.console_rect(calendar_main_panel, 15, 1, 32, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(calendar_main_panel, libtcod.black)
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.white)
			libtcod.console_print_ex(calendar_main_panel, 31, 2, libtcod.BKGND_NONE,
				libtcod.CENTER, GetDateText(self.active_journal_day))
			
			# display journal entries from current scroll position
			n = 0
			y = 6
			for (time, text) in self.journal[self.active_journal_day]:
				
				# skip this entry if we're not yet at the current scroll location
				if self.journal_scroll_line > n:
					n += 1
					continue
				
				# stop displaying if we're near the bottom of the console
				if y >= 56:
					break
				
				libtcod.console_set_default_foreground(calendar_main_panel, libtcod.white)
				libtcod.console_print(calendar_main_panel, 2, y, time)
				
				libtcod.console_set_default_foreground(calendar_main_panel, libtcod.light_grey)
				lines = wrap(text, 44, subsequent_indent=' ')
				for line in lines:
					libtcod.console_print(calendar_main_panel, 11, y, line)
					y += 1
		
		# field hospital menu
		elif self.active_calendar_menu == 4:
			
			libtcod.console_set_default_background(calendar_main_panel, libtcod.Color(200, 0, 0))
			libtcod.console_rect(calendar_main_panel, 15, 1, 32, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(calendar_main_panel, libtcod.black)
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.white)
			libtcod.console_print_ex(calendar_main_panel, 31, 2, libtcod.BKGND_NONE,
				libtcod.CENTER, '+ Field Hospital +')
			
			libtcod.console_print(calendar_main_panel, 2, 10, 'Crewman')
			libtcod.console_print_ex(calendar_main_panel, 58, 10, libtcod.BKGND_NONE,
				libtcod.RIGHT, 'Days until Recovery')
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.grey)
			for x in range(2, 59):
				libtcod.console_put_char(calendar_main_panel, x, 11, '-')
			
			# list any crewmen currently in the field hospital
			y = 13
			
			if len(campaign.hospital) == 0:
				libtcod.console_set_default_foreground(calendar_main_panel, libtcod.grey)
				libtcod.console_print(calendar_main_panel, 2, y, 'No crewmen currently in hospital')
				return
			
			libtcod.console_set_default_foreground(calendar_main_panel, libtcod.lighter_grey)
			
			# determine which crewman in the list to start on
			if selected_hospital_crewman <= 4:
				n = 0
			else:
				n = selected_hospital_crewman - 4
			for crewman in campaign.hospital[n:]:
				
				if n == selected_hospital_crewman:
					libtcod.console_set_default_background(calendar_main_panel, libtcod.darker_blue)
					libtcod.console_rect(calendar_main_panel, 2, y, 57, 2, False, libtcod.BKGND_SET)
					libtcod.console_set_default_background(calendar_main_panel, libtcod.black)
				
				PrintExtended(calendar_main_panel, 2, y, crewman.GetName(), first_initial=True)
				
				(days_min, days_max) = crewman.field_hospital
				if days_min == 0:
					text = 'Maximum '
				else:
					text = str(days_min) + '-'
				text += str(days_max)
				libtcod.console_print_ex(calendar_main_panel, 50, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, text)
				y += 4
				n += 1
				
				if y >= 51:
					break
			
			
	# update the display of the campaign calendar interface
	def UpdateCCDisplay(self):
		libtcod.console_blit(calendar_bkg, 0, 0, 0, 0, con, 0, 0)		# background frame
		libtcod.console_blit(day_outline, 0, 0, 0, 0, con, 1, 1)		# summary of current day
		libtcod.console_blit(calendar_cmd_con, 0, 0, 0, 0, con, 1, 38)		# command menu
		libtcod.console_blit(calendar_main_panel, 0, 0, 0, 0, con, 26, 1)	# main panel
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
	
	# main campaign calendar loop
	def DoCampaignCalendarLoop(self):
		
		def ProceedToNextDay():
			
			self.journal_scroll_line = 0
			
			# record what will soon be the previous day
			previous_day = self.today
			
			# set today to next day in calendar
			self.today = self.combat_calendar[day_index+1]
			
			# re-calculate crew ages
			for position in campaign.player_unit.positions_list:
				if position.crewman is None: continue
				if not position.crewman.alive: continue
				position.crewman.CalculateAge()
			
			# check for start of new week
			self.CheckForNewWeek()
			
			# subtract days elapsed from days remaining from any crewmen in field hospital
			if len(self.hospital) == 0: return
			
			(year1, month1, day1) = previous_day.split('.')
			(year2, month2, day2) = self.today.split('.')
			a = datetime(int(year1), int(month1), int(day1), 0, 0, 0)
			b = datetime(int(year2), int(month2), int(day2), 0, 0, 0)
			days_past = (b-a).days
			
			# iterate in reverse order since we may remove some crewmen from the list
			returning_crewmen = []
			for crewman in reversed(self.hospital):
				
				(min_days, max_days) = crewman.field_hospital
				if min_days > 0:
					min_days -= days_past
					if min_days < 0:
						min_days = 0
				
				if max_days > 0:
					max_days -= days_past
					if max_days < 0:
						max_days = 0
				
				# crewman with 0 max days left are automatically returned to action
				if max_days == 0:
					crewman.field_hospital = None
					returning_crewmen.append(crewman)
					self.hospital.remove(crewman)
					continue
				
				# roll for return to action based on how many days elapsed
				if min_days <= 0:
					if GetPercentileRoll() <= days_past * FIELD_HOSPITAL_RELEASE_CHANCE:
						crewman.field_hospital = None
						returning_crewmen.append(crewman)
						self.hospital.remove(crewman)
						continue
				
				# crewman remains in hospital, update days remaining
				crewman.field_hospital = (min_days, max_days)
			
			# sort remaining crewmen in hospital
			self.hospital.sort(key=lambda x: x.field_hospital)
			
			# give player option to assign returning crew
			if len(returning_crewmen) > 0:
				if len(returning_crewmen) == 1:
					text = 'One crewman has'
				else:
					text = 'Crewmen have'
				text += ' returned from their stay in the field hospital and may be re-assigned to your tank.'
				ShowNotification(text)
				self.ShowAssignPositionsMenu(unassigned_crewmen = returning_crewmen)
		
		
		# consoles for campaign calendar interface
		global calendar_bkg, day_outline, calendar_cmd_con, calendar_main_panel
		global campaign_day
		
		# selected crew position and selected field hospital crewman if any
		selected_position = 0
		selected_hospital_crewman = 0
		
		# create consoles
		calendar_bkg = LoadXP('calendar_bkg.xp')
		day_outline = NewConsole(24, 36, libtcod.black, libtcod.white)
		calendar_cmd_con = NewConsole(24, 21, libtcod.black, libtcod.white)
		calendar_main_panel = NewConsole(63, 58, libtcod.black, libtcod.white)
		
		# generate consoles for the first time
		self.UpdateDayOutlineCon()
		self.UpdateCalendarCmdCon()
		self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
		
		if not (campaign_day.started and not campaign_day.ended):
			self.UpdateCCDisplay()
		
		
		exit_loop = False
		while not exit_loop:
			
			# if we've initiated a campaign day or are resuming a saved game with a
			# campaign day running, go into the campaign day loop now
			# also check to see if we're still in a scenario within the campaign day
			if campaign_day.started and (not campaign_day.ended or scenario is not None):
							
				campaign_day.DoCampaignDayLoop()
				
				# player was taken out
				if campaign.ended:
					self.LogDayRecords()
					self.DoEnd()
					exit_loop = True
					continue
				
				if session.exiting:
					exit_loop = True
					continue
				
				# do end-of-campaign day stuff
				self.ShowEndOfDay()
				
				# redraw the screen
				self.UpdateDayOutlineCon()
				self.UpdateCalendarCmdCon()
				self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
				self.UpdateCCDisplay()
				
			libtcod.console_flush()
			keypress = GetInputEvent()	
			if not keypress: continue
			
			# game menu
			if key.vk == libtcod.KEY_ESCAPE:
				ShowGameMenu()
				if session.exiting:
					exit_loop = True
					continue
			
			# debug menu
			elif key.vk == libtcod.KEY_F2:
				if not DEBUG: continue
				ShowDebugMenu()
				continue
			
			# mapped key commands
			key_char = DeKey(chr(key.c).lower())
			
			# switch active menu
			if key_char in ['1', '2', '3', '4']:
				if self.active_calendar_menu != int(key_char):
					self.active_calendar_menu = int(key_char)
					PlaySoundFor(None, 'tab_select')
					self.UpdateCalendarCmdCon()
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
				continue
			
			# proceed menu active
			if self.active_calendar_menu == 1:
				
				# debug only - skip day
				if chr(key.c).lower() == 's':
					if not DEBUG: continue
					campaign_day.started = True
					campaign_day.ended = True
					self.UpdateCalendarCmdCon()
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
				
				# start or proceed to next day
				if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				
					# start new day
					if not campaign_day.ended:
						campaign_day.AmmoReloadMenu()	# allow player to load ammo
						campaign_day.started = True
						continue			# continue in loop to go into campaign day layer
				
					# proceed to next day or end campaign
					else:
						
						# add day records to campaign log
						self.LogDayRecords()
						
						# if Player Commander is active and the player character has just been sent
						# to the field hospital, need to jump ahead in calendar, choose a new tank, generate a new crew
						commander_in_a_coma = False
						for crewman in self.hospital:
							if not crewman.is_player_commander: continue
							commander_in_a_coma = True
							
							# clear all other crewmen from current tank
							for position in campaign.player_unit.positions_list:
								position.crewman = None
							
							# calculate length of player commander field hospital stay
							# returns True if Commander stays in hospital past end of campaign calendar
							if self.CommanderInAComa(crewman):
								
								# check for completion of a full-length campaign
								if len(campaign.combat_calendar) >= campaign.stats['combat_days']:
									session.ModifySteamStat('completed_campaigns', 1)
								
								# NEW: remove commander from field hospital in case player wants to continue
								# into another campaign
								self.hospital.remove(crewman)
								self.hospital.sort(key=lambda x: x.field_hospital)
								crewman.field_hospital = None
								
								self.DoEnd()
								exit_loop = True
							break
						
						# if commander just spent time in the field hospital, remove anyone else who was in the hospital
						if commander_in_a_coma:
							self.hospital = []
						
						if exit_loop:
							continue
						
						# only do the following if commander did not just return from field hospital
						if not commander_in_a_coma:
							
							# check for end of campaign as a result of reaching end of calendar
							day_index = self.combat_calendar.index(self.today)
							if day_index == len(campaign.combat_calendar) - 1:
								
								# check for completion of a full-length campaign
								if len(campaign.combat_calendar) >= campaign.stats['combat_days']:
									session.ModifySteamStat('completed_campaigns', 1)
								
								self.DoEnd()
								exit_loop = True
								continue
							
							# if player tank was destroyed, allow player to choose a new one
							if not self.player_unit.alive:
								self.ReplacePlayerTank()
							else:
								# fix any broken weapons on player tank
								for weapon in self.player_unit.weapon_list:
									if weapon.broken:
										ShowMessage('Your ' + weapon.GetStat('name') + ' is repaired.')
										weapon.broken = False
							
							# start new calendar day, may also trigger return of field hospital crewmen
							ProceedToNextDay()
							
							# check for crew replacement if there remain any empty positions on the tank
							campaign_day.DoCrewReplacementCheck(self.player_unit)
						
						# handle refitting weeks here
						if 'refitting' in self.current_week:
							
							# if Player Commander just returned from the field hospital, no need
							# to give them another tank selection, can skip the refitting day
							if not commander_in_a_coma:
							
								self.ShowStartOfDay()
								
								# allow player to change tanks
								if ShowNotification('Your battlegroup has been recalled for refitting. Do you want to request a new tank?', confirm=True):
									self.ReplacePlayerTank()
							
							day_index = self.combat_calendar.index(self.today)
							
							# proceed to next combat day
							ProceedToNextDay()
						
						
						# create a new campaign day
						campaign_day = CampaignDay()
						for (hx, hy) in CAMPAIGN_DAY_HEXES:
							campaign_day.map_hexes[(hx,hy)].CalcCaptureVP()
						campaign_day.GenerateRoads()
						campaign_day.GenerateRivers()
						
						self.ShowStartOfDay()
						campaign.AddJournal('Start of day')
						
						# set currently displayed journal entry to the new day
						self.active_journal_day = self.today
						
						# make sure currently selected position is still ok for a new tank
						if selected_position >= len(campaign.player_unit.positions_list):
							selected_position = 0
						
						SaveGame()
						BackupGame()
						
						# redraw the screen
						self.UpdateDayOutlineCon()
						self.UpdateCalendarCmdCon()
						self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
						self.UpdateCCDisplay()
						continue
					
			# crew menu active
			elif self.active_calendar_menu == 2:
				
				# select different crew position
				# allow arrow key inputs too
				if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					if key_char == 'w' or key.vk == libtcod.KEY_UP:
						selected_position -= 1
						if selected_position < 0:
							selected_position = len(campaign.player_unit.positions_list) - 1
				
					else:
						selected_position += 1
						if selected_position == len(campaign.player_unit.positions_list):
							selected_position = 0
					PlaySoundFor(None, 'menu_select')
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
				
				# open crewman menu
				elif key_char == 'e':
					crewman = campaign.player_unit.positions_list[selected_position].crewman
					if crewman is None: continue
					crewman.ShowCrewmanMenu()
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
				
				# swap position menu
				elif key_char == 'p':
					ShowSwapPositionMenu()
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
				
				# set tank nickname
				elif key_char == 't':
					player_tank_name = ShowTextInputMenu('Enter a name for your tank', '', MAX_TANK_NAME_LENGTH, [])
					if player_tank_name != '':
						campaign.player_unit.unit_name = player_tank_name
					self.UpdateCalendarCmdCon()
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
			
			# journal menu active
			elif self.active_calendar_menu == 3:
				
				# cycle active journal day displayed
				if key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
					
					keys_list = list(self.journal.keys())
					i = keys_list.index(self.active_journal_day)
					
					if key_char == 'a' or key.vk == libtcod.KEY_LEFT:
						if i == 0:
							i = len(keys_list) - 1
						else:
							i -= 1
					else:
						if i == len(keys_list) - 1:
							i = 0
						else:
							i += 1
					self.active_journal_day = keys_list[i]
					self.journal_scroll_line = 0
					PlaySoundFor(None, 'menu_select')
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
				
				# shift display scroll
				elif key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					
					if key_char == 's' or key.vk == libtcod.KEY_DOWN:
						self.journal_scroll_line += 1
					else:
						self.journal_scroll_line -= 1
					
					if self.journal_scroll_line < 0:
						self.journal_scroll_line = 0
					else:
						journal_length = len(self.journal[self.active_journal_day])
						if self.journal_scroll_line > journal_length - 50:
							self.journal_scroll_line = journal_length - 50
					PlaySoundFor(None, 'menu_select')
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
			
			# field hospital menu active
			elif self.active_calendar_menu == 4:
				
				# no possible commands
				if len(self.hospital) == 0: continue
				
				# select different crewman
				if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					if key_char == 'w' or key.vk == libtcod.KEY_UP:
						selected_hospital_crewman -= 1
						if selected_hospital_crewman < 0:
							selected_hospital_crewman = len(campaign.hospital) - 1
				
					else:
						selected_hospital_crewman += 1
						if selected_hospital_crewman == len(campaign.hospital):
							selected_hospital_crewman = 0
					PlaySoundFor(None, 'menu_select')
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue
				
				# open crewman menu
				elif key_char == 'e':
					crewman = campaign.hospital[selected_hospital_crewman]
					crewman.ShowCrewmanMenu()
					self.UpdateCCMainPanel(selected_position, selected_hospital_crewman)
					self.UpdateCCDisplay()
					continue




# Zone Hex: a hex on the campaign day map, each representing a map of scenario hexes
class CDMapHex:
	def __init__(self, hx, hy, mission):
		self.hx = hx
		self.hy = hy
		self.terrain_type = ''		# placeholder for terrain type in this zone
		self.console_seed = libtcod.random_get_int(0, 1, 128)	# seed for console image generation
		self.objective = None		# pointer to objective info if any
		self.landmines = False		# landmines are present in this zone
		
		# road links in 6 directions: false if dirt road, true if stone
		self.road_links = [None,None,None,None,None,None]
		self.rivers = []		# river edges
		self.bridges = []		# bridged edges
		
		self.controlled_by = 1		# which player side currently controls this zone
		self.enemy_strength = 0		# current enemy strength in zone
		self.known_to_player = False	# player knows enemy strength and organization in this zone
		self.enemy_units = []		# list of enemy unit_ids that are present in this zone
		self.enemy_desc = ''		# text description of expected enemy presence here
		
		# VP value if captured by player
		self.vp_value = 0
		
		# Pathfinding stuff
		self.parent = None
		self.g = 0
		self.h = 0
		self.f = 0
		
		self.Reset()
	
	
	# reset zone stats
	def Reset(self):
		self.coordinate = (chr(self.hy+65) + str(5 + int(self.hx - (self.hy - self.hy&1) / 2)))


	# (re)generate enemy strength level, and list of enemy units in this zone
	# if unit_list is not none, use that instead of generating one
	def GenerateStrengthAndUnits(self, mission, skip_strength=False, unit_list=None, player_attacked=False):
		
		self.known_to_player = False
		
		# impassible zone
		if 'impassible' in CD_TERRAIN_TYPES[self.terrain_type]:
			self.enemy_strength = 0
			self.enemy_units = []
			return
		
		if not player_attacked:
		
			# friendly-controlled zone, not North Africa
			if campaign.stats['region'] != 'North Africa' and self.controlled_by == 0:
				self.enemy_strength = 0
				self.enemy_units = []
				return
			
			# friendly-controlled zone, North Africa, and a place of interest
			if campaign.stats['region'] == 'North Africa' and self.controlled_by == 0:
				if self.terrain_type in DESERT_CAPTURE_ZONES:
					self.enemy_strength = 0
					self.enemy_units = []
					return
		
		if not skip_strength:
			if 'average_resistance' in campaign.current_week:
				avg_strength = campaign.current_week['average_resistance']
			else:
				avg_strength = 5
			
			# apply mission modifiers
			if mission == 'Patrol':
				avg_strength -= 2
			elif mission == 'Advance':
				avg_strength -= 1
			elif mission in ['Battle', 'Fighting Withdrawal']:
				avg_strength += 2
			elif mission == 'Counterattack':
				avg_strength += 1
			
			if avg_strength < 1:
				avg_strength = 1
			
			# roll for actual strength level
			self.enemy_strength = 0
			for i in range(2):
				self.enemy_strength += libtcod.random_get_int(0, 0, avg_strength)
			self.enemy_strength = int(self.enemy_strength / 2) + 1
			
			# modify for forces operating behind friendly lines
			if self.controlled_by == 0:
				self.enemy_strength = int(self.enemy_strength / 3)
			
			if self.enemy_strength < 1:
				self.enemy_strength = 1
			elif self.enemy_strength > 10:
				self.enemy_strength = 10
		
		# clear any existing units in the list
		self.enemy_units = []
		
		# unit list has been provided
		if unit_list is not None:
			for (nation, unit_id) in unit_list:
				self.enemy_units.append((nation, unit_id))
		
		else:
		
			# choose a default enemy nation for these units; other nations are possible
			# but most will be this one
			default_enemy_nation = choice(campaign.current_week['enemy_nations'])
			
			num_units = 4
			for i in range(3):
				roll = libtcod.random_get_int(0, 0, 5) + libtcod.random_get_int(0, 0, 5)
				if roll >= self.enemy_strength:
					num_units -= 1
			
			enemy_units_remaining = num_units
			
			enemy_unit_classes = list(campaign.stats['enemy_unit_class_odds'].items())
			enemy_class_dict = {}
			
			while enemy_units_remaining > 0:
				
				# choose enemy nation for this unit - not always default
				if GetPercentileRoll() <= 85.0:
					enemy_nation = default_enemy_nation
				else:
					enemy_nation = choice(campaign.current_week['enemy_nations'])
				
				unit_type_list = campaign.stats['enemy_unit_list'][enemy_nation]
				
				# choose a random unit class
				unit_class = None
				while unit_class is None:
					if libtcod.console_is_window_closed(): sys.exit()
					k, value = choice(enemy_unit_classes)
					
					# special - some classes less likely if player is being attacked
					if player_attacked:
						if k == 'Armoured Train Car':
							if GetPercentileRoll() <= 85.0:
								continue
						if k in ['Anti-Tank Gun', 'Artillery Gun', 'Anti-Aircraft Gun']:
							if GetPercentileRoll() <= 75.0:
								continue
					
					if libtcod.random_get_int(0, 1, 100) <= value:
						unit_class = k
				
				# if unit type for this class has already been set, use that one instead
				# default nation only
				if enemy_nation == default_enemy_nation and unit_class in enemy_class_dict:
					self.enemy_units.append((enemy_nation, enemy_class_dict[unit_class]))
					enemy_units_remaining -= 1
					continue
				
				# choose a random unit type within this class
				type_list = []
				for unit_id in unit_type_list:
					# unrecognized unit id - maybe not added yet?
					if unit_id not in session.unit_types: continue
					# not the right class
					if session.unit_types[unit_id]['class'] != unit_class: continue
					type_list.append(unit_id)
				
				# no unit types of the required class found
				if len(type_list) == 0:
					continue
				
				# select unit type: run through shuffled list and roll against rarity if any
				shuffle(type_list)
				
				selected_unit_id = None
				for unit_id in type_list:
					
					# campaign option active
					if campaign.options['ahistorical']:
						selected_unit_id = unit_id
						break
					
					# check for campaign-defined dates for this unit type
					# and skip if too early to spawn
					if 'enemy_unit_dates' in campaign.stats:
						if unit_id in campaign.stats['enemy_unit_dates']:
							if campaign.stats['enemy_unit_dates'][unit_id] > campaign.today:
								continue
					
					# do captured unit check; captured units are less likely to be spawned
					if 'enemy_captured_units' in campaign.stats:
						if unit_id in campaign.stats['enemy_captured_units']:
							if GetPercentileRoll() > 25.0:
								continue
					
					# roll for rarity
					if campaign.DoRarityCheck(unit_id):
						selected_unit_id = unit_id
						break
				
				# no suitable unit type found, roll for a new unit class
				if selected_unit_id is None: continue
				
				# add this unit_id to the class dict
				enemy_class_dict[unit_class] = selected_unit_id
				
				# add the final selected unit id to list
				self.enemy_units.append((enemy_nation, selected_unit_id))
				
				# if enemy was a Support Team, chance that an extra unit will be spawned as well
				if unit_class == 'Support Weapon Team':
					if libtcod.random_get_int(0, 1, 6) == 1:
						continue
				enemy_units_remaining -= 1
		
		# run through list of enemy units and generate a text description of enemy presence
		# may be inaccurate, but will be accurate if player saw these units before
		
		SIMILAR_CLASSES = [
			["Infantry Squad", "Support Weapon Team", "Cavalry Squad"],
			["Tankette", "Light Tank", "Armoured Car", "Truck", "APC", "Self-Propelled AA Gun"],
			["Medium Tank", "Assault Gun", "Tank Destroyer", "Heavy Tank"],
			["Anti-Tank Gun", "Artillery Gun", "Anti-Aircraft Gun"]
		]
		
		possible_classes = list(campaign.stats['enemy_unit_class_odds'])
		
		self.enemy_desc = ''
		
		chance1 = 3.0
		chance2 = 25.0
		chance3 = 10.0
		if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Improved Recon'):
			chance1 = 1.5
			chance2 = 15.0
			chance3 = 5.0
		
		for (nation, unit_id) in self.enemy_units:
			unit_class = session.unit_types[unit_id]['class']
			
			# chance that this one will not be included
			if len(self.enemy_desc) > 0:
				if GetPercentileRoll() <= chance1 and unit_list is None:
					continue
			
			if GetPercentileRoll() <= chance2 and unit_list is None:
				for class_list in SIMILAR_CLASSES:
					if unit_class not in class_list: continue
					for wrong_class in sample(class_list, len(class_list)):
						if wrong_class == unit_class: continue
						if wrong_class not in possible_classes: continue
						unit_class = wrong_class
						break
			
			if len(self.enemy_desc) > 0:
				self.enemy_desc += ', '
			self.enemy_desc += unit_class
		
		# chance that an extra one will be included
		if GetPercentileRoll() <= chance3 and unit_list is None:
			unit_class = choice(list(campaign.stats['enemy_unit_class_odds']))
			if len(self.enemy_desc) > 0:
				self.enemy_desc += ', '
			self.enemy_desc += unit_class
	
	
	# (re)calculate VP value if captured by player
	def CalcCaptureVP(self):
		
		(hx, hy) = campaign_day.player_unit_location
		
		if campaign.stats['region'] == 'North Africa':
			if self.terrain_type not in DESERT_CAPTURE_ZONES:
				self.vp_value = 0
				return
		
		if campaign_day.mission == 'Spearhead':
			self.vp_value = int(((9 - self.hy) + (campaign_day.maps_traversed * 8)) / SPEARHEAD_HEXROW_LEVELS)
			if self.vp_value < 1:
				self.vp_value = 1
		else:
		
			if self.terrain_type in ['Forest', 'Hills', 'Villages']:
				self.vp_value = 2
			else:
				self.vp_value = 1
			
			if campaign_day.mission == 'Advance':
				self.vp_value += 1
			
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Defensive Strategy'):
				self.vp_value -= 1
		
		if campaign.stats['region'] == 'North Africa':
			self.vp_value = self.vp_value * DESERT_CAPTURE_MULTIPLIER
		
		if self.vp_value < 0:
			self.vp_value = 0
	
	
	# reset pathfinding info for this zone
	def ClearPathInfo(self):
		self.parent = None
		self.g = 0
		self.h = 0
		self.f = 0
		
	
	# set control of this hex by the given player
	# also handles successful defense of a friendly zone
	# if no_vp is True, player doesn't receive VP or credit for this capture
	def CaptureMe(self, player_num, no_vp=False, no_generation=False):
		
		# already held by player
		if self.controlled_by == 0 and player_num == 0:
			no_vp = True
		
		# captured by enemy
		if player_num == 1:
			self.controlled_by = player_num
			# generate new strength level and enemy unit list
			if not no_generation:
				self.GenerateStrengthAndUnits(campaign_day.mission)
			return
		
		# captured by friendlies
		
		# check for VP reward
		if not no_vp:
			if self.controlled_by == 1:
				campaign_day.AddRecord('Map Areas Captured', 1)
				campaign.AddJournal('Captured an enemy-held zone')
				# award zone VP value and record steam stat
				campaign.AwardVP(self.vp_value)
				session.ModifySteamStat('zones_captured', 1)
		
		# set new zone control
		self.controlled_by = player_num
		
		# if it's the start of a campaign, set known to player
		if campaign_day is None:
			self.known_to_player = True
			return
		
		# if player is not present, set known to player
		(hx, hy) = campaign_day.player_unit_location
		if not (self.hx == hx and self.hy == hy):
			self.known_to_player = True
		
		# if north africa, some terrain types can still have enemies present
		if campaign.stats['region'] == 'North Africa' and self.terrain_type not in DESERT_CAPTURE_ZONES:
				
			# reduce enemy strength instead
			self.enemy_strength -= libtcod.random_get_int(0, 1, 5)
			if self.enemy_strength < 0:
				self.enemy_strength = 0
			
			# no strength remaining, clear any remaining units
			if self.enemy_strength == 0:
				self.enemy_units = []
			
			else:
			
				# regenerate unit classes present
				self.GenerateStrengthAndUnits(campaign_day.mission, skip_strength=True)
			
		else:
		
			# clear any enemy units
			self.enemy_strength = 0
			self.enemy_units = []
		
		# check for objective completion
		if self.objective is not None:
			if self.objective['type'] in ['Recon', 'Capture']:
				ShowMessage('You completed an objective!')
				campaign.AwardVP(self.objective['vp_reward'])
				self.objective = None


	# reveal any enemy activity in this and adjacent friendly-controlled zones
	def RevealAdjacentZones(self):
		#self.known_to_player = True
		for direction in range(6):
			(hx, hy) = campaign_day.GetAdjacentCDHex(self.hx, self.hy, direction)
			if (hx, hy) not in campaign_day.map_hexes: continue
			if campaign_day.map_hexes[(hx, hy)].controlled_by == 1: continue
			campaign_day.map_hexes[(hx, hy)].known_to_player = True
		campaign_day.UpdateCDUnitCon()
		campaign_day.UpdateCDHexInfoCon()
		campaign_day.UpdateCDDisplay()



# Campaign Day: represents one calendar day in a campaign with a 5x7 map of terrain hexes, each of
# which may spawn a Scenario
class CampaignDay:
	def __init__(self):
		
		# campaign day records
		self.records = {}
		for text in RECORD_LIST:
			self.records[text] = 0
		self.enemies_destroyed = {}
		
		self.started = False				# day is in progress
		self.ended = False				# day has been completed
		self.maps_traversed = 0				# how many map scrolls have taken place
		self.mission = ''
		self.GenerateMission()				# roll for type of mission today
		
		self.coastal_map = None
		if 'coastal_chance' in campaign.current_week:
			chance = float(campaign.current_week['coastal_chance'])
			if GetPercentileRoll() <= chance:
				self.coastal_map = choice(['left', 'right'])
		
		# check for setting a new world location
		if 'location' in campaign.current_week:
			location = campaign.current_week['location'].split(',')
			campaign.latitude = float(location[0])
			campaign.longitude = float(location[1])
		
		self.day_vp = 0					# counter of how many VP were earned today
		self.travel_time_spent = False
		
		# current weather conditions, will be set by GenerateWeather
		self.weather = {
			'Cloud Cover' : '',
			'Precipitation' : '',
			'Fog' : 0,			# not used yet
			'Sand' : 0,			# not used yet
			'Ground' : '',
			'Temperature' : ''
		}
		self.weather_update_clock = 0		# number of in-game minutes until next weather update
		self.GenerateWeather()
		
		self.fate_points = 3			# number of fate points protecting the player today
		if campaign.options['fate_points'] is False:
			self.fate_points = 0
		
		# set max number of units in player squad
		player_unit_class = campaign.player_unit.GetStat('class')
		if player_unit_class == 'Tankette':
			campaign.player_squad_max = 4
		elif player_unit_class in ['Light Tank', 'Tank Destroyer']:
			campaign.player_squad_max = 3
		elif player_unit_class in ['Medium Tank', 'Assault Gun', 'Heavy Tank']:
			campaign.player_squad_max = 2
		
		# spawn player squad units
		self.player_squad = []
		self.SpawnPlayerSquad()
		
		# smoke grenades and smoke mortar ammo
		self.smoke_grenades = 6
		self.smoke_mortar_rounds = 0
		if campaign.player_unit.GetStat('smoke_mortar') is not None:
			self.smoke_mortar_rounds = 10
		
		# calculate start and end of daylight, current moon phase
		self.CalcDaylight()
		
		# combat day length in minutes
		hours = self.end_of_day['hour'] - self.day_clock['hour']
		minutes = self.end_of_day['minute'] - self.day_clock['minute']
		if minutes < 0:
			hours -= 1
			minutes += 60
		self.day_length = minutes + (hours * 60)
		
		# current odds of a random event being triggered
		self.random_event_chance = BASE_CD_RANDOM_EVENT_CHANCE
		
		# generate campaign day map and terrain, placeholder for objectives
		self.map_hexes = {}
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			self.map_hexes[(hx,hy)] = CDMapHex(hx, hy, self.mission)
		self.GenerateCDMapTerrain()
		
		if self.mission == 'Fighting Withdrawal':
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				self.map_hexes[(hx, hy)].controlled_by = 0
		elif self.mission == 'Counterattack':
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				self.map_hexes[(hx, hy)].controlled_by = 0
			hy = 0
			hx1 = 0 - floor(hy / 2)
			for hx in range(hx1, hx1 + 5):
				if (hx, hy) not in self.map_hexes: continue
				self.map_hexes[(hx, hy)].controlled_by = 1
		elif self.mission == 'Battle':
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				self.map_hexes[(hx, hy)].controlled_by = 1
			for hy in range(6, 9):
				hx1 = 0 - floor(hy / 2)
				for hx in range(hx1, hx1 + 5):
					if (hx, hy) not in self.map_hexes: continue
					self.map_hexes[(hx, hy)].controlled_by = 0
		
		# impassible hexes are held by nobody
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx, hy)].terrain_type]:
				self.map_hexes[(hx, hy)].controlled_by = 2
		
		
		
		# dictionary of screen display locations on the display console
		self.cd_map_index = {}
		
		# list of screen display locations that contain a bridge
		self.cd_map_bridge_locations = []
		
		# set up initial player location
		if self.mission == 'Fighting Withdrawal':
			hx, hy = 2, 0				# top center of map
		elif self.mission == 'Battle':
			hx, hy = -1, 6				# lower center of map
		elif self.mission == 'Counterattack':
			hx, hy = 2, 1				# second row of map
		else:
			hx, hy = -2, 8				# bottom center of map
		
		# place player as close as possible to target location
		for hx_mod in [0, -1, 1, -2, 2, -3, 3, 4, -4]:
			# target is off map
			if (hx+hx_mod, hy) not in self.map_hexes: continue
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx+hx_mod, hy)].terrain_type]:
				continue
			self.player_unit_location = (hx+hx_mod, hy)
			break
		else:
			print('ERROR: Could not place player in a clear map hex')
			self.player_unit_location = (hx, hy)
		
		self.GenerateObjectives()
		self.GenerateMinefields()
		
		self.active_menu = 3				# number of currently active command menu
		self.selected_position = 0			# selected crew position in crew command menu tab
		self.selected_direction = None			# select direction for support, travel, etc.
		self.abandoned_tank = False			# set to true if player abandoned their tank that day
		self.player_withdrew = False			# set to true if player withdrew from the battle
		
		self.gun_list = []				# guns on player tank
		self.selected_gun = None			# selected gun for Resupply menu
		
		self.BuildPlayerGunList()
		
		self.air_support_level = 0.0
		if 'air_support_level' in campaign.current_week:
			self.air_support_level = campaign.current_week['air_support_level']
		
		self.arty_support_level = 0.0
		if 'arty_support_level' in campaign.current_week:
			self.arty_support_level = campaign.current_week['arty_support_level']
		
		self.unit_support_level = 0.0
		if 'unit_support_level' in campaign.current_week:
			self.unit_support_level = campaign.current_week['unit_support_level']
		
		self.advancing_fire = False			# player is using advancing fire when moving
		self.air_support_request = False		# " requesting air support upon move
		self.arty_support_request = False		# " arty "
		self.unit_support_request = False		# " unit "
		self.unit_support_type = None			# to be selected upon moving into a enemy-held zone
		
		self.encounter_mod = 0.0			# increases every time player caputures an area without resistance
		
		# set player location to player control if required
		self.map_hexes[self.player_unit_location].CaptureMe(0, no_vp=True)
		
		# set enemy strength and units present in each zone
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			self.map_hexes[(hx,hy)].GenerateStrengthAndUnits(self.mission)
		
		# animation object; keeps track of active animations on the animation console
		self.animation = {
			'rain_active' : False,
			'rain_drops' : [],
			'snow_active' : False,
			'snowflakes' : [],
			'hex_highlight' : False
		}
	
	
	# show unit support type selection menu
	def GetUnitSupportChoice(self):
		
		# draw the menu console
		def DrawMenuCon():
			
			libtcod.console_clear(game_menu_con)
			
			libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
			DrawFrame(game_menu_con, 0, 0, 84, 54)
			
			# menu title
			libtcod.console_set_default_background(game_menu_con, libtcod.darker_blue)
			libtcod.console_rect(game_menu_con, 1, 1, 82, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(game_menu_con, libtcod.black)
			libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
			libtcod.console_print(game_menu_con, 33, 2, 'Select Unit Support Type')
			
			# list available support types
			libtcod.console_set_default_foreground(game_menu_con, libtcod.lighter_blue)
			libtcod.console_print(game_menu_con, 17, 17, 'Unit Support Type')
			libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
			y = 20
			for text in choice_list:
				if text == selection:
					libtcod.console_set_default_background(game_menu_con, libtcod.darker_blue)
					libtcod.console_rect(game_menu_con, 17, y-1, 20, 3, False, libtcod.BKGND_SET)
					libtcod.console_set_default_background(game_menu_con, libtcod.black)
				libtcod.console_print(game_menu_con, 17, y, text)
				y += 3
			
			# details on units in selected type
			libtcod.console_set_default_foreground(game_menu_con, libtcod.lighter_blue)
			libtcod.console_print(game_menu_con, 40, 17, 'Possible Support Units')
			libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
			y = 20
			for unit_id in campaign.stats['player_unit_support'][selection]:
				libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
				libtcod.console_print(game_menu_con, 40, y, unit_id)
				libtcod.console_set_default_foreground(game_menu_con, libtcod.light_grey)
				libtcod.console_print(game_menu_con, 61, y, session.unit_types[unit_id]['class'])
				y += 2
			
			
			# command keys
			libtcod.console_set_default_foreground(game_menu_con, ACTION_KEY_COL)
			libtcod.console_print(game_menu_con, 30, 46, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(game_menu_con, 30, 47, 'Bksp')
			libtcod.console_print(game_menu_con, 30, 48, 'Tab')
			
			libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
			libtcod.console_print(game_menu_con, 38, 46, 'Select Support Type')
			libtcod.console_print(game_menu_con, 38, 47, 'Cancel Support Request')
			libtcod.console_print(game_menu_con, 38, 48, 'Proceed with Request')
			
			
			libtcod.console_blit(game_menu_con, 0, 0, 0, 0, con, 3, 3)
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# generate list of choices and choose first one by default
		choice_list = list(campaign.stats['player_unit_support'])
		# shouldn't happen, but just check
		if len(choice_list) == 0: return False
		selection = choice_list[0]
		
		# darken screen background
		libtcod.console_blit(darken_con, 0, 0, 0, 0, con, 0, 0, 0.0, 0.7)
	
		# generate menu console for the first time and blit to screen
		DrawMenuCon()
		
		# get input from player
		exit_menu = False
		while not exit_menu:
			
			if DEBUG:
				if libtcod.console_is_window_closed(): sys.exit()
			
			libtcod.console_flush()
			keypress = GetInputEvent()
			if not keypress: continue
			
			# cancel support request - confirm first
			if key.vk in [libtcod.KEY_BACKSPACE, libtcod.KEY_ESCAPE]:
				if not ShowNotification('Cancel support request and proceed with travel?', confirm=True):
					continue
				exit_menu = True
				continue
			
			# proceed with selected unit support type
			elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				return selection
			
			key_char = DeKey(chr(key.c).lower())
			
			# change selected option
			if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				i = choice_list.index(selection)
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if i == 0:
						i = len(choice_list) - 1
					else:
						i -= 1
				else:
					if i == len(choice_list) - 1:
						i = 0
					else:
						i += 1
				selection = choice_list[i]
				DrawMenuCon()
				continue
		
		# cancel request
		return None
	
	
	# returns true if travel between these two zones would require a river crossing
	def RiverCrossing(self, hx1, hy1, hx2, hy2):
		if (hx1, hy1) not in self.map_hexes: return False
		if (hx2, hy2) not in self.map_hexes: return False
		if self.GetDirectionToAdjacentCD(hx1, hy1, hx2, hy2) not in self.map_hexes[(hx1,hy1)].rivers:
			if self.GetDirectionToAdjacentCD(hx2, hy2, hx1, hy1) not in self.map_hexes[(hx2,hy2)].rivers:
				return False
		if self.GetDirectionToAdjacentCD(hx1, hy1, hx2, hy2) in self.map_hexes[(hx1,hy1)].bridges:
			return False
		if self.GetDirectionToAdjacentCD(hx2, hy2, hx1, hy1) in self.map_hexes[(hx2,hy2)].bridges:
			return False
		return True
	
	
	# calculate local sunrise and sunset time, moon phase for this day in the calendar
	def CalcDaylight(self):
		
		location = LocationInfo('', '', '', campaign.latitude, campaign.longitude)
		current_date = campaign.today.split('.')
		year = int(current_date[0])
		month = int(current_date[1])
		day = int(current_date[2])
		try:
			s = sun(location.observer, date=datetime(year, month, day))
			sunrise = s['sunrise']
			sunset = s['sunset']
			
			# account for difference from UTC
			sunrise += timedelta(minutes = int(campaign.longitude * 4))
			sunset += timedelta(minutes = int(campaign.longitude * 4))
		
		# some locations will be too far north for the sun to ever set
		except:
			sunrise = datetime(year, month, day, 4, 0, 0)
			sunset = datetime(year, month, day, 22, 0, 0)
		
		self.start_of_day = {}
		self.start_of_day['hour'] = sunrise.hour
		self.start_of_day['minute'] = sunrise.minute
		
		if self.start_of_day['hour'] < 4:
			self.start_of_day['hour'] = 4
			self.start_of_day['minute'] = 0
		
		self.day_clock = {}
		self.day_clock['hour'] = self.start_of_day['hour']
		self.day_clock['minute'] = self.start_of_day['minute']
		
		self.end_of_day = {}
		self.end_of_day['hour'] = sunset.hour
		self.end_of_day['minute'] = sunset.minute
		
		if self.end_of_day['hour'] >= 22:
			self.end_of_day['hour'] = 22
			self.end_of_day['minute'] = 0
		
		# calculate current moon phase
		phase = round(moon.phase(date(year, month, day)), 2)
		if phase <= 6.99:
			self.moon_phase = 'New Moon'
		elif phase <= 13.99:
			self.moon_phase = 'First Quarter'
		elif phase <= 20.99:
			self.moon_phase = 'Full Moon'
		else:
			self.moon_phase = 'Last Quarter'
	
	
	# handle a recon or tavel command from the player on the Campaign Day map
	# return amount of minutes taken to travel or recon
	def ReconOrTravel(self, recon, map_hex2, withdrawing=False):
		
		global scenario
		
		# recon
		if recon:
			if map_hex2.known_to_player: return False
			if map_hex2.controlled_by == 0: return False
			map_hex2.known_to_player = True
			text = 'Estimated enemy strength in zone: ' + str(map_hex2.enemy_strength)
			ShowMessage(text, cd_highlight=(map_hex2.hx, map_hex2.hy))
			campaign_day.AdvanceClock(0, 10)
			DisplayTimeInfo(time_con)
			
			# check for objective completion
			if map_hex2.objective is not None:
				if map_hex2.objective['type'] == 'Recon':
					ShowMessage('You completed an objective!')
					campaign.AwardVP(map_hex2.objective['vp_reward'])
					map_hex2.objective = None

			return 10
		
		# travel
		
		# if unit support request is active, prompt player to select type of support
		if self.unit_support_request:
			unit_choice = self.GetUnitSupportChoice()
			if unit_choice is None:
				self.unit_support_request = False
			else:
				self.unit_support_type = unit_choice
		
		# check for river crossing - only if not withdrawing
		river_time_required = 0
		(hx1, hy1) = self.player_unit_location
		if self.RiverCrossing(hx1, hy1, map_hex2.hx, map_hex2.hy) and not withdrawing:
			
			roll = GetPercentileRoll()
			
			if self.weather['Temperature'] == 'Extreme Cold':
				roll -= 40.0
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Explorer'):
				roll -= 25.0
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Prepared Positions'):
				roll = 0.0
			
			river_time_required = self.CalculateTravelTime(hx1, hy1, map_hex2.hx, map_hex2.hy)
			
			# modify time required
			if roll <= 50.0:
				river_time_required = int(river_time_required * 0.5)
			elif roll <= 75.0:
				river_time_required = int(river_time_required * 0.75)
			elif roll <= 95.0:
				river_time_required = int(river_time_required * 1.0)
			else:
				river_time_required = int(river_time_required * 1.23)
			
			PlaySoundFor(campaign.player_unit, 'movement')
			ShowMessage('It takes you an additional ' + str(river_time_required) + ' minutes to find ' +
				'a safe crossing point to cross the river.')
			campaign_day.AdvanceClock(0, river_time_required)
			DisplayTimeInfo(time_con)
		
		travel_time = self.MovePlayerTo(map_hex2.hx, map_hex2.hy)
		self.UpdateCDCommandCon()
		self.UpdateCDDisplay()
		
		# fatigue check for player crew if extreme weather
		if self.weather['Temperature'] in ['Extreme Hot', 'Extreme Cold']:
			for position in campaign.player_unit.positions_list:
				if position.crewman is None: continue
				position.crewman.DoFatigueCheck()
		
		# roll to trigger battle encounter if enemies present
		if map_hex2.enemy_strength > 0 and len(map_hex2.enemy_units) > 0:
			
			if map_hex2.controlled_by == 0:
				text = 'You enter the allied-held zone'
			elif map_hex2.controlled_by == 1:
				text = 'You enter the enemy-held zone'
			else:
				text = 'You enter the neutral zone'
			
			# check for Patrol mission award
			if self.mission == 'Patrol':
				campaign.AwardVP(1)
			
			# resolve advancing fire if any
			text += self.ResolveAdvancingFire()
			
			ShowMessage(text)
										
			# roll for scenario trigger
			roll = GetPercentileRoll() - campaign_day.encounter_mod
			
			if DEBUG:
				if session.debug['Always Scenario']:
					roll = 1.0
				elif session.debug['Never Scenario']:
					roll = 100.0
			
			# lower chance of encounters in North Africa maps
			if campaign.stats['region'] == 'North Africa':
				odds = float(map_hex2.enemy_strength) * 7.5
			else:
				odds = float(map_hex2.enemy_strength) * 9.5
			
			if roll <= odds:
				ShowMessage('You encounter enemy resistance!')
				self.AdvanceClock(0, 15)
				DisplayTimeInfo(time_con)
				DisplayLoadingMsg()
				scenario = Scenario(map_hex2)
				self.encounter_mod = 0.0
				self.AddRecord('Battles Fought', 1)
				campaign.AddJournal('Entered an enemy-held zone, encountered resistance')
				return river_time_required + travel_time + 15
			
			ShowMessage('You find no enemy resistance in this area.')
			if map_hex2.controlled_by == 1:	
				campaign.AddJournal('Entered an enemy-held zone, no resistance.')
			else:
				campaign.AddJournal('Entered a zone with some enemy presence, but found no resistance.')
			map_hex2.CaptureMe(0)
				
			self.encounter_mod += 30.0
			
			# spend support costs and reset flags
			if self.air_support_request:
				if GetPercentileRoll() <= self.air_support_level:
					self.air_support_level -= float(libtcod.random_get_int(0, 1, 3)) * 5.0
				if self.air_support_level < 0.0:
					self.air_support_level = 0.0
				self.air_support_request = False
			
			if self.arty_support_request:
				if GetPercentileRoll() <= self.arty_support_level:
					self.arty_support_level -= float(libtcod.random_get_int(0, 1, 3)) * 5.0
				if self.arty_support_level < 0.0:
					self.arty_support_level = 0.0
				self.arty_support_request = False
			
			if self.unit_support_request:
				if GetPercentileRoll() <= self.unit_support_level:
					self.unit_support_level -= float(libtcod.random_get_int(0, 1, 3)) * 5.0
				if self.unit_support_level < 0.0:
					self.unit_support_level = 0.0
				self.unit_support_request = False
				self.unit_support_type = None
		
		# entering a friendly zone
		else:
			ShowMessage('You enter the allied-held zone.')
		
		# no battle triggered
		if map_hex2.terrain_type == 'Oasis':
			ShowMessage('Your crew have chance to rest in the oasis.')
			for position in campaign.player_unit.positions_list:
				if position.crewman is None: continue
				position.crewman.Rest()

		# recalculate VP values and check for map shift
		for (hx, hy), cd_hex in self.map_hexes.items():
			cd_hex.CalcCaptureVP()
		DisplayTimeInfo(time_con)
		self.CheckForCDMapShift()
		return river_time_required + travel_time
	
	
	# resolve advancing fire for player and squad; return a text description of action
	def ResolveAdvancingFire(self):
		
		# none to resolve
		if not self.advancing_fire: return '.'
		
		text = ', using advancing fire against anything suspicious.'
		
		# check for HE and MG FP across squad
		unit_list = [campaign.player_unit]
		if len(campaign_day.player_squad) > 0:
			unit_list += campaign_day.player_squad
		
		total_he = 0
		player_he = 0
		total_fp = 0
		for unit in unit_list:
			
			# build a list of weapons that will be fired
			firing_list = []
			for weapon in unit.weapon_list:
				
				if weapon.GetStat('type') != 'Gun' and weapon.GetStat('type') not in MG_WEAPONS: continue
				if weapon.broken: continue
				
				# if player unit, needs to have a crewman in the correct position
				if unit.is_player:
					if weapon.GetStat('fired_by') is not None:
						crewman_found = False
						position_list = weapon.GetStat('fired_by')
						for position in position_list:
							crewman = unit.GetPersonnelByPosition(position)
							if crewman is None: continue
							if not crewman.alive: continue
							crewman_found = True
							break
						
						if not crewman_found: continue
				
				if weapon.GetStat('type') == 'Gun':
					if 'HE' not in weapon.ammo_stores: continue
					if weapon.ammo_stores['HE'] == 0: continue
					
					# don't use HE if limited
					if 'special_ammo' in weapon.stats:
						if 'HE' in weapon.stats['special_ammo']:
							continue
				
				firing_list.append(weapon)
			
			# determine total firepower from all firing weapons
			for weapon in firing_list:
				
				if weapon.GetStat('type') == 'Gun':
					
					# determine how many shells are fired
					max_shells = 7
					if weapon.max_ammo <= 60:
						max_shells = 3
					
					i = libtcod.random_get_int(0, 1, max_shells)
					if i > weapon.ammo_stores['HE']:
						i = weapon.ammo_stores['HE']
					weapon.ammo_stores['HE'] -= i
					total_he += i
					total_fp += weapon.GetEffectiveFP() * i
					if unit.is_player:
						player_he += i
				
				elif weapon.GetStat('type') in MG_WEAPONS:
					total_fp += int(weapon.GetStat('fp')) * libtcod.random_get_int(0, 0, 3)
				
		
		# no effective advancing fire
		if total_fp == 0:
			self.advancing_fire = False
			return '.'
		
		if player_he > 0:
			text += ' You fired a total of ' + str(player_he) + ' HE rounds.'
		
		# do the effectiveness roll based on total FP
		if GetPercentileRoll() > round(float(total_fp) * 0.4, 1):
			self.advancing_fire = False
		
		return text
		
	
	# set landmine zones for this map
	def GenerateMinefields(self):
		if 'landmines_chance' not in campaign.current_week: return
		chance = float(campaign.current_week['landmines_chance'])
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx,hy)].terrain_type]:
				continue
			if GetPercentileRoll() <= chance:
				self.map_hexes[(hx,hy)].landmines = True
	
	
	# generate objectives for this map
	def GenerateObjectives(self):
		
		# initial objective types
		OBJECTIVE_CHOICES = ['Capture', 'Recon', 'Hold']
		
		(phx, phy) = self.player_unit_location
		locations = []
		
		# determine current number of objectives already on map
		current_objectives = 0
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if self.map_hexes[(hx, hy)].objective is not None:
				current_objectives += 1
		
		if current_objectives >= 3: return
		
		# build initial list of possible hexes
		hex_list = []
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx, hy)].terrain_type]:
				continue
			if GetHexDistance(hx, hy, phx, phy) < 2: continue
			if len(self.GetHexPath(hx, hy, phx, phy)) == 0: continue
			hex_list.append((hx, hy))
		
		# no possible locations (should not happen)
		if len(hex_list) == 0: return
		
		# generate enough objectives to bring total up to three
		for i in range(3 - current_objectives):
			
			for tries in range(300):
			
				objective = {}
				
				# select random type
				objective['type'] = choice(OBJECTIVE_CHOICES)
				
				# greater chance of Hold objective in these missions
				if self.mission in ['Fighting Withdrawal', 'Counterattack']:
					if objective['type'] != 'Hold':
						objective['type'] = choice(OBJECTIVE_CHOICES)
				
				# try to find a suitable location
				suitable_hex_list = []
				for (hx, hy) in hex_list:
					
					# already an objective here
					if self.map_hexes[(hx, hy)].objective is not None: continue
					
					if objective['type'] == 'Recon':
						if self.map_hexes[(hx, hy)].known_to_player: continue
						if self.map_hexes[(hx, hy)].controlled_by == 0: continue
					elif objective['type'] == 'Capture':
						if self.map_hexes[(hx, hy)].controlled_by != 1: continue
					elif objective['type'] == 'Hold':
						if self.map_hexes[(hx, hy)].controlled_by != 0: continue
	
					# make sure it's not too close to another objective
					too_close = False
					for (hx2, hy2) in locations:
						if GetHexDistance(hx, hy, hx2, hy2) <= 2:
							too_close = True
							break
					if too_close: continue
						
					suitable_hex_list.append((hx, hy))
				
				# no suitable locations
				if len(suitable_hex_list) == 0:
					continue
				
				# place objective in random good location
				(hx, hy) = choice(suitable_hex_list)
				objective['hx'] = hx
				objective['hy'] = hy
				
				if objective['type'] == 'Recon':
					objective['vp_reward'] = 4
				elif objective['type'] == 'Capture':
					objective['vp_reward'] = 8
					self.map_hexes[(hx, hy)].enemy_strength += libtcod.random_get_int(0, 2, 5)
					if self.map_hexes[(hx, hy)].enemy_strength > 10:
						self.map_hexes[(hx, hy)].enemy_strength = 10
				elif objective['type'] == 'Hold':
					objective['vp_reward'] = 6
				
				self.map_hexes[(hx, hy)].objective = objective
				locations.append((hx, hy))
				break
	
	
	# check to see what happens when the player waits for resupply
	def DoResupplyCheck(self):
		
		global scenario
		
		# check for clear path to friendly edge
		if not self.PlayerHasPath():
			ShowMessage('You are cut off from friendly forces! No resupply possible.')
			return
		
		# roll for possible attack on player hex
		# odds based on average strength of enemy-held adjacent hexes, plus enemy strength
		# in player hex if neutral
		total_strength = 0
		(hx, hy) = self.player_unit_location
		if self.map_hexes[(hx,hy)].controlled_by == 2:
			total_strength += self.map_hexes[(hx,hy)].enemy_strength
		
		for direction in range(6):
			(hx1, hy1) = self.GetAdjacentCDHex(hx, hy, direction)
			if (hx1, hy1) not in CAMPAIGN_DAY_HEXES: continue
			if self.map_hexes[(hx1,hy1)].controlled_by == 0: continue
			total_strength += self.map_hexes[(hx1,hy1)].enemy_strength
		
		total_strength = float(total_strength) / 6.0
		if total_strength <= 1.0:
			total_strength = 0.0
		
		roll = GetPercentileRoll()
		
		if roll <= total_strength * 10.0:
			self.AdvanceClock(0, 5 * libtcod.random_get_int(0, 1, 3))
			DisplayTimeInfo(time_con)
			ShowMessage('While you are waiting for resupply, enemy forces attack your zone!')
			campaign.AddJournal('Enemy forces attacked our zone while we were waiting for resupply.')
			DisplayLoadingMsg()
			scenario = Scenario(self.map_hexes[(hx,hy)])
			self.AddRecord('Battles Fought', 1)
			self.UpdateCDUnitCon()
			self.UpdateCDControlCon()
			self.UpdateCDGUICon()
			self.UpdateCDCommandCon()
			self.UpdateCDHexInfoCon()
			self.UpdateCDDisplay()
			return
		
		# roll for time required
		minutes = 5 * libtcod.random_get_int(0, 3, 6)
		
		# spend time
		self.AdvanceClock(0, minutes)
		DisplayTimeInfo(time_con)
		self.UpdateCDDisplay()
		
		ShowMessage('Resupply trucks arrive ' + str(minutes) + ' minutes later.')
		campaign.AddJournal('We have been resupplied.')
		session.ModifySteamStat('resupplied', 1)
		
		# allow player to replenish ammo, also replenish smoke grenades and mortar rounds
		self.AmmoReloadMenu(resupply=True)
		self.smoke_grenades = 6
		if campaign.player_unit.GetStat('smoke_mortar') is not None:
			self.smoke_mortar_rounds = 10
		self.UpdateCDDisplay()
		
		# check for dead crewman removal, living crew have a chance to rest 
		for position in campaign.player_unit.positions_list:
			if position.crewman is None: continue
			if not position.crewman.alive:
				position.crewman = None
				self.UpdateCDPlayerUnitCon()
				self.UpdateCDDisplay()
				ShowMessage('The body of your ' + position.name + ' is taken back by the supply team.')
			else:
				position.crewman.Rest()
		
		self.UpdateCDDisplay()
		self.CheckForZoneCapture('resupply')
		self.CheckForRandomEvent()
		SaveGame()
		
	
	# check to see if clear path between hexes in top and bottom row
	def CheckClearMapPath(self):
		path_good = False
		STARTING_HEXES = [(-4,8), (-3,8), (-2,8), (-1,8), (0,8)]
		ENDING_HEXES = [(4,0), (3,0), (2,0), (1,0), (0,0)]
		
		for (hx1, hy1) in STARTING_HEXES:
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx1,hy1)].terrain_type]: continue
			for (hx2, hy2) in ENDING_HEXES:
				if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx2,hy2)].terrain_type]: continue
				if len(self.GetHexPath(hx1, hy1, hx2, hy2)) == 0:
					continue
				path_good = True
				break
			if path_good:
				break
		
		return path_good
	
	
	# returns a path from one campaign day hex zone to another
	# can be set to be blocked by enemy-held zones
	# based on function from ArmCom 1, which was based on:
	# http://stackoverflow.com/questions/4159331/python-speed-up-an-a-star-pathfinding-algorithm
	# http://www.policyalmanac.org/games/aStarTutorial.htm
	def GetHexPath(self, hx1, hy1, hx2, hy2, avoid_terrain=[], enemy_zones_block=False):
		
		# retrace a set of nodes and return the best path
		def RetracePath(end_node):
			path = []
			node = end_node
			done = False
			while not done:
				path.append((node.hx, node.hy))
				if node.parent is None: break	# we've reached the end
				node = node.parent	
			path.reverse()
			return path
		
		# clear any old pathfinding info
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			self.map_hexes[(hx,hy)].ClearPathInfo()
		
		node1 = self.map_hexes[(hx1, hy1)]
		node2 = self.map_hexes[(hx2, hy2)]
		open_list = set()	# contains the nodes that may be traversed by the path
		closed_list = set()	# contains the nodes that will be traversed by the path
		start = node1
		start.h = GetHexDistance(node1.hx, node1.hy, node2.hx, node2.hy)
		start.f = start.g + start.h
		end = node2
		open_list.add(start)		# add the start node to the open list
		
		while open_list:
			
			# grab the node with the best H value from the list of open nodes
			current = sorted(open_list, key=lambda inst:inst.f)[0]
			
			# we've reached our destination
			if current == end:
				return RetracePath(current)
			
			# move this node from the open to the closed list
			open_list.remove(current)
			closed_list.add(current)
			
			# add the nodes connected to this one to the open list
			for direction in range(6):
				
				# get the hex coordinates in this direction
				hx, hy = self.GetAdjacentCDHex(current.hx, current.hy, direction)
				
				# no map hex exists here, skip
				if (hx, hy) not in CAMPAIGN_DAY_HEXES: continue
				
				node = self.map_hexes[(hx,hy)]
				
				# hex terrain is impassible, skip
				if 'impassible' in CD_TERRAIN_TYPES[node.terrain_type]: continue
				
				# ignore nodes on closed list
				if node in closed_list: continue
								
				if enemy_zones_block:
					if node.controlled_by == 1:
						continue
				
				if len(avoid_terrain) > 0:
					if node.terrain_type in avoid_terrain:
						continue
				
				# not really used yet
				cost = 1
				
				g = current.g + cost
				
				# if not in open list, add it
				if node not in open_list:
					node.g = g
					node.h = GetHexDistance(node.hx, node.hy, node2.hx, node2.hy)
					node.f = node.g + node.h
					node.parent = current
					open_list.add(node)
				# if already in open list, check to see if can make a better path
				else:
					if g < node.g:
						node.parent = current
						node.g = g
						node.f = node.g + node.h
		
		# no path possible
		return []
	
	
	# generate terrain for this campaign map
	def GenerateCDMapTerrain(self, avoid_y=False):
		cd_hex_numbers = {}
		
		terrain_dict = REGIONS[campaign.stats['region']]['cd_terrain_odds'].copy()
		
		# check to see if current campaign week modifies this and change dictionary value
		if 'terrain_odds_modifier' in campaign.current_week:
			for k, v in campaign.current_week['terrain_odds_modifier'].items():
				terrain_dict[k] = v
		# base odds should total 100, but campaign week may modify this, so we can scale the odds
		total_chance = 0
		for terrain_type, odds in terrain_dict.items():
			total_chance += odds
		
		for tries in range(300):
			
			# check for coastal daymap
			if self.coastal_map is not None:
				if self.coastal_map == 'left':
					hx = 0
				else:
					hx = 4
				hy = 0
				for i in range(9):
					self.map_hexes[(hx,hy)].terrain_type = 'Ocean'
					if self.coastal_map == 'right':
						if self.GetAdjacentCDHex(hx, hy, 2) in CAMPAIGN_DAY_HEXES:
							(hx, hy) = self.GetAdjacentCDHex(hx, hy, 2)
						else:
							(hx, hy) = self.GetAdjacentCDHex(hx, hy, 3)
					else:
						if self.GetAdjacentCDHex(hx, hy, 3) in CAMPAIGN_DAY_HEXES:
							(hx, hy) = self.GetAdjacentCDHex(hx, hy, 3)
						else:
							(hx, hy) = self.GetAdjacentCDHex(hx, hy, 2)
		
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				
				if avoid_y:
					if hy == avoid_y:
						continue
				
				map_hex = self.map_hexes[(hx,hy)]
				
				while map_hex.terrain_type == '':
					
					terrain_type = choice(list(terrain_dict.keys()))
					odds = terrain_dict[terrain_type]
					
					# check for terrain types that have already been spawned
					if 'max_per_map' in CD_TERRAIN_TYPES[terrain_type]:
						if terrain_type in cd_hex_numbers:
							if cd_hex_numbers[terrain_type] == CD_TERRAIN_TYPES[terrain_type]['max_per_map']:
								continue
					
					# check for restrictions on adjacent terrain types
					if 'no_adjacent' in CD_TERRAIN_TYPES[terrain_type]:
						blocked_by_adjacent = False
						for direction in range(6):
							(hx2, hy2) = self.GetAdjacentCDHex(hx, hy, direction)
							# off map
							if (hx2, hy2) not in self.map_hexes: continue
							if self.map_hexes[(hx2,hy2)].terrain_type in CD_TERRAIN_TYPES[terrain_type]['no_adjacent']:
								blocked_by_adjacent = True
								break
						if blocked_by_adjacent:
							continue
					
					if libtcod.random_get_int(0, 0, total_chance) <= odds:
						map_hex.terrain_type = terrain_type
						
						# record addition of this terrain type
						if terrain_type in cd_hex_numbers:
							cd_hex_numbers[terrain_type] += 1
						else:
							cd_hex_numbers[terrain_type] = 1
						break
			
			# map terrain is finished, make sure that it can be traversed
			if self.CheckClearMapPath():
				break
			
			# clear all terrain
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				self.map_hexes[(hx,hy)].terrain_type = ''
			
	
	# checks to see if player has a clear path back to the friendly map edge
	def PlayerHasPath(self):
		path_good = False
		(hx1, hy1) = self.player_unit_location
		
		if hy1 == 8:
			path_good = True
		else:
			for hx2 in range(-4, 1):
				if len(self.GetHexPath(hx1, hy1, hx2, 8, enemy_zones_block=True)) != 0:
					path_good = True
					break
		return path_good
		
	
	# set up the list of player guns and select the first one if any
	def BuildPlayerGunList(self):
		self.gun_list = []
		self.selected_gun = None
		for weapon in campaign.player_unit.weapon_list:
			if weapon.GetStat('type') == 'Gun':
				self.gun_list.append(weapon)
		if len(self.gun_list) > 0:
			self.selected_gun = self.gun_list[0]
	
	
	# spawn squad members to bring player squad up to full strength
	def SpawnPlayerSquad(self):
		
		for i in range(campaign.player_squad_max - len(self.player_squad)):
			
			# determine unit type
			if 'player_squad_list' in campaign.stats:
				if campaign.player_unit.unit_id in campaign.stats['player_squad_list']:
					unit_id = choice(campaign.stats['player_squad_list'][campaign.player_unit.unit_id])
				else:
					unit_id = campaign.player_unit.unit_id
			else:
				unit_id = campaign.player_unit.unit_id
			
			# do a rarity check if squadmate is different model from player
			if unit_id != campaign.player_unit.unit_id:
				if not campaign.options['ahistorical'] and 'rarity' in session.unit_types[unit_id]:
					unit_ok = True
					for date, chance in session.unit_types[unit_id]['rarity'].items():
						if date > campaign.today:
							unit_ok = False
							break
					if not unit_ok:
						unit_id = campaign.player_unit.unit_id
			
			unit = Unit(unit_id)
			unit.nation = campaign.player_unit.nation
			unit.ai = AI(unit)
			unit.GenerateNewPersonnel()
			self.player_squad.append(unit)
	
	
	# move the player from current position to a new position on the Campaign Day map
	def MovePlayerTo(self, hx2, hy2):
		(hx1, hy1) = self.player_unit_location
		mins = self.CalculateTravelTime(hx1,hy1,hx2,hy2)
		
		# clear any selected direction
		self.selected_direction = None
		self.UpdateCDGUICon()
		
		# calculate animation path
		(x,y) = self.PlotCDHex(hx1, hy1)
		(x2,y2) = self.PlotCDHex(hx2, hy2)
		line = GetLine(0, 0, x2-x, y2-y)
		
		# do sound effect
		PlaySoundFor(campaign.player_unit, 'movement')
		
		# show animation
		for (x, y) in line:
			session.cd_x_offset = x
			session.cd_y_offset = y
			self.UpdateCDUnitCon()
			self.UpdateCDDisplay()
			Wait(20)
		session.cd_x_offset = 0
		session.cd_y_offset = 0
		
		# advance clock and set new player location
		campaign_day.AdvanceClock(0, mins)
		self.player_unit_location = (hx2, hy2)
		self.map_hexes[self.player_unit_location].RevealAdjacentZones()
		DisplayWeatherInfo(cd_weather_con)
		self.UpdateCDUnitCon()
		self.UpdateCDDisplay()
		return mins
		
	
	# check for shift of campaign day map:
	# shift displayed map up or down, triggered by player reaching other end of map
	def CheckForCDMapShift(self):
		
		(player_hx, player_hy) = self.player_unit_location
		
		if self.mission in ['Fighting Withdrawal', 'Counterattack']:
			if player_hy != 8: return
		else:
			if player_hy != 0: return
		
		ShowMessage('You enter a new map area.')
		campaign.AddJournal('Entered a new map area')
		self.maps_traversed += 1
		session.ModifySteamStat('areas_advanced', 1)
		DisplayTimeInfo(time_con)
		
		# determine direction to shift map based on current player location
		if player_hy == 8:
			shift_down = False
		elif player_hy == 0:
			shift_down = True
		else:
			return
		
		if shift_down:
			new_hy = 8
			hx_mod = -4
		else:
			new_hy = 0
			hx_mod = +4
		
		# copy terrain for current player row to new row
		for hx in range(player_hx-4, player_hx+5):
			if (hx, player_hy) not in CAMPAIGN_DAY_HEXES: continue
			self.map_hexes[(hx+hx_mod, new_hy)] = self.map_hexes[(hx, player_hy)]
			self.map_hexes[(hx+hx_mod, new_hy)].hx = hx+hx_mod
			self.map_hexes[(hx+hx_mod, new_hy)].hy = new_hy
			self.map_hexes[(hx+hx_mod, new_hy)].Reset()
		
		self.player_unit_location = (player_hx+hx_mod, new_hy)
		
		# generate new map hexes and terrain for remainder of map
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if hy == new_hy: continue
			self.map_hexes[(hx,hy)] = CDMapHex(hx, hy, self.mission)
		self.GenerateCDMapTerrain(avoid_y=new_hy)
		
		# calculate capture VP for all map zones
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			self.map_hexes[(hx,hy)].CalcCaptureVP()
	
		# set up zone control for new map
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if (hx, hy) == self.player_unit_location: continue
			if hy == new_hy: continue
			if self.mission in ['Fighting Withdrawal', 'Counterattack']:
				self.map_hexes[(hx, hy)].controlled_by = 0
			else:
				self.map_hexes[(hx, hy)].controlled_by = 1
		
		# set new enemy strength and units for all new zones
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if hy == new_hy: continue
			self.map_hexes[(hx,hy)].GenerateStrengthAndUnits(self.mission)
		
		# generate new objectives and landmines
		self.GenerateObjectives()
		self.GenerateMinefields()
		
		# update consoles
		self.UpdateCDMapCon()
		self.UpdateCDGUICon()
		self.UpdateCDPlayerUnitCon()
		
		SaveGame()
		
		
	# roll for type of mission for today
	def GenerateMission(self):
		roll = GetPercentileRoll()
		for k, v in campaign.current_week['mission_odds'].items():
			if roll <= v:
				self.mission = k
				return
			roll -= float(v)
		
		print('ERROR: unable to set a mission for today, choosing default')
		for k, v in self.current_week['mission_odds'].items():
			self.mission = k
			return
	
	
	# check to see if travel between hexes on the Campaign Day map is possible
	def CheckTravel(self, hx1, hy1, hx2, hy2):
		
		# check for impassible terrain
		if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx2,hy2)].terrain_type]:
			return 'N/A: Impassible'
		
		# check for missing or dead driver
		crewman = campaign.player_unit.GetPersonnelByPosition('Driver')
		if crewman is None:
			return 'N/A: No Driver'
		if not crewman.alive:
			return 'N/A: Driver is dead'
		
		return ''
		
	
	# calculate required travel time in minutes from one zone to another
	def CalculateTravelTime(self, hx1, hy1, hx2, hy2):
		
		direction = self.GetDirectionToAdjacentCD(hx1, hy1, hx2, hy2)
		
		# check for road link
		if self.map_hexes[(hx1,hy1)].road_links[direction] is not None:
			# dirt road
			if self.map_hexes[(hx1,hy1)].road_links[direction] is False:
				mins = 15
			# stone road
			else:
				mins = 10
			
			# poor quality roads
			if 'poor_quality_roads' in REGIONS[campaign.stats['region']]:
				if self.weather['Ground'] == 'Muddy':
					mins = mins * 2
			
		else:
			mins = CD_TERRAIN_TYPES[self.map_hexes[(hx2,hy2)].terrain_type]['travel_time']
		
		# check ground conditions
		if self.weather['Ground'] == 'Deep Snow':
			mins += 20
		elif self.weather['Ground'] in ['Muddy', 'Snow']:
			mins += 10
		elif self.weather['Precipitation'] != 'None':
			mins += 5
		
		# check for river crossing
		if self.RiverCrossing(hx1, hy1, hx2, hy2):
			mins += int(mins/2)
		
		# check for active support request flag(s) when moving into enemy or neutral zone
		if self.map_hexes[(hx2,hy2)].controlled_by in [1, 2]:
			if self.arty_support_request:
				if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Ad Hoc'):
					mins += 10
				else:
					mins += 15
			if self.air_support_request:
				if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Ad Hoc'):
					mins += 5
				else:
					mins += 10
			if self.unit_support_request:
				if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Ad Hoc'):
					mins += 10
				else:
					mins += 15
				
		return mins
		
	
	# increments one of the combat day records, also increments campaign record
	def AddRecord(self, name, i):
		self.records[name] += i
		campaign.records[name] += i
	
	
	# generate a new random set of initial weather conditions, should only be called when day is created
	def GenerateWeather(self):
		
		# determine current calendar season
		weather_odds_dict = REGIONS[campaign.stats['region']]['season_weather_odds']
		date = campaign.today[campaign.today.find('.') + 1:]
		
		for season, value in weather_odds_dict.items():
			if date <= value['end_date']:
				break
		else:
			# catch cases where date is late in the calendar year
			season = 'Winter'
		
		weather_odds = weather_odds_dict[season]
		self.weather['Season'] = season
		
		# roll for ground cover
		self.weather['Ground'] = None
		roll = GetPercentileRoll()
		for result, chance in weather_odds['ground_conditions'].items():
			if roll <= chance:
				self.weather['Ground'] = result
				break
			roll -= chance
		
		# choose first possible result as default
		if self.weather['Ground'] == None:
			for result, chance in weather_odds['ground_conditions'].items():
				if chance > 0.0:
					self.weather['Ground'] = result
					break
		
		# roll for temperature
		self.weather['Temperature'] = None
		roll = GetPercentileRoll()
		for result, chance in weather_odds['temperature'].items():
			if roll <= chance:
				self.weather['Temperature'] = result
				break
			roll -= chance
		if self.weather['Temperature'] == None:
			for result, chance in weather_odds['temperature'].items():
				if chance > 0.0:
					self.weather['Temperature'] = result
					break
		
		# roll for cloud cover
		self.weather['Cloud Cover'] = None
		roll = GetPercentileRoll()
		for result, chance in weather_odds['cloud_cover'].items():
			if roll <= chance:
				self.weather['Cloud Cover'] = result
				break
			roll -= chance
		if self.weather['Cloud Cover'] == None:
			for result, chance in weather_odds['cloud_cover'].items():
				if chance > 0.0:
					self.weather['Cloud Cover'] = result
					break
		
		# roll for precipitation
		roll = GetPercentileRoll()
		for result, chance in weather_odds['precipitation'].items():
			
			if chance == 0.0: continue
			
			# don't allow rain if extreme hot
			if self.weather['Temperature'] == 'Extreme Hot':
				self.weather['Precipitation'] = 'None'
				break
			
			# only allow snow if weather is cold
			if result in ['Light Snow', 'Snow', 'Blizzard'] and self.weather['Temperature'] not in ['Extreme Cold', 'Cold']:
				roll -= chance
				continue
			# only allow rain if weather is warm
			if result in ['Rain', 'Heavy Rain'] and self.weather['Temperature'] in ['Extreme Cold', 'Cold']:
				roll -= chance
				continue
			
			if roll <= chance:
				self.weather['Precipitation'] = result
				break
			roll -= chance
		else:
			self.weather['Precipitation'] = 'None'
		
		# if precipitation has been rolled, fix clear cloud cover
		if self.weather['Precipitation'] != 'None' and self.weather['Cloud Cover'] == 'Clear':
			self.weather['Cloud Cover'] = choice(['Scattered', 'Heavy', 'Overcast'])
		
		# fog level: 0-3
		self.weather['Fog'] = 0
		if campaign.stats['region'] != 'North Africa' and self.weather['Cloud Cover'] != 'Clear' and self.weather['Temperature'] in ['Cold', 'Mild']:
			
			roll = GetPercentileRoll()
			
			if self.weather['Precipitation'] in ['Snow', 'Blizzard']:
				roll -= 40.0
			elif self.weather['Season'] in ['Spring', 'Autumn']:
				roll += 10.0
			if self.weather['Ground'] in ['Wet', 'Muddy']:
				roll += 25.0
			
			if roll <= 70.0:
				self.weather['Fog'] = 0
			elif roll <= 85.0:
				self.weather['Fog'] = 1
			elif roll <= 95.0:
				self.weather['Fog'] = 2
			else:
				self.weather['Fog'] = 3
		
		# set first weather update countdown
		self.weather_update_clock = BASE_WEATHER_UPDATE_CLOCK + (libtcod.random_get_int(0, 1, 16))
	
	
	# update weather conditions, possibly changing them
	def UpdateWeather(self):
		
		# reset update clock
		self.weather_update_clock = BASE_WEATHER_UPDATE_CLOCK + (libtcod.random_get_int(0, 1, 16))
		
		# get weather odds for region
		weather_odds_dict = REGIONS[campaign.stats['region']]['season_weather_odds'][self.weather['Season']]
		
		# check for ground condition update
		roll = GetPercentileRoll()
		
		# muddy ground drying out
		if self.weather['Ground'] == 'Muddy':
			if self.weather['Precipitation'] == 'None':
				if roll <= GROUND_CONDITION_CHANGE_CHANCE:
					self.weather['Ground'] = 'Wet'
					ShowMessage('The muddy ground has dried out a little.')
		
		# wet ground drying out
		elif self.weather['Ground'] == 'Wet':
			if self.weather['Precipitation'] == 'None':
				if roll <= GROUND_CONDITION_CHANGE_CHANCE:
					self.weather['Ground'] = 'Dry'
					ShowMessage('The ground has completely dried out.')
			
			elif self.weather['Precipitation'] in ['Rain', 'Heavy Rain']:
				
				if self.weather['Precipitation'] == 'Heavy Rain':
					roll -= HEAVY_PRECEP_MOD
				if roll <= GROUND_CONDITION_CHANGE_CHANCE:
					self.weather['Ground'] = 'Muddy'
					ShowMessage('The ground has become muddy.')
		
		# snowy ground deepening
		elif self.weather['Ground'] == 'Snow':
			if self.weather['Precipitation'] in ['Snow', 'Blizzard']:
				if self.weather['Precipitation'] == 'Blizzard':
					roll -= HEAVY_PRECEP_MOD
				if roll <= GROUND_CONDITION_CHANGE_CHANCE:
					self.weather['Ground'] = 'Deep Snow'
					ShowMessage('The snow has accumilated and is now deep.')
		
		# dry ground - can get wet or snowy
		else:
			
			if self.weather['Precipitation'] in ['Rain', 'Heavy Rain']:
				if self.weather['Precipitation'] == 'Heavy Rain':
					roll -= HEAVY_PRECEP_MOD
				if roll <= GROUND_CONDITION_CHANGE_CHANCE:
					self.weather['Ground'] = 'Wet'
					ShowMessage('The ground has become wet.')
			
			elif self.weather['Precipitation'] in ['Snow', 'Blizzard']:
				if self.weather['Precipitation'] == 'Blizzard':
					roll -= HEAVY_PRECEP_MOD
				if roll <= GROUND_CONDITION_CHANGE_CHANCE:
					self.weather['Ground'] = 'Snow'
					ShowMessage('The ground is now covered in snow.')
					
					# update map consoles to reflect new ground cover
					campaign_day.UpdateCDMapCon()
					if scenario is not None:
						scenario.UpdateHexmapCon()
		
		
		# roll to see weather change takes place
		if GetPercentileRoll() > 15.0: return
		
		# roll for possible type of weather change
		roll = GetPercentileRoll()
			
		# change in precipitation level
		if roll <= 70.0:
			
			# no change possible
			if self.weather['Cloud Cover'] == 'Clear':
				return
			
			roll = GetPercentileRoll()
			
			if self.weather['Precipitation'] == 'None':
				
				if self.weather['Temperature'] in ['Cold', 'Extreme Cold']:
					
					if roll <= weather_odds_dict['precipitation']['Light Snow']:
						self.weather['Precipitation'] = 'Light Snow'
						ShowMessage('Light snow begins to fall.')
					elif roll <= weather_odds_dict['precipitation']['Snow']:
						self.weather['Precipitation'] = 'Snow'
						ShowMessage('Snow begins to fall.')
					else:
						return
				else:
					
					if roll <= weather_odds_dict['precipitation']['Mist']:
						self.weather['Precipitation'] = 'Mist'
						ShowMessage('A light mist begins to fall.')
					elif roll <= weather_odds_dict['precipitation']['Rain']:
						self.weather['Precipitation'] = 'Rain'
						ShowMessage('Rain begins to fall.')
					elif roll <= weather_odds_dict['precipitation']['Heavy Rain']:
						self.weather['Precipitation'] = 'Heavy Rain'
						ShowMessage('A heavy downpour suddenly begins to fall.')
					else:
						return
			
			elif self.weather['Precipitation'] == 'Mist':
				if roll <= 40.0:
					self.weather['Precipitation'] = 'None'
					ShowMessage('The light mist has cleared up.')
				elif roll <= weather_odds_dict['precipitation']['Rain']:
					self.weather['Precipitation'] = 'Rain'
					ShowMessage('The light mist thickens into a steady rain.')
				elif roll <= weather_odds_dict['precipitation']['Heavy Rain']:
					self.weather['Precipitation'] = 'Heavy Rain'
					ShowMessage('The light mist suddenly turns into a heavy downpour.')
				else:
					return
			
			elif self.weather['Precipitation'] == 'Rain':
				if roll <= 30.0:
					self.weather['Precipitation'] = 'None'
					ShowMessage('The rain has cleared up.')
				elif roll <= weather_odds_dict['precipitation']['Mist']:
					self.weather['Precipitation'] = 'Mist'
					ShowMessage('The rain turns into a light mist.')
				elif roll <= weather_odds_dict['precipitation']['Heavy Rain']:
					self.weather['Precipitation'] = 'Heavy Rain'
					ShowMessage('The rain gets heavier.')
				else:
					return
			
			elif self.weather['Precipitation'] == 'Heavy Rain':
				if roll <= weather_odds_dict['precipitation']['Mist']:
					self.weather['Precipitation'] = 'Mist'
					ShowMessage('The rain turns into a light mist.')
				elif roll <= weather_odds_dict['precipitation']['Rain']:
					self.weather['Precipitation'] = 'Rain'
					ShowMessage('The rain lightens a little.')
				else:
					return

			elif self.weather['Precipitation'] == 'Light Snow':
				if roll <= 30.0:
					self.weather['Precipitation'] = 'None'
					ShowMessage('The snow stops falling.')
				elif roll <= weather_odds_dict['precipitation']['Snow']:
					self.weather['Precipitation'] = 'Snow'
					ShowMessage('The snow gets a little heavier.')
				elif roll <= weather_odds_dict['precipitation']['Blizzard']:
					self.weather['Precipitation'] = 'Blizzard'
					ShowMessage('The snow starts falling very heavily.')
				else:
					return
			
			elif self.weather['Precipitation'] == 'Snow':
				if roll <= 20.0:
					self.weather['Precipitation'] = 'None'
					ShowMessage('The snow stops falling.')
				elif roll <= weather_odds_dict['precipitation']['Light Snow']:
					self.weather['Precipitation'] = 'Light Snow'
					ShowMessage('The snow gets a little lighter.')
				elif roll <= weather_odds_dict['precipitation']['Blizzard']:
					self.weather['Precipitation'] = 'Blizzard'
					ShowMessage('The snow starts falling very heavily.')
				else:
					return
			
			elif self.weather['Precipitation'] == 'Blizzard':
				if roll <= weather_odds_dict['precipitation']['Light Snow']:
					self.weather['Precipitation'] = 'Light Snow'
					ShowMessage('The snow gets quite a bit lighter.')
				elif roll <= weather_odds_dict['precipitation']['Snow']:
					self.weather['Precipitation'] = 'Snow'
					ShowMessage('The snow gets a bit lighter.')
				else:
					return
			
			# update animations
			self.InitAnimations()
			if scenario is not None:
				scenario.InitAnimations()
		
		# possible change in fog level
		elif roll <= 75.0:
			if campaign.stats['region'] == 'North Africa':
				return
			if self.weather['Cloud Cover'] == 'Clear' or self.weather['Temperature'] not in ['Cold', 'Mild']:
				return
			
			roll = GetPercentileRoll()
			
			if self.weather['Fog'] == 0:
				if self.weather['Precipitation'] in ['Snow', 'Blizzard']:
					roll += 20.0
				elif self.weather['Season'] in ['Spring', 'Autumn']:
					roll -= 10.0
				if self.weather['Ground'] in ['Wet', 'Muddy']:
					roll -= 5.0
				
				if roll <= 15.0:
					self.weather['Fog'] = 1
					ShowMessage('A light fog spreads across the area.')
			
			elif self.weather['Fog'] == 1:
				if roll <= 80.0:
					self.weather['Fog'] = 0
					ShowMessage('The fog has completely cleared.')
				elif roll <= 95.0:
					self.weather['Fog'] = 2
					ShowMessage('The fog thickens somewhat.')
				else:
					self.weather['Fog'] = 3
					ShowMessage('The fog suddenly becomes very thick.')
			
			elif self.weather['Fog'] == 2:
				if roll <= 20.0:
					self.weather['Fog'] = 0
					ShowMessage('The fog has completely cleared.')
				elif roll <= 90.0:
					self.weather['Fog'] = 1
					ShowMessage('The fog thins out a little.')
				else:
					self.weather['Fog'] = 3
					ShowMessage('The fog thickens somewhat.')
			
			elif self.weather['Fog'] == 3:
				if roll <= 20.0:
					self.weather['Fog'] = 1
					ShowMessage('The fog has thinned out a great deal.')
				else:
					self.weather['Fog'] = 2
					ShowMessage('The fog thins out a little.')
			
			# update scenario map console in case it's required
			if scenario is not None:
				scenario.UpdateHexmapCon()
		
		# change in cloud level
		else:
			
			if weather_odds_dict['cloud_cover']['Heavy'] == 0.0: return
			
			roll = GetPercentileRoll()
			
			if self.weather['Cloud Cover'] == 'Clear':
				if roll <= 85.0:
					self.weather['Cloud Cover'] = 'Scattered'
					ShowMessage('Scattered clouds begin to form.')
				else:
					self.weather['Cloud Cover'] = 'Heavy'
					ShowMessage('A heavy cloud front rolls in.')
			
			elif self.weather['Cloud Cover'] == 'Scattered':
				if roll <= 75.0:
					self.weather['Cloud Cover'] = 'Clear'
					ShowMessage('The clouds part and the sky is clear.')
				elif roll <= 90.0:
					self.weather['Cloud Cover'] = 'Heavy'
					ShowMessage('The cloud cover gets thicker.')
				else:
					self.weather['Cloud Cover'] = 'Overcast'
					ShowMessage('A storm front has rolled in.')
			
			elif self.weather['Cloud Cover'] == 'Heavy':
				if roll <= 85.0:
					self.weather['Cloud Cover'] = 'Scattered'
					ShowMessage('The clouds begin to thin out.')
				else:
					self.weather['Cloud Cover'] = 'Overcast'
					ShowMessage('The cloud cover thickens.')
			
			# overcast
			else:
				self.weather['Cloud Cover'] = 'Heavy'
				ShowMessage('The cloud cover begins to thin out but remains heavy.')
			
			# check for instant clearing of fog
			if self.weather['Fog'] > 0 and (self.weather['Cloud Cover'] == 'Clear' or self.weather['Temperature'] not in ['Cold', 'Mild']):
				self.weather['Fog'] = 0
				if scenario is not None:
					scenario.UpdateHexmapCon()
				ShowMessage('The fog suddenly clears up completely.')
			
			# stop any precipitation if clouds have cleared up
			if self.weather['Cloud Cover'] == 'Clear' and self.weather['Precipitation'] != 'None':
				self.weather['Precipitation'] = 'None'
				
				# stop animation
				self.InitAnimations()
				if scenario is not None:
					scenario.InitAnimations()

	
	# advance the current campaign day time, check for end of day, and also weather conditions update
	def AdvanceClock(self, hours, minutes, skip_checks=False):
		self.day_clock['hour'] += hours
		self.day_clock['minute'] += minutes
		while self.day_clock['minute'] >= 60:
			self.day_clock['hour'] += 1
			self.day_clock['minute'] -= 60
		
		if skip_checks: return
		
		self.CheckForEndOfDay()
		
		# check for weather update
		self.weather_update_clock -= hours * 60
		self.weather_update_clock -= minutes
		
		if self.weather_update_clock <= 0:
			# check for weather conditions change, update relevant consoles
			self.UpdateWeather()
			self.UpdateCDCommandCon()
			DisplayWeatherInfo(cd_weather_con)
			if scenario is not None:
				if scenario.init_complete:
					DisplayWeatherInfo(scen_weather_con)
		
	
	# sets flag if we've met or exceeded the set length of the combat day
	def CheckForEndOfDay(self):
		# already ended
		if self.ended: return
		if self.day_clock['hour'] > self.end_of_day['hour']:
			self.ended = True
		if self.day_clock['hour'] == self.end_of_day['hour']:
			if self.day_clock['minute'] >= self.end_of_day['minute']:
				self.ended = True
	
	
	# roll for trigger of random Campaign Day event
	def CheckForRandomEvent(self):
		
		# don't trigger an event if day has already ended
		if self.ended: return
		
		# don't trigger if a scenario just started
		if scenario is not None: return
		
		roll = GetPercentileRoll()
		
		if DEBUG:
			if session.debug['Always CD Random Event']:
				roll = 1.0
		
		# no event this time, increase chance for next time
		if roll > self.random_event_chance:
			self.random_event_chance += 2.0
			return
		
		# roll for type of event
		roll = GetPercentileRoll()
		
		# enemy strength increases
		if roll <= 30.0:
			hex_list = []
			for (hx, hy) in self.map_hexes:
				if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx,hy)].terrain_type]: continue
				if self.map_hexes[(hx,hy)].controlled_by == 0: continue
				hex_list.append((hx, hy))
			
			if len(hex_list) == 0:
				return
			
			(hx, hy) = choice(hex_list)
			map_hex = self.map_hexes[(hx,hy)]
			
			map_hex.enemy_strength += libtcod.random_get_int(0, 1, 3)
			if map_hex.enemy_strength > 10:
				map_hex.enemy_strength = 10
			
			map_hex.GenerateStrengthAndUnits(self.mission, skip_strength=True)
			
			# don't show anything if zone not known to player
			if not map_hex.known_to_player: return
			
			ShowMessage('We have reports of an increase of enemy strength in a zone!', cd_highlight=(hx,hy))
		
		# reveal enemy strength and units
		elif roll <= 40.0:
			
			hex_list = []
			for (hx, hy) in self.map_hexes:
				if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx,hy)].terrain_type]: continue
				if self.map_hexes[(hx,hy)].controlled_by == 0: continue
				if self.map_hexes[(hx,hy)].known_to_player: continue
				if self.map_hexes[(hx,hy)].objective is not None: continue
				hex_list.append((hx, hy))
			
			if len(hex_list) == 0:
				return
			
			(hx, hy) = choice(hex_list)
			self.map_hexes[(hx,hy)].known_to_player = True
			
			ShowMessage('We have received information about expected enemy presence in an area.', cd_highlight=(hx,hy))
		
		# loss of recon knowledge and possible change in strength/enemy units
		elif roll <= 60.0:
			
			hex_list = []
			for (hx, hy) in self.map_hexes:
				if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx,hy)].terrain_type]: continue
				if self.map_hexes[(hx,hy)].controlled_by == 0: continue
				if not self.map_hexes[(hx,hy)].known_to_player: continue
				hex_list.append((hx, hy))
			
			if len(hex_list) == 0:
				return
			
			(hx, hy) = choice(hex_list)
			map_hex = self.map_hexes[(hx,hy)]
			ShowMessage('Enemy movement reported in a map zone, estimated strength no longer certain.', cd_highlight=(hx,hy))
			map_hex.GenerateStrengthAndUnits(self.mission)
		
		# increase a current support level
		elif roll <= 75.0:
			
			choices = []
			if 'air_support_level' in campaign.current_week:
				choices.append('air_support_level')
			if 'arty_support_level' in campaign.current_week:
				choices.append('arty_support_level')
			if 'unit_support_level' in campaign.current_week:
				choices.append('unit_support_level')
			
			if len(choices) == 0: return
			
			support_type = choice(choices)
			text = 'Additional '
			if support_type == 'air_support_level':
				text += 'air'
				self.air_support_level += (5.0 * float(libtcod.random_get_int(0, 1, 4)))
				# make sure does not go beyond initial level
				if self.air_support_level > campaign.current_week['air_support_level']:
					self.air_support_level = campaign.current_week['air_support_level']
			elif support_type == 'arty_support_level':
				text += 'artillery'
				self.arty_support_level += (5.0 * float(libtcod.random_get_int(0, 1, 4)))
				if self.arty_support_level > campaign.current_week['arty_support_level']:
					self.arty_support_level = campaign.current_week['arty_support_level']
			else:
				text += 'unit'
				self.unit_support_level += (5.0 * float(libtcod.random_get_int(0, 1, 4)))
				if self.unit_support_level > campaign.current_week['unit_support_level']:
					self.unit_support_level = campaign.current_week['unit_support_level']
			
			text += ' support has made available to you from Command.'
			ShowMessage(text)
		
		# crewmen lose fatigue points
		elif roll <= 85.0:
			for position in campaign.player_unit.positions_list:
				if position.crewman is None: continue
				if not position.crewman.alive: continue
				position.crewman.fatigue -= int(position.crewman.stats['Morale'] / 2)
				if position.crewman.fatigue < BASE_FATIGUE:
					position.crewman.fatigue = BASE_FATIGUE
			ShowMessage('Your crew feel a little less fatigued than before.')
				
		# no other random events for now
		else:
			return
		
		# random event finished: reset random event chance, update consoles and screen
		self.random_event_chance = BASE_CD_RANDOM_EVENT_CHANCE
		self.UpdateCDUnitCon()
		self.UpdateCDControlCon()
		self.UpdateCDGUICon()
		self.UpdateCDCommandCon()
		self.UpdateCDHexInfoCon()
		self.UpdateCDDisplay()
	
	
	# check for zone capture/loss
	# if last player action was 'capture_zone', then the player's own zone won't be selected as one that
	# the enemy captures
	def CheckForZoneCapture(self, last_player_action):
		
		global scenario
		
		# don't trigger zone capture checks if day has already ended
		if self.ended: return
		
		# set modifiers for base odds of enemy/friendly zone capture
		if campaign_day.mission == 'Advance':
			friendly_multiplier = 3.0
			enemy_multipler = 0.3
		elif campaign_day.mission == 'Spearhead':
			friendly_multiplier = 0.5
			enemy_multipler = 0.2
		elif campaign_day.mission == 'Battle':
			friendly_multiplier = 1.0
			enemy_multipler = 1.0
		elif campaign_day.mission == 'Fighting Withdrawal':
			friendly_multiplier = 0.1
			enemy_multipler = 7.0
		elif campaign_day.mission == 'Counterattack':
			friendly_multiplier = 0.3
			enemy_multipler = 3.0
		elif campaign_day.mission == 'Patrol':
			friendly_multiplier = 0.1
			enemy_multipler = 0.1
		# no other missions for now
		else:
			return
		
		# build a list of hex zones that are liable to be captured, plus odds of their capture
		hex_list = []
		for (hx, hy) in self.map_hexes:
			
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx,hy)].terrain_type]:
				continue
			
			# skip if player present and just captured this zone
			if last_player_action == 'capture_zone':
				(player_hx, player_hy) = self.player_unit_location
				if hx == player_hx and hy == player_hy:
					continue
			
			# skip objective hexes other than Hold objectives
			if self.map_hexes[(hx,hy)].objective is not None:
				if self.map_hexes[(hx,hy)].objective['type'] != 'Hold':
					continue
			
			map_hex = self.map_hexes[(hx,hy)]
			
			# determine number of adjacent hexes held by other side
			adjacent_enemy_hexes = 0
			for direction in range(6):
				(hx2, hy2) = self.GetAdjacentCDHex(hx, hy, direction)
				if (hx2, hy2) not in self.map_hexes: continue
				
				# impassible hex
				if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx2,hy2)].terrain_type]:
					continue
				
				if self.map_hexes[(hx2,hy2)].controlled_by != map_hex.controlled_by:
					
					# if river crossing, chance that this one doesn't count
					if self.RiverCrossing(hx, hy, hx2, hy2):
						if GetPercentileRoll() <= 75.0:
							continue
					adjacent_enemy_hexes += 1
			
			# zones on top/bottom row automatically count as bordering two enemy hexes
			# if held by other side
			if campaign_day.mission in ['Fighting Withdrawal', 'Counterattack']:
				if hy == 0 and map_hex.controlled_by == 0:
					adjacent_enemy_hexes += 2
			elif campaign_day.mission in ['Advance', 'Spearhead', 'Battle', 'Patrol']:
				if hy == 8 and map_hex.controlled_by == 1:
					adjacent_enemy_hexes += 2
			
			if adjacent_enemy_hexes == 0: continue
			
			# enemy-held zone has been cut off
			if adjacent_enemy_hexes == 6 and map_hex.controlled_by == 1:
				map_hex.enemy_strength = int(map_hex.enemy_strength / 2)
			
			# add the hex to list of possible capture targets
			hex_list.append((hx, hy, adjacent_enemy_hexes))
			
		if len(hex_list) == 0:
			return
		
		# roll for each possible captured hex zone
		shuffle(hex_list)
		capture_list = []
		friendly_captures = 0
		enemy_captures = 0
		for (hx, hy, adjacent_enemy_hexes) in hex_list:
			
			odds = adjacent_enemy_hexes * CD_ZONE_CAPTURE_CHANCE
			
			if self.map_hexes[(hx,hy)].controlled_by == 0:
				odds = round(odds * enemy_multipler, 1)
			else:
				odds = round(odds * friendly_multiplier, 1)
			
			# modify final odds by last player action that triggered this check
			if last_player_action == 'wait':
				odds = round(odds * 1.3, 1)
			elif last_player_action == 'quick_move':
				odds = round(odds * 0.5, 1)
			if last_player_action == 'slow_move':
				odds = round(odds * 0.85, 1)
			
			if GetPercentileRoll() > odds: continue
			
			capture_list.append((hx, hy))
			
			# skip for now if this is player location
			if (hx, hy) == self.player_unit_location:
				continue
			
			# friendly hex zone captured
			if self.map_hexes[(hx,hy)].controlled_by == 0:
				self.map_hexes[(hx,hy)].CaptureMe(1)
				enemy_captures += 1
				
			# enemy hex zone captured
			else:
				self.map_hexes[(hx,hy)].CaptureMe(0, no_vp=True)
				friendly_captures += 1
				
		# show messages for captured zones
		if enemy_captures > 0:
			self.UpdateCDControlCon()
			self.UpdateCDDisplay()
			libtcod.console_flush()
			if enemy_captures == 1:
				ShowMessage('Enemy forces have captured an allied-held zone!')
			else:
				ShowMessage('Enemy forces have captured multiple allied-held zones!')
		
		if friendly_captures > 0:
			self.UpdateCDControlCon()
			self.UpdateCDDisplay()
			libtcod.console_flush()
			if friendly_captures == 1:
				ShowMessage('Allied forces have captured an enemy-held zone!') 
			else:
				ShowMessage('Allied forces have captured multiple enemy-held zones!')

		# update visibility of adjacent zones
		self.map_hexes[self.player_unit_location].RevealAdjacentZones()

		# player zone was in the capture list, trigger a scenario
		if self.player_unit_location in capture_list:
			ShowMessage('Enemy forces have attacked your zone!')
			campaign.AddJournal('Enemy forces attacked our zone.')
			session.ModifySteamStat('attacked_in_zone', 1)
			DisplayLoadingMsg()
			map_hex = self.map_hexes[self.player_unit_location]
			scenario = Scenario(map_hex)
			self.AddRecord('Battles Fought', 1)
		
		# update consoles and screen
		self.UpdateCDUnitCon()
		self.UpdateCDControlCon()
		self.UpdateCDGUICon()
		self.UpdateCDCommandCon()
		self.UpdateCDHexInfoCon()
		self.UpdateCDDisplay()
	
	
	# menu for restocking ammo for main guns on the player tank
	# is resupply is true, player is resupplying in the middle of a combat day
	def AmmoReloadMenu(self, resupply=False):
		
		# update the menu console and draw to screen
		def UpdateMenuCon():
			
			libtcod.console_clear(con)
			
			# window title
			libtcod.console_set_default_background(con, libtcod.dark_blue)
			libtcod.console_rect(con, 0, 2, WINDOW_WIDTH, 5, True, libtcod.BKGND_SET)
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print_ex(con, WINDOW_XM, 4, libtcod.BKGND_NONE,
				libtcod.CENTER, 'Ammo Load')
			
			# left column: description of ammo types available to current gun
			x = 2
			y = 9
			
			libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
			libtcod.console_print(con, x-1, y, 'Available Ammo Types')
			y += 3
			
			for ammo_type in weapon.stats['ammo_type_list']:
				
				if ammo_type not in AMMO_DESCRIPTIONS: continue
				
				(text1, text2) = AMMO_DESCRIPTIONS[ammo_type]
				libtcod.console_set_default_foreground(con, libtcod.white)
				
				lines = wrap(text1 + ' (' + ammo_type + ')', 26)
				for line in lines:
					libtcod.console_print(con, x, y, line)
					y += 1
				
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				lines = wrap(text2, 24)
				y += 1
				for line in lines:
					libtcod.console_print(con, x, y, line)
					y += 1
				
				# rare ammo type, not yet available
				if ammo_type in weapon.rare_ammo_na:
					libtcod.console_set_default_foreground(con, libtcod.light_red)
					libtcod.console_print(con, x, y, '(Not Yet Available)')
					y += 1
				
				# rare or otherwise limited ammo type
				elif ammo_type in weapon.rare_ammo:
					libtcod.console_set_default_foreground(con, libtcod.light_blue)
					libtcod.console_print(con, x, y, '(Limited Availability)')
					y += 1
				
				y += 3
			
			# dividing line
			libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			libtcod.console_vline(con, 30, 9, 45)
			
			# player unit portrait
			x = 33
			y = 9
			libtcod.console_set_default_background(con, PORTRAIT_BG_COL)
			libtcod.console_rect(con, x, y, 25, 8, True, libtcod.BKGND_SET)
			portrait = campaign.player_unit.GetStat('portrait')
			if portrait is not None:
				libtcod.console_blit(LoadXP(portrait), 0, 0, 0, 0, con, x, y)
			libtcod.console_set_default_foreground(con, libtcod.white)
			if campaign.player_unit.unit_name != '':
				libtcod.console_print(con, x, y, campaign.player_unit.unit_name)
			libtcod.console_set_default_background(con, libtcod.black)
			
			# list guns in gun list
			y = 18
			for gun in gun_list:
				if gun == weapon:
					libtcod.console_set_default_background(con, libtcod.dark_blue)
					libtcod.console_rect(con, WINDOW_XM-10, y, 20, 1, True, libtcod.BKGND_SET)
					libtcod.console_set_default_background(con, libtcod.black)
				libtcod.console_print_ex(con, WINDOW_XM, y, libtcod.BKGND_NONE,
					libtcod.CENTER, gun.GetStat('name'))
				y += 1
			
			
			# show current numerical values for each ammo type
			# also which type is currently selected
			x = 37
			y = 25
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_set_default_background(con, libtcod.darker_yellow)
			if not use_rr:
				libtcod.console_rect(con, x+9, y, 2, 1, False, libtcod.BKGND_SET)
			else:
				libtcod.console_rect(con, x+12, y, 2, 1, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			libtcod.console_print(con, x+9, y, 'ST')
			libtcod.console_print(con, x+12, y, 'RR')
			y += 1
			total_loaded = 0
			for ammo_type in weapon.stats['ammo_type_list']:
				if ammo_type in weapon.ammo_stores:
					
					# display amount remaining if limited supply
					if ammo_type in weapon.rare_ammo:
						
						# not yet available
						if ammo_type in weapon.rare_ammo_na:
							libtcod.console_print(con, x-4, y, 'N/A')
						else:
							amount = weapon.rare_ammo[ammo_type] - weapon.ammo_stores[ammo_type] - weapon.ready_rack[ammo_type]
							libtcod.console_set_default_foreground(con, AMMO_TYPE_COLOUR[ammo_type])
							libtcod.console_print(con, x-3, y, str(amount))
					
					if selected_ammo_type == ammo_type:
						libtcod.console_set_default_background(con, libtcod.dark_blue)
						libtcod.console_rect(con, x+2, y, 12, 1, True, libtcod.BKGND_SET)
						libtcod.console_set_default_background(con, libtcod.black)
					
					libtcod.console_put_char_ex(con, x, y, 7, AMMO_TYPE_COLOUR[ammo_type],
						libtcod.black)
					
					libtcod.console_set_default_foreground(con, libtcod.white)
					libtcod.console_print(con, x+2, y, ammo_type)
					
					libtcod.console_set_default_foreground(con, libtcod.light_grey)
					libtcod.console_print_ex(con, x+10, y, libtcod.BKGND_NONE,
						libtcod.RIGHT, str(weapon.ammo_stores[ammo_type]))
					libtcod.console_print_ex(con, x+13, y, libtcod.BKGND_NONE,
						libtcod.RIGHT, str(weapon.ready_rack[ammo_type]))
					total_loaded += weapon.ammo_stores[ammo_type]
					
					y += 1
			
			y += 1
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, x+2, y, 'Total')
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			libtcod.console_print_ex(con, x+10, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(ammo_num))
			libtcod.console_print_ex(con, x+13, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(rr_num))
			
			y += 1
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			libtcod.console_print(con, x+2, y, '------------')
			
			y += 1
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, x+2, y, 'Max')
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			libtcod.console_print_ex(con, x+10, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(weapon.max_ammo))
			libtcod.console_print_ex(con, x+13, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(weapon.rr_size))
			
			# note maximum possible extra ammo
			y += 2
			if total_loaded > weapon.max_ammo:
				libtcod.console_set_default_foreground(con, libtcod.light_red)
				text = str(total_loaded - weapon.max_ammo)
			else:
				text = '0'
			text += '/' + str(weapon.max_plus_extra_ammo - weapon.max_ammo)
			libtcod.console_print(con, x+2, y, 'Extra:')
			libtcod.console_print_ex(con, x+13, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			
			
			# command menu
			x = 34
			y = 40
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			if len(gun_list) == 1:
				libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			libtcod.console_print(con, x, y, EnKey('q').upper())
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, x, y+1, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(con, x, y+2, EnKey('r').upper())
			libtcod.console_print(con, x, y+4, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_print(con, x, y+5, EnKey('z').upper())
			libtcod.console_print(con, x, y+7, EnKey('x').upper())
			libtcod.console_print(con, x, y+10, 'Tab')
			
			
			libtcod.console_set_default_foreground(con, libtcod.white)
			if len(gun_list) == 1:
				libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			libtcod.console_print(con, x+4, y, 'Cycle Selected Gun')
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, x+4, y+1, 'Select Ammo Type')
			libtcod.console_print(con, x+4, y+2, 'Toggle Ready Rack')
			libtcod.console_print(con, x+4, y+4, 'Unload/Load ' + str(add_num))
			libtcod.console_print(con, x+4, y+5, 'Toggle 1/10')
			libtcod.console_print(con, x+4, y+7, 'Default Load')
			libtcod.console_print(con, x+4, y+10, 'Accept and Continue')
			
			
			# right column: visual depicition of main stores and ready rack
			x = 61
			y = 24
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, x, y, 'Stores')
			libtcod.console_print(con, x+10, y, 'Ready Rack')
			
			# highlight active stores
			libtcod.console_set_default_background(con, libtcod.darker_yellow)
			if not use_rr:
				xh = x
				w = 9
			else:
				xh = x+10
				w = 10
			libtcod.console_rect(con, xh, y, w, 1, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			
			y += 2
			
			ammo_count = weapon.ammo_stores.copy()
			rr_count = weapon.ready_rack.copy()
			
			# main stores
			libtcod.console_set_default_foreground(con, libtcod.darker_grey)
			xm = 0
			ym = 0
			total = 0
			bg_col = libtcod.black
			for ammo_type in AMMO_TYPES:
				if ammo_type in ammo_count:
					for i in range(ammo_count[ammo_type]):
						
						# if we're in extra ammo territory, set background colour to red
						if total >= weapon.max_ammo:
							bg_col = libtcod.dark_red
	
						libtcod.console_put_char_ex(con, x+xm, y+ym, 7,
							AMMO_TYPE_COLOUR[ammo_type], bg_col)
						
						if xm == 8:
							xm = 0
							ym += 1
						else:
							xm += 1
						
						total += 1
			
			# fill out empty slots up to max ammo
			if total < weapon.max_ammo:
				for i in range(weapon.max_ammo - total):
					libtcod.console_put_char(con, x+xm, y+ym, 9)
					if xm == 8:
						xm = 0
						ym += 1
					else:
						xm += 1
			
			# ready rack
			x += 10
			libtcod.console_set_default_foreground(con, libtcod.darker_grey)
			xm = 0
			ym = 0
			total = 0
			for ammo_type in AMMO_TYPES:
				if ammo_type in rr_count:
					for i in range(rr_count[ammo_type]):
						libtcod.console_put_char_ex(con, x+xm, y+ym, 7,
							AMMO_TYPE_COLOUR[ammo_type], libtcod.black)
						if xm == 8:
							xm = 0
							ym += 1
						else:
							xm += 1
						
						total += 1
			
			# fill out empty slots up to max ready rack size
			if total < weapon.rr_size:
				for i in range(weapon.rr_size - total):
					libtcod.console_put_char(con, x+xm, y+ym, 9)
					if xm == 8:
						xm = 0
						ym += 1
					else:
						xm += 1
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		
		# (re)calculate total ammo loads, max load, and max extra ammo
		def CalculateAmmoLoads():
			ammo_num = 0
			for ammo_type in AMMO_TYPES:
				if ammo_type in weapon.ammo_stores:
					ammo_num += weapon.ammo_stores[ammo_type]
			rr_num = 0
			for ammo_type in AMMO_TYPES:
				if ammo_type in weapon.ready_rack:
					rr_num += weapon.ready_rack[ammo_type]
			return (ammo_num, rr_num)
		
		
		
		ammo_num = 0
		rr_num = 0
		add_num = 1
		use_rr = False
		
		# Build list of all guns on unit
		gun_list = []
		for weapon in campaign.player_unit.weapon_list:
			if weapon.stats['type'] != 'Gun': continue
			gun_list.append(weapon)
		
		# no guns to load
		if len(gun_list) == 0: return
		
		# build list of rare ammo
		for weapon in gun_list:
			weapon.GenerateRareAmmo(resupply=resupply)
			
		# select first weapon in list and first ammo type
		weapon = gun_list[0]
		selected_ammo_type = weapon.stats['ammo_type_list'][0]
		
		# calculate current ammo load
		(ammo_num, rr_num) = CalculateAmmoLoads()
		
		# draw screen for first time
		UpdateMenuCon()
		
		# menu input loop
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			keypress = GetInputEvent()
			if not keypress: continue
			
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				
				# check to see if player might have skipped this step by mistake
				no_ammo_loaded = False
				for gun in gun_list:
					total_ammo = 0
					for ammo_type in AMMO_TYPES:
						if ammo_type in gun.ammo_stores:
							total_ammo += gun.ammo_stores[ammo_type]
					
					if total_ammo == 0:
						no_ammo_loaded = True
						break
				
				if no_ammo_loaded:
					text = 'No ammo loaded in at least one gun! Are you sure you want to proceed?'
					if ShowNotification(text, confirm=True):
						exit_menu = True
						continue
				else:
					exit_menu = True
					continue
			
			# mapped key commands
			key_char = DeKey(chr(key.c).lower())
			
			# cycle selected gun
			if key_char == 'q':
				if len(gun_list) == 1: continue
				
				i = gun_list.index(weapon)
				if i == len(gun_list) - 1:
					weapon = gun_list[0]
				else:
					weapon = gun_list[i+1]
				
				# calculate ammo load numbers for this gun
				(ammo_num, rr_num) = CalculateAmmoLoads()
				UpdateMenuCon()
				continue
			
			# change selected ammo type
			elif key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				i = weapon.stats['ammo_type_list'].index(selected_ammo_type)
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if i == 0:
						i = len(weapon.stats['ammo_type_list']) - 1
					else:
						i -= 1
				else:
					if i == len(weapon.stats['ammo_type_list']) - 1:
						i = 0
					else:
						i += 1
				selected_ammo_type = weapon.stats['ammo_type_list'][i]
				UpdateMenuCon()
				continue
			
			# toggle load/unload ready rack
			elif key_char == 'r':
				use_rr = not use_rr
				UpdateMenuCon()
				continue
			
			# load 1/10 shell of selected type
			elif key_char == 'd' or key.vk == libtcod.KEY_RIGHT:
				
				real_add_num = add_num
				
				# if rare ammo, make sure enough remains to load selected amount
				if selected_ammo_type in weapon.rare_ammo:
					if weapon.rare_ammo[selected_ammo_type] == 0: continue
					amount = weapon.rare_ammo[selected_ammo_type] - weapon.ammo_stores[selected_ammo_type] - weapon.ready_rack[selected_ammo_type] - add_num
					if amount < 0: continue
				
				# make sure there is enough room before loading, otherwise add as many as possible
				if use_rr:
					if rr_num + add_num > weapon.rr_size:
						real_add_num = weapon.rr_size - rr_num
						if real_add_num < 0: real_add_num = 0
					weapon.ready_rack[selected_ammo_type] += real_add_num
					rr_num += real_add_num
				else:
					if ammo_num + add_num > weapon.max_plus_extra_ammo:
						real_add_num = weapon.max_plus_extra_ammo - ammo_num
						if real_add_num < 0: real_add_num = 0
					weapon.ammo_stores[selected_ammo_type] += real_add_num
					ammo_num += real_add_num
				
				if real_add_num == 0: continue
				
				if real_add_num == 1:
					PlaySoundFor(None, 'move_1_shell')
				else:
					PlaySoundFor(None, 'move_10_shell')
				UpdateMenuCon()
				continue
			
			# unload 1/10 shell of selected type
			elif key_char == 'a' or key.vk == libtcod.KEY_LEFT:
				
				real_add_num = add_num
				
				# make sure shell(s) are available, remove as many as possible
				if use_rr:
					if weapon.ready_rack[selected_ammo_type] - add_num < 0:
						real_add_num = weapon.ready_rack[selected_ammo_type]
					weapon.ready_rack[selected_ammo_type] -= real_add_num
					rr_num -= real_add_num
				else:
				
					if weapon.ammo_stores[selected_ammo_type] - add_num < 0:
						real_add_num = weapon.ammo_stores[selected_ammo_type]
					weapon.ammo_stores[selected_ammo_type] -= real_add_num
					ammo_num -= real_add_num
				
				if real_add_num == 0: continue
				
				if real_add_num == 1:
					PlaySoundFor(None, 'move_1_shell')
				else:
					PlaySoundFor(None, 'move_10_shell')
				UpdateMenuCon()
				continue
			
			# toggle adding/removing 1/10
			elif key_char == 'z':
				
				if add_num == 1:
					add_num = 10
				else:
					add_num = 1
				UpdateMenuCon()
				continue
			
			# replace current load with default
			elif key_char == 'x':
				(ammo_num, rr_num) = weapon.AddDefaultAmmoLoad()
				PlaySoundFor(None, 'move_10_shell')
				UpdateMenuCon()
				continue
		
		# for each gun, select the first ammo type as default
		for weapon in gun_list:
			weapon.ammo_type = weapon.stats['ammo_type_list'][0]
		
	
	# check to see whether crew within this unit recover from negative statuses
	# called after a scenario is finished
	# at present this is only used for player unit, but in future could be used for AI units as well
	def DoCrewRecoveryCheck(self, unit):
		
		# don't bother for dead units or if campaign is already over
		if not unit.alive or campaign.ended: return
		
		for position in unit.positions_list:
			if position.crewman is None: continue
			if not position.crewman.alive: continue
		
			# Shaken, Stunned, and Unconscious crew automatically recover
			position.crewman.condition = 'Good Order'
			
			# do a final check for each critical wound improving or getting worse
			for (k, v) in position.crewman.injury.items():
				if v is None: continue
				if v != 'Critical': continue
				roll = GetPercentileRoll() - 20.0
				
				if roll <= position.crewman.stats['Grit'] * 10.0:
					position.crewman.injury[k] = 'Serious'
					continue
				else:
					# check for fate point usage
					if position.crewman.is_player_commander and campaign_day.fate_points > 0:
						campaign_day.fate_points -= 1
						position.crewman.injury[k] = 'Serious'
						continue
					
					position.crewman.KIA()
					if position.crewman.is_player_commander:
						text = 'You succumb to your ' + k + ' injury and die. Your campaign is over.'
					else:
						text = 'Your crewman succumbed to their ' + k + ' injury and has died.'
					ShowMessage(text,crewman=position.crewman)
					campaign.AddJournal(text)
					break
				
	
	# check to see whether dead or seriously injured crewmen need to be replaced in this unit
	def DoCrewReplacementCheck(self, unit):
		
		# don't do for any unit other than the player unit right now
		if unit != campaign.player_unit: return
		
		# don't bother for dead units or if campaign is already over
		if not unit.alive or campaign.ended: return
				
		# add new recruits to fill in any empty positions
		for position in unit.positions_list:
			if position.crewman is None:
				position.crewman = Personnel(unit, unit.nation, position)
				text = 'A new crewman joins your crew in the ' + position.name + ' position.'
				ShowMessage(text)
	
	
	# generate roads linking zones; only dirt roads for now
	def GenerateRoads(self):
		
		# clear any existing roads
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			for direction in range(6):
				self.map_hexes[(hx,hy)].road_links[direction] = None
		
		# see if a road network is generated on this map
		dirt_road = False
		stone_road = False
		
		if GetPercentileRoll() <= float(REGIONS[campaign.stats['region']]['stone_road_odds']):
			stone_road = True
		if GetPercentileRoll() <= float(REGIONS[campaign.stats['region']]['dirt_road_odds']):
			dirt_road = True
		
		# no roads generated
		if not dirt_road and not stone_road: return
		
		# choose a random edge hex
		edge_list = []
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			
			# don't include impassible hexes for starting point
			if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx,hy)].terrain_type]:
				continue
			
			for d in range(6):
				if self.GetAdjacentCDHex(hx, hy, d) not in CAMPAIGN_DAY_HEXES:
					edge_list.append((hx, hy))
					break
		(hx1, hy1) = choice(edge_list)
		
		# find the hex on opposite edge of map
		hx2 = hx1 * -1
		if hy1 > 4:
			hy2 = hy1 - ((hy1 - 4) * 2)
		elif hy1 == 4:
			hy2 = 4
		else:
			hy2 = hy1 + ((4 - hy1) * 2)
		
		# plot the road
		hex_path = self.GetHexPath(hx1, hy1, hx2, hy2, avoid_terrain=['Fortress'])
		
		for i in range(len(hex_path)-1):
			(hx1,hy1) = hex_path[i]
			(hx2,hy2) = hex_path[i+1]
			d = self.GetDirectionToAdjacentCD(hx1,hy1,hx2,hy2)
			if stone_road:
				self.map_hexes[(hx1,hy1)].road_links[d] = True
				self.map_hexes[(hx2,hy2)].road_links[ConstrainDir(d + 3)] = True
			else:
				self.map_hexes[(hx1,hy1)].road_links[d] = False
				self.map_hexes[(hx2,hy2)].road_links[ConstrainDir(d + 3)] = False
		
		
		# link all settled hexes to a road branch - using dirt roads only
		# build a list of all settled hexes
		hex_list = []
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if self.map_hexes[(hx,hy)].terrain_type in ['Villages']:
				
				# already on a road
				if self.map_hexes[(hx,hy)].road_links != [None,None,None,None,None,None]: continue
							
				hex_list.append((hx, hy))
		
		if len(hex_list) > 0:
			shuffle(hex_list)
			for (hx1, hy1) in hex_list:
				
				# find the nearest CD map hex with at least one road link
				link_list = []
				for (hx2, hy2) in CAMPAIGN_DAY_HEXES:
					# same hex
					if hx2 == hx1 and hy2 == hy1: continue
					
					# no roads there
					if self.map_hexes[(hx2,hy2)].road_links == [None,None,None,None,None,None]: continue
										
					# get the distance to the possible link
					d = GetHexDistance(hx1, hy1, hx2, hy2)
					
					link_list.append((d,hx2,hy2))
				
				# no possible links!
				if len(link_list) == 0:
					continue
				
				# sort the list by distance and get the nearest one
				link_list.sort(key = lambda x: x[0])
				(d,hx2,hy2) = link_list[0]
				
				# generate a road to link the two
				hex_path = self.GetHexPath(hx1, hy1, hx2, hy2, avoid_terrain=['Fortress'])
				for i in range(len(hex_path)-1):
					(hx1,hy1) = hex_path[i]
					(hx2,hy2) = hex_path[i+1]
					d = self.GetDirectionToAdjacentCD(hx1,hy1,hx2,hy2)
					self.map_hexes[(hx1,hy1)].road_links[d] = False
					self.map_hexes[(hx2,hy2)].road_links[ConstrainDir(d + 3)] = False
				
	
	
	# generate rivers and bridges along hex zone edges
	def GenerateRivers(self):
		
		# no rivers in this region at all
		if 'river_odds' not in REGIONS[campaign.stats['region']]:
			return
		
		# clear any existing rivers and bridges
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			self.map_hexes[(hx,hy)].rivers = []
			self.map_hexes[(hx,hy)].bridges = []
		self.cd_map_bridge_locations = []
		
		# roll for how many rivers are on map (max 2)
		rivers = 0
		odds = float(REGIONS[campaign.stats['region']]['river_odds'])
		if GetPercentileRoll() <= odds:
			rivers += 1
			if GetPercentileRoll() <= odds:
				rivers += 1
		if rivers == 0: return
		
		# create the rivers
		for i in range(rivers):
			
			# build a list of map edge hexes
			edge_list = []
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				for d in range(6):
					if self.GetAdjacentCDHex(hx, hy, d) not in CAMPAIGN_DAY_HEXES:
						edge_list.append((hx, hy))
						break
			
			# determine starting and ending hex 
			(hx1, hy1) = choice(edge_list)
			shuffle(edge_list)
			for (hx2, hy2) in edge_list:
				if GetHexDistance(hx1, hy1, hx2, hy2) < 5: continue
				break
			
			# run through the hex line
			hex_line = GetHexLine(hx1, hy1, hx2, hy2)
			for index in range(len(hex_line)):
			
				(hx, hy) = hex_line[index]
				
				# hex is off map; should not happen
				if (hx, hy) not in CAMPAIGN_DAY_HEXES: continue
				
				# chance that river will end within map
				if GetPercentileRoll() <= 2.0:
					break
				
				# each hex needs 1+ hexsides to become rivers
				
				# determine direction to previous hex
				if hx == hx1 and hy == hy1:
					
					# for first hex, we need to use off-board hex as previous location
					for direction1 in range(6):
						if self.GetAdjacentCDHex(hx, hy, direction1) not in CAMPAIGN_DAY_HEXES:
							break
				
				else:
					# otherwise use direction toward previous hex
					(hx_n, hy_n) = hex_line[index-1]
					direction1 = self.GetDirectionToAdjacentCD(hx, hy, hx_n, hy_n)
				
				# determine direction to next hex
				
				# for final hex, we need to use an off-board hex as next location
				if index == len(hex_line) - 1:
					for direction2 in range(6):
						if self.GetAdjacentCDHex(hx, hy, direction2) not in CAMPAIGN_DAY_HEXES:
							break
				else:
					# otherwise try to use direction toward next hex
					(hx_n, hy_n) = hex_line[index+1]
					direction2 = self.GetDirectionToAdjacentCD(hx, hy, hx_n, hy_n)
				
				# determine rotation path (clockwise or counter clockwise)
				path1 = []
				for i in range(6):
					path1.append(ConstrainDir(direction1 + i))
					if ConstrainDir(direction1 + i) == direction2: break
					
				path2 = []
				for i in range(6):
					path2.append(ConstrainDir(direction1 - i))
					if ConstrainDir(direction1 - i) == direction2: break
				
				# pick shortest path
				if len(path1) < len(path2):
					path = path1
				else:
					path = path2
				
				for direction in path[1:]:
					# may have already been added by an earlier river
					if direction in self.map_hexes[(hx,hy)].rivers: continue
				
					self.map_hexes[(hx,hy)].rivers.append(direction)
					
					# add bridge if road already present between the two hexes
					if self.map_hexes[(hx,hy)].road_links[direction] is not None:
						if direction not in self.map_hexes[(hx,hy)].bridges:
							self.map_hexes[(hx,hy)].bridges.append(direction)
						continue
					
					# randomly add bridges
					if direction not in self.map_hexes[(hx,hy)].bridges:
						
						# don't add if zone in this direction is impassible
						(hx2, hy2) = self.GetAdjacentCDHex(hx, hy, direction) 
						if (hx2, hy2) in CAMPAIGN_DAY_HEXES:
							if 'impassible' in CD_TERRAIN_TYPES[self.map_hexes[(hx2,hy2)].terrain_type]:
								continue
						
						if GetPercentileRoll() <= 10.0:
							self.map_hexes[(hx,hy)].bridges.append(direction)
		
		
	# plot the centre of a day map hex location onto the map console
	# top left of hex 0,0 will appear at cell 2,2
	def PlotCDHex(self, hx, hy):
		x = (hx*6) + (hy*3)
		y = (hy*5)
		return (x+5,y+6)
	
	
	# returns the hx, hy location of the adjacent hex in direction
	def GetAdjacentCDHex(self, hx1, hy1, direction):
		(hx_m, hy_m) = CD_DESTHEX[direction]
		return (hx1+hx_m, hy1+hy_m)
	
	
	# returns the direction toward an adjacent hex
	def GetDirectionToAdjacentCD(self, hx1, hy1, hx2, hy2):
		hx_mod = hx2 - hx1
		hy_mod = hy2 - hy1
		if (hx_mod, hy_mod) in CD_DESTHEX:
			return CD_DESTHEX.index((hx_mod, hy_mod))
			# hex is not adjacent
			return -1
	
	
	# display an after-action report with information on a completed campaign day
	def DisplayCampaignDaySummary(self):
		
		# load and display AAR background image
		libtcod.console_blit(LoadXP('aar_report_bkg.xp'), 0, 0, 0, 0, con, 0, 0)
		
		libtcod.console_set_default_foreground(con, libtcod.black)
		
		# campaign name, menu title, and date
		lines = wrap(campaign.stats['name'], 20)
		y = 3
		for line in lines[:2]:
			libtcod.console_print_ex(con, 26, y, libtcod.BKGND_NONE, libtcod.CENTER,
				line)
			y+=1
		libtcod.console_print_ex(con, 26, 6, libtcod.BKGND_NONE, libtcod.CENTER,
			'After-Action Report')
		libtcod.console_print_ex(con, 26, 9, libtcod.BKGND_NONE, libtcod.CENTER,
			GetDateText(campaign.today))
		
		libtcod.console_print(con, 10, 11, '. . . . . . . . . . . . . . . . .')
		
		# day result: survived or destroyed
		libtcod.console_print(con, 10, 14, 'Outcome of Day:')
		
		if campaign.player_oob:
			col = libtcod.red
			text = 'COMMANDER OUT OF ACTION'
		elif campaign_day.abandoned_tank:
			col = libtcod.light_grey
			text = 'ABANDONED TANK'
		elif campaign.player_unit.immobilized:
			col = libtcod.light_red
			text = 'IMMOBILIZED'
		elif campaign.player_unit.alive:
			col = libtcod.light_blue
			text = 'SURVIVED'
		else:
			col = ENEMY_UNIT_COL
			text = 'TANK LOST'
		libtcod.console_set_default_foreground(con, col)
		libtcod.console_print_ex(con, 26, 16, libtcod.BKGND_NONE, libtcod.CENTER,
			text)
		
		# player survived another combat day
		if text == 'SURVIVED':
			session.ModifySteamStat('days_survived', 1)
		
		# stats
		libtcod.console_set_default_foreground(con, libtcod.black)
		libtcod.console_print(con, 10, 19, 'Stats:')
		y = 21
		for text in RECORD_LIST:
			libtcod.console_print(con, 13, y, text + ':')
			libtcod.console_print_ex(con, 39, y, libtcod.BKGND_NONE, libtcod.RIGHT,
				str(campaign_day.records[text]))
			y += 1
			if y == 56:
				break
		
		# second page
		# enemy units destroyed
		libtcod.console_print_ex(con, 63, 6, libtcod.BKGND_NONE, libtcod.CENTER,
			'Enemy Units Destroyed')
		y = 9
		
		if len(campaign_day.enemies_destroyed) == 0:
			libtcod.console_print(con, 48, y, 'None')
		else:
			for (unit_id, number) in campaign_day.enemies_destroyed.items():
				libtcod.console_print(con, 48, y, unit_id)
				libtcod.console_print_ex(con, 79, y, libtcod.BKGND_NONE, libtcod.RIGHT,
					'x ' + str(number))
				y += 1
				if y == 41: break
		
		libtcod.console_print(con, 47, 43, '. . . . . . . . . . . . . . . . .')
		
		# VP earned
		libtcod.console_print(con, 47, 45, 'Base VP Earned:')
		libtcod.console_print(con, 47, 46, 'Campaign Options Modifier:')
		libtcod.console_print(con, 47, 47, 'Player Unit Modifier:')
		libtcod.console_print(con, 47, 49, 'Total VP Earned Today:')
		
		libtcod.console_set_default_foreground(con, libtcod.blue)
		
		# calculate and display base day vp
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if self.map_hexes[(hx,hy)].objective is None: continue
			if self.map_hexes[(hx,hy)].objective['type'] == 'Hold' and self.map_hexes[(hx,hy)].controlled_by == 0:
				self.day_vp += self.map_hexes[(hx,hy)].objective['vp_reward']
		libtcod.console_print_ex(con, 79, 45, libtcod.BKGND_NONE, libtcod.RIGHT,
			str(self.day_vp))
		
		# campaign options modifier if any
		if campaign.vp_modifier == 0.0:
			text = '--'
		else:
			self.day_vp += int(float(self.day_vp) * campaign.vp_modifier)
			if campaign.vp_modifier > 0.0:
				text = '+'
			else:
				text = ''
			text += str(int(campaign.vp_modifier * 100.0)) + '%'
		libtcod.console_print_ex(con, 79, 46, libtcod.BKGND_NONE, libtcod.RIGHT,
			text)
		
		# tank model vp modifier if any
		text = '--'
		if 'tank_vp_modifiers' in campaign.stats:
			if campaign.player_unit.unit_id in campaign.stats['tank_vp_modifiers']:
				text = ''
				self.day_vp = int(float(self.day_vp) * campaign.stats['tank_vp_modifiers'][campaign.player_unit.unit_id])
				modifier = campaign.stats['tank_vp_modifiers'][campaign.player_unit.unit_id]
				if modifier > 1.0:
					text = '+'
				text += str(int(round((modifier - 1.0) * 100.0, 0))) + '%'
		libtcod.console_print_ex(con, 79, 47, libtcod.BKGND_NONE, libtcod.RIGHT,
			text)
		
		# final earned VP
		libtcod.console_print_ex(con, 79, 49, libtcod.BKGND_NONE, libtcod.RIGHT,
			str(self.day_vp))
		
		libtcod.console_set_default_foreground(con, libtcod.black)
		libtcod.console_print(con, 47, 52, '. . . . . . . . . . . . . . . . .')
		
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 56, 55, 'Tab')
		libtcod.console_set_default_foreground(con, libtcod.black)
		libtcod.console_print(con, 64, 55, 'Continue')
		
		# display console to screen
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# get input from player
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# end menu
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				exit_menu = True
	
	
	##### Campaign Day Console Functions #####
	
	# generate/update the campaign day map console, 35x53
	def UpdateCDMapCon(self):
		
		def RecordScreenLocations(hx, hy):
			self.cd_map_index[(x, y-3)] = (hx, hy)
			for x1 in range(x-1, x+2):
				self.cd_map_index[(x1, y-2)] = (hx, hy)
				self.cd_map_index[(x1, y+2)] = (hx, hy)
			for x1 in range(x-2, x+3):
				self.cd_map_index[(x1, y-1)] = (hx, hy)
				self.cd_map_index[(x1, y)] = (hx, hy)
				self.cd_map_index[(x1, y+1)] = (hx, hy)
			self.cd_map_index[(x, y+3)] = (hx, hy)
		
		CHAR_LOCATIONS = [
			(3,1), (2,2), (3,2), (4,2), (1,3), (2,3), (3,3), (4,3), (5,3),
			(1,4), (2,4), (4,4), (5,4), (1,5), (2,5), (3,5), (4,5), (5,5),
			(2,6), (3,6), (4,6), (3,7)
		]
		CLOSE_CHAR_LOCATIONS = [
			(3,2), (2,3), (3,3), (4,3), (2,4), (4,4), (2,5), (3,5), (4,5),
			(3,6)
		]
		
		def GetRandomLocation():
			return CHAR_LOCATIONS[libtcod.random_get_int(generator, 0, 21)]
		
		libtcod.console_clear(cd_map_con)
		self.cd_map_index = {}
		
		# draw map hexes to console
		# load base zone image - depends on region and current ground conditions
		if self.weather['Ground'] in ['Snow', 'Deep Snow']:
			dayhex = LoadXP('dayhex_openground_snow.xp')
			bg_col = libtcod.Color(158,158,158)
		elif campaign.stats['region'] == 'North Africa':
			dayhex = LoadXP('dayhex_openground_desert.xp')
			bg_col = libtcod.Color(128,102,64)
		else:
			dayhex = LoadXP('dayhex_openground.xp')
			bg_col = libtcod.Color(0,64,0)
		temp_con = libtcod.console_new(7, 9)
		libtcod.console_set_key_color(temp_con, KEY_COLOR)
		
		# draw any Ocean hexes first, so that other hexes are drawn overtop
		for (hx, hy), cd_hex in self.map_hexes.items():
			if cd_hex.terrain_type != 'Ocean': continue
			(x,y) = self.PlotCDHex(hx, hy)
			# use special hex image here
			libtcod.console_blit(LoadXP('dayhex_ocean.xp'), 0, 0, 0, 0, temp_con, 0, 0)
			libtcod.console_blit(temp_con, 0, 0, 0, 0, cd_map_con, x-3, y-4)
			RecordScreenLocations(hx, hy)
		
		for (hx, hy), cd_hex in self.map_hexes.items():
			
			if cd_hex.terrain_type == 'Ocean': continue
			
			# generate console image for this zone's terrain type
			libtcod.console_blit(dayhex, 0, 0, 0, 0, temp_con, 0, 0)
			
			generator = libtcod.random_new_from_seed(cd_hex.console_seed)
			
			if campaign.stats['region'] == 'North Africa' and cd_hex.terrain_type == 'Flat':
				for (x,y) in CHAR_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 30) <= 29: continue
					libtcod.console_put_char_ex(temp_con, x, y, 247, libtcod.Color(102,82,51), bg_col)
			
			elif cd_hex.terrain_type == 'Forest':
				for (x,y) in CHAR_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 10) <= 4: continue
					
					char = 6
					if self.weather['Ground'] in ['Snow', 'Deep Snow']:
						if libtcod.random_get_int(generator, 1, 2) == 1:
							char = 24
							if libtcod.random_get_int(generator, 1, 3) == 1: char += 100
							col = libtcod.Color(libtcod.random_get_int(generator, 60, 100),20,20)
						else:
							col = libtcod.Color(0,libtcod.random_get_int(generator, 100, 170),0)
					
					elif campaign.stats['region'] == 'North Africa':
						col = libtcod.Color(0,libtcod.random_get_int(generator, 60, 100),0)
					
					elif self.weather['Season'] == 'Spring':
						if libtcod.random_get_int(generator, 1, 20) == 1:
							c = libtcod.random_get_int(generator, 200, 220)
							col = libtcod.Color(c,50,c)
						else:
							col = libtcod.Color(0,libtcod.random_get_int(generator, 100, 170),0)
					
					elif self.weather['Season'] == 'Autumn':
						roll = libtcod.random_get_int(generator, 1, 10)
						if roll <= 2:
							c = libtcod.random_get_int(generator, 120, 160)
							col = libtcod.Color(c,0,0)
						elif roll <= 4:
							c = libtcod.random_get_int(generator, 90, 110)
							col = libtcod.Color(c*2,c,0)
						elif roll <= 4:
							c = libtcod.random_get_int(generator, 80, 100)
							col = libtcod.Color(c,80,50)
						else:
							col = libtcod.Color(0,libtcod.random_get_int(generator, 100, 170),0)
					
					else:
						col = libtcod.Color(0,libtcod.random_get_int(generator, 100, 170),0)
					
					libtcod.console_put_char_ex(temp_con, x, y, char, col, bg_col)
				
			elif cd_hex.terrain_type == 'Hills':
				if self.weather['Ground'] in ['Snow', 'Deep Snow']:
					c = libtcod.random_get_int(generator, 170, 210)
					col = libtcod.Color(c,c,c)
				elif campaign.stats['region'] == 'North Africa':
					c = libtcod.random_get_int(generator, -15, 15)
					col = libtcod.Color(160+c,130+c,100+c)
				else:
					col = libtcod.Color(70,libtcod.random_get_int(generator, 110, 150),0)
				x = libtcod.random_get_int(generator, 2, 3)
				libtcod.console_put_char_ex(temp_con, x, 2, 236, col, bg_col)
				libtcod.console_put_char_ex(temp_con, x+1, 2, 237, col, bg_col)
				
				if libtcod.random_get_int(generator, 0, 1) == 0:
					x = 1
				else:
					x = 4
				libtcod.console_put_char_ex(temp_con, x, 4, 236, col, bg_col)
				libtcod.console_put_char_ex(temp_con, x+1, 4, 237, col, bg_col)
				
				x = libtcod.random_get_int(generator, 2, 3)
				libtcod.console_put_char_ex(temp_con, x, 6, 236, col, bg_col)
				libtcod.console_put_char_ex(temp_con, x+1, 6, 237, col, bg_col)
			
			elif cd_hex.terrain_type == 'Mountains':
				c = libtcod.random_get_int(generator, -5, 5)
				col = libtcod.Color(75+c,75+c,75+c)
				col2 = libtcod.Color(75+c-10,75+c-10,75+c-10)
				
				for (x,y) in CHAR_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 3) == 1: continue
					libtcod.console_put_char_ex(temp_con, x, y, 177, col2, bg_col)
				
				# top and bottom rows
				x = libtcod.random_get_int(generator, 2, 3)
				libtcod.console_put_char_ex(temp_con, x, 2, 16, col, bg_col)
				libtcod.console_put_char_ex(temp_con, x+1, 2, 31, col, bg_col)
				x = libtcod.random_get_int(generator, 2, 3)
				libtcod.console_put_char_ex(temp_con, x, 6, 16, col, bg_col)
				libtcod.console_put_char_ex(temp_con, x+1, 6, 31, col, bg_col)
				
				# second and fourth rows
				for y in [3,5]:
					x = libtcod.random_get_int(generator, 1, 4)
					libtcod.console_put_char_ex(temp_con, x, y, 16, col, bg_col)
					libtcod.console_put_char_ex(temp_con, x+1, y, 31, col, bg_col)
				
				# middle row
				x = libtcod.random_get_int(generator, 2, 3)
				libtcod.console_put_char_ex(temp_con, x, 4, 16, col, bg_col)
				libtcod.console_put_char_ex(temp_con, x+1, 4, 31, col, bg_col)
				
			elif cd_hex.terrain_type == 'Fields':
				for (x,y) in CHAR_LOCATIONS:
					if self.weather['Ground'] in ['Snow', 'Deep Snow']:
						col = libtcod.Color(50,40,20)
						char = 124
					else:
						c = libtcod.random_get_int(generator, 120, 190)
						col = libtcod.Color(c,c,0)
						char = 176
					libtcod.console_put_char_ex(temp_con, x, y, char,
						col, bg_col)
				
			elif cd_hex.terrain_type == 'Marsh':
				elements = libtcod.random_get_int(generator, 7, 13)
				while elements > 0:
					(x,y) = GetRandomLocation()
					if libtcod.console_get_char(temp_con, x, y) == 176: continue
					libtcod.console_put_char_ex(temp_con, x, y, 176,
						libtcod.Color(45,0,180), bg_col)
					elements -= 1
				
			elif cd_hex.terrain_type == 'Villages':
				for (x,y) in CLOSE_CHAR_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 2) == 1: continue
					c = libtcod.random_get_int(generator, 1, 4)
					if c <= 3:
						char = 249
						if campaign.stats['region'] == 'North Africa':
							col = libtcod.Color(190,170,140)
						else:
							col = libtcod.Color(77,77,77)
					else:
						char = 15
						col = libtcod.darkest_green
					libtcod.console_put_char_ex(temp_con, x, y, char,
						col, bg_col)
			
			elif cd_hex.terrain_type == 'Scrub':
				for (x,y) in CHAR_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 10) <= 8: continue
					if libtcod.random_get_int(generator, 1, 2) == 1:
						char = 247
					else:
						char = 15
					libtcod.console_put_char_ex(temp_con, x, y, char, libtcod.Color(32,64,0), bg_col)
			
			elif cd_hex.terrain_type == 'Hamada':
				elements = libtcod.random_get_int(generator, 7, 11)
				while elements > 0:
					(x,y) = GetRandomLocation()
					if libtcod.random_get_int(generator, 1, 3) <= 2:
						char = 177
					else:
						char = 250
					libtcod.console_put_char_ex(temp_con, x, y, char, libtcod.Color(51,51,51), bg_col)
					elements -= 1
			
			elif cd_hex.terrain_type == 'Sand':
				for (x,y) in CHAR_LOCATIONS:
					c = libtcod.random_get_int(generator, 130, 150)
					libtcod.console_put_char_ex(temp_con, x, y, 176,
						libtcod.Color(c,c,0), bg_col)
			
			elif cd_hex.terrain_type == 'Oasis':
				for (x,y) in CLOSE_CHAR_LOCATIONS:
					c = libtcod.random_get_int(generator, 1, 3)
					if c == 1:
						char = 7
						col = libtcod.Color(0,0,255)
					elif c == 2:
						char = 6
						col = libtcod.dark_green
					else:
						char = 15
						col = libtcod.darkest_green
					libtcod.console_put_char_ex(temp_con, x, y, char,
						col, bg_col)
			
			elif cd_hex.terrain_type == 'Fortress':
				c = libtcod.random_get_int(generator, -15, 15)
				col = libtcod.Color(190+c,170+c,140+c)
				col2 = libtcod.Color(190+c+30,170+c+30,140+c+30)
				
				# corner towers
				libtcod.console_put_char_ex(temp_con, 2, 3, 10,
					col, col2)
				libtcod.console_put_char_ex(temp_con, 4, 3, 10,
					col, col2)
				libtcod.console_put_char_ex(temp_con, 2, 5, 10,
					col, col2)
				libtcod.console_put_char_ex(temp_con, 4, 5, 10,
					col, col2)
				
				# walls
				libtcod.console_put_char_ex(temp_con, 3, 3, 205,
					col, bg_col)
				libtcod.console_put_char_ex(temp_con, 2, 4, 186,
					col, bg_col)
				libtcod.console_put_char_ex(temp_con, 4, 4, 186,
					col, bg_col)
				
				# gate
				libtcod.console_put_char_ex(temp_con, 3, 5, 61,
					col, bg_col)
			
			elif cd_hex.terrain_type == 'Lake':
				for (x,y) in CHAR_LOCATIONS:
					libtcod.console_put_char_ex(temp_con, x, y, 0,
						libtcod.black, RIVER_COL)
				libtcod.console_set_char_background(temp_con, 3, 4,
					RIVER_COL, libtcod.BKGND_SET)
			
			# draw landmine depictions if any
			if cd_hex.landmines:
				elements = libtcod.random_get_int(generator, 3, 5)
				while elements > 0:
					(x,y) = GetRandomLocation()
					# don't overwrite fortresses
					if libtcod.console_get_char(temp_con, x, y) in [10, 61, 186, 205]: continue
					libtcod.console_put_char_ex(temp_con, x, y, 250,
						libtcod.red, bg_col)
					elements -= 1
			
			# draw the final image to the map console
			(x,y) = self.PlotCDHex(hx, hy)
			libtcod.console_blit(temp_con, 0, 0, 0, 0, cd_map_con, x-3, y-4)
			
			# record screen locations of hex
			RecordScreenLocations(hx, hy)
			
		del temp_con, dayhex
		
		# set a default road color in case we need to draw an edge road first
		if campaign.stats['region'] == 'North Africa':
			col = libtcod.Color(160,130,100)
		else:
			col = DIRT_ROAD_COL
		
		# draw stone and dirt roads overtop
		for (hx, hy), map_hex in self.map_hexes.items():
			if map_hex.road_links == [None,None,None,None,None,None]: continue
			
			road_num = 0
			
			(x1, y1) = self.PlotCDHex(hx, hy)
			
			for direction in range(3):
				
				if map_hex.road_links[direction] is None: continue
				
				# get the other zone linked by road
				(hx2, hy2) = self.GetAdjacentCDHex(hx, hy, direction)
				if (hx2, hy2) not in self.map_hexes: continue
				
				road_num += 1
				
				# paint road
				if map_hex.road_links[direction] is False:
					if campaign.stats['region'] == 'North Africa':
						col = libtcod.Color(160,130,100)
					else:
						col = DIRT_ROAD_COL
				else:
					col = STONE_ROAD_COL
				(x2, y2) = self.PlotCDHex(hx2, hy2)
				line = GetLine(x1, y1, x2, y2)
				for (x, y) in line:
				
					# don't paint outside of map area
					if libtcod.console_get_char_background(cd_map_con, x, y) == libtcod.black:
						continue
					libtcod.console_set_char_background(cd_map_con, x, y,
						col, libtcod.BKGND_SET)
			
			# if map hex is on edge and has 1 road connection, draw a road leading off the edge of the map
			if road_num > 1: continue
			
			off_map_hexes = []
			for direction in range(6):
				(hx2, hy2) = self.GetAdjacentCDHex(hx, hy, direction)
				if (hx2, hy2) not in self.map_hexes:
					off_map_hexes.append((hx2, hy2))
			if len(off_map_hexes) == 0: continue
			
			(hx2, hy2) = off_map_hexes[0]
			(x2, y2) = self.PlotCDHex(hx2, hy2)
			for (x, y) in GetLine(x1, y1, x2, y2):
				if libtcod.console_get_char_background(cd_map_con, x, y) == libtcod.black:
					break
					
				libtcod.console_set_char_background(cd_map_con, x, y,
					col, libtcod.BKGND_SET)
					
				# if character is not blank or hex edge, remove it
				if libtcod.console_get_char(cd_map_con, x, y) not in [0, 249, 250]:
					libtcod.console_set_char(cd_map_con, x, y, 0)
		
		# draw rivers overtop
		for (hx, hy), map_hex in self.map_hexes.items():
			if len(map_hex.rivers) == 0: continue
			
			(x, y) = self.PlotCDHex(hx, hy)
			
			# draw each river edge
			for direction in map_hex.rivers:
				for (xm, ym) in CD_HEX_EDGE_CELLS[direction]:
					libtcod.console_put_char_ex(cd_map_con, x+xm, y+ym, 0,
						libtcod.white, RIVER_COL)
					
			# draw any bridges
			for direction in map_hex.bridges:
				for (xm, ym) in CD_HEX_EDGE_CELLS[direction][1:-1]:
					bg_col = libtcod.console_get_char_background(cd_map_con, x+xm, y+ym)
					if direction in [0, 3]:
						char = 47
					elif direction in [2, 5]:
						char = 92
					else:
						char = 45
					libtcod.console_put_char_ex(cd_map_con, x+xm, y+ym, char,
						libtcod.dark_sepia, bg_col)
					# also record location
					self.cd_map_bridge_locations.append((x+xm, y+ym))
		
		# draw hex row and column guides
		for i in range(0, 9):
			libtcod.console_put_char_ex(cd_map_con, 0, 6+(i*5), chr(i+65),
				libtcod.light_green, libtcod.black)
		for i in range(0, 5):
			libtcod.console_put_char_ex(cd_map_con, 7+(i*6), 50, chr(i+49),
				libtcod.light_green, libtcod.black)
		for i in range(5, 9):
			libtcod.console_put_char_ex(cd_map_con, 32, 39-((i-5)*10), chr(i+49),
				libtcod.light_green, libtcod.black)
		
		# draw arrows in direction of possible travel
		if self.mission in ['Fighting Withdrawal', 'Counterattack']:
			y = 52
			char = 25
		else:
			y = 0
			char = 24
		
		for i in range(0, 5):
			libtcod.console_put_char_ex(cd_map_con, 5+(i*6), y, char, libtcod.black,
				libtcod.darkest_green)
	
	
	# generate/update the campaign day unit layer console
	def UpdateCDUnitCon(self):
		libtcod.console_clear(cd_unit_con)
		libtcod.console_set_default_foreground(cd_unit_con, libtcod.white)
		
		# enemy strength level, player arty/air support
		libtcod.console_set_default_foreground(cd_unit_con, libtcod.red)
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			map_hex = self.map_hexes[(hx,hy)]
			if map_hex.enemy_strength > 0 and map_hex.known_to_player:
				(x,y) = self.PlotCDHex(hx, hy)
				libtcod.console_print(cd_unit_con, x, y-1, str(map_hex.enemy_strength))
		
		# draw player unit group
		(hx, hy) = self.player_unit_location
		(x,y) = self.PlotCDHex(hx, hy)
		
		# apply animation offset if any
		x += session.cd_x_offset
		y += session.cd_y_offset
		
		libtcod.console_put_char_ex(cd_unit_con, x, y, '@', libtcod.white, libtcod.black)
	
	
	# generate/update the zone control console, showing the battlefront between two sides
	def UpdateCDControlCon(self):
		libtcod.console_clear(cd_control_con)
		
		# run through every hex, if it's not under enemy control, see if there an adjacent
		# enemy-controlled hex and if so, draw a border there
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if self.map_hexes[(hx,hy)].controlled_by == 1: continue
			
			for direction in range(6):
				(hx_m, hy_m) = CD_DESTHEX[direction]
				hx2 = hx+hx_m
				hy2 = hy+hy_m
				
				# hex is off map
				if (hx2, hy2) not in self.map_hexes: continue
				# hex is not enemy-controlled
				if self.map_hexes[(hx2,hy2)].controlled_by != 1: continue
				
				# draw a border
				(x,y) = self.PlotCDHex(hx, hy)
				for (xm,ym) in CD_HEX_EDGE_CELLS2[direction]:
					libtcod.console_put_char_ex(cd_control_con, x+xm,
						y+ym, chr(249), libtcod.red, libtcod.black)
		
		# highlight any objective hexes
		for (hx, hy) in CAMPAIGN_DAY_HEXES:
			if self.map_hexes[(hx,hy)].objective is None: continue
			(x,y) = self.PlotCDHex(hx, hy)
			libtcod.console_put_char_ex(cd_control_con, x, y, chr(249),
				libtcod.yellow, libtcod.black)
	
	
	# generate/update the GUI console
	def UpdateCDGUICon(self):
		libtcod.console_clear(cd_gui_con)
		
		# movement menu, direction currently selected
		if self.active_menu == 3 and self.selected_direction is not None:
			
			# draw directional line
			(hx, hy) = self.player_unit_location
			(x1,y1) = self.PlotCDHex(hx, hy)
			(hx, hy) = self.GetAdjacentCDHex(hx, hy, self.selected_direction)
			if (hx, hy) in self.map_hexes:
				(x2,y2) = self.PlotCDHex(hx, hy)
				line = GetLine(x1,y1,x2,y2)
				for (x,y) in line[1:-1]:
					libtcod.console_put_char_ex(cd_gui_con, x, y, 250, libtcod.green,
						libtcod.black)
				(x,y) = line[-1]
				libtcod.console_put_char_ex(cd_gui_con, x, y, CD_DIR_ARROW[self.selected_direction],
					libtcod.green, libtcod.black)
	
	
	# generate/update the player unit console
	def UpdateCDPlayerUnitCon(self):
		libtcod.console_clear(cd_player_unit_con)
		DisplayUnitInfo(cd_player_unit_con, 0, 0, campaign.player_unit.unit_id, campaign.player_unit,
			status=False)
	
	
	# generate/update the command menu console 25x41
	def UpdateCDCommandCon(self):
		libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
		libtcod.console_set_default_background(cd_command_con, libtcod.black)
		libtcod.console_clear(cd_command_con)
		
		libtcod.console_set_default_foreground(cd_command_con, TITLE_COL)
		libtcod.console_print(cd_command_con, 6, 0, 'Command Menu')
		
		x = 0
		for (text, num, col) in CD_MENU_LIST:
			libtcod.console_set_default_background(cd_command_con, col)
			libtcod.console_rect(cd_command_con, x, 1, 2, 1, True, libtcod.BKGND_SET)
			
			# display menu number
			libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
			libtcod.console_print(cd_command_con, x, 1, str(num))
			libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			
			x += 2
			
			# display menu text if tab is active
			if self.active_menu == num:
				libtcod.console_rect(cd_command_con, x, 1, len(text)+2, 1,
					True, libtcod.BKGND_SET)
				libtcod.console_print(cd_command_con, x, 1, text)
				x += len(text) + 2
		
		# fill in rest of menu line with final colour
		libtcod.console_rect(cd_command_con, x, 1, 25-x, 1, True, libtcod.BKGND_SET)
		libtcod.console_set_default_background(cd_command_con, libtcod.black)
		
		# supply
		if self.active_menu == 1:
			
			if self.selected_gun is not None:
				libtcod.console_print(cd_command_con, 6, 3, self.selected_gun.stats['name'])
				self.selected_gun.DisplayAmmo(cd_command_con, 6, 5)
			
				libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
				libtcod.console_print(cd_command_con, 4, 14, EnKey('q').upper())
				libtcod.console_print(cd_command_con, 2, 15, EnKey('d').upper() + '/' + EnKey('a').upper())
				libtcod.console_print(cd_command_con, 4, 16, EnKey('c').upper())
				HOTKEYS = ['t', 'g', 'b', 'n']
				y = 17
				for ammo_type in self.selected_gun.stats['ammo_type_list']:
					libtcod.console_print(cd_command_con, 4, y, EnKey(HOTKEYS[y-17]).upper())
					y += 1
				
				libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
				libtcod.console_print(cd_command_con, 6, 14, 'Cycle Selected Gun')
				libtcod.console_print(cd_command_con, 6, 15, 'Add/Remove to RR')
				libtcod.console_print(cd_command_con, 6, 16, 'Cycle Ammo Type')
				y = 17
				for ammo_type in self.selected_gun.stats['ammo_type_list']:
					libtcod.console_print(cd_command_con, 6, y, 'Fill RR with ' + ammo_type)
					y += 1
			
			# display smoke grenades and smoke mortar ammo if any
			libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			text = 'Smoke Grenades: ' + str(self.smoke_grenades)
			libtcod.console_print(cd_command_con, 0, 22, text)
			if campaign.player_unit.GetStat('smoke_mortar') is not None:
				text = 'Smoke Mortar Rounds: ' + str(self.smoke_mortar_rounds)
				libtcod.console_print(cd_command_con, 0, 23, text)
			
			libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
			libtcod.console_print(cd_command_con, 4, 37, EnKey('r').upper())
			libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
			libtcod.console_print(cd_command_con, 6, 37, 'Request Resupply')
		
		# crew
		elif self.active_menu == 2:
			
			DisplayCrew(campaign.player_unit, cd_command_con, 0, 3,
				self.selected_position, show_default=True)
			
			libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
			libtcod.console_print(cd_command_con, 3, 35, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(cd_command_con, 3, 36, EnKey('p').upper())
			libtcod.console_print(cd_command_con, 3, 37, EnKey('e').upper())
			libtcod.console_print(cd_command_con, 3, 38, EnKey('h').upper())
			libtcod.console_print(cd_command_con, 3, 39, EnKey('c').upper())
			
			libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
			libtcod.console_print(cd_command_con, 8, 35, 'Select Position')
			libtcod.console_print(cd_command_con, 8, 36, 'Swap Position')
			libtcod.console_print(cd_command_con, 8, 37, 'Crewman Menu')
			libtcod.console_print(cd_command_con, 8, 38, 'Toggle Hatch')
			libtcod.console_print(cd_command_con, 8, 39, 'Clear Default')
		
		# travel
		elif self.active_menu == 3:
			
			# display current support levels at top
			y = 3
			if 'air_support_level' in campaign.current_week:
				libtcod.console_print(cd_command_con, 0, y, 'Air Support:')
				if campaign_day.weather['Cloud Cover'] == 'Overcast' or campaign_day.weather['Fog'] > 0:
					text = 'Not Possible'
				else:
					text = str(int(self.air_support_level)) + '%'
				libtcod.console_print_ex(cd_command_con, 24, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, text)
				y += 1
			
			if 'arty_support_level' in campaign.current_week:
				libtcod.console_print(cd_command_con, 0, y, 'Artillery Support:')
				text = str(int(self.arty_support_level)) + '%'
				libtcod.console_print_ex(cd_command_con, 24, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, text)
				y += 1
			
			if 'player_unit_support' in campaign.stats:
				libtcod.console_print(cd_command_con, 0, y, 'Unit Support:')
				text = str(int(self.unit_support_level)) + '%'
				libtcod.console_print_ex(cd_command_con, 24, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, text)
			
			# display directional options
			x1 = 12
			y1 = 10
			
			# display possible support/move/recon directions
			libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			libtcod.console_put_char(cd_command_con, x1, y1, '@')
			
			for direction in range(6):
				libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
				
				if self.selected_direction is not None:
					if self.selected_direction == direction:
						libtcod.console_set_default_foreground(cd_command_con, libtcod.light_green)
						
				(k, x, y, char) = CD_TRAVEL_CMDS[direction]
				libtcod.console_put_char(cd_command_con, x1+x, y1+y, EnKey(k).upper())
				if direction <= 2:
					x+=1
				else:
					x-=1
				libtcod.console_set_default_foreground(cd_command_con, libtcod.dark_green)
				libtcod.console_put_char(cd_command_con, x1+x, y1+y, chr(char))
			
			if self.selected_direction is None:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.light_grey)
				libtcod.console_print_ex(cd_command_con, 13, y1+4, libtcod.BKGND_NONE, libtcod.CENTER,
					'Select a Direction')
			
			# display Return and Wait commands (always available)
			libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
			libtcod.console_print(cd_command_con, 1, 36, EnKey('i').upper())
			libtcod.console_print(cd_command_con, 1, 37, EnKey('w').upper())
			libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
			libtcod.console_print(cd_command_con, 5, 36, 'Return to Base')
			libtcod.console_print(cd_command_con, 5, 37, 'Wait/Defend')
			
			# check to see whether travel in selected direction is possible
			map_hex = None
			if self.selected_direction is not None:
				
				(hx1, hy1) = self.player_unit_location
				(hx2, hy2) = self.GetAdjacentCDHex(hx1, hy1, self.selected_direction)
				if (hx2, hy2) not in self.map_hexes: return
				
				# calculate and display travel time
				libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
				libtcod.console_print(cd_command_con, 0, 20, 'Travel Time:')
				travel_text = self.CheckTravel(hx1, hy1, hx2, hy2)
				
				# travel not allowed
				if travel_text != '':
					libtcod.console_set_default_foreground(cd_command_con, libtcod.light_red)
				else:
					travel_text = str(self.CalculateTravelTime(hx1, hy1, hx2, hy2)) + ' mins.'
				libtcod.console_print(cd_command_con, 1, 21, travel_text)
				
				# don't display anything further if travel is N/A
				if 'N/A' in travel_text:
					return
				
				# river crossing
				if self.RiverCrossing(hx1, hy1, hx2, hy2):
					libtcod.console_print(cd_command_con, 1, 22, 'River Crossing')
				
				# display enemy strength/organization if any and chance of encounter
				map_hex = self.map_hexes[(hx2,hy2)]
				if map_hex.controlled_by in [1, 2]:
					
					libtcod.console_set_default_foreground(cd_command_con, libtcod.red)
					libtcod.console_print(cd_command_con, 3, 15, 'Destination is')
					if map_hex.controlled_by == 1:
						text = 'Enemy Controlled'
					else:
						text = 'Neutral Territory'
					
					libtcod.console_print(cd_command_con, 3, 16, text)
					
					# display recon option if strength is unknown travel is possible
					if not map_hex.known_to_player and 'N/A' not in text:
						libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
						libtcod.console_print(cd_command_con, 0, 18, 'Recon: 10 mins.')
						libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
						libtcod.console_print(cd_command_con, 1, 38, EnKey('r').upper())
						libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
						libtcod.console_print(cd_command_con, 5, 38, 'Recon')
					
				# display enemy strength if present and known
				if map_hex.enemy_strength > 0 and map_hex.known_to_player:
					libtcod.console_set_default_foreground(cd_command_con, libtcod.red)
					if map_hex.controlled_by != 1:
						libtcod.console_print(cd_command_con, 3, 15, 'Enemy forces active')
						libtcod.console_print(cd_command_con, 3, 16, 'in this area')
					libtcod.console_print(cd_command_con, 3, 17, 'Strength: ' + str(map_hex.enemy_strength))
					libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
				
				libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
				libtcod.console_print(cd_command_con, 1, 39, 'Tab')
				libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
				libtcod.console_print(cd_command_con, 5, 39, 'Proceed')
			
			# determine if offensive support options should be displayed
			attack_options = False
			if self.selected_direction is not None:
				if map_hex.enemy_strength > 0:
					attack_options = True
			
			libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			libtcod.console_print(cd_command_con, 1, 28, 'Support Options')
			
			libtcod.console_set_default_foreground(cd_command_con, ACTION_KEY_COL)
			libtcod.console_print(cd_command_con, 1, 30, EnKey('t').upper())
			libtcod.console_print(cd_command_con, 1, 31, EnKey('g').upper())
			libtcod.console_print(cd_command_con, 1, 32, EnKey('b').upper())
			libtcod.console_print(cd_command_con, 1, 33, EnKey('n').upper())
			
			# advancing fire
			if not attack_options:
				libtcod.console_set_default_background(cd_command_con, libtcod.darkest_grey)
				libtcod.console_rect(cd_command_con, 3, 30, 20, 1, True, libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(cd_command_con, libtcod.black)
			elif self.advancing_fire:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			else:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.dark_grey)
			libtcod.console_print(cd_command_con, 3, 30, 'Advancing Fire')
			
			# air support request
			if not attack_options or 'air_support_level' not in campaign.current_week or self.weather['Cloud Cover'] == 'Overcast' or self.weather['Fog'] > 0:
				libtcod.console_set_default_background(cd_command_con, libtcod.darkest_grey)
				libtcod.console_rect(cd_command_con, 3, 31, 20, 1, True, libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(cd_command_con, libtcod.black)
			elif self.air_support_request:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			else:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.dark_grey)
			libtcod.console_print(cd_command_con, 3, 31, 'Request Air Support')
			
			# artillery support request
			if not attack_options or 'arty_support_level' not in campaign.current_week:
				libtcod.console_set_default_background(cd_command_con, libtcod.darkest_grey)
				libtcod.console_rect(cd_command_con, 3, 32, 20, 1, True, libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(cd_command_con, libtcod.black)
			elif self.arty_support_request:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			else:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.dark_grey)
			libtcod.console_print(cd_command_con, 3, 32, 'Request Arty Support')
			
			# unit support request
			if 'unit_support_level' not in campaign.current_week:
				libtcod.console_set_default_background(cd_command_con, libtcod.darkest_grey)
				libtcod.console_rect(cd_command_con, 3, 33, 20, 1, True, libtcod.BKGND_SET)
				libtcod.console_set_default_foreground(cd_command_con, libtcod.black)
			elif self.unit_support_request:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.white)
			else:
				libtcod.console_set_default_foreground(cd_command_con, libtcod.dark_grey)
			libtcod.console_print(cd_command_con, 3, 33, 'Request Unit Support')
			
			libtcod.console_set_default_background(cd_command_con, libtcod.black)
			
		# group
		elif self.active_menu == 4:
			
			libtcod.console_set_default_foreground(cd_command_con, TITLE_COL)
			libtcod.console_print(cd_command_con, 1, 5, 'You:')
			libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
			libtcod.console_print(cd_command_con, 1, 6, campaign.player_unit.unit_id)
			
			libtcod.console_set_default_foreground(cd_command_con, TITLE_COL)
			libtcod.console_print(cd_command_con, 1, 8, 'Your Squad:')
			libtcod.console_set_default_foreground(cd_command_con, libtcod.lighter_grey)
			y = 9
			for unit in self.player_squad:
				libtcod.console_print(cd_command_con, 2, y, unit.unit_id)
				y += 1
	
	
	# generate/update the campaign info console 23x5
	def UpdateCDCampaignCon(self):
		libtcod.console_set_default_background(cd_campaign_con, libtcod.darkest_blue)
		libtcod.console_clear(cd_campaign_con)
		libtcod.console_set_default_foreground(cd_campaign_con, libtcod.light_blue)
		libtcod.console_print_ex(cd_campaign_con, 11, 0, libtcod.BKGND_NONE, libtcod.CENTER,
			'Day Mission')
		libtcod.console_print_ex(cd_campaign_con, 11, 3, libtcod.BKGND_NONE, libtcod.CENTER,
			'VP Today')
		libtcod.console_set_default_foreground(cd_campaign_con, libtcod.white)
		libtcod.console_print_ex(cd_campaign_con, 11, 1, libtcod.BKGND_NONE, libtcod.CENTER,
			campaign_day.mission)
		libtcod.console_print_ex(cd_campaign_con, 11, 4, libtcod.BKGND_NONE, libtcod.CENTER,
			str(campaign_day.day_vp))
	
	
	# generate/update the zone info console 23x35
	def UpdateCDHexInfoCon(self):
		libtcod.console_clear(cd_hex_info_con)
		
		libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.blue)
		libtcod.console_print_ex(cd_hex_info_con, 11, 0, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Zone Info')
		
		x = mouse.cx - 29 - window_x
		y = mouse.cy - 6 - window_y
		
		# bridge location
		if (x,y) in self.cd_map_bridge_locations:
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.dark_sepia)
			libtcod.console_print(cd_hex_info_con, 2, 2, 'Bridge')
			return
		
		# no zone here or mouse cursor outside of map area
		if (x,y) not in self.cd_map_index or x < 2 or x > 30:
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_grey)
			libtcod.console_print(cd_hex_info_con, 2, 2, 'Mouseover an area')
			libtcod.console_print(cd_hex_info_con, 2, 3, 'for info')
			return
		
		# find the hex
		(hx, hy) = self.cd_map_index[(x,y)]
		cd_hex = self.map_hexes[(hx, hy)]
		
		# display hex zone coordinates
		libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_green)
		libtcod.console_print_ex(cd_hex_info_con, 11, 1, libtcod.BKGND_NONE,
			libtcod.CENTER, cd_hex.coordinate)
		
		# DEBUG - display hx,hy
		if DEBUG:
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.yellow)
			libtcod.console_print_ex(cd_hex_info_con, 22, 0, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(hx) + ',' + str(hy))
		
		# terrain and description
		libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.white)
		libtcod.console_print(cd_hex_info_con, 0, 3, cd_hex.terrain_type)
		
		libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_grey)
		y = 5
		lines = wrap(CD_TERRAIN_TYPES[cd_hex.terrain_type]['description'], 21)
		for line in lines:
			libtcod.console_print(cd_hex_info_con, 1, y, line)
			y += 1
			if y == 10: break
		
		if 'impassible' in CD_TERRAIN_TYPES[cd_hex.terrain_type]:
			return
		
		# control
		if cd_hex.controlled_by == 0:
			libtcod.console_set_default_foreground(cd_hex_info_con, ALLIED_UNIT_COL)
			libtcod.console_print(cd_hex_info_con, 0, 12, 'Friendly controlled')
		else:
			# enemy-controlled
			if cd_hex.controlled_by == 1:
				col = ENEMY_UNIT_COL
				text = 'Enemy controlled'
			else:
				col = libtcod.sepia
				text = 'Neutral Territory'
			libtcod.console_set_default_foreground(cd_hex_info_con, col)
			libtcod.console_print(cd_hex_info_con, 0, 12, text)
			
		# VP value if captured
		if cd_hex.controlled_by == 1:
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_blue)
			libtcod.console_print(cd_hex_info_con, 0, 13, 'Capture VP Value: ' + str(cd_hex.vp_value))
		
		# roads
		if False in cd_hex.road_links:
			libtcod.console_set_default_foreground(cd_hex_info_con, DIRT_ROAD_COL)
			text = 'Dirt Road'
			if 'poor_quality_roads' in REGIONS[campaign.stats['region']]:
				if self.weather['Ground'] == 'Muddy':
					text += ' - MUD'
			libtcod.console_print(cd_hex_info_con, 0, 14, text)
		if True in cd_hex.road_links:
			libtcod.console_set_default_foreground(cd_hex_info_con, STONE_ROAD_COL)
			libtcod.console_print(cd_hex_info_con, 0, 15, 'Stone Road')
		
		# landmines
		if cd_hex.landmines:
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_red)
			libtcod.console_print(cd_hex_info_con, 0, 16, 'Landmines')
		
		# description of enemy resistance if known
		if cd_hex.enemy_strength > 0 and cd_hex.known_to_player:
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_red)
			libtcod.console_print(cd_hex_info_con, 0, 18, 'Estimated Enemies:')
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_grey)
			lines = wrap(cd_hex.enemy_desc, 20)
			y = 19
			for line in lines:
				libtcod.console_print(cd_hex_info_con, 0, y, line)
				y += 1
		
		# objective if any
		if cd_hex.objective is not None:
			libtcod.console_set_default_background(cd_hex_info_con, libtcod.darkest_blue)
			libtcod.console_rect(cd_hex_info_con, 0, 26, 22, 1, True, libtcod.BKGND_SET)
			libtcod.console_set_default_background(cd_hex_info_con, libtcod.black)
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.yellow)
			libtcod.console_print(cd_hex_info_con, 0, 26, cd_hex.objective['type'])
			
			# vp reward
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_grey)
			libtcod.console_print(cd_hex_info_con, 0, 27, 'Reward:')
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.white)
			libtcod.console_print(cd_hex_info_con, 8, 27, str(cd_hex.objective['vp_reward']) + ' VP')
			
			# objective description
			libtcod.console_set_default_foreground(cd_hex_info_con, libtcod.light_grey)
			y = 29
			lines = wrap(CD_OBJECTIVES[cd_hex.objective['type']], 22)
			for line in lines:
				libtcod.console_print(cd_hex_info_con, 0, y, line)
				y += 1
	
	
	# starts or re-starts looping animations based on weather conditions
	def InitAnimations(self):
		
		# reset animations
		self.animation['rain_active'] = False
		self.animation['rain_drops'] = []
		self.animation['snow_active'] = False
		self.animation['snowflakes'] = []
		self.animation['hex_highlight'] = False
		self.animation['hex_flash'] = 0
		
		# check for rain or snow animation
		if campaign_day.weather['Precipitation'] in ['Rain', 'Heavy Rain']:
			self.animation['rain_active'] = True
		elif campaign_day.weather['Precipitation'] in ['Light Snow', 'Snow', 'Blizzard']:
			self.animation['snow_active'] = True
		
		# set up rain if any
		if self.animation['rain_active']:
			self.animation['rain_drops'] = []
			num = 8
			if campaign_day.weather['Precipitation'] == 'Heavy Rain':
				num = 16
			for i in range(num):
				x = libtcod.random_get_int(0, 4, 36)
				y = libtcod.random_get_int(0, 0, 50)
				lifespan = libtcod.random_get_int(0, 1, 5)
				self.animation['rain_drops'].append((x, y, lifespan))		
		
		# set up snow if any
		if self.animation['snow_active']:
			self.animation['snowflakes'] = []
			if campaign_day.weather['Precipitation'] == 'Light Snow':
				num = 4
			elif campaign_day.weather['Precipitation'] == 'Snow':
				num = 8
			else:
				num = 16
			for i in range(num):
				x = libtcod.random_get_int(0, 4, 36)
				y = libtcod.random_get_int(0, 0, 50)
				lifespan = libtcod.random_get_int(0, 4, 10)
				self.animation['snowflakes'].append((x, y, lifespan))	
		
	
	# update campaign day animation frame and console 36x52
	def UpdateAnimCon(self):
		
		libtcod.console_clear(cd_anim_con)
		
		# update rain display
		if self.animation['rain_active']:
			
			# update location of each rain drop, spawn new ones if required
			for i in range(len(self.animation['rain_drops'])):
				(x, y, lifespan) = self.animation['rain_drops'][i]
				
				# respawn if finished
				if lifespan == 0:
					x = libtcod.random_get_int(0, 4, 36)
					y = libtcod.random_get_int(0, 0, 50)
					lifespan = libtcod.random_get_int(0, 1, 5)
				else:
					y += 2
					lifespan -= 1
				
				self.animation['rain_drops'][i] = (x, y, lifespan)
			
			# draw drops to screen
			for (x, y, lifespan) in self.animation['rain_drops']:
				
				# skip if off screen
				if x < 0 or y > 50: continue
				
				if lifespan == 0:
					char = 111
				else:
					char = 124
				libtcod.console_put_char_ex(cd_anim_con, x, y, char, libtcod.light_blue,
					libtcod.black)
		
		# update snow display
		if self.animation['snow_active']:
			
			# update location of each snowflake
			for i in range(len(self.animation['snowflakes'])):
				(x, y, lifespan) = self.animation['snowflakes'][i]
				
				# respawn if finished
				if lifespan == 0:
					x = libtcod.random_get_int(0, 4, 36)
					y = libtcod.random_get_int(0, 0, 50)
					lifespan = libtcod.random_get_int(0, 4, 10)
				else:
					x += choice([-1, 0, 1])
					y += 1
					lifespan -= 1
				
				self.animation['snowflakes'][i] = (x, y, lifespan)
			
			# draw snowflakes to screen
			for (x, y, lifespan) in self.animation['snowflakes']:
				
				# skip if off screen
				if x < 0 or y > 50: continue
				
				libtcod.console_put_char_ex(cd_anim_con, x, y, 249, libtcod.white,
					libtcod.black)
		
		# show hex highlight
		if self.animation['hex_highlight']:
			
			(hx, hy) = self.animation['hex_highlight']
			(x,y) = self.PlotCDHex(hx, hy)
			x += 1
			y -= 1
			
			if self.animation['hex_flash'] == 1:
				char = 250
				self.animation['hex_flash'] = 0
			else:
				char = 249
				self.animation['hex_flash'] = 1
			
			for direction in range(6):
				for (xm,ym) in CD_HEX_EDGE_CELLS[direction]:
					libtcod.console_put_char_ex(cd_anim_con, x+xm, y+ym,
						char, libtcod.light_blue, libtcod.black)
		
		# reset update timer
		session.anim_timer  = time.time()
	
	
	# draw all campaign day consoles to screen
	def UpdateCDDisplay(self):
		libtcod.console_clear(con)
		
		libtcod.console_blit(daymap_bkg, 0, 0, 0, 0, con, 0, 0)			# background frame
		libtcod.console_blit(cd_map_con, 0, 0, 0, 0, con, 29, 6)		# terrain map
		libtcod.console_blit(cd_control_con, 0, 0, 0, 0, con, 29, 6, 1.0, 0.0)	# zone control layer
		libtcod.console_blit(cd_unit_con, 0, 0, 0, 0, con, 29, 6, 1.0, 0.0)	# unit group layer
		libtcod.console_blit(cd_gui_con, 0, 0, 0, 0, con, 29, 6, 1.0, 0.0)	# GUI layer
		
		libtcod.console_blit(cd_anim_con, 0, 0, 0, 0, con, 28, 7, 1.0, 0.0)	# animation console
		
		libtcod.console_blit(time_con, 0, 0, 0, 0, con, 36, 1)			# date and time
		
		libtcod.console_blit(cd_player_unit_con, 0, 0, 0, 0, con, 1, 1)		# player unit info		
		libtcod.console_blit(cd_command_con, 0, 0, 0, 0, con, 1, 18)		# command menu
		
		libtcod.console_blit(cd_weather_con, 0, 0, 0, 0, con, 69, 3)		# weather info
		libtcod.console_blit(cd_campaign_con, 0, 0, 0, 0, con, 66, 18)		# campaign info
		libtcod.console_blit(cd_hex_info_con, 0, 0, 0, 0, con, 66, 24)		# zone info
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	
	
	# main campaign day input loop
	def DoCampaignDayLoop(self):
		
		# consoles for day map interface
		global daymap_bkg, cd_map_con, cd_anim_con, cd_unit_con, cd_control_con, cd_command_con
		global cd_player_unit_con, cd_gui_con, time_con, cd_campaign_con, cd_weather_con
		global cd_hex_info_con
		global scenario
		
		# create consoles
		daymap_bkg = LoadXP('daymap_bkg.xp')
		cd_map_con = NewConsole(35, 53, libtcod.black, libtcod.white)
		cd_anim_con = NewConsole(36, 52, libtcod.black, libtcod.white)
		cd_unit_con = NewConsole(35, 53, KEY_COLOR, libtcod.white)
		cd_control_con = NewConsole(35, 53, KEY_COLOR, libtcod.red)
		cd_gui_con = NewConsole(35, 53, KEY_COLOR, libtcod.red)
		time_con = NewConsole(21, 5, libtcod.darkest_grey, libtcod.white)
		cd_player_unit_con = NewConsole(25, 16, libtcod.black, libtcod.white)
		cd_command_con = NewConsole(25, 41, libtcod.black, libtcod.white)
		cd_weather_con = NewConsole(18, 12, libtcod.darkest_grey, libtcod.white)
		cd_campaign_con = NewConsole(23, 5, libtcod.black, libtcod.white)
		cd_hex_info_con = NewConsole(23, 35, libtcod.black, libtcod.white)
		
		# generate consoles for the first time
		self.UpdateCDMapCon()
		self.UpdateCDUnitCon()
		self.UpdateCDControlCon()
		self.UpdateCDGUICon()
		self.UpdateCDPlayerUnitCon()
		self.UpdateCDCommandCon()
		self.UpdateCDCampaignCon()
		self.UpdateCDHexInfoCon()
		DisplayWeatherInfo(cd_weather_con)
		DisplayTimeInfo(time_con)
		
		if scenario is not None:
			self.UpdateCDDisplay()
		
		# init looping animations
		self.InitAnimations()
		
		# calculate initial time to travel to front lines
		if not self.travel_time_spent:
			minutes = 5 + (libtcod.random_get_int(0, 1, 3) * 10)
			
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Ad Hoc'):
				minutes -= 15
				if minutes < 5:
					minutes = 5
			
			self.AdvanceClock(0, minutes, skip_checks=True)
			DisplayTimeInfo(time_con)
			text = 'It takes you ' + str(minutes) + ' minutes to travel to the front lines.'
			ShowMessage(text)
			campaign.AddJournal('Arrived at front lines')
			self.travel_time_spent = True
			
			# recon adjacent friendly hexes if needed
			self.map_hexes[self.player_unit_location].RevealAdjacentZones()
			
		# Required because otherwise selected_gun can be pointing to an outdated version
		self.BuildPlayerGunList()
		
		# record mouse cursor position to check when it has moved
		mouse_x = -1
		mouse_y = -1
		
		exit_loop = False
		while not exit_loop:
			
			# player was taken out of action
			if campaign.player_oob:
				self.DisplayCampaignDaySummary()
				exit_loop = True
				continue
			
			# if we've initiated a scenario or are resuming a saved game with a scenario
			# running, go into the scenario loop now
			if scenario is not None:
				
				scenario.DoScenarioLoop()
				
				if session.exiting:
					exit_loop = True
					continue
				
				# scenario is finished
				# FUTURE: move to separate function within CampaignDay
				if scenario.finished:
					
					# check for player crew recovery
					self.DoCrewRecoveryCheck(campaign.player_unit)
					
					# check for player character death - ends campaign
					for position in campaign.player_unit.positions_list:
						if position.crewman is None: continue
						if position.crewman.is_player_commander and not position.crewman.alive:
							scenario = None
							self.ended = True
							campaign.ended = True
							campaign.player_oob = True
							continue
					
					# tank was immobilized, abandoned, or destroyed: campaign day is over
					if campaign.player_unit.immobilized or not campaign.player_unit.alive:
						
						if campaign.player_unit.immobilized and campaign.player_unit.alive:
							ShowMessage('Your tank is rescued by a recovery team and ' +
								'your crew transported back to friendly lines.',
								longer_pause=True)
						scenario = None
						self.DisplayCampaignDaySummary()
						self.ended = True
						exit_loop = True
						continue
					
					# check for automatic unbog, weapon unjamming
					if campaign.player_unit.bogged:
						ShowMessage('You free your tank from being bogged down.')
						campaign.player_unit.bogged = False
					for weapon in campaign.player_unit.weapon_list:
						if weapon.jammed:
							weapon.jammed = False
							ShowMessage(weapon.GetStat('name') + ' is no longer jammed.')
					
					# check for fatigue accumulation
					for position in campaign.player_unit.positions_list:
						if position.crewman is None: continue
						position.crewman.DoFatigueCheck()
					
					# player withdrew from the battle
					if self.player_withdrew:
						
						DisplayTimeInfo(time_con)
						
						# reset flags and get the player's current location
						self.advancing_fire = False
						self.player_withdrew = False			
						(hx1, hy1) = self.player_unit_location
						map_hex = self.map_hexes[(hx1,hy1)]
						
						# capture this zone for the enemy (if possible) but don't generate new enemy units, will do that in next step
						map_hex.CaptureMe(1, no_generation=True)
						
						# if possible, set enemy units based on surviving enemies from scenario
						unit_list = []
						for unit in scenario.units:
							if not unit.alive: continue
							if not unit.owning_player == 1: continue
							if unit.immobilized or unit.routed: continue
							unit_list.append((unit.nation, unit.unit_id))
						
						# clear the scenario object now
						scenario = None
						
						if len(unit_list) > 0:
							map_hex.GenerateStrengthAndUnits(self.mission, unit_list=unit_list)
						else:
							map_hex.GenerateStrengthAndUnits(self.mission)
						
						# check for end of day after withdrawing from a battle
						self.CheckForEndOfDay()
						if self.ended:
							self.DisplayCampaignDaySummary()
							exit_loop = True
							continue
						
						# move player to adjacent friendly or neutral zone
						hex_list = []
						
						for direction in range(6):
							(hx2, hy2) = self.GetAdjacentCDHex(hx1, hy1, direction)
							if (hx2, hy2) not in self.map_hexes: continue
							if self.map_hexes[(hx2,hy2)].controlled_by == 1: continue
							if self.CheckTravel(hx1,hy1,hx2,hy2) != '':
								continue
							hex_list.append((hx2, hy2))
						
						# adjacent friendly or neutral hex found
						if len(hex_list) > 0:
							self.ReconOrTravel(False, self.map_hexes[choice(hex_list)], withdrawing=True)
							self.CheckForCDMapShift()
						
						# no adjacent friendly hex, must move into an enemy-held zone
						else:
							for direction in range(6):
								(hx2, hy2) = self.GetAdjacentCDHex(hx1, hy1, direction)
								if (hx2, hy2) not in self.map_hexes: continue
								if self.map_hexes[(hx2,hy2)].controlled_by == 0: continue
								if self.CheckTravel(hx1,hy1,hx2,hy2) != '':
									continue
								hex_list.append((hx2, hy2))
							
							# something went really wrong!
							if len(hex_list) == 0:
								ShowMessage('ERROR: Could not find an adjacent hex zone!')
							else:
								ShowMessage('You are forced to move into unfriendly territory.')
								self.ReconOrTravel(False, self.map_hexes[choice(hex_list)], withdrawing=True)
								self.UpdateCDCampaignCon()
								self.UpdateCDControlCon()
								self.UpdateCDUnitCon()
								self.UpdateCDCommandCon()
								self.UpdateCDHexInfoCon()
								self.UpdateCDDisplay()
					
					else:
						# clear the scenario object
						scenario = None
						self.map_hexes[self.player_unit_location].CaptureMe(0)
						self.map_hexes[self.player_unit_location].known_to_player = True
					
					DisplayTimeInfo(time_con)
					self.UpdateCDPlayerUnitCon()
					self.UpdateCDDisplay()
					libtcod.console_flush()
					
					# another battle was triggered
					if scenario is not None:
						self.BuildPlayerGunList()
						SaveGame()
						continue
					
					# another battle was not triggered
					self.CheckForEndOfDay()
					if not self.ended:
						self.CheckForRandomEvent()
						self.CheckForZoneCapture('capture_zone')
						# recalculate capture VPs
						for (hx, hy), cd_hex in self.map_hexes.items():
							cd_hex.CalcCaptureVP()
						self.CheckForCDMapShift()
					
					self.BuildPlayerGunList()
					SaveGame()
					
				DisplayTimeInfo(time_con)
				self.UpdateCDCampaignCon()
				self.UpdateCDControlCon()
				self.UpdateCDUnitCon()
				self.UpdateCDCommandCon()
				self.UpdateCDHexInfoCon()
				self.UpdateCDDisplay()
			
			# check for end of campaign day
			if self.ended:
				ShowMessage('Your combat day has ended.')
				campaign.AddJournal('End of day')
				self.DisplayCampaignDaySummary()
				exit_loop = True
				continue
			
			# check for animation update
			if time.time() - session.anim_timer >= 0.20:
				self.UpdateAnimCon()
				self.UpdateCDDisplay()
			
			libtcod.console_flush()
			keypress = GetInputEvent()
			
			# check to see if mouse cursor has moved
			if mouse.cx != mouse_x or mouse.cy != mouse_y:
				mouse_x = mouse.cx
				mouse_y = mouse.cy
				self.UpdateCDHexInfoCon()
				self.UpdateCDDisplay()
			
			if not keypress: continue
			
			# game menu
			if key.vk == libtcod.KEY_ESCAPE:
				ShowGameMenu()
				if session.exiting:
					exit_loop = True
					continue
			
			# debug menu
			elif key.vk == libtcod.KEY_F2:
				if not DEBUG: continue
				ShowDebugMenu()
				continue
			
			# mapped key commands
			key_char = DeKey(chr(key.c).lower())
			
			# switch active menu
			if key_char in ['1', '2', '3', '4']:
				if self.active_menu != int(key_char):
					self.active_menu = int(key_char)
					PlaySoundFor(None, 'tab_select')
					self.UpdateCDGUICon()
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
				continue
			
			# supply menu active
			if self.active_menu == 1:
				
				if self.selected_gun is not None:
					
					# cycle active ammo type
					if key_char == 'c':
						if self.selected_gun.CycleAmmo():
							PlaySoundFor(None, 'menu_select')
							self.UpdateCDCommandCon()
							self.UpdateCDDisplay()
						continue
				
					# move shell to/from ready rack
					elif key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
						if key_char == 'a' or key.vk == libtcod.KEY_LEFT:
							add_num = -1
						else:
							add_num = 1
						
						if self.selected_gun.ManageRR(add_num):
							self.UpdateCDCommandCon()
							self.UpdateCDDisplay()
						continue
					
					# cycle selected gun
					elif key_char == 'q':
						if len(self.gun_list) <= 1: continue
						i = self.gun_list.index(self.selected_gun)
						if i == len(self.gun_list) - 1:
							i = 0
						else:
							i += 1
						self.selected_gun = self.gun_list[i]
						PlaySoundFor(None, 'menu_select')
						self.UpdateCDCommandCon()
						self.UpdateCDDisplay()
						continue
					
					# hotkeys: fill RR with a given ammo type
					elif key_char in ['t', 'g', 'b', 'n']:
						
						i = ['t', 'g', 'b', 'n'].index(key_char)
						if i > len(self.selected_gun.stats['ammo_type_list']) - 1: continue
						
						# NEW: empty current RR contents
						for ammo_type in AMMO_TYPES:
							if ammo_type in self.selected_gun.ready_rack:
								self.selected_gun.ammo_stores[ammo_type] += self.selected_gun.ready_rack[ammo_type]
								self.selected_gun.ready_rack[ammo_type] = 0
						
						# save current ammo type so we can switch back
						old_ammo_type = self.selected_gun.ammo_type
						self.selected_gun.ammo_type = self.selected_gun.stats['ammo_type_list'][i]
						self.selected_gun.ManageRR(self.selected_gun.rr_size)
						self.selected_gun.ammo_type = old_ammo_type	
						self.UpdateCDCommandCon()
						self.UpdateCDDisplay()
						continue

				# request resupply
				if key_char == 'r':
					if not ShowNotification('Transmit a request for resupply?', confirm=True):
						continue	
					self.DoResupplyCheck()	
					continue
			
			# crew menu active
			elif self.active_menu == 2:
				
				# change selected crew position
				if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					if key_char == 'w' or key.vk == libtcod.KEY_UP:
						self.selected_position -= 1
						if self.selected_position < 0:
							self.selected_position = len(campaign.player_unit.positions_list) - 1
					else:
						self.selected_position += 1
						if self.selected_position == len(campaign.player_unit.positions_list):
							self.selected_position = 0
					PlaySoundFor(None, 'menu_select')
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# open crewman menu
				elif key_char == 'e':
					crewman = campaign.player_unit.positions_list[self.selected_position].crewman
					if crewman is None: continue
					crewman.ShowCrewmanMenu()
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# swap position menu
				elif key_char == 'p':
					ShowSwapPositionMenu()
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# toggle hatch for selected crewman
				elif key_char == 'h':
					crewman = campaign.player_unit.positions_list[self.selected_position].crewman
					if crewman is None: continue
					if crewman.ToggleHatch():
						PlaySoundFor(crewman, 'hatch')
						self.UpdateCDCommandCon()
						self.UpdateCDDisplay()
						continue
				
				# clear default command and hatch status
				elif key_char == 'c':
					crewman = campaign.player_unit.positions_list[self.selected_position].crewman
					if crewman is None: continue
					if crewman.default_start is None: continue
					crewman.default_start = None
					ShowMessage("Crewman's default command and hatch status has been cleared.")
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
			
			# travel menu active
			elif self.active_menu == 3:
				
				# select direction 
				if key_char in DIRECTION_KEYS:
					direction = DIRECTION_KEYS.index(key_char)
					
					# if no zone in this direction, don't allow it to be selected
					(hx1, hy1) = self.player_unit_location
					(hx2, hy2) = self.GetAdjacentCDHex(hx1, hy1, direction)
					if (hx2, hy2) not in self.map_hexes: continue
					
					if self.selected_direction is None:
						self.selected_direction = direction
					else:
						# cancel direction
						if self.selected_direction == direction:
							self.selected_direction = None
						else:
							self.selected_direction = direction
					self.UpdateCDGUICon()
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# wait/defend
				if key_char == 'w':
					if ShowNotification('Remain in place for 15 minutes?', confirm=True):
						ShowMessage('You remain in place, ready for possible attack.')
						self.selected_direction = None
						self.AdvanceClock(0, 15)
						DisplayTimeInfo(time_con)
						self.UpdateCDDisplay()
						
						# if unit support is active, show menu now
						if self.unit_support_request:
							unit_choice = self.GetUnitSupportChoice()
							if unit_choice is None:
								self.unit_support_request = False
							else:
								self.unit_support_type = unit_choice
						
						self.CheckForZoneCapture('wait')
						
						# NEW: if attacked during Fighting Withdrawl/Counterattack mission, award VP
						if scenario is not None:
							if self.mission in ['Fighting Withdrawal', 'Counterattack']:
								campaign.AwardVP(3)
						
						# check for random event, crewmen can rest if no battle triggered
						else:
							self.CheckForRandomEvent()
							for position in campaign.player_unit.positions_list:
								if position.crewman is None: continue
								position.crewman.Rest()
						
						SaveGame()
					continue
				
				# return to base
				elif key_char == 'i':
					
					# check for clear path to friendly edge
					if not self.PlayerHasPath():
						ShowMessage('You are cut off from friendly forces! You must have a clear path to the bottom map edge to return.')
						continue
					
					free_return = False
					for weapon in campaign.player_unit.weapon_list:
						if weapon.broken:
							if weapon.GetStat('type') == 'Gun' or len(campaign.player_unit.weapon_list) == 1:
								free_return = True
								break
					for position in campaign.player_unit.positions_list:
						if position.crewman is None:
							free_return = True
							break
						if not position.crewman.alive:
							free_return = True
							break
					
					text = 'Return to Base?'
					if not free_return:
						text += "You will forfeit half of today's VP."
					if ShowNotification(text, confirm=True):
						
						if not free_return:
							campaign_day.day_vp -= int(campaign_day.day_vp / 2)	
						ShowMessage('You return to base.')
						campaign.AddJournal('Returned to base')
						self.ended = True
					continue
				
				# toggle unit support request
				if key_char == 'n':
					if 'unit_support_level' not in campaign.current_week:
						continue
					self.unit_support_request = not self.unit_support_request
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# no direction selected
				if self.selected_direction is None: continue
				
				# if travel is not possible, no more commands available
				(hx1, hy1) = self.player_unit_location
				(hx2, hy2) = self.GetAdjacentCDHex(hx1, hy1, self.selected_direction)
				if (hx2, hy2) not in self.map_hexes:
					continue
				map_hex2 = self.map_hexes[(hx2,hy2)]
				if self.CheckTravel(hx1,hy1,hx2,hy2) != '':
					continue
				
				# toggle advancing fire
				if key_char == 't':
					self.advancing_fire = not self.advancing_fire
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# toggle air support request
				if key_char == 'g':
					if 'air_support_level' not in campaign.current_week:
						continue
					if self.weather['Cloud Cover'] == 'Overcast' or self.weather['Fog'] > 0:
						continue
					self.air_support_request = not self.air_support_request
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# toggle artillery support request
				if key_char == 'b':
					if 'arty_support_level' not in campaign.current_week:
						continue
					self.arty_support_request = not self.arty_support_request
					self.UpdateCDCommandCon()
					self.UpdateCDDisplay()
					continue
				
				# recon or proceed with travel
				if key_char == 'r' or key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
					
					# no direction set
					if self.selected_direction is None:
						continue
					
					time_taken = self.ReconOrTravel(key_char == 'r', map_hex2)
						
					# update consoles
					self.UpdateCDCampaignCon()
					self.UpdateCDControlCon()
					self.UpdateCDUnitCon()
					self.UpdateCDCommandCon()
					self.UpdateCDHexInfoCon()
					self.UpdateCDDisplay()
					
					# if no battle was triggered, do random event and zone capture checks
					if scenario is None and not (key_char == 'r'):
						self.CheckForRandomEvent()
						# TODO: check this, might be too restrictive
						if time_taken <= 20:
							self.CheckForZoneCapture('quick_move')
						else:
							self.CheckForZoneCapture('slow_move')
						
					SaveGame()
					continue




# Scenario: represents a single battle encounter
class Scenario:
	def __init__(self, cd_map_hex):
		
		self.init_complete = False			# flag to say that scenario has already been set up
		self.cd_map_hex = cd_map_hex			# Campaign Day map hex where this scenario is taking place
		self.ambush = False				# enemy units activate first, greater chance of spawning behind player
		self.finished = False				# Scenario has ended, returning to Campaign Day map
		self.class_type_dict = {}			# dictionary of unit types for each class; once set, further units will be of the same type
		
		# animation object; keeps track of active animations on the animation console
		self.animation = {
			'rain_active' : False,
			'rain_drops' : [],
			'snow_active' : False,
			'snowflakes' : [],
			'gun_fire_active' : False,
			'gun_fire_line' : [],
			'small_arms_fire_action' : False,
			'small_arms_fire_line' : [],
			'small_arms_lifetime' : 0,
			'air_attack' : None,
			'air_attack_line' : [],
			'bomb_effect' : None,
			'bomb_effect_lifetime' : 0,
			'grenade_effect' : None,
			'grenade_effect_lifetime' : 0,
			'ft_effect' : None,
			'ft_effect_lifetime' : 0,
			'psk_fire_action' : False,
			'psk_fire_line' : [],
			'hex_highlight' : False,
			'hex_flash' : 0
		}
		
		# current odds of a random event being triggered
		self.random_event_chance = BASE_RANDOM_EVENT_CHANCE
		
		# number of times enemy reinforcement random event has been triggered
		self.enemy_reinforcements = 0
		
		# generate hex map: single hex surrounded by 4 hex rings. Final ring is not normally
		# part of play and stores units that are coming on or going off of the map proper
		# also store pointers to hexes in a dictionary for quick access
		self.map_hexes = []
		self.hex_dict = {}
		for r in range(0, 5):
			for (hx, hy) in GetHexRing(0, 0, r):
				self.map_hexes.append(MapHex(hx,hy))
				self.hex_dict[(hx,hy)] = self.map_hexes[-1]
		
		# dictionary of console cells covered by map hexes
		self.hex_map_index = {}
		self.BuildHexmapDict()
		
		# attack console display is active
		self.attack_con_active = False
		
		self.units = []						# list of units in play
		self.player_unit = None					# placeholder for player unit
		
		# turn and phase information
		self.current_turn = 1					# current scenario turn
		self.active_player = 0					# currently active player (0 is human player)
		self.phase = PHASE_COMMAND				# current phase
		self.advance_phase = False				# flag for input loop to automatically advance to next phase/turn
		
		self.player_pivot = 0					# keeps track of player unit pivoting
		
		# player targeting
		self.target_list = []					# list of possible player targets
		self.selected_weapon = None				# player's currently selected weapon
		
		self.selected_position = 0				# index of selected position in player unit
	
	
	# spawn friendly reinforcement unit into a battle in progress
	def SpawnFriendlyReinforcements(self):
		
		# build a list of possible spawn locations around the edge of the map
		hex_list = []
		for (hx, hy) in GetHexRing(0, 0, 3):
			if len(self.hex_dict[(hx,hy)].unit_stack) > 0:
				if self.hex_dict[(hx,hy)].unit_stack[0].owning_player == 1:
					continue
			hex_list.append((hx, hy))
		if len(hex_list) == 0: return
		
		# build a list of possible units
		unit_list = []
		for unit_id in campaign.stats['player_unit_list']:
			
			# check availability of unit_id
			if not campaign.options['ahistorical']:
				
				# do player availibility check
				if 'player_unit_dates' in campaign.stats:
					if unit_id in campaign.stats['player_unit_dates']:
						if campaign.stats['player_unit_dates'][unit_id] > campaign.today:
							continue
				
				# do rarity check based on current date
				if not campaign.DoRarityCheck(unit_id):
					continue
				
			unit_list.append(unit_id)
		
		for support_category in list(campaign.stats['player_unit_support']):
			for unit_id in campaign.stats['player_unit_support'][support_category]:
				
				# some support units won't wander into a battle
				if session.unit_types[unit_id]['category'] in ['Gun', 'Train Car']:
					continue
				
				# do rarity check based on current date
				if not campaign.DoRarityCheck(unit_id):
					continue
				
				unit_list.append(unit_id)
		
		# shouldn't happen, but you never know
		if len(unit_list) == 0: return
		
		# select and spawn the unit
		unit = Unit(choice(unit_list))
		unit.owning_player = 0
		unit.nation = campaign.player_unit.nation
		unit.ai = AI(unit)
		unit.ai.Reset()
		unit.GenerateNewPersonnel()
		(hx, hy) = choice(hex_list)
		unit.SpawnAt(hx, hy)
		direction = GetDirectionToward(hx, hy, 0, 0)
		unit.facing = direction
		if 'turret' in unit.stats:
			unit.turret_facing = direction
		self.GenerateUnitLoS(unit)
		self.UpdateUnitCon()
		self.UpdateScenarioDisplay()
		ShowMessage('A friendly ' + unit.unit_id + ' arrives and joins the battle!',
			scenario_highlight=(hx, hy))
		
	
	# player attempts to withdraw from the battle
	def AttemptWithdraw(self):
		enemies_in_range = 0
		for unit in self.units:
			if not unit.alive: continue
			if unit.owning_player == 0: continue
			distance = GetHexDistance(unit.hx, unit.hy, 0, 0)
			if distance == 1:
				enemies_in_range += 2
			elif distance == 2:
				enemies_in_range += 1
		
		if enemies_in_range == 0: return True
		
		chance = enemies_in_range * 15.0
		if chance > 97.0: chance = 97.0
		roll = GetPercentileRoll()
		
		# skill check
		if self.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Tactical Retreat'):
			roll += 20.0
		
		if roll <= chance:
			return False
		return True
	
	
	# return the chance for unit1 to spot unit2
	def CalcSpotChance(self, unit1, unit2, crewman=None):
		
		distance = GetHexDistance(unit1.hx, unit1.hy, unit2.hx, unit2.hy)	
		chance = SPOT_BASE_CHANCE[distance]
		
		# target size
		size_class = unit2.GetStat('size_class')
		if size_class is not None:
			if size_class == 'Small':
				chance -= 7.0
			elif size_class == 'Very Small':
				chance -= 18.0
			elif size_class == 'Large':
				chance += 7.0
			elif size_class == 'Very Large':
				chance += 18.0
		
		# precipitation modifier
		if campaign_day.weather['Precipitation'] in ['Rain', 'Snow']:
			chance -= 5.0 * float(distance)
		elif campaign_day.weather['Precipitation'] in ['Heavy Rain', 'Blizzard']:
			chance -= 10.0 * float(distance)
		
		# fog, smoke, or dust concealment - only apply the one that will have the most effect
		vision_mod = 1.0
		
		if campaign_day.weather['Fog'] > 0:
			if 4 - distance <= campaign_day.weather['Fog']:
				mod = round(0.75 / distance, 2)
				if mod < vision_mod:
					vision_mod = mod
		
		effective_smoke = (float(unit1.smoke) * 0.5) + float(unit2.smoke)
		if effective_smoke > 0.0:
			mod = round(0.75 / effective_smoke, 2)
			if mod < vision_mod:
				vision_mod = mod
		
		effective_dust = (float(unit1.dust) * 0.5) + float(unit2.dust)
		if effective_dust > 0.0:
			mod = round(0.75 / effective_dust, 2)
			if mod < vision_mod:
				vision_mod = mod
		
		if vision_mod < 1.0:
			chance = chance * vision_mod
		
		# target moved and/or fired
		if unit2.moving: chance = chance * 1.5
		if unit2.fired:
			if unit2.GetStat('stealthy_firing') is None:
				chance = chance * 2.0
		
		# infantry are not as good at spotting from their lower position
		if unit1.GetStat('category') == 'Infantry' and distance > 1:
			if distance == 2:
				chance = chance * 0.75
			else:
				chance = chance * 0.5
		
		# target terrain
		chance += unit2.GetTEM()
		
		# crewman modifiers if any
		if crewman is not None:
		
			mod = crewman.GetSkillMod(float(crewman.stats['Perception'] * PERCEPTION_SPOTTING_MOD))
			if not crewman.ce:
				mod = mod * 0.8
			
			chance = chance * mod
			
			if crewman.current_cmd != 'Spot':
				chance = chance * 0.8
			
			# spotting crew skill
			if 'Eagle Eyed' in crewman.skills and crewman.ce:
				chance += crewman.GetSkillMod(10.0)
			
			# spotting crew head/neck injury
			if crewman.injury['Head & Neck'] is not None:
				if crewman.injury['Head & Neck'] != 'Light':
					chance = chance * 0.5
		
		# target is HD to spotter
		if len(unit2.hull_down) > 0:
			if GetDirectionToward(unit2.hx, unit2.hy, unit1.hx, unit1.hy) in unit2.hull_down:
				chance = chance * 0.5
		
		# target has been hit by effective fp
		if unit2.hit_by_fp:
			chance = chance * 4.0
		
		return round(chance, 1)
	
	
	# do a round of spotting for AI units on one side, uses a simplified procedure
	def DoAISpotChecks(self, owning_player):
		
		for unit1 in self.units:
			if not unit1.alive: continue
			if unit1.owning_player != owning_player: continue
			
			# build list of units that it's possible to spot
			spot_list = []
			for unit2 in scenario.units:
				if unit2.owning_player == owning_player: continue
				if not unit2.alive: continue
				if unit2.spotted: continue
				if not unit1.los_table[unit2]: continue
				spot_list.append(unit2)
			
			# no units possible to spot
			if len(spot_list) == 0: continue
			
			# roll once for each unit
			for unit2 in spot_list:
				chance = scenario.CalcSpotChance(unit1, unit2)
				if chance <= 0.0: continue
				if GetPercentileRoll() <= chance:
					unit2.SpotMe()
					scenario.UpdateUnitCon()
					scenario.UpdateScenarioDisplay()
					
					# display message unless part of player squad
					if unit2 in scenario.player_unit.squad: continue
					
					if unit2 == scenario.player_unit:
						text = 'You were'
					else:
						text = unit2.GetName()
						if unit2.owning_player == 0:
							text += ' was'
					text += ' spotted'
					if unit2.owning_player == 0:
						text += ' by ' + unit1.GetName()
					text += '!'
					ShowMessage(text, portrait=unit2.GetStat('portrait'),
						scenario_highlight=(unit2.hx, unit2.hy))
	
	
	# roll to see whether two units on the scenario map have LoS to each other
	# if chance_only, will only calculate chance and return that
	def DoLoSRoll(self, unit1, unit2, chance_only=False):
		
		# no need for dead units
		if not unit1.alive or not unit2.alive: return False
		
		# if unit1 is on Overrun and unit2 is directly ahead, automatically has LoS
		if unit1.overrun and unit2.hx == 0 and unit2.hy == -1:
			return True
		
		# base odds of LoS based on range between the two units
		distance = GetHexDistance(unit1.hx, unit1.hy, unit2.hx, unit2.hy)
		if distance == 0:		# same hex
			chance = 100.0
		elif distance == 1:		# close range
			chance = 97.0
		elif distance == 2:		# medium range
			chance = 90.0
		elif distance == 3:		# long range
			chance = 85.0
		else:
			return False		# off map: no chance
		
		# modify base chance by terrain of both units
		terrain_mod = 0.0
		
		if unit1.terrain is not None:
			terrain_mod -= SCENARIO_TERRAIN_EFFECTS[unit1.terrain]['los_mod']
		if unit2.terrain is not None:
			terrain_mod -= SCENARIO_TERRAIN_EFFECTS[unit2.terrain]['los_mod']
		
		chance += terrain_mod
		chance = round(chance, 1)
		
		if chance_only: return chance
		
		if GetPercentileRoll() <= chance:
			return True
		return False
	
	
	# do the initial line of sight checks between all units
	def GenerateLoS(self):
		
		def AddLoS(unit1, unit2):
			unit1.los_table[unit2] = True
			unit2.los_table[unit1] = True
		
		# clear all LoS tables
		for unit in self.units:
			unit.los_table = {}
		
		# check each unit against every other
		for unit1 in self.units:
			for unit2 in self.units:
				
				# already added in opposite direction
				if unit1 in unit2.los_table: continue
				
				# same unit
				if unit1 == unit2:
					AddLoS(unit1, unit2)
					continue
				
				# same side and same hex
				if unit1.owning_player == unit2.owning_player and unit1.hx == unit2.hx and unit1.hy == unit2.hy:
					AddLoS(unit1, unit2)
					continue
				
				# roll for LoS between the units
				if self.DoLoSRoll(unit1, unit2):
					AddLoS(unit1, unit2)
					continue
				
				unit1.los_table[unit2] = False
				unit2.los_table[unit1] = False


	# add a newly spawned unit to the existing units' LoS tables
	# can also regenerate LoS links between this unit and every other unit
	def GenerateUnitLoS(self, unit1):
		
		def AddLoS(unit1, unit2):
			unit1.los_table[unit2] = True
			unit2.los_table[unit1] = True
		
		unit1.los_table = {}
		
		for unit2 in self.units:
			
			# same unit
			if unit1 == unit2:
				AddLoS(unit1, unit2)
				continue
			
			# same side and same hex
			if unit1.owning_player == unit2.owning_player and unit1.hx == unit2.hx and unit1.hy == unit2.hy:
				AddLoS(unit1, unit2)
				continue
			
			# roll for LoS between the units
			if self.DoLoSRoll(unit1, unit2):
				AddLoS(unit1, unit2)
				continue
			
			unit1.los_table[unit2] = False
			unit2.los_table[unit1] = False


	# roll at start of scenario to see whether player has been ambushed
	def DoAmbushRoll(self):
		
		# skip roll entirely if no enemy units remaining
		all_enemies_dead = True
		for unit in self.units:
			if unit.owning_player == 1 and unit.alive:
				all_enemies_dead = False
				break
		if all_enemies_dead: return
		
		# no ambush possible if player has Motti national skill
		if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Motti'):
			return
		
		chance = 10.0
		
		if campaign_day.weather['Precipitation'] in ['Heavy Rain', 'Snow', 'Blizzard']:
			chance += 10.0
		if campaign_day.mission == 'Patrol':
			chance -= 5.0
		elif campaign_day.mission in ['Advance', 'Spearhead']:
			chance += 10.0
		if self.cd_map_hex.terrain_type in ['Forest', 'Villages']:
			chance += 10.0
		elif self.cd_map_hex.terrain_type == 'Hills':
			chance += 15.0
		
		for position in ['Commander', 'Commander/Gunner']:
			crewman = self.player_unit.GetPersonnelByPosition(position)
			if crewman is None: continue
			if 'Unique Opportunities' in crewman.skills:
				chance -= 20.0
				break
			if 'Enemy Spotted!' in crewman.skills:
				chance -= crewman.GetSkillMod(10.0)
				break
			
		
		if self.player_unit.GetStat('recce') is not None:
			chance -= 5.0
		
		crew_exposed = False
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			if not position.crewman.alive or position.crewman.condition == 'Unconscious': continue
			if position.crewman.ce:
				crew_exposed = True
				break
		if crew_exposed:
			chance -= 10.0
		
		if chance < 3.0:
			chance = 3.0
		
		if GetPercentileRoll() <= chance:
			self.ambush = True
	
	
	# check for end of scenario and set flag if it has ended
	def CheckForEnd(self):
		all_enemies_dead = True
		for unit in self.units:
			if unit.owning_player == 1 and unit.alive:
				if GetHexDistance(0, 0, unit.hx, unit.hy) > 3: continue
				all_enemies_dead = False
				break
		if all_enemies_dead:
			ShowMessage('Victory! No enemy units remain in this area.')
			self.finished = True
			return
		
		# check for loss of player crew
		all_crew_dead = True
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			if position.crewman.alive:
				all_crew_dead = False
				break
		if all_crew_dead:
			ShowMessage('Your crew is all dead.')
			scenario.player_unit.DestroyMe()
			return
		
		# check for end of campaign day, but don't end the scenario
		campaign_day.CheckForEndOfDay()
	
	
	# check for triggering of a random event in a scenario
	def CheckForRandomEvent(self):
		
		roll = GetPercentileRoll()
		
		if roll > self.random_event_chance:
			self.random_event_chance += 1.0
			return
		
		# roll for type of event
		roll = GetPercentileRoll()
		
		# friendly air attack
		if roll <= 10.0:
			if 'air_support_level' not in campaign.current_week: return
			if 'player_air_support' not in campaign.stats: return
			if campaign_day.weather['Cloud Cover'] == 'Overcast' or campaign_day.weather['Fog'] > 0: return
			self.DoAirAttack()
			
		# friendly arty attack
		elif roll <= 20.0:
			if 'arty_support_level' not in campaign.current_week: return
			if 'player_arty_support' not in campaign.stats: return
			self.DoArtilleryAttack()
			
		# enemy reinforcement
		elif roll <= 30.0:
			if self.enemy_reinforcements > 0:
				if GetPercentileRoll() <= (float(self.enemy_reinforcements) * 40.0):
					return
			self.enemy_reinforcements += 1
			if self.SpawnEnemyUnits(reinforcement=True):
				ShowMessage('Enemy reinforcements have arrived!')
		
		# sniper attack on player
		elif roll <= 40.0:
			
			# less likely in north african terrain
			if campaign.stats['region'] == 'North Africa':
				if GetPercentileRoll() <= 80.0: return
			
			# check for vulnerable targets and select one if any
			crew_list = self.player_unit.VulnerableCrew()
			if len(crew_list) == 0: return
			crew_target = choice(crew_list)
			
			# do attack roll
			chance = BASE_SNIPER_TK_CHANCE
			
			# precipitation modifier
			if campaign_day.weather['Precipitation'] in ['Rain', 'Light Snow']:
				chance -= 5.0
			elif campaign_day.weather['Precipitation'] == ['Heavy Rain', 'Blizzard']:
				chance -= 15.0
			
			# target moving
			if self.player_unit.moving: chance -= 10.0
			
			# target terrain
			chance += self.player_unit.GetTEM()
			
			# odds too low
			if chance < 15.0: return
			
			# do attack roll
			roll = GetPercentileRoll()
			
			# miss
			if roll > chance:
				PlaySoundFor(None, 'ricochet')
				text = "The ricochet from a sniper's bullet rings out, narrowly missing "
				if crew_target.is_player_commander:
					text += 'you!'
				else:
					text += 'your crewman:'
				ShowMessage(text, longer_pause=True, crewman=crew_target)
				if crew_target.is_player_commander:
					session.ModifySteamStat('near_miss', 1)
					
			else:
				PlaySoundFor(None, 'sniper_hit')
				if crew_target.is_player_commander:
					text = 'You have been hit by a sniper!'
				else:
					text = 'Your crewman has been hit by a sniper!'
				ShowMessage(text, longer_pause=True, crewman=crew_target)
				if crew_target.ResolveAttack({'sniper' : True}) is None:
					ShowMessage('Luckily it was a grazing hit and did no damage.', longer_pause=True)
		
		# random enemy tank is immobilized
		elif roll <= 50.0:
			
			unit_list = []
			for unit in self.units:
				if not unit.alive: continue
				if unit.owning_player == 0: continue
				if unit.GetStat('armour') is None: continue
				unit_list.append(unit)
			
			# no possible units to immobilize
			if len(unit_list) == 0:
				return
			
			unit = choice(unit_list)
			unit.ImmobilizeMe()
			if unit.spotted:
				ShowMessage(unit.GetName() + ' has been immobilized!',
					scenario_highlight=(unit.hx, unit.hy))
		
		# enemy air attack on player
		elif roll <= 55.0:
			if 'enemy_air_support' not in campaign.stats: return
			if campaign_day.weather['Cloud Cover'] == 'Overcast' or campaign_day.weather['Fog'] > 0: return
			self.DoAirAttack(player_target=True)
		
		# enemy artillery attack on player
		elif roll <= 60.0:
			if 'enemy_arty_support' not in campaign.stats: return
			self.DoArtilleryAttack(player_target=True)
		
		# friendly reinforcements
		elif roll <= 65.0:
			if 'player_unit_support' not in campaign.stats: return
			self.SpawnFriendlyReinforcements()
		
		# infantry harass player
		elif roll <= 95.0:
			
			# find active infantry units
			unit_list = []
			for unit in self.units:
				if not unit.alive: continue
				if unit.owning_player == 0: continue
				if unit.routed: continue
				if unit.unit_id not in ['Riflemen', 'Rifle Cavalry', 'HMG Team', 'Light Mortar Team']: continue
				if unit.unit_id in ['Riflemen', 'Rifle Cavalry', 'Light Mortar Team']:
					if GetHexDistance(0, 0, unit.hx, unit.hy) > 1: continue
				unit_list.append(unit)
			
			if len(unit_list) == 0:
				return
			
			shuffle(unit_list)
			for unit in unit_list:
				# make sure attack is possible
				if self.CheckAttack(unit, unit.weapon_list[0], self.player_unit) != '': continue
				
				unit.MoveToTopOfStack()
				self.UpdateUnitCon()
				self.UpdateScenarioDisplay()
				libtcod.console_flush()
				
				ShowMessage(unit.GetName() + ' fires harassing fire at you!')
				
				if unit.Attack(unit.weapon_list[0], self.player_unit):
					
					# won't cause AP hits
					self.player_unit.ap_hits_to_resolve = []
					self.player_unit.ResolveFP()
		
		else:
			return
		
		# an event was triggered, so reset random event chance
		self.random_event_chance = BASE_RANDOM_EVENT_CHANCE
	
	
	##################################################################################
	
	# Bail-out mini game
	# if abandoning_tank is true, no chance of a crew injury from the initial knock-out hit
	# if location is set, crew in hull/turret as appropriate will have a higher chance of injury
	def PlayerBailOut(self, location=None, weapon=None, abandoning_tank=False):
		
		# build the list of possible actions, and odds of success, for a crewman
		def BuildActionList(crewman):
			
			# clear any old actions
			crewman.action_list = [('None', 0.0)]
			
			# no other actions possible
			if not crewman.alive or crewman.condition == 'Unconscious':
				crewman.current_action = crewman.action_list[0]
				return
				
			# crewmen in safe location can only return to tank
			if crewman.current_position.location == 'Safe Location':
				crewman.action_list.append(('Return to Tank', 75.0))
			
			# crewmen on tank exterior
			elif crewman.current_position.location == 'Tank Exterior':
				crewman.action_list.append(('Move to Safe Location', 85.0))
				crewman.action_list.append(('Suppressing Fire', 100.0))
				crewman.action_list.append(('Aid Crewmen Bailing Out', 100.0))
			
			# crewman still inside tank
			else:
				
				# open a hatch
				if crewman.current_position.hatch:
					if not crewman.current_position.hatch_open:
						if on_fire:
							chance = 30.0
						elif smoke:
							chance = 50.0
						else:
							chance = 90.0
						crewman.action_list.append(('Open Hatch', chance))
				
				# open another hatch in the same location
				for position in self.player_unit.positions_list:
					if position == crewman.current_position: continue
					if position.location != crewman.current_position.location: continue
					if not position.hatch: continue
					if position.hatch_open: continue
					if on_fire:
						chance = 15.0
					elif smoke:
						chance = 25.0
					else:
						chance = 45.0
					crewman.action_list.append(('Open ' + position.name + ' Hatch', chance))
				
				# bail-out actions
				text = ''
				chance = 0.0
				
				# bail out while already exposed
				if crewman.current_position.open_top or crewman.current_position.crew_always_ce:
					text, chance = 'Bail Out', 95.0
				
				# bail out of open hatch in current location
				elif crewman.current_position.hatch_open:
					text, chance = 'Bail Out through Hatch', 75.0
				
				# bail out of open hatch
				else:
					# in nearby location
					for position in self.player_unit.positions_list:
						if position.location != crewman.current_position.location: continue
						if position.hatch_open:
							text, chance = 'Bail Out through Nearby Hatch', 55.0
							break
					
					# in other location
					if text == '':
						for position in self.player_unit.positions_list:
							if position.location == crewman.current_position.location: continue
							if not position.hatch_open: continue
							text, chance = 'Bail Out through ' + position.location + ' Hatch', 20.0
							break
				
				if chance > 0.0:
					# modify bail-out chance
					if on_fire:
						chance -= 25.0
					elif smoke:
						chance -= 15.0
					if crewman.condition == 'Stunned':
						chance -= 15.0
					# apply modifiers from any leg/foot injuries
					for (k, v) in crewman.injury.items():
						if k not in ['Right Leg & Foot', 'Left Leg & Foot']: continue
						if v is None: continue
						if v not in ['Heavy', 'Serious', 'Critical']: continue
						if v in ['Heavy', 'Serious']:
							chance -= 40.0
						else:
							chance -= 60.0
					if 'Gymnast' in crewman.skills:
						chance += crewman.GetSkillMod(10.0)
					
					crewman_helping = False
					for position in self.player_unit.positions_list:
						if position.crewman is None: continue
						if position.location != crewman.current_position.location: continue
						(text2, odds) = position.crewman.current_action
						if text2 == 'Aid Crewmen in Location':
							crewman_helping = True
							break
					if crewman_helping:
						chance += 20.0
							
					if chance < 10.0:
						chance = 10.0
					elif chance > 95.0:
						chance = 95.0
					
					crewman.action_list.append((text, chance))
				
				# move to an empty position in the tank
				for position in self.player_unit.positions_list:
					if position == crewman.current_position: continue
					if position.crewman is not None: continue
					if position.location == crewman.current_position.location:
						chance = 85.0
					else:
						chance = 70.0
					crewman.action_list.append(('Go to ' + position.name + ' Position', chance))
				
				# help crewmen in same location
				for position in self.player_unit.positions_list:
					if position.location != crewman.current_position.location: continue
					if position.crewman is None: continue
					if not position.crewman.alive: continue
					if position.crewman == crewman: continue
					if position.crewman.condition != 'Good Order':
						chance = 100.0
						if on_fire:
							chance -= 25.0
						elif smoke:
							chance -= 15.0
						crewman.action_list.append(('Aid Crewmen in Location', chance))
						break
				
				# suppressing fire
				if crewman.ce:
					chance = 100.0
					if on_fire:
						chance -= 50.0
					elif smoke:
						chance -= 25.0
					crewman.action_list.append(('Suppressing Fire', chance))
			
			# if currently selected action is still in list, select that one, even if odds have changed
			for i in range(len(crewman.action_list)):
				if crewman.current_action[0] == crewman.action_list[i][0]:
					crewman.current_action = crewman.action_list[i]
					return
			
			# unable to find this action in current list, reset to default
			crewman.current_action = crewman.action_list[0]
		
		# clear the current action displayed, and display a positive or negative result for a crewman
		# up to two lines of max 43 characters each
		def DisplayResult(crewman, result_text, positive_result):
			y = 18 + (player_crew.index(crewman) * 6)
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_set_default_background(con, libtcod.black)
			libtcod.console_rect(con, 43, y-1, 45, 5, True, libtcod.BKGND_SET)
			if positive_result:
				libtcod.console_set_default_background(con, libtcod.light_blue)
			else:
				libtcod.console_set_default_background(con, libtcod.dark_red)	
			libtcod.console_rect(con, 44, y, 43, 3, True, libtcod.BKGND_SET)
			libtcod.console_set_default_background(con, libtcod.black)
			lines = wrap(result_text, 43)
			ys = 0
			for line in lines[:2]:
				libtcod.console_print(con, 44, y+1+ys, line)
				ys += 1
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			libtcod.console_flush()
			Wait(150, ignore_animations=True)
		
		# do the selected action for the crewman
		def DoBailoutAction(crewman):
			
			# check for recovery from negative condition
			if crewman.condition != 'Good Order':
				condition_change = False
				
				# check for crewmen in same location helping
				crewman_helping = False
				for position in self.player_unit.positions_list:
					if position.crewman is None: continue
					if position.location != crewman.current_position.location: continue
					(text, odds) = position.crewman.current_action
					if text == 'Aid Crewmen in Location':
						crewman_helping = True
						break
				
				if crewman_helping:
					base_modifier = 20.0
				else:
					base_modifier = 40.0
				
				if crewman.condition == 'Shaken':
					if crewman.DoMoraleCheck(base_modifier):
						crewman.condition = 'Good Order'
						condition_change = True
				elif crewman.condition == 'Stunned':
					if crewman.DoMoraleCheck(base_modifier * 2):
						crewman.condition = 'Good Order'
						condition_change = True
				elif crewman.condition == 'Unconscious':
					if crewman.DoGritCheck(base_modifier * 3):
						crewman.condition = 'Stunned'
						condition_change = True
				
				if condition_change:
					if crewman.current_position.name in PLAYER_POSITIONS:
						text = 'Your condition improves, you are now: ' + crewman.condition
						ShowSimpleMessage(text)
					else:
						text = "Your crewman's condition improves to " + crewman.condition + ':'
						ShowSimpleMessage(text, crewman=crewman)

			(text, odds) = crewman.current_action
			
			# no action to do here
			if text in ['None']:
				return
			
			result_text = 'Failed: ' + text
			roll = GetPercentileRoll()
			
			# aid crewmen bailing out (automatic)
			if text == 'Aid Crewmen Bailing Out':
				result_text = 'Success: Aiding crewmen bailing out'
			
			# attempt to open a hatch
			elif text == 'Open Hatch':
				
				# skip if hatch already open
				if crewman.current_position.hatch_open:
					result_text = 'Hatch already open'
				else:
					if roll <= odds:
						if crewman.ToggleHatch():
							result_text = 'Success: Hatch now open'
						else:
							result_text = 'Unable to open hatch in this location'
			
			# attempt to open a nearby hatch
			elif text[:4] == 'Open':
				text = text.split(' ')[1]
				for position in self.player_unit.positions_list:
					if position.name == text:
						if position.hatch_open:
							result_text = 'Hatch already open'
						else:
							if roll <= odds:	
								if position.TogglePositionHatch():
									result_text = 'Success: Hatch now open'
								else:
									result_text = 'Unable to open hatch in this location'
						break
			
			# attempt to move to an empty position within the tank
			elif text[:5] == 'Go to ':
				text = text.split(' ')[2]
				for position in self.player_unit.positions_list:
					if position.name == text:
						if position.crewman is not None:
							result_text = 'Cannot move: Position is occupied.'
							break
						if roll <= odds:
							crewman.current_position = position
							position.crewman = crewman
							crewman.SetCEStatus()
							result_text = 'Success: Moved to ' + text + ' position'
						break
			
			# move from tank exterior to safe location
			elif text == 'Move to Safe Location':
				if roll <= odds:
					crewman.current_position = safe_location_position
					result_text = 'Success: Moved to a safe location'
				
			# return to tank exterior from safe location
			elif text == 'Return to Tank':
				if roll <= odds:
					crewman.current_position = tank_exterior_position
					result_text = 'Success: Returned to the tank exterior'
			
			# suppressing fire
			elif text == 'Suppressing Fire':
				if roll <= odds:
					result_text = 'Success: Firing suppressing fire'
				else:
					crewman.current_action = ('None', 0.0)
			
			# aid fellow crewman
			elif text == 'Aid Crewmen in Location':
				if roll <= odds:
					result_text = 'Success: Aiding any crewmen in location'
				else:
					result_text = 'Failed: Unable to aid fellow crewmen'
					crewman.current_action = ('None', 0.0)
			
			# bail out to tank exterior
			elif 'Bail Out' in text:
				# check for crewmen helping outside tank (multiple modifiers possible)
				for friendly_crewman in player_crew:
					if not friendly_crewman.alive: continue
					if friendly_crewman.current_position.location != 'Tank Exterior': continue
					if friendly_crewman.current_action == 'Aid Crewmen Bailing Out':
						roll -= 15.0
				
				if roll <= odds:
					crewman.current_position = tank_exterior_position
					result_text = 'Success: Bailed out to tank exterior'
			
			# display outcome
			DisplayResult(crewman, result_text, roll<=odds)
			
		# (re)draw the bail-out console and display on screen
		def UpdateBailOutConsole(no_highlight=False):
			
			libtcod.console_clear(con)
			
			# window title
			libtcod.console_set_default_background(con, libtcod.light_red)
			libtcod.console_rect(con, 0, 0, WINDOW_WIDTH, 3, True, libtcod.BKGND_SET)
			libtcod.console_set_default_foreground(con, libtcod.black)
			libtcod.console_print_ex(con, WINDOW_XM, 1, libtcod.BKGND_NONE,
				libtcod.CENTER, 'BAILING OUT')
			
			# display player unit
			libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
			libtcod.console_print(con, 1, 4, self.player_unit.unit_id)
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			libtcod.console_print(con, 1, 5, self.player_unit.GetStat('class'))
			libtcod.console_set_default_background(con, PORTRAIT_BG_COL)
			libtcod.console_rect(con, 1, 6, 25, 8, True, libtcod.BKGND_SET)
			portrait = self.player_unit.GetStat('portrait')
			if portrait is not None:
				libtcod.console_blit(LoadXP(portrait), 0, 0, 0, 0, con, 1, 6)
			libtcod.console_set_default_foreground(con, libtcod.white)
			if self.player_unit.unit_name != '':
				libtcod.console_print(con, 1, 6, self.player_unit.unit_name)
			
			# display tank status, nearby allies, visible enemies
			libtcod.console_set_default_foreground(con, libtcod.lighter_grey)
			libtcod.console_print(con, 27, 4, 'Status:')
			
			if abandoning_tank:
				libtcod.console_print(con, 28, 5, 'Abandoning')
			elif not self.player_unit.alive:
				libtcod.console_print(con, 28, 5, 'Knocked Out')
			
			if smoke:
				libtcod.console_set_default_foreground(con, libtcod.light_grey)
				libtcod.console_print(con, 27, 7, 'SMOKE')
			
			if fire_chance > 0.0:
				libtcod.console_set_default_foreground(con, libtcod.light_red)
				if on_fire:
					libtcod.console_print(con, 27, 9, 'FIRE')
				else:
					libtcod.console_print(con, 27, 9, 'Fire Chance:')
					libtcod.console_print(con, 28, 10, str(int(fire_chance)) + '%')
			
			libtcod.console_set_default_foreground(con, ALLIED_UNIT_COL)
			libtcod.console_print(con, 41, 4, 'Nearby Allies:')
			y = 6
			for unit in nearby_allies:
				libtcod.console_print(con, 42, y, unit.GetName())
				y += 1
				if y == 15: break
			
			libtcod.console_set_default_foreground(con, ENEMY_UNIT_COL)
			libtcod.console_print(con, 65, 4, 'Enemies in Sight:')
			y = 6
			for (distance, unit) in enemies_in_los:
				libtcod.console_print(con, 64, y, distance)
				libtcod.console_print(con, 66, y, unit.GetName())
				y += 1
				if y == 12: break
			
			# display current time and round
			libtcod.console_set_default_foreground(con, libtcod.white)
			text = str(campaign_day.day_clock['hour']).zfill(2) + ':' + str(campaign_day.day_clock['minute']).zfill(2)
			libtcod.console_print(con, 27, 13, text)
			text = 'Round ' + str(current_round) + '/' + str(max_rounds)
			libtcod.console_print(con, 43, 13, text)
			
			# column headings
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_set_default_background(con, libtcod.darker_blue)
			libtcod.console_rect(con, 2, 15, 18, 1, False, libtcod.BKGND_SET)
			libtcod.console_print(con, 3, 15, 'Crewman & Status')
			libtcod.console_rect(con, 22, 15, 10, 1, False, libtcod.BKGND_SET)
			libtcod.console_print(con, 23, 15, 'Location')
			libtcod.console_rect(con, 43, 15, 8, 1, False, libtcod.BKGND_SET)
			libtcod.console_print(con, 44, 15, 'Action')
			libtcod.console_set_default_background(con, libtcod.black)
			
			# row and column borders
			libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			DrawFrame(con, 1, 16, 88, 37)
			DrawFrame(con, 21, 16, 22, 37)
			for y in range(22, 51, 6):
				DrawFrame(con, 1, y, 88, 0)
			
			# list of crew
			y = 18
			libtcod.console_set_default_foreground(con, libtcod.white)
			for crewman in player_crew:
				
				# highlight if currently selected
				if selected_crewman == crewman and not no_highlight:
					libtcod.console_set_default_background(con, libtcod.darkest_blue)
					libtcod.console_rect(con, 2, y-1, 86, 5, False, libtcod.BKGND_SET)
					libtcod.console_set_default_background(con, libtcod.black)
				
				# crewman name and current status
				PrintExtended(con, 2, y, crewman.GetName(), first_initial=True)
				
				if not crewman.alive:
					libtcod.console_set_default_foreground(con, libtcod.light_red)
					text = 'Dead'
				else:
					if crewman.condition != 'Good Order':
						libtcod.console_set_default_foreground(con, libtcod.light_red)
					text = crewman.condition
				libtcod.console_print(con, 2, y+2, text)
				
				# critical injury if any
				for (k, v) in crewman.injury.items():
					if v != 'Critical': continue
					libtcod.console_set_default_foreground(con, libtcod.light_red)
					libtcod.console_print(con, 2, y+3, 'Critical Injury')
					break
				
				# location - could be in, on, or outside the tank
				libtcod.console_set_default_foreground(con, libtcod.white)
				libtcod.console_print(con, 23, y, crewman.current_position.location)
				if crewman.current_position.name is not None:
					libtcod.console_print(con, 23, y+1, crewman.current_position.name)
					if on_fire:
						libtcod.console_set_default_foreground(con, libtcod.light_red)
						libtcod.console_print(con, 38, y, 'FIRE')
						libtcod.console_set_default_foreground(con, libtcod.white)
					
				if crewman.current_position.location in ['Turret', 'Hull']:
					if not crewman.current_position.hatch:
						text = 'No Hatch'
					elif crewman.current_position.hatch_open:
						text = 'Hatch Open'
					else:
						text = 'Hatch Shut'
					libtcod.console_print(con, 23, y+2, text)
				
				# currently selected action and odds of success
				(text, odds) = crewman.current_action
				libtcod.console_print(con, 44, y, text)
				if odds > 0.0 and odds != 100.0:
					libtcod.console_print(con, 44, y+2, '(' + str(odds) + '%)')
				
				y += 6
				if y >= 54: break
			
			# player commands
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, 32, 54, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(con, 32, 55, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_print(con, 32, 57, 'Space')
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			libtcod.console_print(con, 38, 54, 'Select Crewman')
			libtcod.console_print(con, 38, 55, 'Select Action')
			libtcod.console_print(con, 38, 57, 'Proceed')
			
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			
		
		# set up initial round, max rounds
		current_round = 1
		max_rounds = 8
		
		# calculate fire chance per round
		if abandoning_tank:
			fire_chance = 0.0
		elif self.player_unit.GetStat('wet_stowage') is None:
			fire_chance = 5.0
		else:
			fire_chance = 2.0
		if weapon is not None:
			if weapon.GetStat('name') == 'Flame Thrower':
				fire_chance = 20.0
		
		# flags: tank is on fire, smoke
		on_fire = False
		smoke = False
		
		# create a separate list of crew
		# include dead crewman still in their position
		player_crew = []
		for position in self.player_unit.positions_list:
			if position.crewman is None: continue
			player_crew.append(position.crewman)
		
		# select first crewman by default
		selected_crewman = player_crew[0]
		
		# create two new Positions: tank exterior and safe location
		tank_exterior_position = Position(self.player_unit, {'name' : None,
			'location' : 'Tank Exterior'})
		safe_location_position = Position(self.player_unit, {'name' : None,
			'location' : 'Safe Location'})
		
		# build list of squadmates
		nearby_allies = []
		for unit in self.units:
			if not unit.alive: continue
			if unit.owning_player != 0: continue
			if unit.is_player: continue
			if GetHexDistance(0, 0, unit.hx, unit.hy) > 1: continue
			nearby_allies.append(unit)
		
		# build list of enemies in LoS
		enemies_in_los = []
		for unit in self.units:
			if not unit.alive: continue
			if unit.owning_player == 0: continue
			if unit not in self.player_unit.los_table: continue
			distance = GetHexDistance(0, 0, unit.hx, unit.hy)
			if distance == 1:
				text = 'C'
			elif distance == 2:
				text = 'M'
			else:
				text = 'L'
			enemies_in_los.append((text, unit))
		
		# generate initial list of crew bailout actions
		for crewman in player_crew:
			BuildActionList(crewman)
		
		# draw initial menu screen
		UpdateBailOutConsole(no_highlight=True)
		
		# if tank was knocked out, do initial injury checks on crew, explosion test
		if not abandoning_tank:
			
			ShowSimpleMessage('Resolving effect of knock-out hit.')
			
			# roll for player tank explosion
			player_explosion = False
			if self.player_unit.DoExplosionRoll(location, weapon):
				PlaySoundFor(self.player_unit, 'vehicle_explosion')
				ShowSimpleMessage('The impact ignites an explosion in your tank, destroying it from the inside out.')
				player_explosion = True
				smoke = True
				on_fire = True
			
			crew_effect = False
			for crewman in player_crew:
				if not crewman.alive: continue
				result = crewman.ResolveAttack({'ko_hit':True, 'location':location,
					'weapon':weapon}, explosion=player_explosion,
					show_messages=False)
				
				# display result if any
				if result is not None:
					UpdateBailOutConsole(no_highlight=True)
					DisplayResult(crewman, 'Affected by KO Hit: ' + result, False)
					crew_effect = True
			if not crew_effect:
				ShowSimpleMessage('No effect on your crew.')
		
		# if all crew dead, skip bailout procedure
		all_dead = True
		for crewman in player_crew:
			if crewman.alive:
				all_dead = False
				break
		if all_dead:
			ShowSimpleMessage('All your crew are dead.')
			return
		
		# do initial smoke roll
		if not abandoning_tank and not smoke:
			roll = GetPercentileRoll()
			if roll <= 20.0:
				smoke = True
				ShowSimpleMessage('Your tank fills with smoke.')
		
		# generate final list of crew bailout actions
		for crewman in player_crew:
			BuildActionList(crewman)
		
		# final update of screen with selected crewman highlighted
		UpdateBailOutConsole()
		
		ShowSimpleMessage('Round ' + str(current_round) + '/' + str(max_rounds))
		
		exit_menu = False
		while not exit_menu:
			if DEBUG:
				if libtcod.console_is_window_closed(): sys.exit()
			libtcod.console_flush()
			if not GetInputEvent(): continue
			
			# debug menu
			if key.vk == libtcod.KEY_F2:
				if not DEBUG: continue
				ShowDebugMenu()
				continue
			
			# proceed to next round, or finish bail-out procedure
			elif key.vk == libtcod.KEY_SPACE:
				
				# do crewmen actions
				UpdateBailOutConsole(no_highlight=True)
				for crewman in player_crew:
					DoBailoutAction(crewman)
					UpdateBailOutConsole(no_highlight=True)
				
				# update possible actions for next turn
				for crewman in player_crew:
					BuildActionList(crewman)
					UpdateBailOutConsole(no_highlight=True)
				
				# if all crew in safe location, display message and end bail-out procedure
				all_safe = True
				for crewman in player_crew:
					if not crewman.alive: continue
					if crewman.current_position.location != 'Safe Location':
						all_safe = False
						break
				if all_safe:
					ShowSimpleMessage('All your crew are safe.')
					exit_menu = True
					continue
				
				all_dead = True
				for crewman in player_crew:
					if crewman.alive:
						all_dead = False
						break
				if all_dead:
					ShowSimpleMessage('All your crew are dead.')
					exit_menu = True
					continue
				
				# if tank is on fire, check for crewmen injuries
				if on_fire:
					for crewman in player_crew:
						if crewman.current_position.location in ['Tank Exterior', 'Safe Location']:
							continue
						result = crewman.ResolveAttack({'burn_up' : True}, show_messages=False)
						# display result if any
						if result is not None:
							DisplayResult(crewman, 'Affected by Fire: ' + result, False)
						BuildActionList(crewman)
						UpdateBailOutConsole(no_highlight=True)
				
				# otherwise, do fire roll
				else:
					roll = GetPercentileRoll()
					if roll <= fire_chance:
						on_fire = True
						UpdateBailOutConsole(no_highlight=True)
						ShowSimpleMessage('Your tank has caught on fire.')
				
				# do smoke roll
				if not abandoning_tank and not smoke:
					roll = GetPercentileRoll()
					if on_fire: roll -= 50.0
					if roll <= 5.0:
						smoke = True
						ShowSimpleMessage('Your tank fills with smoke.')
				
				# check for enemies in LoS attacking player
				incoming_fp = 0
				for (distance, unit) in enemies_in_los:
					chance = 10.0
					
					# suppression by nearby allies
					if len(nearby_allies) >= 2:
						chance -= 3.0
					elif len(nearby_allies) == 1:
						chance -= 1.5
					
					# suppression by crewmen - close range only
					if distance == 'C':
						for crewman in player_crew:
							if crewman.current_action[0] == 'Suppressing Fire':
								chance -= 2.0
					
					if chance < 1.0: chance = 1.0
					roll = GetPercentileRoll()
					
					if roll > chance: continue
					
					if distance == 'C':
						incoming_fp += 4
					elif distance == 'M':
						incoming_fp += 2
					else:
						incoming_fp += 1
					
				# apply any incoming firepower to exposed crewmen and crewmen on tank exterior
				if incoming_fp > 0:
					
					# play attacking sounds
					for i in range(4):
						if libtcod.random_get_int(0, 1, 5) == 1:
							PlaySound('zb_53_mg_00')
						else:
							PlaySound('rifle_fire_0' + str(libtcod.random_get_int(0, 0, 3)))
					
					ShowSimpleMessage('Enemy units fire at your tank, resolving ' +
						str(incoming_fp) + ' firepower.')
					fp_result = False
					for crewman in player_crew:
						if not crewman.alive: continue
						if crewman.current_position.location == 'Safe Location':
							continue
						if crewman.current_position.location != 'Tank Exterior' and not crewman.ce:
							continue
						result = crewman.ResolveAttack({'firepower' : incoming_fp}, show_messages=False)
						# display result if any
						if result is not None:
							UpdateBailOutConsole(no_highlight=True)
							DisplayResult(crewman, 'Hit by Firepower: ' + result, False)
							fp_result = True
					if not fp_result:
						ShowSimpleMessage('No effect.')
				
				# end of final round 
				if current_round == max_rounds:
					
					# do final rescue checks
					for crewman in player_crew:
						if not crewman.alive: continue
						if crewman.current_position.location == 'Safe Location':
							continue
						if crewman.current_position.location == 'Tank Exterior':
							if crewman.condition == 'Unconscious':
								result_text = 'Taken'
							else:
								result_text = 'Escaped'
							result_text += ' to safe location'
						else:
							if on_fire and crewman.condition == 'Unconscious':
								crewman.KIA()
								result_text = 'Burns to death in the tank.'
							else:
								if crewman.condition == 'Unconscious':
									result_text = 'Taken'
								else:
									result_text = 'Escaped'
								result_text += ' to safe location'
						
						if crewman.alive:
							crewman.current_position.location = 'Safe Location'
							UpdateBailOutConsole(no_highlight=True)
						
						DisplayResult(crewman, result_text, crewman.alive)
					
					exit_menu = True
					continue
				
				current_round += 1
				selected_crewman = player_crew[0]
				UpdateBailOutConsole()
				ShowSimpleMessage('Round ' + str(current_round) + '/' + str(max_rounds))
				continue	
			
			# key commands
			key_char = DeKey(chr(key.c).lower())
			
			# change selected crewman
			if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				i = player_crew.index(selected_crewman)
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if i == 0:
						i = len(player_crew) - 1
					else:
						i -= 1
				else:
					if i == len(player_crew) - 1:
						i = 0
					else:
						i += 1
				selected_crewman = player_crew[i]
				PlaySoundFor(None, 'menu_select')
				UpdateBailOutConsole()
				continue
			
			# change selected action
			elif key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
				if len(selected_crewman.action_list) <= 1: continue
				i = selected_crewman.action_list.index(selected_crewman.current_action)
				if key_char == 'a' or key.vk == libtcod.KEY_LEFT:
					if i == 0:
						i = len(selected_crewman.action_list) - 1
					else:
						i -= 1
				else:
					if i == len(selected_crewman.action_list) - 1:
						i = 0
					else:
						i += 1
				selected_crewman.current_action = selected_crewman.action_list[i]
				PlaySoundFor(None, 'menu_select')
				UpdateBailOutConsole()
				continue
	
	
	##################################################################################
	
	
	# spawn enemy units on the scenario layer
	# if reinforcement is True, only spawn one unit and add them to the LoS tables
	# if unit_id is set, don't randomly roll and use that one
	def SpawnEnemyUnits(self, reinforcement=False, nation=None, unit_id=None):
		
		enemy_unit_list = []
		
		# spawning one particular unit
		if nation is not None and unit_id is not None:
			enemy_unit_list.append((nation, unit_id))
		
		# enemy reinforcements arrive
		elif reinforcement:
			unit_list = []
			for unit in self.units:
				if unit.owning_player == 0: continue
				unit_list.append((unit.nation, unit.unit_id))
			
			# check adjacent zones too
			for direction in range(6):
				(hx, hy) = campaign_day.GetAdjacentCDHex(self.cd_map_hex.hx, self.cd_map_hex.hy, direction)
				# make sure this adjacent zone is on map
				if (hx, hy) not in CAMPAIGN_DAY_HEXES: continue
				if len(campaign_day.map_hexes[(hx, hy)].enemy_units) > 0:
					unit_list += campaign_day.map_hexes[(hx, hy)].enemy_units
				
			if len(unit_list) == 0: return False
			enemy_unit_list.append(choice(unit_list))
		
		else:
		
			# player is being attacked in own zone, generate enemy units for this zone
			if self.cd_map_hex.controlled_by == 0 and len(self.cd_map_hex.enemy_units) == 0:
				self.cd_map_hex.GenerateStrengthAndUnits(campaign_day.mission, player_attacked=True)
			
			for (nation, unit_id) in self.cd_map_hex.enemy_units:
				enemy_unit_list.append((nation, unit_id))
		
		# spawn one unit per unit id in the list
		for (nation, unit_id) in enemy_unit_list:
	
			# determine spawn location
			distance = libtcod.random_get_int(0, 1, 3)
			
			if distance == 1:
				if GetPercentileRoll() <= 65.0:
					distance += 1
			if session.unit_types[unit_id]['category'] == 'Infantry':
				if GetPercentileRoll() <= 75.0:
					distance -= 1
			elif session.unit_types[unit_id]['category'] in ['Cavalry', 'Vehicle']:
				if GetPercentileRoll() <= 60.0:
					distance += 1
			
			# check for campaign skill
			if self.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Unique Opportunities'):
				distance += 1	
			
			if distance < 1:
				distance = 1
			elif distance > 3:
				distance = 3
			
			hex_list = GetHexRing(0, 0, distance)
			shuffle(hex_list)
			
			# choose a random hex in which to spawn
			for (hx, hy) in hex_list:
				
				# make sure no units from opposing force already here
				if len(self.hex_dict[(hx,hy)].unit_stack) > 0:
					if self.hex_dict[(hx,hy)].unit_stack[0].owning_player == 0:
						continue
				
				# if player spotted enemy units first, unlikely that they will spawn behind the player
				if not self.ambush:
					if GetDirectionToward(hx, hy, 0, 0) in [5, 0, 1]:
						if GetPercentileRoll() <= 85.0: continue
				break
			
			# create the unit
			unit = Unit(unit_id)
			unit.owning_player = 1
			unit.nation = nation
			unit.ai = AI(unit)
			unit.ai.Reset()
			unit.GenerateNewPersonnel()
			unit.SpawnAt(hx, hy)
			
			# automatically deploy if gun
			# FUTURE: guns might be surprised undeployed
			if unit.GetStat('category') == 'Gun':
				unit.deployed = True
			
			# if current campaign region is north africa, german and italian vehicles are all unreliable before Oct. 1941
			if campaign.stats['region'] == 'North Africa' and unit.nation in ['Germany', 'Italy']:
				if campaign.today < '1941.10.01' and unit.GetStat('category') == 'Vehicle':
					unit.stats['unreliable'] = True
			
			# check for special weapon presence in unit
			if unit.GetStat('class') == 'Infantry Squad':
				
				added_sw = False
				
				# check for PF
				if not added_sw and nation == 'Germany' and campaign.today >= '1943.07.01':
					chance = 3
					if campaign.today <= '1943.09.30':
						chance -= 1
					elif campaign.today >= '1945.01.01':
						chance += 1
					if libtcod.random_get_int(0, 1, 10) <= chance:
						unit.weapon_list.append(Weapon(unit, PF_WEAPON))
						added_sw = True
				
				# check for MOL
				if not added_sw:
					chance = 3
					if libtcod.random_get_int(0, 1, 10) <= chance:
						unit.weapon_list.append(Weapon(unit, MOL_WEAPON))
						added_sw = True
				
				# check for DC
				if not added_sw:
					chance = 2
					if libtcod.random_get_int(0, 1, 10) <= chance:
						unit.weapon_list.append(Weapon(unit, DC_WEAPON))
			
			# set facing
			if unit.GetStat('category') not in ['Infantry', 'Cavalry']:
				if self.ambush:
					# set facing toward player
					direction = GetDirectionToward(unit.hx, unit.hy, 0, 0)
				else:
					# random facing
					direction = libtcod.random_get_int(0, 0, 5)
				unit.facing = direction
				if 'turret' in unit.stats:
					unit.turret_facing = direction
			
			# some units can be spawned dug-in, entrenched, or fortified
			if unit.GetStat('category') in ['Infantry', 'Gun'] and campaign_day.mission != 'Fighting Withdrawal':
				
				if campaign_day.mission in ['Battle', 'Counterattack']:
					chance1 = 5.0
					chance2 = 15.0
					chance3 = 25.0
				else:
					chance1 = 2.0
					chance2 = 10.0
					chance3 = 15.0
				
				roll = GetPercentileRoll()
				
				if roll <= chance1:
					unit.fortified = True
				elif roll <= chance2:
					unit.entrenched = True
				elif roll <= chance3:	
					unit.dug_in = True
			
			# reinforcements need to be added to the LoS table
			if reinforcement:
				self.GenerateUnitLoS(unit)
			
			# special: some units are spawned with non-combat companion units
			if unit_id == 'Light Artillery Car':
				unit2 = Unit('Locomotive')
				unit2.owning_player = 1
				unit2.nation = unit.nation
				unit2.ai = AI(unit)
				unit2.ai.Reset()
				unit2.GenerateNewPersonnel()
				unit2.SpawnAt(hx, hy)
				unit2.facing = GetDirectionToward(unit2.hx, unit2.hy, 0, 0)
				if reinforcement:
					self.GenerateUnitLoS(unit2)
			
			# set up transported unit if any
			if 'enemy_transported_units' in campaign.stats:
				transport_dict = campaign.stats['enemy_transported_units']
				if unit.nation not in transport_dict: continue
				if unit_id not in transport_dict[unit.nation]: continue
				transport_list = list(transport_dict[unit.nation][unit_id].items())
				shuffle(transport_list)
				for k, value in transport_list:
					if libtcod.random_get_int(0, 1, 100) <= value:
						unit.transport = k
						break
		
		return True			
	
	
	# given a combination of an attacker, weapon, and target, see if this would be a
	# valid attack; if not, return a text description of why not
	# if ignore_facing is true, we don't check whether weapon is facing correct direction
	def CheckAttack(self, attacker, weapon, target, ignore_facing=False):
		
		# check that proper crew command has been set if player is attacking
		if attacker == self.player_unit:
			
			position_list = weapon.GetStat('fired_by')
			if position_list is None:
				return 'No positions to fire this weapon'
			
			if weapon.GetStat('type') == 'Gun':
				command_req = 'Operate Gun'
			elif weapon.GetStat('type') in MG_WEAPONS:
				command_req = 'Operate MG'
			else:
				return 'Unknown weapon type!'
				
			crewman_found = False
			aamg_bu = False
			
			# check each crew position and try to find a crewman on the correct command to operate this weapon
			for position in self.player_unit.positions_list:
				
				if position.name not in position_list: continue
				if position.crewman is None: continue
				if position.crewman.current_cmd != command_req: continue
				
				# check that position is in same location as weapon mount if any
				if weapon.GetStat('mount') is not None:
					if position.location != weapon.GetStat('mount'):
						continue
				
				# if AA MG, crewman must normally be CE to operate
				if weapon.GetStat('type') == 'AA MG':
					if not position.crewman.ce and weapon.GetStat('bu_ok') is None:
						aamg_bu = True
						continue
				
				crewman_found = True
				break
			
			if not crewman_found and aamg_bu:
				return 'Crewman must be CE to operate this weapon'
			elif not crewman_found:
				return 'No crewman operating this weapon'
		
		# check that weapon isn't broken, isn't jammed, and hasn't already fired
		if weapon.broken:
			return 'Weapon is broken!'
		if weapon.jammed:
			return 'Weapon is jammed!'
		if weapon.fired:
			return 'Weapon has already fired this turn'
		
		# close combat attacks
		if weapon.GetStat('type') == 'Close Combat':
			if not target.spotted:
				return 'Target location unknown'
			if attacker.pinned:
				return 'Cannot initiate Close Combat when Pinned'
		
		# not a ballistic attack and no LoS
		elif weapon.GetStat('ballistic_attack') is None:
			if not attacker.los_table[target]:
				return 'No Line of Sight to Target'
		
		# if we're not ignoring facing,
		# check that target is in covered hexes and range
		if not ignore_facing:
			if (target.hx, target.hy) not in weapon.covered_hexes:
				return "Target not in weapon's covered arc"
		
		# check that current ammo is available and this ammo would affect the target
		if weapon.GetStat('type') == 'Gun':
			
			if weapon.ammo_type is None:
				return 'No ammo loaded'
			
			# check that at least one shell of required ammo is available
			ammo_avail = False
			if weapon.using_rr:
				if weapon.ready_rack[weapon.ammo_type] > 0:
					ammo_avail = True
			if weapon.ammo_stores[weapon.ammo_type] > 0:
				ammo_avail = True
			if not ammo_avail:
				return 'No more ammo of the selected type'
			
			# concealed targets may be attacked with AP
			if target.spotted:
				if weapon.ammo_type in AP_AMMO_TYPES and target.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']:
					return 'AP has no effect on target'
		
		# check firing group restrictions
		for weapon2 in attacker.weapon_list:
			if weapon2 == weapon: continue
			if not weapon2.fired: continue
			if weapon2.GetStat('firing_group') == weapon.GetStat('firing_group'):
				return 'A weapon on this mount has already fired'
		
		# check for hull-mounted weapons blocked by HD status
		if len(attacker.hull_down) > 0:
			mount = weapon.GetStat('mount')
			if mount is not None:
				if mount == 'Hull':
					if weapon.GetStat('type') != 'Turret MG':
						if attacker.facing == attacker.hull_down[0]:
							return 'Weapon blocked by HD status'
		
		# check for turret-mounted weapons blocked by hull direction
		if not ignore_facing:
			mount = weapon.GetStat('mount')
			if mount is not None:
				if mount == 'Turret':
					blocked_dirs = weapon.GetStat('blocked_hull_dirs')
					if blocked_dirs is not None:
						if str(ConstrainDir(attacker.turret_facing - attacker.facing)) in blocked_dirs:
							return 'Weapon blocked by hull direction'
		
		# attack can proceed
		return ''
	
	
	# generate a profile for a given attack
	# if pivot or turret_rotate are set to True, will override actual attacker status
	def CalcAttack(self, attacker, weapon, target, pivot=False, turret_rotate=False):
				
		profile = {}
		profile['attacker'] = attacker
		profile['weapon'] = weapon
		profile['ammo_type'] = weapon.ammo_type
		profile['target'] = target
		profile['modifier'] = ''	# placeholder for any final modifiers to attack result
		profile['result'] = ''		# placeholder for text rescription of result
				
		# determine attack type
		weapon_type = weapon.GetStat('type')
		if weapon_type == 'Gun':
			profile['type'] = 'Point Fire'
		elif weapon_type == 'Small Arms' or weapon_type in MG_WEAPONS:
			profile['type'] = 'Area Fire'
			profile['effective_fp'] = 0		# placeholder for effective fp
		elif weapon_type == 'Close Combat':
			profile['type'] = 'Close Combat'
		else:
			print('ERROR: Weapon type not recognized: ' + weapon.stats['name'])
			return None
		
		# determine if ballistic attack
		profile['ballistic_attack'] = False
		if weapon.GetStat('ballistic_attack') is not None:
			profile['ballistic_attack'] = True
		
		# for player unit only:
		# determine crewman operating weapon:
		# need to find a match between positions that can fire the weapon,
		# and who is on the correct command
		profile['crewman'] = None
		if attacker.is_player:
			
			if weapon.GetStat('fired_by') is not None:
				if weapon_type == 'Gun':
					command_req = 'Operate Gun'
				elif weapon_type in MG_WEAPONS:
					command_req = 'Operate MG'
				
				position_list = weapon.GetStat('fired_by')
				
				for position in attacker.positions_list:
					if position.name not in position_list: continue
					if position.crewman is None: continue
					if position.crewman.current_cmd != command_req: continue
					
					# check that position is in same location as weapon mount if any
					if weapon.GetStat('mount') is not None:
						if position.location != weapon.GetStat('mount'):
							continue
					
					# if AA MG, crewman must normally be CE to operate
					if weapon.GetStat('type') == 'AA MG':
						if not position.crewman.ce and weapon.GetStat('bu_ok') is None:
							continue
					
					# found operating crewman
					profile['crewman'] = position.crewman
					break
			
			# unable to find firing crewman
			if profile['crewman'] is None: return None
		
		# calculate distance to target
		distance = GetHexDistance(attacker.hx, attacker.hy, target.hx, target.hy)
		
		# list of modifiers
		# [maximum displayable modifier description length is two lines of 17 and 16 characters]
		
		modifier_list = []
		
		# base critical hit chance
		profile['critical_hit'] = CRITICAL_HIT
		
		# DC, FT, MOL can't get critical hits
		if weapon.GetStat('name') in ['Demolition Charge', 'Flame Thrower', 'Molotovs']:
			profile['critical_hit'] = 0.0
		
		# point fire attacks (eg. guns)
		if profile['type'] == 'Point Fire':
			
			# calculate critical hit chance modifier
			if profile['crewman'] is not None:
				if 'Knows Weak Spots' in profile['crewman'].skills:
					if weapon_type == 'Gun' and target.GetStat('armour') is not None:
						profile['critical_hit'] += profile['crewman'].GetSkillMod(2.0)
			
			# calculate base success chance
			
			# possible to fire HE at concealed targets
			if not target.spotted:
				# use infantry chance as base chance
				profile['base_chance'] = PF_BASE_CHANCE[distance][1]
			else:
				if target.GetStat('category') == 'Vehicle':
					profile['base_chance'] = PF_BASE_CHANCE[distance][0]
				else:
					profile['base_chance'] = PF_BASE_CHANCE[distance][1]
			
			# calculate modifiers and build list of descriptions
			
			# description max length is 19 chars
			
			# attacker is moving
			if attacker.moving:
				modifier_list.append(('Attacker Moving', -60.0))
			
			# attacker pivoted
			elif pivot or attacker.facing != attacker.previous_facing:
				if weapon.GetStat('turntable') is not None:
					modifier_list.append(('Attacker Pivoted', -15.0))
				else:
					modifier_list.append(('Attacker Pivoted', -35.0))
			
			# player or player squad member attacker pivoted
			elif self.player_pivot != 0 and (attacker == scenario.player_unit or attacker in scenario.player_unit.squad):
				modifier_list.append(('Attacker Pivoted', -35.0))

			# weapon has turret rotated
			elif weapon.GetStat('mount') == 'Turret':
				if turret_rotate or attacker.turret_facing != attacker.previous_turret_facing:
					
					# calculate modifier - assume that vehicle has a turret
					if attacker.GetStat('turret') == 'FT':
						mod = -10.0
					elif attacker.GetStat('turret') == 'VST':
						mod = -40.0
					else:
						mod = -20.0
					modifier_list.append(('Turret Rotated', mod))
			
			# attacker pinned or reduced
			if attacker.pinned:
				modifier_list.append(('Attacker Pinned', -60.0))
			elif attacker.reduced:
				modifier_list.append(('Attacker Reduced', -40.0))
			
			# precipitation effects
			if campaign_day.weather['Precipitation'] == 'Rain':
				modifier_list.append(('Rain', -5.0 * float(distance)))
			elif campaign_day.weather['Precipitation'] == 'Snow':
				modifier_list.append(('Snow', -10.0 * float(distance)))
			elif campaign_day.weather['Precipitation'] == 'Heavy Rain':
				modifier_list.append(('Heavy Rain', -15.0 * float(distance)))
			elif campaign_day.weather['Precipitation'] == 'Blizzard':
				modifier_list.append(('Blizzard', -20.0 * float(distance)))
			
			# fog, smoke, or dust concealment - only apply the one that will have the most effect
			vision_mod_text = ''
			vision_mod = 0.0
			
			if campaign_day.weather['Fog'] > 0:
				if 4 - distance <= campaign_day.weather['Fog']:
					mod = round(-35.0 * distance, 1)
					if mod < vision_mod:
						vision_mod_text = 'Fog'
						vision_mod = mod
			
			effective_smoke = float(attacker.smoke + target.smoke)
			if effective_smoke > 0.0:
				mod = round(-25.0 * effective_smoke, 1)
				if mod < vision_mod:
					vision_mod_text = 'Smoke'
					vision_mod = mod
			
			effective_dust = float(attacker.dust + target.dust)
			if effective_dust > 0.0:
				mod = round(-15.0 * effective_dust, 1)
				if mod < vision_mod:
					vision_mod_text = 'Dust'
					vision_mod = mod
			
			if vision_mod < 0.0:
				modifier_list.append((vision_mod_text, vision_mod))
			
			
			# inferior gun
			if weapon_type == 'Gun':
				if weapon.GetStat('inferior_gun') is not None:
					modifier_list.append(('Inferior Gun', -10.0))
			
			# ballistic attack with no LoS
			if profile['ballistic_attack'] and not attacker.los_table[target]:
				modifier_list.append(('No LoS', -20.0))
			
			# concealed target
			if not target.spotted:
				modifier_list.append(('Unspotted Target', -40.0))
			
			# spotted target
			else:
				
				# check to see if weapon has acquired target
				if weapon.acquired_target is not None:
					(ac_target, level) = weapon.acquired_target
					if ac_target == target:
						text = 'Acquired Target'
						if level == 1:
							text += '+'
						modifier_list.append((text, AC_BONUS[distance][level]))
				
				# target is moving
				if target.moving:
					
					if attacker.GetStat('category') == 'Vehicle':
						
						# fixed mount guns have a higher penalty
						if weapon.GetStat('mount') == 'Hull':
							mod = -45.0
						else:
							mod = -30.0
					
					elif attacker.GetStat('category') == 'Gun':
						
						if attacker.GetStat('turntable') is not None:
							mod = -15.0
						else:
							mod = -30.0
					
					else:
						mod = -30.0
					
					if mod != 0.0:
						modifier_list.append(('Target Moving', mod))
				
				# target size
				size_class = target.GetStat('size_class')
				if size_class is not None:
					if size_class != 'Normal':
						text = size_class + ' Target'
						mod = PF_SIZE_MOD[size_class]
						modifier_list.append((text, mod))
				
				# target is on overrun
				if target.overrun:
					
					# point blank range
					if attacker.hx == 0 and attacker.hy == -1:
						modifier_list.append(('Point Blank Range', 20.0))
				
				else:
				
					# target terrain
					tem = target.GetTEM()
					if tem != 0.0:
						if profile['ballistic_attack']:
							tem = round((tem * 0.5), 1)
						modifier_list.append(('Target in ' + target.terrain, tem))
			
			# long / short-barreled gun
			long_range = weapon.GetStat('long_range')
			if long_range is not None:
				if long_range == 'S' and distance > 1:
					modifier_list.append(('Short Gun', -12.0))
				
				elif long_range == 'L' and distance > 1:
					modifier_list.append(('Long Gun', 12.0))
				
				elif long_range == 'LL':
					if distance == 2:
						modifier_list.append(('Very Long Gun', 12.0))
					elif distance >= 3:
						modifier_list.append(('Very Long Gun', 24.0))
			
			if weapon_type == 'Gun' and not profile['ballistic_attack']:
				
				# APCR/APDS ammo
				if profile['ammo_type'] in ['APCR', 'APDS']:
					
					if 2 <= distance <= 3:
						modifier_list.append((profile['ammo_type'], -12.0))
					elif 4 <= distance <= 5:
						modifier_list.append((profile['ammo_type'], -24.0))
					elif distance >= 6:
						modifier_list.append((profile['ammo_type'], -36.0))
					
				# smaller-calibre gun at longer range
				calibre_mod = 0
				
				if weapon.stats['name'] == 'AT Rifle':
					calibre = 20
				else:
					calibre = int(weapon.stats['calibre'])
				
				if calibre <= 40 and distance >= 2:
					calibre_mod -= 1	
				
				if calibre <= 57:
					if distance == 2:
						calibre_mod -= 1
					elif distance == 3:
						calibre_mod -= 2
					elif distance >= 4:
						calibre_mod -= 3
				if calibre_mod < 0:
					modifier_list.append(('Small Calibre', (8.0 * calibre_mod)))
				
				# Smoke Ammo
				if profile['ammo_type'] == 'Smoke':
					modifier_list.append(('Area Effect', 20.0))
			
			# ballistic attacks have a higher chance, since they don't usually score a direct hit
			if profile['ballistic_attack']:
				mod = round(profile['base_chance'] * BALLISTIC_TO_HIT_MOD, 1)
				modifier_list.append(('Ballistic Attack', mod))
		
		# area fire
		elif profile['type'] == 'Area Fire':
			
			# set flag if this is a valid overrun attack
			overrun_attack = False
			if attacker.overrun and target.spotted and target.GetStat('category') in ['Infantry', 'Cavalry', 'Gun'] and target.hx == 0 and target.hy == -1:
				overrun_attack = True
			
			# calculate base FP
			fp = int(weapon.GetStat('fp'))
			
			# point blank range multiplier
			if distance == 0:
				fp = fp * 2
			
			profile['base_fp'] = fp
			
			# calculate base effect chance
			if target.GetStat('category') == 'Vehicle':
				base_chance = VEH_FP_BASE_CHANCE
			else:
				base_chance = INF_FP_BASE_CHANCE
			for i in range(2, fp + 1):
				base_chance += FP_CHANCE_STEP * (FP_CHANCE_STEP_MOD ** (i-1)) 
			profile['base_chance'] = round(base_chance, 1)
			
			# store the rounded base chance so we can use it later for modifiers
			base_chance = profile['base_chance']
			
			# calculate modifiers
			
			# overrun attack
			if overrun_attack:
				modifier_list.append(('Overrun Attack', round(base_chance * 0.5, 1)))
			
			else:
			
				# attacker moving
				if attacker.moving:
					mod = round(base_chance / 2.0, 1)
					modifier_list.append(('Attacker Moving', 0.0 - mod))
				
				# attacker pivoted
				elif attacker.facing != attacker.previous_facing:
					mod = round(base_chance / 3.0, 1)
					modifier_list.append(('Attacker Pivoted', 0.0 - mod))
	
				# player attacker pivoted
				elif attacker == scenario.player_unit and self.player_pivot != 0:
					mod = round(base_chance / 3.0, 1)
					modifier_list.append(('Attacker Pivoted', 0.0 - mod))
	
				# weapon turret rotated
				elif weapon.GetStat('mount') == 'Turret':
					if attacker.turret_facing != attacker.previous_turret_facing:
						mod = round(base_chance / 4.0, 1)
						modifier_list.append(('Turret Rotated', 0.0 - mod))
			
			# attacker pinned or reduced
			if attacker.pinned:
				mod = round(base_chance / 2.0, 1)
				modifier_list.append(('Attacker Pinned', 0.0 - mod))
			elif attacker.reduced:
				mod = round(base_chance / 3.0, 1)
				modifier_list.append(('Attacker Reduced', 0.0 - mod))
			
			# fog, smoke, or dust concealment - only apply the one that will have the most effect
			vision_mod_text = ''
			vision_mod = 0.0
			
			if campaign_day.weather['Fog'] > 0:
				if 4 - distance <= campaign_day.weather['Fog']:
					mod = round(base_chance * campaign_day.weather['Fog'] * 0.3, 1)
					if mod > vision_mod:
						vision_mod_text = 'Fog'
						vision_mod = mod
			
			effective_smoke = float(attacker.smoke + target.smoke)
			if effective_smoke > 0.0:
				mod = round(base_chance * effective_smoke * 0.2, 1)
				if mod > vision_mod:
					vision_mod_text = 'Smoke'
					vision_mod = mod
			
			effective_dust = float(attacker.dust + target.dust)
			if effective_dust > 0.0:
				mod = round(base_chance * effective_dust * 0.1, 1)
				if mod > vision_mod:
					vision_mod_text = 'Dust'
					vision_mod = mod
			
			if vision_mod > 0.0:
				modifier_list.append((vision_mod_text, 0.0 - vision_mod))
			
			
			if not target.spotted:
				modifier_list.append(('Unspotted Target', -30.0))
			else:
				
				# check to see if MG has acquired target
				if weapon.acquired_target is not None:
					(ac_target, level) = weapon.acquired_target
					if ac_target == target:
						mod = round(15.0 + (float(level) * 15.0), 1)
						if distance == 3:
							mod = round(mod * 1.15, 1)
						text = 'Acquired Target'
						if level == 1:
							text += '+'
						modifier_list.append((text, mod))
			
				# target is infantry
				if target.GetStat('category') == 'Infantry':
					# and moving
					if target.moving:
						mod = round(base_chance / 2.0, 1)
						modifier_list.append(('Target is Infantry Moving', mod))
					# is support weapon team
				elif target.GetStat('class') == 'Support Weapon Team':
						modifier_list.append(('Target is Small Team', -20.0))
				
				# target size
				size_class = target.GetStat('size_class')
				if size_class is not None:
					if size_class != 'Normal':
						text = size_class + ' Target'
						mod = PF_SIZE_MOD[size_class]
						modifier_list.append((text, mod))
				
				# gun shield
				if not overrun_attack and target.GetStat('gun_shield') is not None:
					if GetFacing(attacker, target) == 'Front':
						modifier_list.append(('Gun Shield', -15.0))
			
				# fortified, entrenched, dug-in, or TEM modifier
				tem_mod = (None, 0.0)
				
				if target.fortified:
					tem_mod = ('Target Fortified', -50.0)
				elif target.entrenched:
					if overrun_attack:
						tem_mod = ('Target Entrenched', -20.0)
					else:
						tem_mod = ('Target Entrenched', -30.0)
				elif target.dug_in:
					if overrun_attack:
						tem_mod = ('Target Dug-in', -5.0)
					else:
						tem_mod = ('Target Dug-in', -15.0)
				
				# apply target terrain modifier if better
				tem = target.GetTEM()
				if tem < tem_mod[1]:
					tem_mod = ('Target in ' + target.terrain, tem)
				
				if tem_mod[0] != None:
					
					(text, mod) = tem_mod
					
					# overrun also reduces any fortified, entrenched, dug-in, or TEM modifier
					if overrun_attack:
						mod = round(mod * 0.5, 1)
					
					modifier_list.append((text, mod))
		
		# close combat attacks (eg. grenades, demo charges, etc.)
		elif profile['type'] == 'Close Combat':
			
			# determine base success chance
			if target.GetStat('category') == 'Vehicle':
				profile['base_chance'] = CC_BASE_CHANCE[0]
			else:
				profile['base_chance'] = CC_BASE_CHANCE[1]
			
			# firing a LATW
			if weapon.stats['name'] in AT_CC_WEAPONS:
				if weapon.stats['name'] in ['Panzerfaust', 'Panzerfaust Klein']:
					profile['base_chance'] = 35.0
				elif weapon.stats['name'] in ['Bazooka', 'Panzerschreck']:
					profile['base_chance'] = 70.0
				elif weapon.stats['name'] == 'PIAT':
					profile['base_chance'] = 50.0
				else:
					profile['base_chance'] = PF_BASE_CHANCE[distance][1]
			
			# calculate modifiers
			
			# attacker has been reduced
			if attacker.reduced:
				modifier_list.append(('Attacker Reduced', -20.0))
			
			# smoke or dust in target location
			if target.smoke >= 2:
				modifier_list.append(('Smoke', 25.0))
			elif target.dust >= 2:
				modifier_list.append(('Dust', 20.0))
			elif target.smoke == 1:
				modifier_list.append(('Smoke', 10.0))
			elif target.dust == 1:
				modifier_list.append(('Dust', 5.0))
			
			# target is a moving vehicle or cavalry
			if target.moving and target.GetStat('category') in ['Vehicle', 'Cavalry']:
				modifier_list.append(('Moving Target', -60.0))
			
			# target size
			size_class = target.GetStat('size_class')
			if size_class is not None:
				if size_class != 'Normal':
					text = size_class + ' Target'
					mod = PF_SIZE_MOD[size_class]
					modifier_list.append((text, mod))
			
			# target terrain
			tem = target.GetTEM()
			if tem != 0.0:
				
				# for placed/thrown weapons, improves odds of getting close enough for a good attack
				if weapon.GetStat('name') in ['Demolition Charge', 'Molotovs', 'Grenades']:
					modifier_list.append((target.terrain, abs(tem)))
				else:
					modifier_list.append((target.terrain, tem))
			
			if target.fortified:
				modifier_list.append(('Target Fortified', -20.0))
		
		# check for Commander directing fire
		for position in ['Commander', 'Commander/Gunner']:
			crewman = attacker.GetPersonnelByPosition(position)
			if crewman is None: continue
			if crewman.current_cmd == 'Direct Fire':
				
				crewman_mod_list = []
				
				# base direction modifier
				mod = crewman.GetSkillMod(3.0)
				if not crewman.ce: mod = mod * 0.5
				crewman_mod_list.append(('Commander Fire Direction', mod))
				
				# check for possible skill modifiers
				if 'Fire Spotter' in crewman.skills:
					mod = crewman.GetSkillMod(5.0)
					if not crewman.ce: mod = mod * 0.5
					crewman_mod_list.append(('Fire Spotter', mod))
				
				if 'MG Spotter' in crewman.skills:
					if weapon_type in MG_WEAPONS:
						mod = crewman.GetSkillMod(7.0)
						if not crewman.ce: mod = mod * 0.5
						crewman_mod_list.append(('MG Spotter', mod))
				
				if 'Gun Spotter' in crewman.skills:
					if weapon_type == 'Gun':
						mod = crewman.GetSkillMod(7.0)
						if not crewman.ce: mod = mod * 0.5
						crewman_mod_list.append(('Gun Spotter', mod))
				
				# sort list by best modifiers and add
				crewman_mod_list.sort(key = lambda x: x[1], reverse=True)
				modifier_list.append(crewman_mod_list[0])
					
				break
		
		# check for firing crew skills
		if profile['crewman'] is not None:
			
			# check for operating crewman in untrained position
			if profile['crewman'].UntrainedPosition():
				modifier_list.append(('Untrained Crewman', -50.0))
			
			else:
				crewman_mod_list = []
				
				if weapon_type == 'Gun':
					
					if 'Crack Shot' in profile['crewman'].skills:
						mod = profile['crewman'].GetSkillMod(3.0)
						crewman_mod_list.append(('Crack Shot', mod))
					if target.moving and 'Target Tracker' in profile['crewman'].skills:
						mod = profile['crewman'].GetSkillMod(7.0)
						crewman_mod_list.append(('Target Tracker', mod))
					if distance == 3 and 'Sniper' in profile['crewman'].skills:
						mod = profile['crewman'].GetSkillMod(7.0)
						crewman_mod_list.append(('Sniper', mod))
					
					# skill for firing in precepitation
					if campaign_day.weather['Precipitation'] in ['Rain', 'Snow', 'Heavy Rain', 'Blizzard'] and 'Target Focus' in profile['crewman'].skills:
						for (text, mod) in modifier_list:
							if text in ['Rain', 'Snow', 'Heavy Rain', 'Blizzard']:
								break
						skill_mod = profile['crewman'].GetSkillMod(8.0)
						if skill_mod > abs(mod):
							skill_mod = abs(mod)
						crewman_mod_list.append(('Target Focus', skill_mod))
				
				# if 1+ skill modifiers are available, sort list by best modifiers and add
				if len(crewman_mod_list) > 0:
					crewman_mod_list.sort(key = lambda x: x[1], reverse=True)
					modifier_list.append(crewman_mod_list[0])
				
			# check for injury modifiers
			for (k, v) in profile['crewman'].injury.items():
				if k not in ['Right Arm & Hand', 'Left Arm & Hand']: continue
				if v is None: continue
				if v not in ['Heavy', 'Serious', 'Critical']: continue
				modifier_list.append(('Arm/Hand Injury', -15.0))	
		
		# operating crewman fatigue
		if profile['crewman'] is not None:
			if profile['crewman'].fatigue > 0:
				modifier_list.append(('Crewman Fatigue', 0.0 - float(profile['crewman'].fatigue * 2)))
		
		# prune out zero modifiers
		for (text, mod) in reversed(modifier_list):
			if mod == 0.0:
				modifier_list.remove((text, mod))
		
		# save the list of modifiers
		profile['modifier_list'] = modifier_list[:]
		
		# calculate total modifier
		total_modifier = 0.0
		for (desc, mod) in modifier_list:
			total_modifier += mod
		
		# calculate final chance of success
		# can range from 0.5 to 99.5
		profile['final_chance'] = RestrictChanceNew(profile['base_chance'] + total_modifier)
		
		# calculate additional outcomes for Area Fire
		if profile['type'] == 'Area Fire':
			profile['full_effect'] = RestrictChanceNew((profile['base_chance'] + 
				total_modifier) * FP_FULL_EFFECT)
			profile['critical_effect'] = RestrictChanceNew((profile['base_chance'] + 
				total_modifier) * FP_CRIT_EFFECT)
		
		return profile
	
	
	# takes an attack profile and generates a profile for an armour penetration attempt
	# uses a slightly different system from to-hit
	def CalcAP(self, profile, air_attack=False, arty_attack=False):
		
		profile['type'] = 'ap'
		modifier_list = []
		
		# create local pointers for convenience
		attacker = profile['attacker']
		weapon = profile['weapon']
		target = profile['target']
		
		# flag for top armour hit (side armour value plus a modifier)
		top_armour = False
		if profile['ballistic_attack'] and profile['result'] == 'CRITICAL HIT':
			top_armour = True
		
		# check for good MOL/DC placement
		if weapon.stats['name'] == 'Demolition Charge':
			if libtcod.random_get_int(0, 1, 6) == 1:
				top_armour = True
		elif weapon.stats['name'] == 'Molotovs':
			if libtcod.random_get_int(0, 1, 4) == 1:
				top_armour = True
		
		# get location hit on target
		location = profile['location']
		# hull hit or target does not have rotatable turret
		if location == 'Hull' or target.turret_facing is None:
			turret_facing = False
		else:
			turret_facing = True
		
		# FUTURE: air attacks can come from different directions
		if air_attack:
			facing = 'Side'
		
		# contact close combat weapons use side armour
		elif weapon.stats['name'] in ['Demolition Charge', 'Flame Thrower', 'Molotovs']:
			facing = 'Side'
		
		# all others depend on facing toward attacker
		else:
			facing = GetFacing(attacker, target, turret_facing=turret_facing)
		
		# set rear facing flag if applicable
		rear_facing = False
		if facing == 'Rear':
			rear_facing = True
			facing = 'Side'
		
		hit_location = (location + '_' + facing).lower()
		
		# generate a text description of location hit
		if top_armour:
			profile['location_desc'] = 'Top'
		else:
			if location == 'Turret' and target.turret_facing is None:
				location = 'Upper Hull'
			profile['location_desc'] = location + ' '
			if rear_facing:
				profile['location_desc'] += 'Rear'
			else:
				profile['location_desc'] += facing
		
		# check for armour rating in hit location
		armour = target.GetStat('armour')
		unarmoured_location = True
		if armour is not None:
			if top_armour and target.GetStat('open_topped') is not None:
				unarmoured_location = True
			elif target.GetStat('open_rear_turret') is not None and hit_location == 'turret_rear':
				unarmoured_location = True
			else:
				if armour[hit_location] != '-':
					unarmoured_location = False
		
		# look up base AP score required
		if weapon.GetStat('type') in MG_WEAPONS:
			calibre = weapon.GetStat('calibre')
			if calibre is None:
				base_score = 4
			elif calibre == '15':
				base_score = 5
			else:
				base_score = 4
			
		elif weapon.GetStat('name') == 'AT Rifle':
			if attacker.nation in ['Soviet Union', 'Finland', 'Japan']:
				base_score = 6
			else:
				base_score = 5
		
		elif weapon.GetStat('type') == 'Close Combat':
			
			name = weapon.GetStat('name')
			
			# SMGs have no chance to penetrate armour
			if name == 'Submachine Guns':
				profile['base_chance'] = 0
				profile['modifier_list'] = []
				profile['final_score'] = 0
				profile['final_chance'] = 0.0
				return profile
			
			# HEAT close combat weapons
			if name in AT_CC_WEAPONS:
				
				if unarmoured_location:
					base_score = 11
				else:
					if name == 'Bazooka':
						if campaign.today < '1944.01.01':
							base_score = 13
						else:
							base_score = 16
					elif weapon.stats['name'] == 'PIAT':
						base_score = 15
					elif weapon.stats['name'] == 'Panzerfaust Klein':
						base_score = 22
					elif weapon.stats['name'] == 'Panzerschreck':
						base_score = 26
					elif weapon.stats['name'] == 'Panzerfaust':
						base_score = 31
			
			# HE / Flame close combat weapons
			else:
				if name == 'Grenades':
					if unarmoured_location:
						base_score = 4
					else:
						base_score = 2
				if name == 'Demolition Charge':
					if unarmoured_location:
						base_score = 12
					else:
						base_score = 16
				elif name == 'Flame Thrower':
					if unarmoured_location:
						base_score = 11
					else:
						base_score = 8
				elif name == 'Molotovs':
					if unarmoured_location:
						base_score = 5
					else:
						base_score = 6

		else:
			calibre = weapon.GetStat('calibre')
			
			# AP hit
			if profile['ammo_type'] == 'AP':
				
				# unarmoured location
				if unarmoured_location:
					calibre = int(calibre)
					if calibre <= 28:
						base_score = 7
					elif calibre <= 57:
						base_score = 8
					elif calibre <= 77:
						base_score = 9
					elif calibre <= 95:
						base_score = 10
					else:
						base_score = 11
				
				# armoured location
				else:
				
					if weapon.GetStat('long_range') is not None:
						calibre += weapon.GetStat('long_range')
					
					if weapon.GetStat('name') == 'AT Rifle':
						base_score = 5
					elif calibre in ['15']:
						base_score = 5
					elif calibre in ['20L']:
						base_score = 6
					elif calibre in ['20LL', '25LL', '37S']:
						base_score = 7
					elif calibre in ['37', '47S', '57S', '70S']:
						base_score = 8
					elif calibre in ['37L', '57', '65S', '76S']:
						base_score = 9
					elif calibre in ['40L', '45L', '47', '75S']:
						base_score = 10
					elif calibre in ['37LL', '45LL', '47L', '50']:
						base_score = 11
					elif calibre in ['76', '84S']:
						base_score = 12
					elif calibre in ['50L', '120S']:
						base_score = 13
					elif calibre in ['75', '105']:
						base_score = 14
					elif calibre in ['57L', '57LL']:
						base_score = 15
					elif calibre in ['75L', '76L', '85L', '150S', '152S']:
						base_score = 17
					elif calibre in ['77L', '200L']:
						base_score = 19
					elif calibre in ['88L']:
						base_score = 20
					elif calibre in ['90L', '105L', '150', '152', '155']:
						base_score = 21
					elif calibre in ['75LL', '76LL']:
						base_score = 23
					elif calibre in ['122L']:
						base_score = 25
					elif calibre in ['88LL', '100L', '120L']:
						base_score = 27
					elif calibre in ['150L', '155L']:
						base_score = 28
					elif calibre in ['140L']:
						base_score = 32
					elif calibre in ['128L', '170L']:
						base_score = 33
					else:
						print('ERROR: not able to find AP score for ' + calibre)
						base_score = 2
			
			# APCR/APDS ammo
			elif profile['ammo_type'] in ['APCR', 'APDS']:
				
				# unarmoured location
				if unarmoured_location:
					calibre = int(calibre)
					if calibre <= 28:
						base_score = 7
					elif calibre <= 57:
						base_score = 8
					elif calibre <= 77:
						base_score = 9
					elif calibre <= 95:
						base_score = 10
					else:
						base_score = 11
				
				# armoured location
				else:
					
					if weapon.GetStat('long_range') is not None:
						calibre += weapon.GetStat('long_range')
					
					if profile['ammo_type'] == 'APDS':
						if calibre == '57L':
							base_score = 18
						elif calibre == '76LL':
							base_score = 25
					else:
						if calibre == '37L':
							base_score = 10
						elif calibre in ['28LL', '45L']:
							base_score = 12
						elif calibre in ['45LL', '47L']:
							base_score = 13
						elif calibre in ['40LL', '50']:
							base_score = 14
						elif calibre == '76L':
							if attacker.nation == 'Soviet Union':
								base_score = 14
							elif attacker.nation == 'United States of America':
								base_score = 22
							else:
								base_score = 20
						elif calibre == '50L':
							base_score = 17
						elif calibre == '57LL':
							base_score = 18
						elif calibre == '85L':
							base_score = 19
						elif calibre in ['75L', '76L']:
							base_score = 20
						elif calibre == '88L':
							base_score = 23
						elif calibre == '90L':
							base_score = 27
						else:
							print('ERROR: not able to find AP score for ' + calibre + ' ' + profile['ammo_type'])
							base_score = 2
			
			# HEAT ammo
			elif profile['ammo_type'] == 'HEAT':
				
				# unarmoured location
				if unarmoured_location:
					base_score = 11
				
				# armoured location
				else:
					
					if calibre in ['57', '65', '94']:
						base_score = 11
					elif calibre == '70':
						base_score = 12
					elif calibre in ['75', '76']:
						base_score = 13
					elif calibre == '100':
						base_score = 14
					elif calibre in ['105', '114']:
						base_score = 15
					elif calibre == '95':
						base_score = 16
					elif calibre == '122':
						base_score = 17
					elif calibre == '150':
						base_score = 21
					elif calibre in ['37', '47']:
						base_score = 26
					else:
						print('ERROR: not able to find AP score for HEAT: ' + calibre)
						base_score = 2
			
			# HE hit
			elif profile['ammo_type'] == 'HE':
				
				calibre = int(calibre)
				
				if unarmoured_location:
					if calibre <= 20:
						base_score = 6
					elif calibre <= 30:
						base_score = 8
					elif calibre <= 40:
						base_score = 9
					elif calibre <= 50:
						base_score = 10
					elif calibre <= 70:
						base_score = 12
					elif calibre <= 80:
						base_score = 14
					elif calibre <= 100:
						base_score = 16
					elif calibre <= 120:
						base_score = 18
					else:
						base_score = 20
				
				# armoured location
				else:
					
					if calibre <= 20:
						base_score = 3
					elif calibre <= 30:
						base_score = 4
					elif calibre <= 40:
						base_score = 5
					elif calibre <= 50:
						base_score = 6
					elif calibre <= 70:
						base_score = 7
					elif calibre <= 80:
						base_score = 8
					elif calibre <= 100:
						base_score = 10
					elif calibre <= 120:
						base_score = 12
					else:
						base_score = 16
		
		profile['base_chance'] = base_score
		
		if not top_armour:
		
			# rear facing and critical hit modifiers
			if rear_facing:
				modifier_list.append(('Rear Facing', 1))
			if profile['result'] == 'CRITICAL HIT':
				modifier_list.append(('Critical Hit', base_score))
			
			# range/calibre modifier
			distance = GetHexDistance(attacker.hx, attacker.hy, target.hx, target.hy)
			if weapon.GetStat('name') == 'AT Rifle':
				if distance <= 1:
					modifier_list.append(('Close Range', 2))
				else:
					modifier_list.append(('Long Range', -2))
			
			elif profile['ammo_type'] == 'AP' and weapon.GetStat('calibre') is not None and not unarmoured_location:
				
				calibre = int(weapon.GetStat('calibre'))
				
				if calibre <= 25:
					if distance <= 1:
						modifier_list.append(('Close Range', 1))
					elif distance <= 3:
						modifier_list.append(('Long Range', -1))
					else:
						modifier_list.append(('V. Long Range', -2))
				else:
					if distance <= 1:
						modifier_list.append(('Close Range', 1))
					elif distance >= 4:
						modifier_list.append(('V. Long Range', -1))
			
			elif profile['ammo_type'] == 'APCR' and weapon.GetStat('calibre') is not None and not unarmoured_location:
				
				calibre = int(weapon.GetStat('calibre'))
				
				if calibre <= 57:
					if distance <= 1:
						modifier_list.append(('Close Range', 2))
					elif 3 <= distance <= 4:
						modifier_list.append(('Medium Range', -2))
					elif distance >= 5:
						modifier_list.append(('Long Range', -4))
				else:
					if distance <= 1:
						modifier_list.append(('Close Range', 2))
					elif 3 <= distance <= 4:
						modifier_list.append(('Medium Range', -1))
					elif distance >= 5:
						modifier_list.append(('Long Range', -3))
			
			elif profile['ammo_type'] == 'APDS' and not unarmoured_location:
			
				if distance <= 1:
					modifier_list.append(('Close Range', 1))
		
		# armoured location modifier; armour NA if flame attack
		if not unarmoured_location and weapon.GetStat('name') not in ['Flame Thrower', 'Molotovs']:
			
			if top_armour:
				target_armour = int(ceil(float(armour['hull_side']) * 0.5))
			else:
				target_armour = int(armour[hit_location])
			if target_armour > 0:
				modifier_list.append(('Armour', 0 - target_armour))
					
		# save the list of modifiers
		profile['modifier_list'] = modifier_list[:]
		
		# calculate total modifer
		total_modifier = 0
		for (desc, mod) in modifier_list:
			total_modifier += mod
		
		# calculate final chance of success
		# possible to be impossible or for penetration to be automatic
		final_score = base_score + total_modifier
		
		profile['final_score'] = final_score
		
		if final_score < 2:
			profile['final_chance'] = 0.0
		elif final_score >= 12:
			profile['final_chance'] = 100.0
		else:
			profile['final_chance'] = Get2D6Odds(final_score)
		
		return profile
	
	
	# generate an attack console to display an attack, AP profile, or HE resolution to the screen and prompt to proceed
	def DisplayAttack(self, profile):
		
		libtcod.console_clear(attack_con)
		
		# display the background outline
		libtcod.console_blit(session.attack_bkg, 0, 0, 0, 0, attack_con, 0, 0)
		
		# window title
		libtcod.console_set_default_background(attack_con, libtcod.darker_blue)
		libtcod.console_rect(attack_con, 1, 1, 25, 1, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(attack_con, libtcod.black)
		
		# set flags on whether attacker/target is spotted
		
		attacker_spotted = True
		if profile['attacker'].owning_player == 1 and not profile['attacker'].spotted:
			attacker_spotted = False
		target_spotted = True
		if profile['target'].owning_player == 1 and not profile['target'].spotted:
			target_spotted = False
		
		if profile['type'] == 'ap':
			text = 'Armour Penetration'
		elif profile['type'] == 'he':
			text = 'HE Hit Resolution'
		elif profile['type'] == 'Close Combat':
			text = 'Close Combat'
		else:
			text = 'Ranged Attack'
		libtcod.console_print_ex(attack_con, 13, 1, libtcod.BKGND_NONE, libtcod.CENTER, text)
		
		# attacker portrait if any
		if profile['type'] in ['Point Fire', 'Area Fire', 'Close Combat']:
			
			libtcod.console_set_default_background(attack_con, PORTRAIT_BG_COL)
			libtcod.console_rect(attack_con, 1, 2, 25, 8, False, libtcod.BKGND_SET)
		
			# FUTURE: store portraits for every active unit type in session object
			if attacker_spotted:
				portrait = profile['attacker'].GetStat('portrait')
				if portrait is not None:
					libtcod.console_blit(LoadXP(portrait), 0, 0, 0, 0, attack_con, 1, 2)
			else:
				libtcod.console_blit(LoadXP('unit_unknown.xp'), 0, 0, 0, 0, attack_con, 1, 2)
		
		# attack description
		if profile['type'] in ['ap', 'he']:
			text1 = profile['target'].GetName()
			if attacker_spotted:
				text2 = 'hit by ' + profile['weapon'].GetStat('name')
			else:
				text2 = 'hit'
			if profile['ammo_type'] is not None:
				text2 += ' (' + profile['ammo_type'] + ')'
			if profile['type'] == 'ap':
				text3 = 'in'
				text4 = profile['location_desc']
			else:
				text3 = ''
				text4 = ''
		else:
			text1 = profile['attacker'].GetName()
			if attacker_spotted:
				text2 = 'attacking with'
				text3 = profile['weapon'].GetStat('name')
				if profile['weapon'].ammo_type is not None:
					text3 += ' ' + profile['weapon'].ammo_type
			else:
				text2 = 'attacking'
			text4 = profile['target'].GetName()
			
		libtcod.console_print_ex(attack_con, 13, 10, libtcod.BKGND_NONE, libtcod.CENTER, text1)
		libtcod.console_print_ex(attack_con, 13, 11, libtcod.BKGND_NONE, libtcod.CENTER, text2)
		libtcod.console_print_ex(attack_con, 13, 12, libtcod.BKGND_NONE, libtcod.CENTER, text3)
		libtcod.console_print_ex(attack_con, 13, 13, libtcod.BKGND_NONE, libtcod.CENTER, text4)
		
		# display target portrait if any
		libtcod.console_set_default_background(attack_con, PORTRAIT_BG_COL)
		libtcod.console_rect(attack_con, 1, 14, 25, 8, False, libtcod.BKGND_SET)
		
		if target_spotted:
			portrait = profile['target'].GetStat('portrait')
			if portrait is not None:
				libtcod.console_blit(LoadXP(portrait), 0, 0, 0, 0, attack_con, 1, 14)
		else:
			libtcod.console_blit(LoadXP('unit_unknown.xp'), 0, 0, 0, 0, attack_con, 1, 14)
		
		# base chance
		text = 'Base '
		if profile['type'] == 'ap':
			text += 'Score to Penetrate:'
		elif profile['type'] == 'he':
			text += 'Score to Destroy:'
		elif profile['type'] == 'Area Fire':
			text += 'Chance of Effect:'
		else:
			text += 'Chance to Hit:'
		libtcod.console_print_ex(attack_con, 13, 23, libtcod.BKGND_NONE, libtcod.CENTER, text)
		text = str(profile['base_chance'])
		if profile['type'] not in ['ap', 'he']:
			text += '%'
		libtcod.console_print_ex(attack_con, 13, 24, libtcod.BKGND_NONE, libtcod.CENTER, text)
		
		# list of modifiers
		libtcod.console_set_default_background(attack_con, libtcod.darker_blue)
		libtcod.console_rect(attack_con, 1, 27, 25, 1, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(attack_con, libtcod.black)
		libtcod.console_print_ex(attack_con, 13, 27, libtcod.BKGND_NONE, libtcod.CENTER,
			'Modifiers')
		
		y = 29
		if len(profile['modifier_list']) == 0:
			libtcod.console_print_ex(attack_con, 13, y, libtcod.BKGND_NONE, libtcod.CENTER,
				'None')
		else:
			for (desc, mod) in profile['modifier_list']:
				
				# description: max displayable length is 17 chars
				# display up to two lines
				if len(desc) <= 17:
					libtcod.console_print(attack_con, 2, y, desc)
				else:
					lines = wrap(desc, 17, subsequent_indent = ' ')
					libtcod.console_print(attack_con, 2, y, lines[0])
					y += 1
					libtcod.console_print(attack_con, 2, y, lines[1])
				
				# amount
				if profile['type'] == 'ap':
					if mod < 0:
						col = libtcod.red
						text = ''
					else:
						col = libtcod.green
						text = '+'
				else:
					if mod > 0.0:
						col = libtcod.green
						text = '+'
					else:
						col = libtcod.red
						text = ''
				
				libtcod.console_set_default_foreground(attack_con, col)
				libtcod.console_print_ex(attack_con, 24, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, text + str(mod))
				libtcod.console_set_default_foreground(attack_con, libtcod.white)
				
				y += 1
				if y == 39: break
		
		# display final score required for AP/HE rolls
		if profile['type'] in ['ap', 'he']:
			libtcod.console_print_ex(attack_con, 13, 40, libtcod.BKGND_NONE, libtcod.CENTER,
				'Score required')
			libtcod.console_print_ex(attack_con, 13, 41, libtcod.BKGND_NONE, libtcod.CENTER,
				str(profile['final_score']))
		
		# display final chance
		libtcod.console_set_default_background(attack_con, libtcod.darker_blue)
		libtcod.console_rect(attack_con, 1, 43, 25, 1, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(attack_con, libtcod.black)
		libtcod.console_print_ex(attack_con, 14, 43, libtcod.BKGND_NONE, libtcod.CENTER,
			'Final Chance')
		
		# display chance graph
		if profile['type'] == 'Area Fire':
			# area fire has partial, full, and critical outcomes possible
			
			# no effect
			libtcod.console_set_default_background(attack_con, libtcod.red)
			libtcod.console_rect(attack_con, 1, 46, 25, 3, False, libtcod.BKGND_SET)
			
			# partial effect
			libtcod.console_set_default_background(attack_con, libtcod.darker_green)
			x = int(ceil(25.0 * profile['final_chance'] / 100.0))
			libtcod.console_rect(attack_con, 1, 46, x, 3, False, libtcod.BKGND_SET)
			
			if profile['final_chance'] > profile['full_effect']:
				libtcod.console_print_ex(attack_con, 24, 46, libtcod.BKGND_NONE,
					libtcod.RIGHT, 'PART')
				text = str(profile['final_chance']) + '%'
				libtcod.console_print_ex(attack_con, 24, 47, libtcod.BKGND_NONE,
					libtcod.RIGHT, text)
			
			# full effect
			libtcod.console_set_default_background(attack_con, libtcod.green)
			x = int(ceil(25.0 * profile['full_effect'] / 100.0))
			libtcod.console_rect(attack_con, 1, 46, x, 3, False, libtcod.BKGND_SET)
			
			if profile['full_effect'] > profile['critical_effect']:
				libtcod.console_print_ex(attack_con, 13, 46, libtcod.BKGND_NONE,
					libtcod.CENTER, 'FULL')
				text = str(profile['full_effect']) + '%'
				libtcod.console_print_ex(attack_con, 13, 47, libtcod.BKGND_NONE,
					libtcod.CENTER, text)
			
			# critical effect
			libtcod.console_set_default_background(attack_con, libtcod.blue)
			x = int(ceil(25.0 * profile['critical_effect'] / 100.0))
			libtcod.console_rect(attack_con, 1, 46, x, 3, False, libtcod.BKGND_SET)
			libtcod.console_print(attack_con, 2, 46, 'CRIT')
			text = str(profile['critical_effect']) + '%'
			libtcod.console_print(attack_con, 2, 47, text)
			
		else:
			
			# miss
			libtcod.console_set_default_background(attack_con, libtcod.red)
			libtcod.console_rect(attack_con, 1, 46, 25, 3, False, libtcod.BKGND_SET)
			
			# hit
			x = int(ceil(25.0 * profile['final_chance'] / 100.0))
			libtcod.console_set_default_background(attack_con, libtcod.green)
			libtcod.console_rect(attack_con, 1, 46, x, 3, False, libtcod.BKGND_SET)
			
			if profile['type'] not in ['ap', 'he']:
				# critical hit band
				libtcod.console_set_default_foreground(attack_con, libtcod.blue)
				for y in range(46, 49):
					libtcod.console_put_char(attack_con, 1, y, 221)
				
				# critical miss band
				libtcod.console_set_default_foreground(attack_con, libtcod.dark_grey)
				for y in range(46, 49):
					libtcod.console_put_char(attack_con, 25, y, 222)
		
			libtcod.console_set_default_foreground(attack_con, libtcod.white)
			libtcod.console_set_default_background(attack_con, libtcod.black)
			
			text = str(profile['final_chance']) + '%'
			
			# AP/HE checks may be automatic or impossible
			if profile['type'] in ['ap', 'he']:
				if profile['final_chance'] == 0.0:
					text = 'Impossible'
				elif profile['final_chance'] == 100.0:
					text = 'Automatic'
			libtcod.console_print_ex(attack_con, 13, 47, libtcod.BKGND_NONE,
				libtcod.CENTER, text)
		
		# display final effect modifier if any
		if profile['modifier'] != '':
			libtcod.console_print_ex(attack_con, 13, 54, libtcod.BKGND_NONE,
				libtcod.CENTER, profile['modifier'])
		
		# return now if RoF attack
		if profile['weapon'].maintained_rof: return
		
		# check for display of fate point or cancel prompt
		display_cancel = False
		display_fate_point = False
		profile['fate_point_allowed'] = False
		if profile['attacker'] == self.player_unit and profile['type'] not in ['ap', 'he']:
			display_cancel = True
		
		if not display_cancel:
			if profile['type'] not in ['ap', 'he'] and profile['target'] == self.player_unit and campaign_day.fate_points > 0 and profile['final_chance'] not in [0.0, 100.0]:
				display_fate_point = True
				profile['fate_point_allowed'] = True
		
		# display remaining fate points allowed to use
		if display_fate_point:
			libtcod.console_set_default_foreground(attack_con, libtcod.darker_purple)
			libtcod.console_print_ex(attack_con, 25, 14, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(campaign_day.fate_points))
		
		# display prompts
		libtcod.console_set_default_foreground(attack_con, ACTION_KEY_COL)
		if display_cancel:
			libtcod.console_print(attack_con, 6, 56, 'Esc')
		elif display_fate_point:
			libtcod.console_print(attack_con, 6, 56, 'F')
		libtcod.console_print(attack_con, 6, 57, 'Tab')
		
		libtcod.console_set_default_foreground(attack_con, libtcod.white)
		if display_cancel:
			libtcod.console_print(attack_con, 12, 56, 'Cancel')
		elif display_fate_point:
			libtcod.console_print(attack_con, 12, 56, 'Fate Point')
		libtcod.console_print(attack_con, 12, 57, 'Continue')
		
		
	
	# do a roll, animate the attack console, and display the results
	# returns an modified attack profile
	def DoAttackRoll(self, profile):
		
		# clear prompts from attack console
		libtcod.console_print(attack_con, 6, 56, '                  ')
		libtcod.console_print(attack_con, 6, 57, '                  ')
		
		result_text = ''
		
		# if AP roll, may not need to roll
		if profile['type'] == 'ap':
			if profile['final_chance'] == 0.0:
				result_text = 'NO PENETRATION'
			elif profile['final_chance'] == 100.0:
				result_text = 'PENETRATED'
		
		# if HE roll, may not need to roll
		elif profile['type'] == 'he':
			if profile['final_chance'] == 0.0:
				result_text = 'NO EFFECT'
			elif profile['final_chance'] == 100.0:
				result_text = 'DESTROYED'
		
		# only roll if outcome not yet determined
		if result_text == '':
		
			# don't animate percentage rolls if player is not involved
			if profile['attacker'] != scenario.player_unit and profile['target'] != scenario.player_unit:
				roll = GetPercentileRoll()
			else:
				for i in range(6):
					roll = GetPercentileRoll()
					
					# check for debug flag - force a hit or penetration
					if i == 5:
						if DEBUG:
							if profile['attacker'] == scenario.player_unit and session.debug['Player Always Hits']:
								while roll >= profile['final_chance']:
									roll = GetPercentileRoll()
							elif profile['target'] == scenario.player_unit and profile['type'] in ['ap', 'he'] and session.debug['Player Always Penetrated']:
								while roll >= profile['final_chance']:
									roll = GetPercentileRoll()
							elif profile['target'] == scenario.player_unit and profile['type'] not in ['ap', 'he'] and session.debug['AI Hates Player']:	
								while roll >= profile['final_chance']:
									roll = GetPercentileRoll()
					
					# clear any previous text
					libtcod.console_print_ex(attack_con, 13, 49, libtcod.BKGND_NONE,
						libtcod.CENTER, '           ')
					
					text = 'Roll: ' + str(roll)
					libtcod.console_print_ex(attack_con, 13, 49, libtcod.BKGND_NONE,
						libtcod.CENTER, text)
					
					scenario.UpdateScenarioDisplay()
					
					# don't animate if fast mode debug flag is set
					if DEBUG and session.debug['Fast Mode']:
						continue
					
					Wait(15)
			
			# record the final roll in the attack profile
			profile['roll'] = roll
				
			# determine location hit on target (not always used)
			location_roll = GetPercentileRoll()
			
			if profile['target'].GetStat('large_turret') is not None:
				location_roll += 25.0
			
			if location_roll <= 75.0:
				profile['location'] = 'Hull'
			else:
				profile['location'] = 'Turret'
			
			# some vehicles have no turret or superstructure
			if profile['location'] == 'Turret' and profile['ballistic_attack'] and 'no_turret' in profile['target'].stats:
				profile['location'] = 'Hull'
			
			# armour penetration roll
			if profile['type'] == 'ap':
				
				if roll >= CRITICAL_MISS:
					result_text = 'NO PENETRATION'
				elif roll <= CRITICAL_HIT:
					result_text = 'PENETRATED'
				elif roll <= profile['final_chance']:
					result_text = 'PENETRATED'
				else:
					result_text = 'NO PENETRATION'
			
			# HE destruction roll
			elif profile['type'] == 'he':
				if roll <= profile['final_chance']:
					result_text = 'DESTROYED'
				else:
					
					# should be an unarmoured vehicle, but just make sure
					if profile['target'].GetStat('armour') is not None:
						result_text = 'NO EFFECT'
					else:
						
						# player target
						if profile['target'].ai is None:
							if not profile['target'].immobilized:
								result_text = 'IMMOBILIZED'
							else:
								result_text = 'NO EFFECT'
						
						# AI target
						else:
							
							if GetPercentileRoll() <= 50.0:
								if not profile['target'].immobilized:
									result_text = 'IMMOBILIZED'
								else:
									result_text = 'NO EFFECT'
							else:
								if profile['target'].ai.state != 'Stunned':
									result_text = 'STUNNED'	
								else:
									result_text = 'NO EFFECT'							
			
			# area fire attack
			elif profile['type'] == 'Area Fire':
				if roll <= profile['critical_effect']:
					
					# no critical effect possible if original odds were <= 3%
					if profile['final_chance'] <= 3.0:
						result_text = 'FULL EFFECT'
						profile['effective_fp'] = profile['base_fp']
					else:
						result_text = 'CRITICAL EFFECT'
						profile['effective_fp'] = profile['base_fp'] * 2
				elif roll <= profile['full_effect']:
					result_text = 'FULL EFFECT'
					profile['effective_fp'] = profile['base_fp']
				elif roll <= profile['final_chance']:
					result_text = 'PARTIAL EFFECT'
					profile['effective_fp'] = int(floor(profile['base_fp'] / 2))
				else:
					result_text = 'NO EFFECT'
				
				# might be converted into an AP MG hit
				if result_text in ['FULL EFFECT', 'CRITICAL EFFECT']:
					if profile['weapon'].GetStat('type') in MG_WEAPONS and profile['target'].GetStat('armour') is not None:
						distance = GetHexDistance(profile['attacker'].hx,
							profile['attacker'].hy, profile['target'].hx,
							profile['target'].hy)
						if distance <= MG_AP_RANGE:
							if result_text == 'FULL EFFECT':
								result_text = 'HIT'
							else:
								result_text = 'CRITICAL HIT'
	
			# point fire or close combat attack
			else:
				
				if roll >= CRITICAL_MISS:
					result_text = 'MISS'
				
				elif roll <= profile['critical_hit']:
					
					# make sure that original roll was a success
					if roll > profile['final_chance']:
						result_text = 'MISS'
					else:
						# no critical hit possible if original odds were <= 3%
						if profile['final_chance'] <= 3.0:
							result_text = 'HIT'
						# no critical hit for DC, FT, MOL
						elif profile['weapon'].GetStat('name') in ['Demolition Charge', 'Flame Thrower', 'Molotovs']:
							result_text = 'HIT'
						else:
							result_text = 'CRITICAL HIT'
				
				elif roll <= profile['final_chance']:
					result_text = 'HIT'
				
				else:
					result_text = 'MISS'
			
			# point fire hit or AP MG hit
			if profile['type'] != 'Close Combat' and result_text in ['HIT', 'CRITICAL HIT']:
				
				# some vehicles have no turret
				if profile['location'] == 'Turret' and 'no_turret' in profile['target'].stats:
					result_text = 'MISS'
				
				# may be saved by HD status
				elif len(profile['target'].hull_down) > 0 and profile['location'] == 'Hull' and not profile['ballistic_attack']:
					direction = GetDirectionToward(profile['target'].hx,
						profile['target'].hy, profile['attacker'].hx,
						profile['attacker'].hy)
					if direction in profile['target'].hull_down:
						
						if profile['target'].hull_down[0] == direction:
							chance = 95.0
						else:
							chance = 80.0
						if GetPercentileRoll() <= chance:
							result_text = 'MISS - HULL DOWN'
			
			# smoke doesn't have critical hits, and HD is N/A
			if profile['ammo_type'] == 'Smoke':
				if result_text in ['CRITICAL HIT', 'MISS - HULL DOWN']:
					result_text = 'HIT'
					
		
		profile['result'] = result_text
		
		# if player is not involved, we can return here
		if profile['attacker'] != scenario.player_unit and profile['target'] != scenario.player_unit:
			return profile
		
		# play sound effect for HD save
		if profile['result'] == 'MISS - HULL DOWN':
			PlaySoundFor(None, 'hull_down_save')
		
		# display result on screen
		libtcod.console_print_ex(attack_con, 13, 51, libtcod.BKGND_NONE,
			libtcod.CENTER, result_text)
		
		# display effective FP if it was successful area fire attack
		if profile['type'] == 'Area Fire' and result_text != 'NO EFFECT':
			libtcod.console_print_ex(attack_con, 13, 52, libtcod.BKGND_NONE,
				libtcod.CENTER, str(profile['effective_fp']) + ' FP')
		
		# check for RoF for gun / MG attacks
		if profile['type'] not in ['ap', 'he'] and profile['weapon'].GetStat('type') in (['Gun'] + MG_WEAPONS):
			
			# FUTURE: possibly allow AI units to maintain RoF?
			if profile['attacker'] == scenario.player_unit:
				
				roll = GetPercentileRoll()
				
				if roll <= profile['weapon'].GetRoFChance():
					profile['weapon'].maintained_rof = True
				else:
					profile['weapon'].maintained_rof = False
				
				if profile['weapon'].maintained_rof:
					libtcod.console_print_ex(attack_con, 13, 53, libtcod.BKGND_NONE,
						libtcod.CENTER, 'Maintained Rate of Fire')
					libtcod.console_set_default_foreground(attack_con, ACTION_KEY_COL)
					libtcod.console_print(attack_con, 6, 56, EnKey('f').upper())
					libtcod.console_set_default_foreground(attack_con, libtcod.white)
					libtcod.console_print(attack_con, 12, 56, 'Fire Again')
		
		# display prompt
		libtcod.console_set_default_foreground(attack_con, ACTION_KEY_COL)
		libtcod.console_print(attack_con, 6, 57, 'Tab')
		libtcod.console_set_default_foreground(attack_con, libtcod.white)
		libtcod.console_print(attack_con, 12, 57, 'Continue')
		
		return profile
	
	
	# selecte a different weapon (or a different ammo type for the current weapon) on the player unit
	def SelectWeapon(self, forward):
		
		if self.selected_weapon is None:
			self.selected_weapon = scenario.player_unit.weapon_list[0]
			return
		
		# if weapon is not broken/jammed and is gun, see if can select a different ammo type instead
		if not self.selected_weapon.broken and not self.selected_weapon.jammed:
			if self.selected_weapon.SelectAmmoType(forward):
				return
		
		if forward:
			m = 1
		else:
			m = -1
		
		i = scenario.player_unit.weapon_list.index(self.selected_weapon) + m
		
		if i < 0:
			self.selected_weapon = scenario.player_unit.weapon_list[-1]
		elif i > len(scenario.player_unit.weapon_list) - 1:
			self.selected_weapon = scenario.player_unit.weapon_list[0]
		else:
			self.selected_weapon = scenario.player_unit.weapon_list[i]
		
		# select proper ammo type if gun
		if self.selected_weapon.GetStat('ammo_type_list') is None: return
		
		if forward:
			i = 0
		else:
			i = -1
		self.selected_weapon.ammo_type = self.selected_weapon.stats['ammo_type_list'][i]
	
	
	# (re)build a sorted list of possible player targets
	def BuildTargetList(self):
		
		self.target_list = []
		
		for unit in self.units:
			# allied unit
			if unit.owning_player == 0: continue
			# beyond active part of map
			if GetHexDistance(0, 0, unit.hx, unit.hy) > 3: continue
			self.target_list.append(unit)
		
		# clear target if old target no longer on list
		for weapon in self.player_unit.weapon_list:
			if weapon.selected_target is None: continue
			if weapon.selected_target not in self.target_list:
				weapon.selected_target = None
		
		# TODO: order targets by direction from player
		
		# try to select a new target automatically
		for weapon in self.player_unit.weapon_list:
			if weapon.selected_target is not None: continue
			for target in self.target_list:
				if (target.hx, target.hy) not in weapon.covered_hexes: continue
				weapon.selected_target = target
				break
	
	
	# cycle selected target for player weapon
	# FUTURE: combine into general "next in list, previous in list, wrap around" function
	def CycleTarget(self, forward):
		
		# no weapon selected
		if self.selected_weapon is None: return
		
		# no targets to select from
		if len(self.target_list) == 0: return
		
		# no target selected yet
		if self.selected_weapon.selected_target is None:
			self.selected_weapon.selected_target = self.target_list[0]
			return
		
		if forward:
			m = 1
		else:
			m = -1
		
		i = self.target_list.index(self.selected_weapon.selected_target)
		i += m
		
		if i < 0:
			self.selected_weapon.selected_target = self.target_list[-1]
		elif i > len(self.target_list) - 1:
			self.selected_weapon.selected_target = self.target_list[0]
		else:
			self.selected_weapon.selected_target = self.target_list[i]
		
		self.selected_weapon.selected_target.MoveToTopOfStack()
		self.UpdateUnitCon()
		self.UpdateUnitInfoCon()
	
	
	# roll to see if air and/or arty support requests were granted, and trigger attacks if so
	def ResolveSupportRequests(self):
		
		# check for air attack first - not in friendly zone
		if campaign_day.air_support_request and not self.cd_map_hex.controlled_by == 0:
			roll = GetPercentileRoll()
			
			# campaign skill modifier
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Combined Operations'):
				roll -= 5.0
			
			granted = False
			if DEBUG:
				if session.debug['Support Requests Always Granted']:
					granted = True
			if roll <= campaign_day.air_support_level:
				granted = True
			
			# check for weather restrictions
			if campaign_day.weather['Cloud Cover'] == 'Overcast':
				ShowMessage('Cannot offer air attack support - cloud cover too heavy.')
				granted = False
			elif campaign_day.weather['Fog'] > 0:
				ShowMessage('Cannot offer air attack support - fog is too thick.')
				granted = False
			
			if granted:
				campaign_day.air_support_level -= float(libtcod.random_get_int(0, 1, 3)) * 5.0
				if campaign_day.air_support_level < 0.0:
					campaign_day.air_support_level = 0.0
				self.DoAirAttack()
			else:
				ShowMessage('Air support request received but we are unable to respond!')
		
		# check for artillery attack, also not in friendly zone
		if campaign_day.arty_support_request and not self.cd_map_hex.controlled_by == 0:
			roll = GetPercentileRoll()
			
			# campaign skill modifiers
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Centralized Fire'):
				roll -= 10.0
			elif campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Combined Operations'):
				roll -= 5.0
			
			granted = False
			if DEBUG:
				if session.debug['Support Requests Always Granted']:
					granted = True
			if roll <= campaign_day.arty_support_level:
				granted = True
			
			if granted:
				campaign_day.arty_support_level -= float(libtcod.random_get_int(0, 1, 3)) * 5.0
				if campaign_day.arty_support_level < 0.0:
					campaign_day.arty_support_level = 0.0
				self.DoArtilleryAttack()
			else:
				ShowMessage('Artillery support request received but we are unable to respond!')
		
		# if player didn't request unit support and is being attacked in own zone, may have some support units for free
		free_unit_support = False
		if not campaign_day.unit_support_request and self.cd_map_hex.controlled_by == 0 and 'unit_support_level' in campaign.current_week:
			roll = GetPercentileRoll()
			if roll <= 33.3:
				campaign_day.unit_support_request = True
				campaign_day.unit_support_type = choice(list(campaign.stats['player_unit_support']))
				free_unit_support = True
		
		# check for unit support request
		if campaign_day.unit_support_request:
			roll = GetPercentileRoll()
			
			# campaign skill modifier
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Combined Operations'):
				roll -= 5.0
			
			granted = False
			if DEBUG:
				if session.debug['Support Requests Always Granted']:
					granted = True
			if roll <= campaign_day.unit_support_level:
				granted = True
			
			if granted:
				if not free_unit_support:
					campaign_day.unit_support_level -= float(libtcod.random_get_int(0, 1, 3)) * 5.0
					if campaign_day.unit_support_level < 0.0:
						campaign_day.unit_support_level = 0.0
				
				# spawn units - determine number of units
				roll = libtcod.random_get_int(0, 1, 10)
				if roll <= 6:
					num_units = 1
				elif roll <= 9:
					num_units = 2
				else:
					num_units = 3
				
				# possible spawn locations
				ring_list = []
				for r in range(1, 4):
					hex_ring = []
					for (hx, hy) in GetHexRing(0, 0, r):
						if len(self.hex_dict[(hx,hy)].unit_stack) > 0:
							if self.hex_dict[(hx,hy)].unit_stack[0].owning_player == 1:
								continue
						hex_ring.append((hx, hy))
					ring_list.append(hex_ring)
				
				text = ''
				
				for tries in range(300):
					
					unit_id = choice(campaign.stats['player_unit_support'][campaign_day.unit_support_type])
					
					# check historical availability of unit
					if not campaign.DoRarityCheck(unit_id):
						continue
					
					# determine spawn location
					found_location = False
					for hex_ring in ring_list:
						shuffle(hex_ring)
						for (hx, hy) in hex_ring:
							# less likely to spawn in front of player if not ambushed
							if not self.ambush:
								if GetDirectionToward(hx, hy, 0, 0) in [2, 3, 4]:
									if GetPercentileRoll() <= 95.0: continue
							found_location = True
							break
						if found_location: break
					
					unit = Unit(unit_id)
					unit.owning_player = 0
					unit.nation = campaign.player_unit.nation
					unit.ai = AI(unit)
					unit.ai.Reset()
					unit.GenerateNewPersonnel()
					unit.SpawnAt(hx, hy)
					if unit.GetStat('category') == 'Gun':
						unit.deployed = True
					unit.facing = 0
					if 'turret' in unit.stats:
						unit.turret_facing = 0
					self.GenerateUnitLoS(unit)
					
					# set up additional transported unit if any
					if 'friendly_transported_units' in campaign.stats:
						transport_dict = campaign.stats['friendly_transported_units']
						if unit_id in transport_dict:
							transport_list = list(transport_dict[unit_id].items())
							shuffle(transport_list)
							for k, value in transport_list:
								if libtcod.random_get_int(0, 1, 100) <= value:
									unit.transport = k
									break
					
					if text != '':
						text += ', '
					text += unit_id
					
					num_units -= 1
					if num_units == 0: break
				
				self.UpdateUnitCon()
				self.UpdateScenarioDisplay()
				
				if free_unit_support:
					msg_text = campaign_day.unit_support_type + ' support unit'
					if num_units == 1:
						msg_text += ' was'
					else:
						msg_text += 's were'
					msg_text += ' nearby and join the battle: ' + text
				else:
				
					msg_text = campaign_day.unit_support_type + ' support unit'
					if num_units == 1:
						msg_text += ' has'
					else:
						msg_text += 's have'
					msg_text += ' arrived: ' + text
				ShowMessage(msg_text)
				
			else:
				if not free_unit_support:
					ShowMessage('Unit support request received but we are unable to respond!')
			
		
		# reset flags
		campaign_day.air_support_request = False
		campaign_day.arty_support_request = False
		campaign_day.unit_support_request = False
		campaign_day.unit_support_type = None
		
		# update GUI console
		self.UpdateGuiCon()
	
	
	# resolve an air support attack
	# if player_target is true, the player squad is the target of an enemy attack
	def DoAirAttack(self, player_target=False):
		
		# determine air unit(s) to spawn
		if player_target:
			plane_id = None
			nation_list = list(campaign.stats['enemy_air_support'])
			shuffle(nation_list)
			for nation in nation_list:
				if nation in campaign.current_week['enemy_nations']:
					plane_id = choice(campaign.stats['enemy_air_support'][nation])
					break
			
			# could not find an appropriate air unit to spawn
			if plane_id is None:
				return
		else:
			plane_id = choice(campaign.stats['player_air_support'])
		
		if player_target:
			friendly_player = 1
			ShowMessage('Enemy air forces launch an attack!')
		else:
			friendly_player = 0
			ShowMessage('Air support attack inbound! Trying to spot targets.')
		
		# calculate base spotting chance and add weather modifiers
		chance = 55.0
			
		if campaign_day.weather['Cloud Cover'] == 'Scattered':
			chance -= 10.0
		elif campaign_day.weather['Cloud Cover'] == 'Heavy':
			chance -= 20.0
		if campaign_day.weather['Precipitation'] in ['Rain', 'Snow']:
			chance -= 15.0
		elif campaign_day.weather['Precipitation'] in ['Heavy Rain', 'Blizzard']:
			chance -= 25.0
		
		if campaign_day.weather['Fog'] > 0:
			chance -= 10.0 * float(campaign_day.weather['Fog'])
		
		# check each hex with 1+ target units present
		target_hex_list = []
		for map_hex in self.map_hexes:
			if len(map_hex.unit_stack) == 0: continue
			if map_hex.unit_stack[0].owning_player == friendly_player: continue
			
			# roll to spot each enemy unit in hex
			for unit in map_hex.unit_stack:
			
				modifier = 0.0
					
				if unit.smoke > 0:
					modifier -= 5.0
				elif unit.dust > 0:
					modifier += 5.0
				
				size_class = unit.GetStat('size_class')
				if size_class is not None:
					if size_class == 'Small':
						modifier -= 7.0
					elif size_class == 'Very Small':
						modifier -= 18.0
					elif size_class == 'Large':
						modifier += 7.0
					elif size_class == 'Very Large':
						modifier += 18.0
				
				if unit.moving:
					modifier += 10.0
				
				modifier += unit.GetTEM()
				
				roll = GetPercentileRoll()
				
				# not spotted
				if roll > RestrictChance(chance + round(modifier * 0.25, 2)):
					continue
				
				# spotted, add this hex to targets and don't check any other units present in this hex
				target_hex_list.append(map_hex)
				break
		
		if len(target_hex_list) == 0:
			ShowMessage('No targets spotted, ending attack.')
			return
		
		
		# roll for number of planes
		roll = libtcod.random_get_int(0, 1, 10)
		
		if roll <= 5:
			num_planes = 1
		elif roll <= 8:
			num_planes = 2
		else:
			num_planes = 3
		
		# create plane units
		plane_unit_list = []
		for i in range(num_planes):
			plane_unit_list.append(Unit(plane_id))
		
		# display message
		text = str(num_planes) + ' ' + plane_id + ' arrive'
		if num_planes == 1: text += 's'
		text += ' for an attack.'
		ShowMessage(text, portrait=plane_unit_list[0].GetStat('portrait'))
		
		# determine calibre for bomb attack
		for weapon in plane_unit_list[0].weapon_list:
			if weapon.stats['name'] == 'Bombs':
				bomb_calibre = int(weapon.stats['calibre'])
				break
		
		# determine effective fp
		for (calibre, effective_fp) in HE_FP_EFFECT:
			if calibre <= bomb_calibre:
				break
		effective_fp = int(effective_fp / 2)
		
		# do one attack animation per target hex
		for map_hex in target_hex_list:
			
			libtcod.console_flush()
			
			# seems to help with spinning wheel of death
			FlushKeyboardEvents()
		
			# determine attack direction and starting position
			(x, y) = self.PlotHex(map_hex.hx, map_hex.hy)
			(x2, y2) = (x, y)
			
			# animation from below
			if y2 <= 30:
				y1 = y2 + 15
				if y1 > 51: y1 = 51
				y2 += 1
				direction = -1
			
			# animation from above
			else:
				y1 = y2 - 15
				if y1 < 9: y1 = 9
				y2 -= 1
				direction = 1
			
			# create air attack animation
			self.animation['air_attack'] = GeneratePlaneCon(direction)
			self.animation['air_attack_line'] = GetLine(x, y1, x, y2)
			
			PlaySoundFor(None, 'plane_incoming')
			
			# let animation run
			while self.animation['air_attack'] is not None:
				libtcod.console_flush()
				CheckForAnimationUpdate()
			
			PlaySoundFor(None, 'stuka_divebomb')
			
			# create bomb animation
			self.animation['bomb_effect'] = (x, y2+direction)
			self.animation['bomb_effect_lifetime'] = 10
			
			# let animation run
			while self.animation['bomb_effect'] is not None:
				libtcod.console_flush()
				CheckForAnimationUpdate()
		
		# do one attack per plane per target hex
		results = False
		for map_hex in target_hex_list:
		
			for unit in plane_unit_list:
			
				# find a target unit in the target hex
				if len(map_hex.unit_stack) == 0:
					continue
				target = choice(map_hex.unit_stack)
			
				# calculate basic to-effect score required
				if not target.spotted:
					chance = PF_BASE_CHANCE[0][1]
				else:
					if target.GetStat('category') == 'Vehicle':
						chance = PF_BASE_CHANCE[0][0]
					else:
						chance = PF_BASE_CHANCE[0][1]
			
				# target size modifier
				size_class = target.GetStat('size_class')
				if size_class is not None:
					if size_class != 'Normal':
						chance += PF_SIZE_MOD[size_class]
				
				# smoke or dust modifier
				if target.smoke >= 2:
					chance -= 30.0
				elif target.dust >= 2:
					chance -= 20.0
				elif target.smoke == 1:
					chance -= 15.0
				elif target.dust == 1:
					chance -= 10.0
				
				chance = RestrictChance(int(chance / 2))
				roll = GetPercentileRoll()
				if roll > chance:
					# chance that a miss will still reveal a concealed unit
					if GetPercentileRoll() <= MISSED_FP_REVEAL_CHANCE:
						target.hit_by_fp = True
					continue
				
				# hit
				results = True
				
				# set plane location on map
				unit.hx = target.hx
				unit.hy = target.hy - direction
				
				# roll for direct hit / near miss
				direct_hit = False
				roll = GetPercentileRoll()
				if roll <= DIRECT_HIT_CHANCE:
					direct_hit = True
				
				# infantry, cavalry, or gun target
				if target.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']:
					
					# direct hit: destroyed
					if direct_hit:
						if target == scenario.player_unit:
							text = 'You were'
						else:
							text = target.GetName() + ' was'
						text += ' destroyed by a direct hit from the air attack!'
						ShowMessage(text, scenario_highlight=(target.hx, target.hy))
						target.DestroyMe()
						continue
					
					target.fp_to_resolve += effective_fp
					target.hit_by_fp = True
					
					if target == scenario.player_unit:
						text = 'You were'
					else:
						text = target.GetName() + ' was'
					text += ' hit by the air attack.'
					ShowMessage(text, scenario_highlight=(target.hx, target.hy))
				
					target.ResolveFP()
				
				# vehicle hit
				elif target.GetStat('category') == 'Vehicle':
					
					# direct hit - unarmoured and open topped vehicles destroyed
					if direct_hit:
						if target.GetStat('armour') is None or target.GetStat('open_topped') is not None:
							
							if target == scenario.player_unit:
								text = 'You were'
							else:
								text = target.GetName() + ' was'
							text += ' destroyed by a direct hit from the air attack.'
							ShowMessage(text, scenario_highlight=(target.hx, target.hy))
							target.DestroyMe()
							continue
					
					# create an attack profile for the AP calculation
					profile = {}
					profile['attacker'] = plane_unit_list[0]
					profile['weapon'] = weapon
					profile['ammo_type'] = 'HE'
					profile['target'] = target
					profile['result'] = ''
					profile['ballistic_attack'] = False
					
					# determine location hit
					if GetPercentileRoll() <= 50.0:
						profile['location'] = 'Hull'
					else:
						profile['location'] = 'Turret'
					
					profile = self.CalcAP(profile, air_attack=True)
					
					# apply direct hit modifier
					if direct_hit:
						profile['final_chance'] = round(profile['final_chance'] * 2.0, 1)
						if profile['final_chance'] > 100.0:
							profile['final_chance'] = 100.0
					
					# do AP roll
					roll = GetPercentileRoll()
					
					# no penetration
					if roll > profile['final_chance']:
						if target == scenario.player_unit:
							text = 'You were'
						else:
							text = target.GetName() + ' was'
						text += ' unaffected by the air attack'
						ShowMessage(text, scenario_highlight=(target.hx, target.hy))
						continue
					
					# penetrated
					if target == scenario.player_unit:
						text = 'Your tank was'
					else:
						text = target.GetName() + ' was'
					text += ' knocked out by the air attack.'
					ShowMessage(text, scenario_highlight=(target.hx, target.hy))
					target.DestroyMe()
				
		if not results:
			ShowMessage('Air attack had no effect.')
		
		# clean up
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		libtcod.console_flush()
	
	
	# resolve an artillery attack
	# if player_target is true, the player squad is the target of an enemy attack
	def DoArtilleryAttack(self, player_target=False):
		
		# determine artillery unit(s) to spawn
		if player_target:
			unit_id = None
			nation_list = list(campaign.stats['enemy_arty_support'])
			shuffle(nation_list)
			for nation in nation_list:
				if nation in campaign.current_week['enemy_nations']:
					unit_id = choice(campaign.stats['enemy_arty_support'][nation])
					break
			
			# could not find an appropriate artillery unit to spawn
			if unit_id is None:
				return
		else:
			unit_id = choice(campaign.stats['player_arty_support'])
		
		if player_target:
			friendly_player = 1
			ShowMessage('Enemy artillery forces fire a bombardment!')
		else:
			friendly_player = 0
			ShowMessage('Artillery support attack inbound! Trying to spot targets.')
		
		# do an attack on every hex with an enemy unit in it
		target_hex_list = []
		for map_hex in self.map_hexes:
			if len(map_hex.unit_stack) == 0: continue
			if map_hex.unit_stack[0].owning_player == friendly_player: continue
			target_hex_list.append(map_hex)
		
		# no possible targets
		if len(target_hex_list) == 0:
			ShowMessage('No targets spotted, ending attack.')
			return
		
		# spawn gun unit and determine effective FP
		gun_unit = Unit(unit_id)
		gun_calibre = int(gun_unit.weapon_list[0].GetStat('calibre'))
		
		ShowMessage('Target spotted, ' + unit_id + ' guns firing for effect.', 
			portrait=gun_unit.GetStat('portrait'))
		
		# display bombardment animation
		for map_hex in target_hex_list:
			libtcod.console_flush()
			# seems to help with spinning wheel of death
			FlushKeyboardEvents()
			(x, y) = self.PlotHex(map_hex.hx, map_hex.hy)
			for i in range(3):
				libtcod.console_flush()
				xm = 3 - libtcod.random_get_int(0, 0, 6)
				ym = 3 - libtcod.random_get_int(0, 0, 6)
				PlaySoundFor(None, 'he_explosion')
				# create bomb animation
				self.animation['bomb_effect'] = (x+xm, y+ym)
				self.animation['bomb_effect_lifetime'] = 2
				
				# let animation run
				while self.animation['bomb_effect'] is not None:
					libtcod.console_flush()
					CheckForAnimationUpdate()
		
		# determine effective fp for gun
		for (calibre, effective_fp) in HE_FP_EFFECT:
			if calibre <= gun_calibre:
				break
		effective_fp = int(effective_fp / 2)
		
		# determine campaign skill modifier if any
		skill_mod = 0
		soft_target_mod = 0
		if not player_target:
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Centralized Fire'):
				skill_mod = -15.0
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Combined Bombardment'):
				soft_target_mod = -25.0
		
		# roll for possible hit against each unit in each target hex
		results = False
		for map_hex in target_hex_list:
		
			for target in map_hex.unit_stack:
				
				if target.owning_player == 0: continue
				if not target.alive: continue
				
				# calculate base effect chance
				if target.GetStat('category') == 'Vehicle':
					chance = VEH_FP_BASE_CHANCE
				else:
					chance = INF_FP_BASE_CHANCE
				for i in range(2, effective_fp + 1):
					chance += FP_CHANCE_STEP * (FP_CHANCE_STEP_MOD ** (i-1)) 
				
				# FUTURE: apply any further modifiers here
				
				chance = RestrictChance(round(chance * 0.5, 1))
				roll = GetPercentileRoll()
				
				# apply campaign skill modifiers if any
				roll += skill_mod
				if target.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']:
					roll += soft_target_mod
				
				# no effect
				if roll > chance:
					# chance that a miss will still reveal a concealed unit
					if GetPercentileRoll() <= MISSED_FP_REVEAL_CHANCE:
						target.hit_by_fp = True
					continue
				
				results = True
				
				# set artillery location on map
				gun_unit.hx = target.hx
				gun_unit.hy = target.hy+4
				
				# roll for direct hit / near miss
				direct_hit = False
				if GetPercentileRoll() <= DIRECT_HIT_CHANCE:
					direct_hit = True
				
				# infantry, cavalry, or gun target hit
				if target.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']:
					
					# direct hit: destroyed
					if direct_hit:
						if target == scenario.player_unit:
							text = 'You were'
						else:
							text = target.GetName() + ' was'
						text += ' destroyed by a direct hit from the artillery attack.'
						ShowMessage(text, scenario_highlight=(target.hx, target.hy))
						target.DestroyMe()
						continue
					
					target.fp_to_resolve += effective_fp
					target.hit_by_fp = True
					
					if target == scenario.player_unit:
						text = 'You were'
					else:
						text = target.GetName() + ' was'
					text += ' hit by artillery attack.'
					ShowMessage(text, scenario_highlight=(target.hx, target.hy))
					
					target.ResolveFP()
				
				# vehicle hit
				elif target.GetStat('category') == 'Vehicle':
					
					# direct hit - unarmoured and open topped vehicles destroyed
					if direct_hit:
						if target.GetStat('armour') is None or target.GetStat('open_topped') is not None:
							if target == scenario.player_unit:
								text = 'You were'
							else:
								text = target.GetName() + ' was'
							text += ' destroyed by a direct hit from the artillery attack.'
							ShowMessage(text, scenario_highlight=(target.hx, target.hy))
							target.DestroyMe()
							continue
					
					# create an attack profile for the AP calculation
					profile = {}
					profile['attacker'] = gun_unit
					profile['weapon'] = gun_unit.weapon_list[0]
					profile['ammo_type'] = 'HE'
					profile['target'] = target
					profile['result'] = ''
					profile['ballistic_attack'] = False
					
					# determine location hit
					if GetPercentileRoll() <= 50.0:
						profile['location'] = 'Hull'
					else:
						profile['location'] = 'Turret'
					
					profile = self.CalcAP(profile, arty_attack=True)
					
					# apply direct hit modifier
					if direct_hit:
						profile['final_chance'] = round(profile['final_chance'] * 2.0, 1)
						if profile['final_chance'] > 100.0:
							profile['final_chance'] = 100.0
					
					# do AP roll
					roll = GetPercentileRoll()
					
					# no penetration
					if roll > profile['final_chance']:
						if target == scenario.player_unit:
							text = 'You were hit by the artillery attack but your tank was not damaged.'
						else:
							text = target.GetName() + ' was hit by the artillery attack but remains unharmed.'
						ShowMessage(text, scenario_highlight=(target.hx, target.hy))
						
						# calculate and apply effective FP
						(profile, effective_fp) = gun_unit.CalcHEEffectiveFP(profile)
						
						target.fp_to_resolve += effective_fp
						target.hit_by_fp = True
						continue
					
					# penetrated
					if target == scenario.player_unit:
						text = 'You were'
					else:
						text = target.GetName() + ' was'
					text += ' destroyed by artillery attack'
					ShowMessage(text, scenario_highlight=(target.hx, target.hy))
					target.DestroyMe()
		
		if not results:
			ShowMessage('Artillery attack had no effect.')
	
	
	# execute a player move forward/backward, repositioning units on the hex map as needed
	def MovePlayer(self, forward, reposition=False):
		
		target_terrain = None
		
		if reposition:
			if not self.player_unit.overrun:
				target_terrain = self.ShowRepositionMenu()
				if target_terrain == ('Cancel', 0.0): return
		
		else:
		
			# check for double bog check 
			if 'Double Bog Check' in SCENARIO_TERRAIN_EFFECTS[self.player_unit.terrain]:
				# FUTURE: check for squad units too
				for unit in self.units:
					if unit != self.player_unit: continue
					unit.DoBogCheck(forward)
			
			# notify player and update consoles if player bogged
			if self.player_unit.bogged:
				ShowMessage('Your tank has becomed bogged.')
				self.UpdatePlayerInfoCon()
				self.UpdateUnitCon()
				self.advance_phase = True
				return
		
		# do sound effect
		PlaySoundFor(self.player_unit, 'movement')
		
		# set statuses
		self.player_unit.moving = True
		self.player_unit.ClearAcquiredTargets()
		for unit in scenario.player_unit.squad:
			unit.moving = True
			if unit.facing is not None:
				unit.facing = 0
			unit.ClearAcquiredTargets()
		
		# landmine check
		if self.player_unit.DoLandmineCheck():
			self.UpdatePlayerInfoCon()
			self.advance_phase = True
			return
		
		if not reposition:
		
			# do move success roll
			if forward:
				chance = scenario.player_unit.forward_move_chance
			else:
				chance = scenario.player_unit.reverse_move_chance
			roll = GetPercentileRoll()
			
			# check for crew action modifier
			for position in ['Commander', 'Commander/Gunner']:
				crewman = self.player_unit.GetPersonnelByPosition(position)
				if crewman is None: continue
				if crewman.current_cmd == 'Direct Movement':
					
					# check for skill modifiers
					if forward and 'Forward!' in crewman.skills:
						mod = crewman.GetSkillMod(7.0)
						if not crewman.ce: mod = mod * 0.5
						chance += mod
					elif 'Driver Direction' in crewman.skills:
						mod = crewman.GetSkillMod(5.0)
						if not crewman.ce: mod = mod * 0.5
						chance += mod
					else:
						mod = crewman.GetSkillMod(3.0)
						if not crewman.ce: mod = mod * 0.5
						chance += mod
				break
			
			# check for driver skill
			crewman = self.player_unit.GetPersonnelByPosition('Driver')
			if crewman is not None:
				if 'Quick Shifter' in crewman.skills:
					mod = crewman.GetSkillMod(5.0)
					if not crewman.ce: mod = mod * 0.5
					chance += mod
			
			# check for debug flag
			if DEBUG:
				if session.debug['Player Always Moves']:
					roll = 1.0
		
			# move was not successful
			if roll > chance:
				
				# clear any alternative bonus and apply bonus for future moves
				if forward:
					self.player_unit.reverse_move_bonus = 0.0
					self.player_unit.forward_move_bonus += BASE_MOVE_BONUS
				else:
					self.player_unit.forward_move_bonus = 0.0
					self.player_unit.reverse_move_bonus += BASE_MOVE_BONUS
				
				# show pop-up message to player
				ShowMessage('You move but not far enough to enter a new map hex')
				
				# set new terrain and LoS for player and squad
				for unit in self.units:
					if unit != self.player_unit and unit not in self.player_unit.squad: continue
					unit.GenerateTerrain()
					self.GenerateUnitLoS(unit)
					unit.CheckForHD()
				
				self.advance_phase = True
				return
		
			# successful move may be cancelled by breakdown
			if self.player_unit.BreakdownCheck():
				ShowMessage('Your vehicle stalls for a moment, making you unable to move further this turn.')
				self.advance_phase = True
				return
		
			# move was successful, clear all bonuses
			self.player_unit.forward_move_bonus = 0.0
			self.player_unit.reverse_move_bonus = 0.0
			
			# calculate new hex positions for each unit in play
			if forward:
				direction = 3
			else:
				direction = 0
			
			# run through list of units and move them
			# player movement will never move an enemy unit into ring 4 nor off board
			for unit in self.units:
				
				if unit == self.player_unit: continue
				if unit in self.player_unit.squad: continue
				
				(new_hx, new_hy) = GetAdjacentHex(unit.hx, unit.hy, direction)
				
				# skip if unit would end up in ring 4 or off board
				if GetHexDistance(0, 0, new_hx, new_hy) > 3:
					continue
				
				# skip if would end up in a hex with an enemy unit
				if len(self.hex_dict[(new_hx,new_hy)].unit_stack) > 0:
					if self.hex_dict[(new_hx,new_hy)].unit_stack[0].owning_player != unit.owning_player:
						continue
				
				# special case: jump over player hex 0,0
				jump = False
				if new_hx == 0 and new_hy == 0:
					(new_hx, new_hy) = GetAdjacentHex(0, 0, direction)
					jump = True
				
				# set destination hex
				unit.dest_hex = (new_hx, new_hy)
				
				# calculate animation locations
				(x1, y1) = self.PlotHex(unit.hx, unit.hy)
				(x2, y2) = self.PlotHex(new_hx, new_hy)
				unit.animation_cells = GetLine(x1, y1, x2, y2)
				# special case: unit is jumping over 0,0
				if jump:
					for i in range(12, 0, -2):
						unit.animation_cells.pop(i)
			
			# animate movement
			for i in range(6):
				for unit in self.units:
					if unit == self.player_unit: continue
					if unit in self.player_unit.squad: continue
					if len(unit.animation_cells) > 0:
						unit.animation_cells.pop(0)
				self.UpdateUnitCon()
				self.UpdateScenarioDisplay()
				Wait(15)
			
			# set new hex location for each moving unit and move into new hex stack
			for unit in self.units:
				if unit.dest_hex is None: continue
				self.hex_dict[(unit.hx, unit.hy)].unit_stack.remove(unit)
				(unit.hx, unit.hy) = unit.dest_hex
				self.hex_dict[(unit.hx, unit.hy)].unit_stack.append(unit)
				# clear destination hex and animation data
				unit.dest_hex = None
				unit.animation_cells = []
		
		# if Drive Into Terrain command is active, allow player to choose target terrain type after a move
		if not reposition and not self.player_unit.overrun:
			crewman = self.player_unit.GetPersonnelByPosition('Driver')
			if crewman is not None:
				if crewman.current_cmd == 'Drive Into Terrain':
					target_terrain = self.ShowRepositionMenu(allow_cancel=False)
		
		# set new terrain, generate new LoS for player and squad
		for unit in self.units:
			if unit != self.player_unit and unit not in self.player_unit.squad: continue
			unit.GenerateTerrain(target_terrain=target_terrain)
			self.GenerateUnitLoS(unit)
			unit.CheckForHD()
			unit.SetSmokeDustLevel()
		
		# show message if player repositioned and is not going on an overrun attack
		if reposition and not self.player_unit.overrun:
			text = 'You move to a new location within the same hex.'
			if self.player_unit.terrain is not None:
				text += ' New terrain: ' + self.player_unit.terrain
			ShowMessage(text, longer_pause=True)
		
		self.UpdatePlayerInfoCon()
		self.UpdateUnitInfoCon()
		self.UpdateUnitCon()
		
		# recalculate move chances and do bog check in new location
		# FUTURE: check AI units too
		for unit in self.units:
			if unit != self.player_unit: continue
			unit.CalculateMoveChances()
			unit.DoBogCheck(forward, reposition=reposition)
		
		# notify player and update consoles if player bogged
		if self.player_unit.bogged:
			ShowMessage('Your tank has becomed bogged.')
			self.UpdatePlayerInfoCon()
			self.UpdateUnitCon()
			self.advance_phase = True
			return
		
		# check for extra move
		if self.player_unit.ExtraMoveCheck():
			ShowMessage('You have moved swiftly enough to take another move action.')
			return
		self.advance_phase = True
	
	
	# display a list of possible target terrain types for Reposition action
	def ShowRepositionMenu(self, allow_cancel=True):
		
		def DrawMenu():
			libtcod.console_clear(menu_con)
			libtcod.console_set_default_foreground(menu_con, libtcod.grey)
			DrawFrame(menu_con, 0, 0, 43, 36)
			libtcod.console_set_default_foreground(menu_con, TITLE_COL)
			libtcod.console_print_ex(menu_con, 22, 3, libtcod.BKGND_NONE, libtcod.CENTER,
				'Target Terrain Type')
			
			y = 7
			n = 0
			for (terrain, odds) in terrain_list:
				libtcod.console_set_default_foreground(menu_con, libtcod.white)
				libtcod.console_print(menu_con, 10, y, terrain)
				libtcod.console_print_ex(menu_con, 33, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(odds) + '%')
				if n == selected_choice:
					libtcod.console_set_default_background(menu_con, HIGHLIGHT_MENU_COL)
					libtcod.console_rect(menu_con, 10, y, 24, 1, False, libtcod.BKGND_SET)
					libtcod.console_set_default_background(menu_con, libtcod.black)
				y += 1
				n += 1
			
			# player commands
			libtcod.console_set_default_foreground(menu_con, ACTION_KEY_COL)
			libtcod.console_print(menu_con, 9, 31, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(menu_con, 9, 32, 'Tab')
			if allow_cancel:
				libtcod.console_print(menu_con, 9, 33, 'Esc')
			
			libtcod.console_set_default_foreground(menu_con, libtcod.light_grey)
			libtcod.console_print(menu_con, 14, 31, 'Select Target Terrain')
			libtcod.console_print(menu_con, 14, 32, 'Proceed')
			if allow_cancel:
				libtcod.console_print(menu_con, 14, 33, 'Cancel Reposition')
			
			libtcod.console_blit(menu_con, 0, 0, 0, 0, con, 24, 12)
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# build list of possible terrain types and odds of getting each
		terrain_list = []
		odds_dict = CD_TERRAIN_TYPES[scenario.cd_map_hex.terrain_type]['scenario_terrain_odds']
		for k, v in odds_dict.items():
			
			# don't allow repositioning into impossible terrain
			if campaign.stats['region'] == 'North Africa':
				if k in ['Woods', 'Wooden Buildings', 'Fields', 'Marsh']: continue
			
			odds = v * 2.0
			
			# apply skill modifiers here
			if self.player_unit.CrewmanHasSkill('Driver', 'Eye for Terrain'):
				odds += 15.0
			if self.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Prepared Positions'):
				odds += 25.0
			
			if odds > 97.0:
				odds = 97.0
			
			terrain_list.append((k, odds))
		
		# create a local copy of the current screen to re-draw when we're done
		temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
		libtcod.console_blit(con, 0, 0, 0, 0, temp_con, 0, 0)
		
		# darken background 
		libtcod.console_blit(darken_con, 0, 0, 0, 0, con, 0, 0, 0.0, 0.5)
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# create display console
		menu_con = NewConsole(43, 36, libtcod.black, libtcod.white)
		
		selected_choice = 0
		result = None
		
		# draw for first time
		DrawMenu()
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			keypress = GetInputEvent()
			if not keypress: continue
			
			# cancel reposition
			if key.vk == libtcod.KEY_ESCAPE and allow_cancel:
				result = ('Cancel', 0.0)
				exit_menu = True
				continue
			
			# proceeed
			elif key.vk in [libtcod.KEY_TAB, libtcod.KEY_ENTER, libtcod.KEY_KPENTER]:
				result = terrain_list[selected_choice]
				exit_menu = True
				continue
			
			key_char = DeKey(chr(key.c).lower())
			
			# change selected terrain
			if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if selected_choice == 0:
						selected_choice = len(terrain_list) - 1
					else:
						selected_choice -= 1
				else:
					if selected_choice == len(terrain_list) - 1:
						selected_choice = 0
					else:
						selected_choice += 1
				
				DrawMenu()
				continue
		
		libtcod.console_blit(temp_con, 0, 0, 0, 0, con, 0, 0)
		return result
	
	
	# pivot the hull of the player unit
	def PivotPlayer(self, clockwise):
		
		if clockwise:
			r = 5
			f = -1
		else:
			r = 1
			f = 1
		
		# calculate new hex positions of units
		for unit in self.units:
			if unit == self.player_unit: continue
			if unit in self.player_unit.squad: continue
			unit.dest_hex = RotateHex(unit.hx, unit.hy, r)
		
		PlaySoundFor(self.player_unit, 'player_pivot')
		
		# FUTURE: animate movement?
		# set new hex location for each unit and move into new hex stack
		for map_hex in self.map_hexes:
			if map_hex.hx == 0 and map_hex.hy == 0: continue
			if len(map_hex.unit_stack) == 0: continue
			for unit in reversed(map_hex.unit_stack):
				
				# already moved
				if unit.dest_hex is None: continue
				
				# set new location then clear their destination
				self.hex_dict[(unit.hx, unit.hy)].unit_stack.remove(unit)
				(unit.hx, unit.hy) = unit.dest_hex
				self.hex_dict[(unit.hx, unit.hy)].unit_stack.insert(0, unit)
				unit.dest_hex = None
			
				# pivot unit facings if any
				if unit.facing is not None:
					unit.facing = ConstrainDir(unit.facing + f)
				if unit.turret_facing is not None:
					unit.turret_facing = ConstrainDir(unit.turret_facing + f)
				
				# pivot unit HD if any
				if len(unit.hull_down) > 0:
					for i in range(3):
						unit.hull_down[i] = ConstrainDir(unit.hull_down[i] + f)
		
		self.UpdatePlayerInfoCon()
		self.UpdateGuiCon()
		self.UpdateUnitCon()
		
		# pivot player HD if any
		if len(self.player_unit.hull_down) > 0:
			for i in range(3):
				self.player_unit.hull_down[i] = ConstrainDir(self.player_unit.hull_down[i] + f)
		
		# record player pivot
		self.player_pivot = ConstrainDir(self.player_pivot + f)
	
	
	# rotate turret of player unit
	def RotatePlayerTurret(self, clockwise):
		
		turret = self.player_unit.GetStat('turret')
		# no turret on player vehicle
		if turret is None: return
		# turret is fixed
		if turret == 'FIXED': return
		
		# weapon on turret has already fired
		for weapon in self.player_unit.weapon_list:
			mount = weapon.GetStat('mount')
			if mount is None: continue
			if mount == 'Turret' and weapon.fired:
				return
		
		if clockwise:
			f = 1
		else:
			f = -1
		scenario.player_unit.turret_facing = ConstrainDir(scenario.player_unit.turret_facing + f)
		
		PlaySoundFor(self.player_unit, 'player_turret')
		
		# update covered hexes for any turret-mounted weapons
		for weapon in scenario.player_unit.weapon_list:
			if weapon.GetStat('mount') != 'Turret': continue
			weapon.UpdateCoveredHexes()
		
		self.UpdateUnitCon()
		self.UpdateGuiCon()
	
	
	# attempt to conceal oneself from or reveal oneself to an enemy unit
	def ConcealOrRevealPlayer(self):
		
		# update the console display and GUI overlay
		def UpdateScreen():
			
			libtcod.console_clear(attack_con)
			libtcod.console_blit(session.attack_bkg, 0, 0, 0, 0, attack_con, 0, 0)
			
			# menu title
			libtcod.console_set_default_background(attack_con, libtcod.darker_blue)
			libtcod.console_rect(attack_con, 1, 1, 25, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(attack_con, libtcod.black)
			libtcod.console_set_default_foreground(attack_con, libtcod.yellow)
			libtcod.console_print(attack_con, 4, 2, 'Conceal/Reveal Self')
			
			libtcod.console_set_default_foreground(attack_con, libtcod.white)
			libtcod.console_hline(attack_con, 1, 4, 25)
			
			# display info on target
			target_spotted = True
			if selected_unit.owning_player == 1 and not selected_unit.spotted:
				target_spotted = False
			
			if target_spotted:
				DisplayUnitInfo(attack_con, 1, 5, selected_unit.unit_id, selected_unit)
			else:
				libtcod.console_print(attack_con, 1, 5, 'Unspotted Enemy Unit')
				libtcod.console_set_default_background(attack_con, PORTRAIT_BG_COL)
				libtcod.console_rect(attack_con, 1, 7, 25, 8, False, libtcod.BKGND_SET)
				libtcod.console_blit(LoadXP('unit_unknown.xp'), 0, 0, 0, 0, attack_con, 1, 7)
			
			libtcod.console_set_default_foreground(attack_con, libtcod.white)
			libtcod.console_hline(attack_con, 1, 24, 25)
			
			libtcod.console_print(attack_con, 2, 26, 'Current Status:')
			if self.player_unit.los_table[selected_unit]:
				text = 'Line of Sight'
				action_type = 'Conceal'
			else:
				text = 'Line of Sight Blocked'
				action_type = 'Reveal'
			libtcod.console_print(attack_con, 4, 27, text)
			
			# display action and odds of success
			libtcod.console_print(attack_con, 2, 29, 'Chance to ' + action_type + ' self:')
			libtcod.console_print(attack_con, 4, 30, str(chance) + '%')
			
			# display bog chance
			libtcod.console_print(attack_con, 2, 32, 'Chance of bogging down:')
			libtcod.console_print(attack_con, 4, 33, str(self.player_unit.bog_chance) + '%')
			
			# command keys
			libtcod.console_set_default_foreground(attack_con, ACTION_KEY_COL)
			libtcod.console_print(attack_con, 5, 55, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_print(attack_con, 5, 56, 'Esc')
			libtcod.console_print(attack_con, 5, 57, 'Tab')
			
			libtcod.console_set_default_foreground(attack_con, libtcod.white)
			libtcod.console_print(attack_con, 11, 55, 'Select Target')
			libtcod.console_print(attack_con, 11, 56, 'Cancel')
			libtcod.console_print(attack_con, 11, 57, 'Proceed')
		
		# calculate the chance of revealing self to / concealing self from selected unit
		def CalculateChance():
			base_chance = self.DoLoSRoll(self.player_unit, selected_unit, chance_only=True)
			
			# modify based on conceal or reveal action
			if self.player_unit.los_table[selected_unit]:
				base_chance = round(base_chance * 0.50, 1)
			else:
				base_chance = round(base_chance * 0.75, 1)
			return base_chance
			
		
		unit = self.player_unit
		
		# build a list of enemy units
		unit_list = []
		for unit in self.units:
			if not unit.alive: continue
			if unit.owning_player == 0: continue
			unit_list.append(unit)
		
		# shouldn't happen, but just check
		if len(unit_list) == 0: return
		
		# TODO: order units by direction from player
		
		# select first unit by default
		selected_unit = unit_list[0]
		
		# calculate initial success chance
		chance = CalculateChance()
		
		# activate the attack console, which we use for target info display and menu commands
		self.attack_con_active = True
		
		# update screen for first time
		UpdateScreen()
		self.UpdateGuiCon(los_highlight=(self.player_unit, selected_unit))  
		self.UpdateScenarioDisplay()
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			keypress = GetInputEvent()
			if not keypress: continue
			
			# cancel action
			if key.vk in [libtcod.KEY_BACKSPACE, libtcod.KEY_ESCAPE]:
				exit_menu = True
				continue
			
			# proceed
			elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				
				# set statuses
				self.player_unit.moving = True
				self.player_unit.ClearAcquiredTargets()
				for unit in scenario.player_unit.squad:
					unit.moving = True
					unit.ClearAcquiredTargets()
				
				# landmine check
				if self.player_unit.DoLandmineCheck():
					self.UpdatePlayerInfoCon()
					self.advance_phase = True
					exit_menu = True
					continue
				
				# do the roll
				roll = GetPercentileRoll()
				
				# check for crew action modifier
				for position in ['Commander', 'Commander/Gunner']:
					crewman = self.player_unit.GetPersonnelByPosition(position)
					if crewman is None: continue
					if crewman.current_cmd == 'Direct Movement':
						if 'Driver Direction' in crewman.skills:
							mod = crewman.GetSkillMod(5.0)
							if not crewman.ce: mod = mod * 0.5
							chance += mod
						else:
							mod = crewman.GetSkillMod(3.0)
							if not crewman.ce: mod = mod * 0.5
							chance += mod
					break
				
				# do sound effect
				PlaySoundFor(self.player_unit, 'movement')
				
				# not successful
				if roll > chance:
					
					if self.player_unit.los_table[selected_unit]:
						ShowMessage('You were not able to move into a position where you are concealed from the target.')
					else:
						ShowMessage('You were not able to move into a position where you are revealed to the target.')
				
				# roll was successful
				else:
					if self.player_unit.los_table[selected_unit]:
						ShowMessage('You were able to move into a position where you are concealed from the target.')
						self.player_unit.los_table[selected_unit] = False
						selected_unit.los_table[self.player_unit] = False
					else:
						ShowMessage('You were able to move into a position where you are revealed to the target.')
						self.player_unit.los_table[selected_unit] = True
						selected_unit.los_table[self.player_unit] = True
				
					# check for HD for player and squad
					for unit in self.units:
						if unit != self.player_unit and unit not in self.player_unit.squad: continue
						unit.CheckForHD()
				
				# check for bog
				if self.player_unit.DoBogCheck(True):
					ShowMessage('Your tank has becomed bogged.')
					self.UpdatePlayerInfoCon()
					self.UpdateUnitCon()
				
				self.advance_phase = True
				exit_menu = True
				continue
			
			key_char = DeKey(chr(key.c).lower())
			
			# change selected target
			if key_char in ['a', 'd']:
				i = unit_list.index(selected_unit)
				if key_char == 'a':
					if i == 0:
						i = len(unit_list) - 1
					else:
						i -= 1
				else:
					if i == len(unit_list) - 1:
						i = 0
					else:
						i += 1
				selected_unit = unit_list[i]
				chance = CalculateChance()
				UpdateScreen()
				self.UpdateGuiCon(los_highlight=(self.player_unit, selected_unit))
				self.UpdateScenarioDisplay()
				continue
		
		# turn off attack console and clear the LoS display on the GUI console
		self.attack_con_active = False
		self.UpdateGuiCon()
		self.UpdateScenarioDisplay()
		
	
	# display a pop-up window with info on a particular unit
	def ShowUnitInfoWindow(self, unit):
		
		# create a local copy of the current screen to re-draw when we're done
		temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
		libtcod.console_blit(0, 0, 0, 0, 0, temp_con, 0, 0)
	
		# darken screen background
		libtcod.console_blit(darken_con, 0, 0, 0, 0, con, 0, 0, 0.0, 0.7)
		
		# create window and draw frame
		window_con = libtcod.console_new(27, 44)
		libtcod.console_set_default_background(window_con, libtcod.black)
		libtcod.console_set_default_foreground(window_con, libtcod.white)
		DrawFrame(window_con, 0, 0, 27, 44)
		
		# draw unit info, description, and command instructions
		DisplayUnitInfo(window_con, 1, 1, unit.unit_id, unit)
		
		text = ''
		for t in unit.GetStat('description'):
			text += t
		lines = wrap(text, 25)
		y = 21
		libtcod.console_set_default_foreground(window_con, libtcod.light_grey)
		for line in lines[:20]:
			libtcod.console_print(window_con, 1, y, line)
			y+=1
		
		libtcod.console_set_default_foreground(window_con, ACTION_KEY_COL)
		libtcod.console_print(window_con, 7, 42, 'ESC')
		libtcod.console_set_default_foreground(window_con, libtcod.lighter_grey)
		libtcod.console_print(window_con, 12, 42, 'Return')
		
		# blit window to screen
		libtcod.console_blit(window_con, 0, 0, 0, 0, con, WINDOW_XM-13, 7)
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		# wait for player to exit view
		exit = False
		while not exit:
			libtcod.console_flush()
			
			# get keyboard and/or mouse event
			if not GetInputEvent(): continue
			
			if key.vk == libtcod.KEY_ESCAPE:
				exit = True
		
		# re-draw original view
		libtcod.console_blit(temp_con, 0, 0, 0, 0, 0, 0, 0)
		del temp_con
	
	
	# advance to next phase/turn and do automatic events
	def AdvanceToNextPhase(self):
		
		# do end of phase actions for player
		
		# end of player turn, switching to enemy turn
		if self.phase == PHASE_ALLIED_ACTION:
			
			# resolve fp on enemy units first
			for unit in reversed(self.units):
				if not unit.alive: continue
				if unit.owning_player == self.active_player: continue
				unit.ResolveFP()
				libtcod.console_flush()
			
			self.phase = PHASE_ENEMY_ACTION
			self.active_player = 1
		
		# end of enemy activation, player's turn
		elif self.phase == PHASE_ENEMY_ACTION:
			
			# resolve fp on player units first
			for unit in reversed(self.units):
				if not unit.alive: continue
				if unit.owning_player == self.active_player: continue
				unit.ResolveFP()
				libtcod.console_flush()
			
			# if units are on overrun, reset their overrun statuses, etc.
			for unit in self.units:
				if unit != self.player_unit and unit not in self.player_unit.squad: continue
				if not unit.overrun: continue
				unit.overrun = False
				unit.GenerateTerrain()
				unit.CheckForHD()
				unit.SetSmokeDustLevel()
			self.UpdateUnitCon()
			
			# advance clock
			campaign_day.AdvanceClock(0, TURN_LENGTH)
			
			# check for end of scenario
			self.CheckForEnd()
			if self.finished: return
			
			# check for random event
			self.CheckForRandomEvent()
			
			# player did not survive random event
			if not self.player_unit.alive:
				campaign_day.ended = True
				return
			
			# check for all enemies dead as result of random event
			self.CheckForEnd()
			if self.finished: return
			
			self.active_player = 0
			self.phase = PHASE_COMMAND
			
			# NEW: reset all friendly units including the player
			for unit in self.units:
				if not unit.alive: continue
				if unit.owning_player != 0: continue
				unit.ResetForNewTurn()
				unit.DoRecoveryRoll()
				unit.CalculateMoveChances()
			
			self.UpdatePlayerInfoCon()
			self.player_unit.MoveToTopOfStack()
		
		# still player turn, advance phase
		else:
			
			# end of movement phase
			if self.phase == PHASE_MOVEMENT:
				
				self.UpdatePlayerInfoCon()
				
				# player pivoted during movement phase
				if self.player_pivot != 0:
					self.player_unit.ClearAcquiredTargets(no_enemy=True)
					
					# do bog check for pivot
					if not self.player_unit.bogged:
						self.player_unit.DoBogCheck(False, pivot=True)
						if self.player_unit.bogged:
							ShowMessage('Your tank has becomed bogged.')
							self.UpdatePlayerInfoCon()
							self.UpdateUnitCon()
			
			# end of shooting phase
			elif self.phase == PHASE_SHOOTING:
				
				# clear GUI console and refresh screen
				libtcod.console_clear(gui_con)
				self.UpdateScenarioDisplay()
				libtcod.console_flush()
				
				# resolve AP and HE hits on enemy units
				for unit in reversed(self.units):
					if not unit.alive: continue
					if unit.owning_player == self.active_player: continue
					unit.ResolveAPHits()
					unit.ResolveHEHits()
				
				# do concealment check for player
				self.player_unit.DoConcealmentCheck()
			
			self.phase += 1
		
		# update the displays
		DisplayTimeInfo(scen_time_con)
		self.UpdateUnitCon()
		self.UpdateScenarioDisplay()
		libtcod.console_flush()
		
		# do automatic actions at start of phase
		
		# command phase: rebuild lists of commands
		if self.phase == PHASE_COMMAND:
			self.player_unit.BuildCmdLists()
		
		# spotting phase: do spotting then automatically advance
		elif self.phase == PHASE_SPOTTING:
			
			# first check for swap position, since this may change current command
			# for crewmen who swap
			for position in self.player_unit.positions_list:
				if position.crewman is None: continue
				if position.crewman.current_cmd == 'Swap Position':
					ShowSwapPositionMenu()
					self.UpdateCrewInfoCon()
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
					break
			
			self.player_unit.DoSpotChecks()
			self.advance_phase = True
		
		# crew action phase:
		elif self.phase == PHASE_CREW_ACTION:
			
			input_command = False
			
			for position in self.player_unit.positions_list:
				if position.crewman is None: continue
				
				# check for withdrawing
				if position.crewman.current_cmd == 'Withdraw':
					if ShowNotification('Attempt to withdraw from this battle?', confirm=True):
						
						PlaySoundFor(self.player_unit, 'movement')
						self.player_unit.moving = True
						self.player_unit.ClearAcquiredTargets()
						self.player_unit.GenerateTerrain()
						self.GenerateUnitLoS(self.player_unit)
						self.player_unit.CheckForHD()
						for unit in self.player_unit.squad:
							unit.moving = True
							unit.ClearAcquiredTargets()
							unit.GenerateTerrain()
							self.GenerateUnitLoS(unit)
							unit.CheckForHD()
						
						if self.AttemptWithdraw():
							ShowMessage('You successfully withdraw from the battle.')
							campaign_day.player_withdrew = True
							self.finished = True
							return
						else:
							ShowMessage('There are too many enemies nearby - you were unable to withdraw from the battle!')
				
				# check for abandoning tank
				elif position.crewman.current_cmd == 'Abandon Tank':
					if ShowNotification('Abandon your tank?', confirm=True):
						campaign.player_unit.alive = False
						ShowMessage('You abandon your tank.')
						campaign.AddJournal('Abandoned tank')
						self.player_unit.alive = False
						self.PlayerBailOut(abandoning_tank=True)
						campaign_day.ended = True
						campaign_day.abandoned_tank = True
						self.finished = True
						return
				
				# check for unbog attempt
				elif position.crewman.current_cmd == 'Attempt Unbog':
					if self.player_unit.DoUnbogCheck():
						ShowMessage('Your tank is no longer bogged down.')
						self.UpdatePlayerInfoCon()
					else:
						ShowMessage('Your tank remains bogged down.')
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
				
				# check for unjam attempt
				elif position.crewman.current_cmd == 'Unjam Weapon':
					for weapon in self.player_unit.weapon_list:
						if not weapon.jammed: continue
						if weapon.GetStat('mount') is not None:
							if weapon.GetStat('mount') != position.location: continue
						if weapon.AttemptUnjam(position.crewman):
							ShowMessage(weapon.GetStat('name') + ' is no longer jammed.')
					self.UpdateUnitCon()
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
				
				# check for smoke grenade
				elif position.crewman.current_cmd == 'Smoke Grenade':
					self.player_unit.smoke += 1
					if self.player_unit.smoke > 2:
						self.player_unit.smoke = 2
					campaign_day.smoke_grenades -= 1
					PlaySoundFor(None, 'smoke')
					ShowMessage('You throw a smoke grenade.')
					self.UpdatePlayerInfoCon()
					self.UpdateUnitCon()
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
				
				# check for smoke mortar
				elif position.crewman.current_cmd == 'Fire Smoke Mortar':
					self.player_unit.smoke = 2
					campaign_day.smoke_mortar_rounds -= 1
					PlaySoundFor(None, 'smoke')
					ShowMessage('The ' + position.name + ' fires off a smoke mortar round.')
					self.UpdatePlayerInfoCon()
					self.UpdateUnitCon()
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
				
				# check for action that needs input in this phase
				elif position.crewman.current_cmd in ['Manage Ready Rack']:
					input_command = True
			
			if not input_command:
				self.advance_phase = True
		
		# movement phase
		elif self.phase == PHASE_MOVEMENT:
			
			# reset player pivot
			self.player_pivot = 0
			
			# don't wait for player input phase if no crewman in position
			crewman = self.player_unit.GetPersonnelByPosition('Driver')
			if crewman is None:
				self.advance_phase = True
			else:
				# driver is on a Drive command
				if crewman.current_cmd in ['Drive', 'Drive Into Terrain']:
					scenario.player_unit.CalculateMoveChances()
				
				# driver is not on a Drive command
				else:
					# advance past phase without waiting for player input
					self.advance_phase = True
					
					# if Driver is on overrun command, set statuses and flags now
					if crewman.current_cmd == 'Overrun':
						ShowMessage('You move into position for an Overrun attack.')
						self.player_unit.overrun = True
						self.MovePlayer(False, reposition=True)
						target_list = [self.player_unit]
						for unit in self.player_unit.squad:
							unit.overrun = True
							self.GenerateUnitLoS(unit)
							target_list.append(unit)
						self.UpdateUnitCon()
						self.UpdateScenarioDisplay()
						libtcod.console_flush()
						
						# enemy gets a chance to do a defensive fire attack (cannot use ballistic weapons)
						for unit in self.units:
							
							if DEBUG:
								if session.debug['No AI Actions']:
									continue
							
							if not unit.alive: continue
							if unit.owning_player != 1: continue
							if unit.routed: continue
							if unit.hx != 0 or unit.hy != -1: continue
							
							# FUTURE: Use unit morale level?
							if GetPercentileRoll() <= 30.0: continue
							
							unit.ai.disposition = 'Combat'
							unit.ai.DoActivation(defensive_fire=True)
						
						# resolve any hits from defensive fire
						for unit in target_list:
							unit.ResolveFP()
							unit.ResolveAPHits()
							unit.ResolveHEHits()
		
		# shooting phase
		elif self.phase == PHASE_SHOOTING:
			
			# check that 1+ crew are on correct order
			skip_phase = True
			for position in self.player_unit.positions_list:
				if position.crewman is None: continue
				if position.crewman.current_cmd in ['Operate Gun', 'Operate MG']:
					skip_phase = False
					break
			
			if skip_phase:
				self.advance_phase = True
			else:
				self.BuildTargetList()
				
				# move current target of current weapon to top of unit stack if required
				if self.selected_weapon is not None:
					if self.selected_weapon.selected_target is not None:
						self.selected_weapon.selected_target.MoveToTopOfStack()
				
				self.UpdateUnitCon()
				self.UpdateGuiCon()
		
		# allied action phase
		elif self.phase == PHASE_ALLIED_ACTION:
			
			self.DoAISpotChecks(0)
			
			# player squad and allies act
			unit_list = []
			for unit in self.player_unit.squad:
				unit_list.append(unit)
			for unit in self.units:
				if not unit.alive: continue
				if unit.owning_player != 0: continue
				if unit.is_player: continue
				if unit in self.player_unit.squad: continue
				unit_list.append(unit)
			
			for unit in unit_list:
				unit.MoveToTopOfStack()
				self.UpdateUnitCon()
				self.UpdateScenarioDisplay()
				libtcod.console_flush()
				
				unit.ai.DoActivation()
				scenario.UpdateUnitCon()
				scenario.UpdateScenarioDisplay()
				libtcod.console_flush()
				
				# resolve any ap or he hits caused by this unit
				for unit2 in self.units:
					if not unit2.alive: continue
					if unit2.owning_player == self.active_player: continue
					unit2.ResolveAPHits()
					unit2.ResolveHEHits()
				
				# do concealment check for this unit
				unit.DoConcealmentCheck()
				libtcod.console_flush()
			
			self.advance_phase = True
		
		# enemy action
		elif self.phase == PHASE_ENEMY_ACTION:
			
			self.DoAISpotChecks(1)
			
			# build list of enemy units to activate
			unit_list = []
			for unit in self.units:
				if unit.owning_player != 1: continue
				if not unit.alive: continue
				unit_list.append(unit)
			
			for unit in unit_list:
				
				# if player has been destroyed, don't keep attacking
				if not self.player_unit.alive:
					break
				
				unit.MoveToTopOfStack()
				self.UpdateUnitCon()
				self.UpdateScenarioDisplay()
				libtcod.console_flush()
				unit.ResetForNewTurn()
				unit.DoRecoveryRoll()
				unit.CalculateMoveChances()
				unit.ai.DoActivation()
				scenario.UpdateUnitCon()
				scenario.UpdateScenarioDisplay()
				libtcod.console_flush()
				
				# resolve any hits caused by this unit
				for unit2 in self.units:
					if not unit2.alive: continue
					if unit2.owning_player == self.active_player: continue
					unit2.ResolveAPHits()
					unit2.ResolveHEHits()

				unit.DoConcealmentCheck()
				libtcod.console_flush()
			
			# clear scenario ambush flag if any
			self.ambush = False
			
			self.advance_phase = True
		
		self.UpdateCrewInfoCon()
		self.UpdateUnitInfoCon()
		self.UpdateCmdCon()
		self.UpdateContextCon()
		self.UpdateGuiCon()
		self.UpdateScenarioDisplay()
		libtcod.console_flush()
	
	
	# update contextual info console
	# 18x12
	def UpdateContextCon(self):
		libtcod.console_clear(context_con)
		
		# if we're advancing to next phase automatically, don't display anything here
		if self.advance_phase: return
		
		# Command Phase: display info about current crew command
		if self.phase == PHASE_COMMAND:
			position = scenario.player_unit.positions_list[self.selected_position]
			
			if position.crewman is None: return
			if not position.crewman.alive:
				libtcod.console_set_default_foreground(context_con, libtcod.light_grey)
				libtcod.console_print(context_con, 0, 0, 'Crewman is dead')
				return
			
			libtcod.console_set_default_foreground(context_con, SCEN_PHASE_COL[self.phase])
			libtcod.console_print(context_con, 0, 0, position.crewman.current_cmd)
			libtcod.console_set_default_foreground(context_con, libtcod.light_grey)
			lines = wrap(session.crew_commands[position.crewman.current_cmd]['desc'], 18)
			y = 2
			for line in lines:
				libtcod.console_print(context_con, 0, y, line)
				y += 1
			
			# display gun ammo if viewing Manage Ready Rack command
			if position.crewman.current_cmd == 'Manage Ready Rack':
				y += 1
				for weapon in scenario.player_unit.weapon_list:
					if weapon.GetStat('type') != 'Gun': continue
					if weapon.GetStat('mount') is None: continue
					if weapon.GetStat('mount') != position.location: continue
					libtcod.console_set_default_foreground(context_con, libtcod.white)
					libtcod.console_print(context_con, 1, y, weapon.stats['name'])
					weapon.DisplayAmmo(context_con, 1, y)
					break
				
		
			# display smoke grenades or mortar rounds remaining if on these commands
			elif position.crewman.current_cmd == 'Smoke Grenade':
				y += 1
				text = 'Smoke Grenades: ' + str(campaign_day.smoke_grenades)
				libtcod.console_print(context_con, 0, y, text)
			
			elif position.crewman.current_cmd == 'Fire Smoke Mortar':
				y += 1
				text = 'Smoke Rounds: ' + str(campaign_day.smoke_mortar_rounds)
				libtcod.console_print(context_con, 0, y, text)
		
		# Movement Phase
		elif self.phase == PHASE_MOVEMENT:
			
			libtcod.console_set_default_foreground(context_con, libtcod.white)
			libtcod.console_print(context_con, 5, 0, 'Success')
			libtcod.console_print(context_con, 14, 0, 'Bog')
			
			libtcod.console_print(context_con, 0, 2, 'Fwd')
			libtcod.console_print(context_con, 0, 4, 'Rev')
			libtcod.console_print(context_con, 0, 6, 'Pivot')
			libtcod.console_print(context_con, 0, 8, 'HD')			
			
			libtcod.console_set_default_foreground(context_con, libtcod.light_grey)
			
			# forward move
			text = str(self.player_unit.forward_move_chance) + '%'
			libtcod.console_print_ex(context_con, 10, 2, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			text = str(self.player_unit.bog_chance) + '%'
			libtcod.console_print_ex(context_con, 16, 2, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			
			# reverse move
			text = str(self.player_unit.reverse_move_chance) + '%'
			libtcod.console_print_ex(context_con, 10, 4, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			text = str(round(self.player_unit.bog_chance * 1.5, 1)) + '%'
			libtcod.console_print_ex(context_con, 16, 4, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			
			# pivot
			libtcod.console_print_ex(context_con, 10, 6, libtcod.BKGND_NONE,
				libtcod.RIGHT, '100%')
			text = str(round(self.player_unit.bog_chance * 0.25, 1)) + '%'
			libtcod.console_print_ex(context_con, 16, 6, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			
			# Hull Down
			text = str(self.player_unit.GetHDChance(driver_attempt=True)) + '%'
			libtcod.console_print_ex(context_con, 10, 8, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			libtcod.console_print_ex(context_con, 16, 8, libtcod.BKGND_NONE,
				libtcod.RIGHT, '0%')
			
		# crew action phase
		elif self.phase == PHASE_CREW_ACTION:
			position = self.player_unit.positions_list[self.selected_position]
			if position.crewman is None: return
			
			if position.crewman.current_cmd == 'Manage Ready Rack':
				
				rr_weapon = None
				for weapon in self.player_unit.weapon_list:
					if weapon.GetStat('type') != 'Gun': continue
					if weapon.GetStat('mount') is None: continue
					if weapon.GetStat('mount') != position.location: continue
					rr_weapon = weapon
					break
				if rr_weapon is None: return
				
				libtcod.console_set_default_foreground(context_con, libtcod.white)
				libtcod.console_set_default_background(context_con, libtcod.darkest_red)
				libtcod.console_rect(context_con, 0, 0, 18, 1, True, libtcod.BKGND_SET)
				libtcod.console_set_default_background(context_con, libtcod.black)
				libtcod.console_print(context_con, 0, 0, rr_weapon.stats['name'])
				
				rr_weapon.DisplayAmmo(context_con, 0, 1)
			
		# Shooting Phase
		elif self.phase == PHASE_SHOOTING:
			
			weapon = self.selected_weapon
			if weapon is None:
				return
			
			libtcod.console_set_default_foreground(context_con, libtcod.white)
			libtcod.console_set_default_background(context_con, libtcod.darkest_red)
			libtcod.console_rect(context_con, 0, 0, 18, 1, True, libtcod.BKGND_SET)
			libtcod.console_print(context_con, 0, 0, weapon.stats['name'])
			libtcod.console_set_default_background(context_con, libtcod.darkest_grey)
			
			if weapon.GetStat('mount') is not None:
				libtcod.console_set_default_foreground(context_con, libtcod.light_grey)
				libtcod.console_print_ex(context_con, 17, 0, libtcod.BKGND_NONE,
					libtcod.RIGHT, weapon.stats['mount'])
			
			if weapon.broken:
				libtcod.console_set_default_foreground(context_con, libtcod.light_red)
				libtcod.console_print(context_con, 0, 1, 'BROKEN')
				return
			elif weapon.jammed:
				libtcod.console_set_default_foreground(context_con, libtcod.light_red)
				libtcod.console_print(context_con, 0, 1, 'JAMMED')
				return
			
			# display target and acquired target status if any
			if weapon.selected_target is not None and weapon.acquired_target is not None:
				(ac_target, level) = weapon.acquired_target
				if ac_target == weapon.selected_target:
					text = 'Acquired Target'
					if level == 1:
						text += '+'
					libtcod.console_set_default_foreground(context_con, libtcod.light_blue)
					libtcod.console_print(context_con, 0, 8, text)
					libtcod.console_set_default_foreground(context_con, libtcod.white)
			
			# if weapon is a gun, display ammo info here
			if weapon.GetStat('type') == 'Gun':
				weapon.DisplayAmmo(context_con, 0, 1)
			# otherwise, can display fp rating
			elif weapon.GetStat('fp') is not None:
				libtcod.console_print(context_con, 0, 1, weapon.GetStat('fp') + ' FP')
			
			if weapon.fired:
				libtcod.console_set_default_foreground(context_con, libtcod.red)
				libtcod.console_print(context_con, 0, 7, 'Fired')
				return
			
			# display RoF chance if any
			libtcod.console_set_default_foreground(context_con, libtcod.white)
			libtcod.console_print_ex(context_con, 17, 1, libtcod.BKGND_NONE,
				libtcod.RIGHT, 'RoF')
			
			libtcod.console_set_default_foreground(context_con, libtcod.light_grey)
			chance = weapon.GetRoFChance()
			if chance > 0.0:
				text = str(chance) + '%'
			else:
				text = 'N/A'
			libtcod.console_print_ex(context_con, 17, 2, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			
			if weapon.selected_target is None:
				libtcod.console_set_default_foreground(context_con, libtcod.red)
				libtcod.console_print(context_con, 0, 8, 'No target selected')
			
			# display info about current target if any
			else:
				result = self.CheckAttack(scenario.player_unit, weapon, weapon.selected_target)
				
				# attack is fine
				if result == '':
					libtcod.console_set_default_foreground(context_con, libtcod.light_blue)
					libtcod.console_print(context_con, 0, 9, 'Ready to fire!')
				# attack is not fine
				else:
					lines = wrap(result, 18)
					y = 9
					libtcod.console_set_default_foreground(context_con, libtcod.red)
					for line in lines:
						libtcod.console_print(context_con, 0, y, line)
						y += 1
						if y == 12: break
	
	
	# update zone info console, 18x5
	def UpdateZoneInfoCon(self):
		libtcod.console_clear(zone_info_con)
		libtcod.console_set_default_foreground(zone_info_con, libtcod.white)
		map_zone = campaign_day.map_hexes[campaign_day.player_unit_location]
		libtcod.console_print_ex(zone_info_con, 9, 0, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Zone: ' + map_zone.terrain_type)
		if map_zone.landmines:
			libtcod.console_set_default_foreground(zone_info_con, libtcod.light_red)
			libtcod.console_print(zone_info_con, 0, 2, 'Landmines')
		if map_zone.objective is not None:
			libtcod.console_set_default_foreground(zone_info_con, libtcod.light_blue)
			libtcod.console_print(zone_info_con, 0, 3, map_zone.objective['type'])
	
	
	# update player unit info console
	def UpdatePlayerInfoCon(self):
		libtcod.console_clear(player_info_con)
		DisplayUnitInfo(player_info_con, 0, 0, scenario.player_unit.unit_id, scenario.player_unit)
	
	
	# update the player crew info console
	def UpdateCrewInfoCon(self):
		libtcod.console_clear(crew_con)
		
		y = 0
		i = 0
		
		for position in scenario.player_unit.positions_list:
			
			# highlight position if selected and in command phase
			if i == scenario.selected_position and scenario.phase in [PHASE_COMMAND, PHASE_CREW_ACTION]:
				libtcod.console_set_default_background(crew_con, libtcod.darker_blue)
				libtcod.console_rect(crew_con, 0, y, 25, 3, True, libtcod.BKGND_SET)
				libtcod.console_set_default_background(crew_con, libtcod.black)
			
			# display position name and location in vehicle (eg. turret/hull)
			# if crewman is untrained in this position, highlight this
			libtcod.console_set_default_foreground(crew_con, libtcod.light_blue)
			if position.crewman is not None:
				if position.crewman.UntrainedPosition():
					libtcod.console_set_default_foreground(crew_con, libtcod.light_red)
			libtcod.console_print(crew_con, 0, y, position.name)
			libtcod.console_set_default_foreground(crew_con, libtcod.white)
			libtcod.console_print_ex(crew_con, 0+24, y, libtcod.BKGND_NONE, 
				libtcod.RIGHT, position.location)
			
			# display name of crewman and buttoned up / exposed status if any
			if position.crewman is None:
				libtcod.console_print(crew_con, 0, y+1, 'Empty')
			else:
				
				if position.crewman.is_player_commander:
					libtcod.console_set_default_foreground(crew_con, libtcod.gold)
				# use nickname if any
				if position.crewman.nickname != '':
					libtcod.console_print(crew_con, 0, y+1, '"' + position.crewman.nickname + '"')
				else:
					PrintExtended(crew_con, 0, y+1, position.crewman.GetName(), first_initial=True)
				libtcod.console_set_default_foreground(crew_con, libtcod.white)
				
				if not position.hatch:
					text = '--'
				elif position.crewman.ce:
					text = 'CE'
				else:
					text = 'BU'
				libtcod.console_print_ex(crew_con, 24, y+1, libtcod.BKGND_NONE, libtcod.RIGHT, text)
			
				# display if crewman is dead
				if not position.crewman.alive:
					libtcod.console_set_default_foreground(crew_con, libtcod.dark_grey)
					libtcod.console_print(crew_con, 0, y+2, 'Dead')
				
				else:
			
					# display warning if crewman has 1+ critical injuries, otherwise display current command
					critical_injury = False
					for (k, v) in position.crewman.injury.items():
						if v is None: continue
						if v == 'Critical':
							critical_injury = True
							break
					
					# display current command
					libtcod.console_set_default_foreground(crew_con, libtcod.dark_yellow)
					libtcod.console_print(crew_con, 0, y+2, position.crewman.current_cmd)
					
					# current condition - display short form to fit in console
					libtcod.console_set_default_foreground(crew_con, libtcod.light_grey)
					if position.crewman.condition != 'Good Order':
						if position.crewman.condition == 'Unconscious':
							text = 'Uncn'
						elif position.crewman.condition == 'Stunned':
							text = 'Stun'
						elif position.crewman.condition == 'Shaken':
							text = 'Shkn'
						else:
							text = ''
					elif critical_injury:
						text = 'Crit'
					else:
						text = ''
					if critical_injury:
						libtcod.console_set_default_foreground(crew_con, libtcod.light_red)
					libtcod.console_print_ex(crew_con, 24, y+2, libtcod.BKGND_NONE, libtcod.RIGHT, 
						text)
			
			libtcod.console_set_default_foreground(crew_con, libtcod.darker_grey)
			for x in range(25):
				libtcod.console_print(crew_con, x, y+3, '-')
			
			libtcod.console_set_default_foreground(crew_con, libtcod.white)
			y += 4
			i += 1
	
	
	# update player command console 25x12
	def UpdateCmdCon(self):
		libtcod.console_clear(cmd_menu_con)
		
		# player not active
		if scenario.active_player == 1: return
		# advancing to next phase automatically
		if self.advance_phase: return
		
		# Any phase in player activation
		libtcod.console_set_default_foreground(cmd_menu_con, ACTION_KEY_COL)
		libtcod.console_print(cmd_menu_con, 1, 10, 'Space')
		libtcod.console_set_default_foreground(cmd_menu_con, libtcod.light_grey)
		libtcod.console_print(cmd_menu_con, 7, 10, 'End Phase')
		
		# Command phase
		if self.phase == PHASE_COMMAND:
			libtcod.console_set_default_foreground(cmd_menu_con, ACTION_KEY_COL)
			libtcod.console_print(cmd_menu_con, 1, 1, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(cmd_menu_con, 1, 2, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_print(cmd_menu_con, 1, 3, 'H')
			libtcod.console_print(cmd_menu_con, 1, 4, EnKey('b').upper())
			libtcod.console_print(cmd_menu_con, 1, 5, EnKey('x').upper())
			libtcod.console_print(cmd_menu_con, 1, 6, EnKey('e').upper())
			
			libtcod.console_set_default_foreground(cmd_menu_con, libtcod.light_grey)
			libtcod.console_print(cmd_menu_con, 7, 1, 'Select Position')
			libtcod.console_print(cmd_menu_con, 7, 2, 'Select Command')
			libtcod.console_print(cmd_menu_con, 7, 3, 'Open/Shut Hatch')
			libtcod.console_print(cmd_menu_con, 7, 4, 'Button/Open Up!')
			libtcod.console_print(cmd_menu_con, 7, 5, 'Set Default')
			libtcod.console_print(cmd_menu_con, 7, 6, 'Crewman Menu')
		
		# Crew action phase
		elif self.phase == PHASE_CREW_ACTION:
			libtcod.console_set_default_foreground(cmd_menu_con, ACTION_KEY_COL)
			libtcod.console_print(cmd_menu_con, 1, 1, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_set_default_foreground(cmd_menu_con, libtcod.light_grey)
			libtcod.console_print(cmd_menu_con, 7, 1, 'Select Position')
			
			# crew command specific actions
			if self.selected_position is None: return
			position = self.player_unit.positions_list[self.selected_position]
			if position.crewman is None: return
			
			if position.crewman.current_cmd == 'Manage Ready Rack':
				
				rr_weapon = None
				for weapon in scenario.player_unit.weapon_list:
					if weapon.GetStat('type') != 'Gun': continue
					if weapon.GetStat('mount') is None: continue
					if weapon.GetStat('mount') != position.location: continue
					rr_weapon = weapon
					break
				if rr_weapon is None: return
				
				libtcod.console_set_default_foreground(cmd_menu_con, ACTION_KEY_COL)
				libtcod.console_print(cmd_menu_con, 1, 2, EnKey('d').upper() + '/' + EnKey('a').upper())
				libtcod.console_print(cmd_menu_con, 1, 3, EnKey('c').upper())
				
				HOTKEYS = ['t', 'g', 'b', 'n']
				y = 4
				for ammo_type in rr_weapon.stats['ammo_type_list']:
					libtcod.console_print(cmd_menu_con, 1, y, EnKey(HOTKEYS[y-4]).upper())
					y += 1
				
				libtcod.console_set_default_foreground(cmd_menu_con, libtcod.light_grey)
				libtcod.console_print(cmd_menu_con, 7, 2, 'Add/Remove Shell')
				libtcod.console_print(cmd_menu_con, 7, 3, 'Cycle Ammo Type')
				y = 4
				for ammo_type in rr_weapon.stats['ammo_type_list']:
					libtcod.console_print(cmd_menu_con, 7, y, 'Fill RR with ' + ammo_type)
					y += 1
				
		
		# Movement phase
		elif self.phase == PHASE_MOVEMENT:
			libtcod.console_set_default_foreground(cmd_menu_con, ACTION_KEY_COL)
			libtcod.console_print(cmd_menu_con, 1, 1, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(cmd_menu_con, 1, 2, EnKey('a').upper() + '/' + EnKey('d').upper())
			libtcod.console_print(cmd_menu_con, 1, 3, EnKey('h').upper())
			libtcod.console_print(cmd_menu_con, 1, 4, EnKey('r').upper())
			libtcod.console_print(cmd_menu_con, 1, 5, EnKey('c').upper())
			
			libtcod.console_set_default_foreground(cmd_menu_con, libtcod.light_grey)
			libtcod.console_print(cmd_menu_con, 5, 1, 'Forward/Reverse')
			libtcod.console_print(cmd_menu_con, 5, 2, 'Pivot Hull')
			libtcod.console_print(cmd_menu_con, 5, 3, 'Attempt Hull Down')
			libtcod.console_print(cmd_menu_con, 5, 4, 'Reposition')
			libtcod.console_print(cmd_menu_con, 5, 5, 'Conceal/Reveal Self')
		
		# Shooting phase
		elif self.phase == PHASE_SHOOTING:
			libtcod.console_set_default_foreground(cmd_menu_con, ACTION_KEY_COL)
			libtcod.console_print(cmd_menu_con, 1, 1, EnKey('w').upper() + '/' + EnKey('s').upper())
			libtcod.console_print(cmd_menu_con, 1, 2, EnKey('a').upper() + '/' + EnKey('d').upper())
			if 'turret' in self.player_unit.stats:
				if self.player_unit.stats['turret'] != 'FIXED':
					libtcod.console_print(cmd_menu_con, 1, 3, EnKey('q').upper() + '/' + EnKey('e').upper())
			libtcod.console_print(cmd_menu_con, 1, 5, EnKey('r').upper())
			libtcod.console_print(cmd_menu_con, 1, 6, EnKey('f').upper())
			
			libtcod.console_set_default_foreground(cmd_menu_con, libtcod.light_grey)
			libtcod.console_print(cmd_menu_con, 7, 1, 'Select Weapon/Ammo')
			libtcod.console_print(cmd_menu_con, 7, 2, 'Select Target')
			if 'turret' in self.player_unit.stats:
				if self.player_unit.stats['turret'] != 'FIXED':
					libtcod.console_print(cmd_menu_con, 7, 3, 'Rotate Turret')
			libtcod.console_print(cmd_menu_con, 7, 5, 'Toggle RR Use')
			libtcod.console_print(cmd_menu_con, 7, 6, 'Fire at Target')
	
	
	# plot the center of a given in-game hex on the scenario hex map console
	# 0,0 appears in centre of console
	def PlotHex(self, hx, hy):
		x = (hx*7) + 26
		y = (hy*6) + (hx*3) + 21
		return (x,y)
	
	
	# build a dictionary of console locations and their corresponding map hexes
	# only called once when Scenario is created
	def BuildHexmapDict(self):
		for map_hex in self.map_hexes:
			# stop when outer hex ring is reached
			if GetHexDistance(0, 0, map_hex.hx, map_hex.hy) > 3: return
			(x,y) = self.PlotHex(map_hex.hx, map_hex.hy)
			
			# record console positions to dictionary
			for x1 in range(x-2, x+3):
				self.hex_map_index[(x1, y-2)] = map_hex
				self.hex_map_index[(x1, y+2)] = map_hex
			for x1 in range(x-3, x+4):
				self.hex_map_index[(x1, y-1)] = map_hex
				self.hex_map_index[(x1, y+1)] = map_hex
			for x1 in range(x-4, x+5):
				self.hex_map_index[(x1, y)] = map_hex
	
	
	# update hexmap console 53x43
	def UpdateHexmapCon(self):
		
		libtcod.console_clear(hexmap_con)
		
		# select base hex console image to use
		if campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
			scen_hex = LoadXP('scen_hex_snow.xp')
		elif campaign.stats['region'] == 'North Africa':
			scen_hex = LoadXP('scen_hex_desert.xp')
		else:
			scen_hex = LoadXP('scen_hex.xp')
		libtcod.console_set_key_color(scen_hex, KEY_COLOR)
		
		# draw hexes to hex map console
		for map_hex in self.map_hexes:
			if GetHexDistance(0, 0, map_hex.hx, map_hex.hy) > 3: break
			(x,y) = self.PlotHex(map_hex.hx, map_hex.hy)
			libtcod.console_blit(scen_hex, 0, 0, 0, 0, hexmap_con, x-5, y-3)
		
		# draw fog/sandstorm depiction overtop
		if campaign_day.weather['Fog'] > 0:
			scen_hex = LoadXP('scen_hex_fog.xp')
			libtcod.console_set_key_color(scen_hex, KEY_COLOR)
			for distance in range(3, 3 - campaign_day.weather['Fog'], -1):
				for (hx, hy) in GetHexRing(0, 0, distance):
					(x,y) = self.PlotHex(hx, hy)
					libtcod.console_blit(scen_hex, 0, 0, 0, 0, hexmap_con, x-5, y-3)
		
		del scen_hex
	
	
	# update unit layer console
	def UpdateUnitCon(self):
		
		libtcod.console_set_default_background(unit_con, KEY_COLOR)
		libtcod.console_clear(unit_con)
		for map_hex in self.map_hexes:
			
			distance = GetHexDistance(0, 0, map_hex.hx, map_hex.hy)
			
			# too far away
			if distance > 3: continue
			
			# no units in hex
			if len(map_hex.unit_stack) == 0: continue
			
			# draw up to two other units in stack
			if config.getboolean('ArmCom2', 'unit_stack_display'):
				if len(map_hex.unit_stack) > 1:
					map_hex.unit_stack[1].DrawMe(-2, 0)
				if len(map_hex.unit_stack) > 2:
					map_hex.unit_stack[2].DrawMe(2, 0)
			
			# draw top unit in stack
			map_hex.unit_stack[0].DrawMe(0, 0)
			
			# draw stack number indicator if any
			if len(map_hex.unit_stack) == 1: continue
			
			# don't draw stack number if top unit is moving
			if len(map_hex.unit_stack[0].animation_cells) > 0: continue
			
			if 4 - distance <= campaign_day.weather['Fog']:
				bg_col = libtcod.Color(128,128,128)
			elif campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
				bg_col = libtcod.Color(158,158,158)
			elif campaign.stats['region'] == 'North Africa':
				bg_col = libtcod.Color(102,82,51)
			else:
				bg_col = libtcod.Color(0,64,0)
			if map_hex.unit_stack[0].turret_facing is not None:
				facing = map_hex.unit_stack[0].turret_facing
			elif map_hex.unit_stack[0].facing is not None:
				facing = map_hex.unit_stack[0].facing
			else:
				facing = 3
			if facing in [5,0,1]:
				y_mod = 1
			else:
				y_mod = -1
			
			# exception: unit is unspotted enemy
			if not map_hex.unit_stack[0].spotted and map_hex.unit_stack[0].owning_player == 1:
				y_mod = -1
			
			# top unit is on overrun
			if map_hex.unit_stack[0].overrun:
				y_mod -= 1
			
			(x,y) = scenario.PlotHex(map_hex.unit_stack[0].hx, map_hex.unit_stack[0].hy)
			text = str(len(map_hex.unit_stack))
			
			if 4 - distance <= campaign_day.weather['Fog']:
				libtcod.console_set_default_foreground(unit_con, libtcod.black)
			else:
				libtcod.console_set_default_foreground(unit_con, libtcod.grey)
			libtcod.console_set_default_background(unit_con, bg_col)
			libtcod.console_print_ex(unit_con, x, y+y_mod, libtcod.BKGND_SET, libtcod.CENTER,
				text)
		
	
	# update GUI console
	def UpdateGuiCon(self, los_highlight=None):
		
		libtcod.console_clear(gui_con)
				
		# display field of view if in command phase
		# but not if there's a support attack still to resolve
		if self.phase == PHASE_COMMAND and not (campaign_day.air_support_request or campaign_day.arty_support_request):
			
			position = scenario.player_unit.positions_list[scenario.selected_position]
			for (hx, hy) in position.visible_hexes:
				(x,y) = scenario.PlotHex(hx, hy)
				libtcod.console_blit(session.scen_hex_fov, 0, 0, 0, 0, gui_con,
					x-5, y-3)
		
		# shooting phase
		elif self.phase == PHASE_SHOOTING:
			
			# display covered hexes if a weapon is selected
			if self.selected_weapon is not None:
				for (hx, hy) in self.selected_weapon.covered_hexes:
					(x,y) = self.PlotHex(hx, hy)
					libtcod.console_blit(session.scen_hex_fov, 0, 0, 0, 0, gui_con,
						x-5, y-3)
			
				# display target recticle if a weapon target is selected
				if self.selected_weapon.selected_target is not None:
					
					if not self.player_unit.los_table[self.selected_weapon.selected_target]:
						col = libtcod.grey
					else:
						col = libtcod.red
					
					# display firing line
					(x1,y1) = self.player_unit.GetScreenLocation()
					(x2,y2) = self.PlotHex(self.selected_weapon.selected_target.hx, self.selected_weapon.selected_target.hy)
					line = GetLine(x1, y1, x2, y2)
					for (x,y) in line[2:-1]:
						libtcod.console_put_char_ex(gui_con, x, y, 250, col, libtcod.black)
		
		if los_highlight is None: return
		
		(unit1, unit2) = los_highlight
		(x1,y1) = self.PlotHex(unit1.hx, unit1.hy)
		if unit1.overrun: y1 -= 1
		(x2,y2) = self.PlotHex(unit2.hx, unit2.hy)
		if unit2.overrun: y2 -= 1
		line = GetLine(x1, y1, x2, y2)
		for (x,y) in line[2:-1]:
			libtcod.console_put_char_ex(gui_con, x, y, 250, libtcod.red, libtcod.black)
			
	
	# update unit info console, which displays basic information about a unit under
	# the mouse cursor
	# 61x5
	def UpdateUnitInfoCon(self):
		libtcod.console_clear(unit_info_con)
		
		# check that cursor is in map area and on a map hex
		x = mouse.cx - 32 - window_x
		y = mouse.cy - 9 - window_y
		if (x,y) not in self.hex_map_index:
			libtcod.console_set_default_foreground(unit_info_con, libtcod.dark_grey)
			libtcod.console_print(unit_info_con, 18, 2, 'Mouseover a hex for details')
			return
		
		map_hex = self.hex_map_index[(x,y)]
	
		# distance from player in right column
		distance = GetHexDistance(0, 0, map_hex.hx, map_hex.hy)
		if distance == 0:
			text = '0-120m.'
		elif distance == 1:
			text = '120-480m.'
		elif distance == 2:
			text = '480-960m.'
		else:
			text = '960-1440m.'
		libtcod.console_set_default_foreground(unit_info_con, libtcod.light_grey)
		libtcod.console_print_ex(unit_info_con, 60, 0, libtcod.BKGND_NONE,
			libtcod.RIGHT, 'Range: ' + text)
		
		# fog effect if any
		if campaign_day.weather['Fog'] > 0:
			if 4 - distance <= campaign_day.weather['Fog']:
				libtcod.console_set_default_foreground(unit_info_con, libtcod.lighter_grey)
				libtcod.console_print_ex(unit_info_con, 60, 1, libtcod.BKGND_NONE,
					libtcod.RIGHT, 'Fog')
		
		# no units in hex
		if len(map_hex.unit_stack) == 0: return
		
		# display info for top unit in stack
		unit = map_hex.unit_stack[0]
		
		# display smoke and/or dust levels
		text = ''
		if unit.smoke > 0:
			text += 'Smoke: ' + str(unit.smoke)
		if unit.dust > 0:
			if unit.smoke > 0:
				text += ' '
			text += 'Dust: ' + str(unit.dust)
		if text != '':
			libtcod.console_set_default_foreground(unit_info_con, libtcod.grey)
			libtcod.console_print_ex(unit_info_con, 60, 2, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
		
		# LoS blocked
		if not self.player_unit.los_table[unit]:
			libtcod.console_set_default_background(unit_info_con, libtcod.grey)
			libtcod.console_rect(unit_info_con, 25, 0, 11, 1, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(unit_info_con, libtcod.darkest_grey)
			libtcod.console_set_default_foreground(unit_info_con, libtcod.black)
			libtcod.console_print(unit_info_con, 25, 0, 'LoS Blocked')
		
		if unit.owning_player == 1 and not unit.spotted:
			libtcod.console_set_default_foreground(unit_info_con, UNKNOWN_UNIT_COL)
			libtcod.console_print(unit_info_con, 0, 0, 'Unspotted Enemy')
			
		else:
			
			if unit == scenario.player_unit:
				col = libtcod.white
			elif unit.owning_player == 0:
				col = ALLIED_UNIT_COL
			else:
				col = ENEMY_UNIT_COL
	
			libtcod.console_set_default_foreground(unit_info_con, col)
			libtcod.console_print(unit_info_con, 0, 0, unit.unit_id)
			libtcod.console_print(unit_info_con, 0, 1, unit.nick_name)

			libtcod.console_set_default_foreground(unit_info_con, libtcod.light_grey)
			text = session.nations[unit.nation]['adjective'] + ' ' + unit.GetStat('class')
			libtcod.console_print(unit_info_con, 0, 2, text)
			
			# statuses
			if unit.immobilized:
				libtcod.console_print(unit_info_con, 0, 3, 'Immobilized')
			elif unit.pinned:
				libtcod.console_print(unit_info_con, 0, 3, 'Pinned')
			elif unit.moving:
				libtcod.console_print(unit_info_con, 0, 3, 'Moving')
			if unit.routed:
				libtcod.console_print(unit_info_con, 0, 4, 'Routed')
			if unit.fired:
				libtcod.console_print(unit_info_con, 12, 3, 'Fired')
			
			# captured
			if unit.owning_player == 1 and 'enemy_captured_units' in campaign.stats:
				if unit.unit_id in campaign.stats['enemy_captured_units']:
					libtcod.console_print(unit_info_con, 8, 4, '(Captured)')
			
			# middle column
			
			# current terrain
			if unit.terrain is not None:
				libtcod.console_set_default_foreground(unit_info_con, libtcod.dark_green)
				libtcod.console_print_ex(unit_info_con, 30, 1, libtcod.BKGND_NONE,
					libtcod.CENTER, unit.terrain)
			
			# for units not in player's own hex
			if not (unit.hx == 0 and unit.hy == 0):
			
				# hull facing if any
				if unit.facing is not None and unit.GetStat('category') not in ['Infantry', 'Cavalry']:
					libtcod.console_put_char_ex(unit_info_con, 27, 3, 'H',
						libtcod.light_grey, libtcod.darkest_grey)
					libtcod.console_put_char_ex(unit_info_con, 28, 3,
						GetDirectionalArrow(unit.facing), libtcod.light_grey,
						libtcod.darkest_grey)
					text = GetFacing(scenario.player_unit, unit)
					libtcod.console_set_default_foreground(unit_info_con, libtcod.light_grey)
					libtcod.console_print(unit_info_con, 30, 3, text)
				
				# turret facing if any
				if unit.turret_facing is not None:
					libtcod.console_put_char_ex(unit_info_con, 27, 4, 'T',
						libtcod.light_grey, libtcod.darkest_grey)
					libtcod.console_put_char_ex(unit_info_con, 28, 4,
						GetDirectionalArrow(unit.turret_facing), libtcod.light_grey,
						libtcod.darkest_grey)
					text = GetFacing(scenario.player_unit, unit, turret_facing=True)
					libtcod.console_set_default_foreground(unit_info_con, libtcod.light_grey)
					libtcod.console_print(unit_info_con, 30, 4, text)
			
			# HD status if any
			if len(unit.hull_down) > 0:
				libtcod.console_set_default_foreground(unit_info_con, libtcod.sepia)
				libtcod.console_print(unit_info_con, 36, 3, 'HD')
				libtcod.console_put_char_ex(unit_info_con, 38, 3,
					GetDirectionalArrow(unit.hull_down[0]), libtcod.sepia,
					libtcod.darkest_grey)
			
			# right column
			
			# dug-in, entrenched, or fortified status
			text = ''
			if unit.dug_in:
				libtcod.console_set_default_foreground(unit_info_con, libtcod.sepia)
				text = 'Dug-in'
			elif unit.entrenched:
				libtcod.console_set_default_foreground(unit_info_con, libtcod.light_sepia)
				text = 'Entrenched'
			elif unit.fortified:
				libtcod.console_set_default_foreground(unit_info_con, libtcod.light_grey)
				text = 'Fortified'
			if text != '':
				libtcod.console_print_ex(unit_info_con, 60, 3, libtcod.BKGND_NONE,
					libtcod.RIGHT, text)
			
			# AI statuses
			if unit.ai is None: return
			if unit in scenario.player_unit.squad: return
			
			text = unit.ai.attitude + ';' + unit.ai.state
			libtcod.console_set_default_foreground(unit_info_con, libtcod.light_purple)
			libtcod.console_print_ex(unit_info_con, 60, 4, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
	
	
	# starts or re-starts looping animations based on weather conditions
	def InitAnimations(self):
		
		# reset animations
		self.animation['rain_active'] = False
		self.animation['rain_drops'] = []
		self.animation['snow_active'] = False
		self.animation['snowflakes'] = []
		self.animation['hex_highlight'] = False
		self.animation['hex_flash'] = 0
		
		# check for rain animation
		if campaign_day.weather['Precipitation'] in ['Rain', 'Heavy Rain']:
			self.animation['rain_active'] = True
		elif campaign_day.weather['Precipitation'] in ['Light Snow', 'Snow', 'Blizzard']:
			self.animation['snow_active'] = True
		
		# set up rain if any
		if self.animation['rain_active']:
			self.animation['rain_drops'] = []
			num = 4
			if campaign_day.weather['Precipitation'] == 'Heavy Rain':
				num = 8
			for i in range(num):
				x = libtcod.random_get_int(0, 4, 50)
				y = libtcod.random_get_int(0, 0, 38)
				lifespan = libtcod.random_get_int(0, 1, 5)
				self.animation['rain_drops'].append((x, y, 4))
		
		# set up snow if any
		if self.animation['snow_active']:
			self.animation['snowflakes'] = []
			if campaign_day.weather['Precipitation'] == 'Light Snow':
				num = 4
			elif campaign_day.weather['Precipitation'] == 'Snow':
				num = 8
			else:
				num = 16
			for i in range(num):
				x = libtcod.random_get_int(0, 4, 50)
				y = libtcod.random_get_int(0, 0, 37)
				lifespan = libtcod.random_get_int(0, 4, 10)
				self.animation['snowflakes'].append((x, y, lifespan))
	
	
	# update the scenario animation frame and console 53x43
	def UpdateAnimCon(self):
		
		libtcod.console_clear(anim_con)
		
		# looping animations
		
		# update rain display
		if self.animation['rain_active']:
			
			# update location of each rain drop, spawn new ones if required
			for i in range(len(self.animation['rain_drops'])):
				(x, y, lifespan) = self.animation['rain_drops'][i]
				
				# respawn if finished
				if lifespan == 0:
					x = libtcod.random_get_int(0, 4, 50)
					y = libtcod.random_get_int(0, 0, 37)
					lifespan = libtcod.random_get_int(0, 1, 5)
				else:
					y += 2
					lifespan -= 1
				
				self.animation['rain_drops'][i] = (x, y, lifespan)
			
			# draw drops to screen
			for (x, y, lifespan) in self.animation['rain_drops']:
				
				# skip if off screen
				if x < 0 or y > 50: continue
				
				if lifespan == 0:
					char = 111
				else:
					char = 124
				libtcod.console_put_char_ex(anim_con, x, y, char, libtcod.light_blue,
					libtcod.black)
		
		# update snow display
		if self.animation['snow_active']:
			
			# update location of each snowflake
			for i in range(len(self.animation['snowflakes'])):
				(x, y, lifespan) = self.animation['snowflakes'][i]
				
				# respawn if finished
				if lifespan == 0:
					x = libtcod.random_get_int(0, 4, 50)
					y = libtcod.random_get_int(0, 0, 37)
					lifespan = libtcod.random_get_int(0, 4, 10)
				else:
					x += choice([-1, 0, 1])
					y += 1
					lifespan -= 1
				
				self.animation['snowflakes'][i] = (x, y, lifespan)
			
			# draw snowflakes to screen
			for (x, y, lifespan) in self.animation['snowflakes']:
				
				# skip if off screen
				if x < 0 or y > 50: continue
				
				libtcod.console_put_char_ex(anim_con, x, y, 249, libtcod.white,
					libtcod.black)
		
		# single-shot animations
		
		# update airplane animation if any
		if self.animation['air_attack'] is not None:
			
			# update draw location
			self.animation['air_attack_line'].pop(0)
			
			# clear if finished
			if len(self.animation['air_attack_line']) == 0:
				self.animation['air_attack'] = None
			else:
				(x,y) = self.animation['air_attack_line'][0]
				libtcod.console_blit(self.animation['air_attack'], 0, 0, 0, 0, anim_con, x-1, y)
		
		# update gun fire animation if any
		if self.animation['gun_fire_active']:
			
			self.animation['gun_fire_line'].pop(0)
			if len(self.animation['gun_fire_line']) > 0:
				self.animation['gun_fire_line'].pop(0)
			
			# clear if finished
			if len(self.animation['gun_fire_line']) == 0:
				self.animation['gun_fire_active'] = False
			else:
				(x,y) = self.animation['gun_fire_line'][0]
				libtcod.console_put_char_ex(anim_con, x, y, 250, libtcod.white,
					libtcod.black)
		
		# update small arms fire if any
		if self.animation['small_arms_fire_action'] is not None:
			
			if self.animation['small_arms_lifetime'] == 0:
				self.animation['small_arms_fire_action'] = None
			else:
				self.animation['small_arms_lifetime'] -= 1
				(x,y) = choice(self.animation['small_arms_fire_line'][2:])
				libtcod.console_put_char_ex(anim_con, x, y, 250, libtcod.yellow,
					libtcod.black)
		
		# update bomb/explosion animation if any
		if self.animation['bomb_effect'] is not None:
			
			if self.animation['bomb_effect_lifetime'] == 0:
				self.animation['bomb_effect'] = None
			else:
				self.animation['bomb_effect_lifetime'] -= 1
				(x,y) = self.animation['bomb_effect']
				if 3 & self.animation['bomb_effect_lifetime'] == 0:
					col = libtcod.red
				elif 2 & self.animation['bomb_effect_lifetime'] == 0:
					col = libtcod.yellow
				else:
					col = libtcod.black
				
				libtcod.console_put_char_ex(anim_con, x, y, 42, col,
					libtcod.black)
		
		# update grenade effect if any
		if self.animation['grenade_effect'] is not None:
			
			if self.animation['grenade_effect_lifetime'] == 0:
				self.animation['grenade_effect'] = None
			else:
				self.animation['grenade_effect_lifetime'] -= 1
				(x,y) = self.animation['grenade_effect']
				x += libtcod.random_get_int(0, -1, 1)
				y += libtcod.random_get_int(0, -1, 1)
				col = choice([libtcod.red, libtcod.yellow, libtcod.black])
				libtcod.console_put_char_ex(anim_con, x, y, 250, col,
					libtcod.black)
		
		# update flamethrower effect if any
		if self.animation['ft_effect'] is not None:
			
			if self.animation['ft_effect_lifetime'] == 0:
				self.animation['ft_effect'] = None
			else:
				self.animation['ft_effect_lifetime'] -= 1
				(x,y) = self.animation['ft_effect']
				x += libtcod.random_get_int(0, -1, 1)
				y += libtcod.random_get_int(0, -1, 1)
				fg_col = choice([libtcod.light_red, libtcod.light_yellow, libtcod.grey])
				bg_col = choice([libtcod.red, libtcod.yellow, libtcod.black])
				libtcod.console_put_char_ex(anim_con, x, y, 177, fg_col,
					bg_col)
		
		# update Panzerschreck firing effect if any
		if self.animation['psk_fire_action']:
			
			self.animation['psk_fire_line'].pop(0)
			
			# clear if finished
			if len(self.animation['psk_fire_line']) == 0:
				self.animation['psk_fire_action'] = False
			else:
				(x,y) = self.animation['psk_fire_line'][0]
				libtcod.console_put_char_ex(anim_con, x, y, 250, libtcod.green,
					libtcod.black)
		
		# update hex highlight if any
		if self.animation['hex_highlight']:
			
			(hx, hy) = self.animation['hex_highlight']
			(x,y) = self.PlotHex(hx, hy)
			
			if self.animation['hex_flash'] == 1:
				char = 250
				self.animation['hex_flash'] = 0
			else:
				char = 249
				self.animation['hex_flash'] = 1
			
			for direction in range(6):
				for (xm,ym) in HEX_EDGE_CELLS[direction]:
					libtcod.console_put_char_ex(anim_con, x+xm, y+ym,
						char, libtcod.light_blue, libtcod.black)
		
		# reset update timer
		session.anim_timer = time.time()
		
	
	# draw all scenario consoles to the screen
	def UpdateScenarioDisplay(self, skip_blit=False):
		libtcod.console_clear(con)
		
		# left column
		if self.attack_con_active:
			libtcod.console_blit(attack_con, 0, 0, 0, 0, con, 0, 0)
		else:
			libtcod.console_blit(bkg_console, 0, 0, 0, 0, con, 0, 0)
			libtcod.console_blit(player_info_con, 0, 0, 0, 0, con, 1, 1)
			libtcod.console_blit(crew_con, 0, 0, 0, 0, con, 1, 21)
			libtcod.console_blit(cmd_menu_con, 0, 0, 0, 0, con, 1, 47)
		
		# main map display
		libtcod.console_blit(hexmap_con, 0, 0, 0, 0, con, 32, 9)
		libtcod.console_blit(unit_con, 0, 0, 0, 0, con, 32, 9)
		libtcod.console_blit(gui_con, 0, 0, 0, 0, con, 32, 9, 1.0, 0.0)
		libtcod.console_blit(anim_con, 0, 0, 0, 0, con, 32, 9, 1.0, 0.0)
		
		# consoles around the edge of map
		libtcod.console_blit(context_con, 0, 0, 0, 0, con, 28, 1)
		libtcod.console_blit(zone_info_con, 0, 0, 0, 0, con, 28, 48)
		libtcod.console_blit(scen_time_con, 0, 0, 0, 0, con, 48, 1)
		libtcod.console_blit(scen_weather_con, 0, 0, 0, 0, con, 71, 1)
		libtcod.console_blit(unit_info_con, 0, 0, 0, 0, con, 28, 54)
		
		if skip_blit == True: return
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	
	
	# main input loop for scenarios
	def DoScenarioLoop(self):
		
		# set up and load scenario consoles
		global bkg_console, crew_con, cmd_menu_con, scen_weather_con
		global player_info_con, context_con, scen_time_con, hexmap_con, unit_con, gui_con
		global anim_con, attack_con, unit_info_con, zone_info_con
		
		# background outline console for left column
		bkg_console = LoadXP('bkg.xp')
		
		player_info_con = NewConsole(25, 18, libtcod.black, libtcod.white)
		crew_con = NewConsole(25, 24, libtcod.black, libtcod.white)
		cmd_menu_con = NewConsole(25, 12, libtcod.black, libtcod.white)
		context_con = NewConsole(18, 12, libtcod.darkest_grey, libtcod.white)
		scen_time_con = NewConsole(21, 6, libtcod.darkest_grey, libtcod.white)
		scen_weather_con = NewConsole(18, 12, libtcod.darkest_grey, libtcod.white)
		unit_info_con = NewConsole(61, 5, libtcod.darkest_grey, libtcod.white)
		zone_info_con = NewConsole(18, 5, libtcod.darkest_grey, libtcod.white)
		hexmap_con = NewConsole(53, 43, libtcod.black, libtcod.black)
		unit_con = NewConsole(53, 43, KEY_COLOR, libtcod.white, key_colour=True)
		gui_con = NewConsole(53, 43, KEY_COLOR, libtcod.white, key_colour=True)
		anim_con = NewConsole(53, 43, KEY_COLOR, libtcod.white, key_colour=True)
		attack_con = NewConsole(27, 60, libtcod.black, libtcod.white)
		
		pin_list = []
		
		# we're starting a new scenario
		if not self.init_complete:
			
			# set up player unit
			self.player_unit = campaign.player_unit
			self.player_unit.ResetMe()
			self.player_unit.facing = 0
			if 'turret' in self.player_unit.stats:
				self.player_unit.turret_facing = 0
			self.player_unit.squad = []
			self.player_unit.SpawnAt(0,0)
			
			# reset player crewman actions
			for position in self.player_unit.positions_list:
				if position.crewman is None: continue
				position.crewman.current_cmd = 'Spot'
			
			# copy over rest of player squad
			for unit in campaign_day.player_squad:
				unit.ResetMe()
				unit.facing = 0
				if 'turret' in unit.stats:
					unit.turret_facing = 0
				unit.SpawnAt(0,0)
				self.player_unit.squad.append(unit)
			
			# try and generate enemy units
			no_units_here = False
			if not self.SpawnEnemyUnits():
				no_units_here = True
			
			# apply effects from advancing fire if any
			if self.cd_map_hex.controlled_by != 0 and campaign_day.advancing_fire:
				for unit in self.units:
					if unit.owning_player == 0: continue
					unit.hit_by_fp = True
					unit.PinTest(10.0)
					if unit.pinned:
						pin_list.append(unit)
			
			# do initial LoS generation
			self.GenerateLoS()
			
			# set up player unit and squad for first activation
			self.player_unit.ResetForNewTurn(skip_smoke=True)
			for unit in self.player_unit.squad:
				unit.ResetForNewTurn(skip_smoke=True)
			
			# try to set crewmen default status if any
			for position in self.player_unit.positions_list:
				if position.crewman is None: continue
				if position.crewman.default_start is None: continue
				(ce, cmd) = position.crewman.default_start
				if position.crewman.ce != ce:
					position.crewman.ToggleHatch()
				if cmd != position.crewman.current_cmd and cmd in position.crewman.cmd_list:
					position.crewman.current_cmd = cmd
				position.UpdateVisibleHexes()
			
			# build player crew command lists
			self.player_unit.BuildCmdLists()
			
			# roll for possible ambush if not friendly-controlled
			if self.cd_map_hex.controlled_by != 0:
				self.DoAmbushRoll()
			
			# if player was ambushed, player squad starts moving and spotted,
			# and enemy units activate first
			if self.ambush:
				for unit in self.units:
					if unit.owning_player == 0:
						unit.moving = True
						unit.SpotMe()
				self.phase = PHASE_ALLIED_ACTION
				self.advance_phase = True
		
		# reset animation timer
		session.anim_timer = time.time()
		
		# init looping animations
		self.InitAnimations()
		
		# generate consoles and draw scenario screen for first time
		self.UpdateContextCon()
		self.UpdateZoneInfoCon()
		DisplayTimeInfo(scen_time_con)
		DisplayWeatherInfo(scen_weather_con)
		self.UpdatePlayerInfoCon()
		self.UpdateCrewInfoCon()
		self.UpdateCmdCon()
		self.UpdateUnitCon()
		self.UpdateGuiCon()
		self.UpdateAnimCon()
		self.UpdateHexmapCon()
		
		# draw the final display, but skip blitting to screen if we're still setting up the scenario
		self.UpdateScenarioDisplay(skip_blit=not self.init_complete)
		
		# finish up init actions if needed
		if not self.init_complete:
			
			self.init_complete = True
			
			# display transition animation between the root console and the new double buffer console
			(hx, hy) = campaign_day.player_unit_location
			(x1, y1) = campaign_day.PlotCDHex(hx, hy)
			x1 = float(x1) + 26.0		# upper right corner
			y1 = float(y1) + 3.0
			x2 = x1 + 6.0		# lower right coner
			y2 = y1 + 8.0
			
			x1_step = x1 / 20.0
			y1_step = y1 / 20.0
			x2_step = (float(WINDOW_WIDTH) - x2) / 20.0
			y2_step = (float(WINDOW_HEIGHT) - y2) / 20.0
			
			for i in range(20):
				
				x1 -= x1_step
				y1 -= y1_step
				x2 += x2_step
				y2 += y2_step
				
				# copy the window over to the root console
				libtcod.console_blit(con, int(x1), int(y1), int(x2-x1), int(y2-y1),
					0, window_x+int(x1), window_y+int(y1))
				DrawFrame(0, window_x+int(x1), window_y+int(y1), int(x2-x1),
					int(y2-y1))
				
				Wait(3, ignore_animations=True)
			
			# clear the root console
			libtcod.console_clear(0)
			
			self.UpdateScenarioDisplay()
			libtcod.console_flush()
			
			# check for no enemy units here
			if no_units_here:
				ShowMessage('No enemy forces seem to be here - must have been a false report.')
				self.finished = True
			
			else:
		
				# check for support request(s) and resolve if any
				self.ResolveSupportRequests()
					
				# all enemy units may have been destroyed
				self.CheckForEnd()
			
			# only check for enemies pinned by advancing fire if the scenario hasn't already eneded
			if not self.finished:
			
				# pin messages
				for unit in pin_list:
					ShowMessage(unit.GetName() + ' was pinned by your Advancing Fire', scenario_highlight=(unit.hx, unit.hy))
				pin_list = []
				
				if self.ambush:
					ShowMessage('You have been ambushed by enemy forces!')
				
				DisplayTimeInfo(scen_time_con)
			
			# record scenario play
			session.ModifySteamStat('scenarios_fought', 1)
			
			SaveGame()
		
		# record mouse cursor position to check when it has moved
		mouse_x = -1
		mouse_y = -1
		
		exit_scenario = False
		while not exit_scenario:
			
			# check for exiting game
			if session.exiting:
				return
			
			# check for scenario finished, return to campaign day map
			if self.finished:
				# copy the scenario unit over to the campaign version
				campaign.player_unit = self.player_unit
				campaign_day.BuildPlayerGunList()
				
				# copy the squad over too
				campaign_day.player_squad = []
				for unit in self.player_unit.squad:
					campaign_day.player_squad.append(unit)
				
				return
			
			libtcod.console_flush()
			
			# trigger advance to next phase
			if self.advance_phase:
				self.advance_phase = False
				self.AdvanceToNextPhase()
				
				# only save if we're about to go back to player input
				if not self.advance_phase:
					SaveGame()
				continue
			
			# check for animation update
			if time.time() - session.anim_timer >= 0.20:
				self.UpdateAnimCon()
				self.UpdateScenarioDisplay()
			
			keypress = GetInputEvent()
			
			##### Mouse Commands #####
			
			# check to see if mouse cursor has moved
			if mouse.cx != mouse_x or mouse.cy != mouse_y:
				mouse_x = mouse.cx
				mouse_y = mouse.cy
				self.UpdateUnitInfoCon()
				self.UpdateScenarioDisplay()
			
			# mouse wheel has moved or right mouse button clicked
			if mouse.wheel_up or mouse.wheel_down or mouse.rbutton_pressed:
				
				# see if cursor is over a hex with 1+ units in it
				x = mouse.cx - 32 - window_x
				y = mouse.cy - 9 - window_y
				if (x,y) in self.hex_map_index:
					map_hex = self.hex_map_index[(x,y)]
					if len(map_hex.unit_stack) > 0:
						if mouse.rbutton_pressed:
							unit = map_hex.unit_stack[0]
							if not (unit.owning_player == 1 and not unit.spotted):
								self.ShowUnitInfoWindow(unit)
							continue
						elif len(map_hex.unit_stack) > 1:
							if mouse.wheel_up:
								map_hex.unit_stack[:] = map_hex.unit_stack[1:] + [map_hex.unit_stack[0]]
							elif mouse.wheel_down:
								map_hex.unit_stack.insert(0, map_hex.unit_stack.pop(-1))
						self.UpdateUnitCon()
						self.UpdateUnitInfoCon()
						self.UpdateScenarioDisplay()
						continue
			
			
			##### Player Keyboard Commands #####
			
			# no keyboard input
			if not keypress: continue
			
			# game menu
			if key.vk == libtcod.KEY_ESCAPE:
				ShowGameMenu()
				continue
			
			# debug menu
			elif key.vk == libtcod.KEY_F2:
				if not DEBUG: continue
				ShowDebugMenu()
				continue
			
			# player not active
			if scenario.active_player == 1: continue
			
			# key commands
			key_char = DeKey(chr(key.c).lower())
			
			# Any Phase
			
			# advance to next phase
			if key.vk == libtcod.KEY_SPACE:
				self.advance_phase = True
				continue
			
			# Command Phase and Crew Action phase
			if self.phase in [PHASE_COMMAND, PHASE_CREW_ACTION]:
			
				# change selected crew position
				if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					
					if key_char == 'w' or key.vk == libtcod.KEY_UP:
						self.selected_position -= 1
						if self.selected_position < 0:
							self.selected_position = len(self.player_unit.positions_list) - 1
					
					else:
						self.selected_position += 1
						if self.selected_position == len(self.player_unit.positions_list):
							self.selected_position = 0
				
					self.UpdateContextCon()
					self.UpdateCrewInfoCon()
					self.UpdateCmdCon()
					self.UpdateGuiCon()
					self.UpdateScenarioDisplay()
					continue
			
			# command phase only
			if self.phase == PHASE_COMMAND:
			
				# change current command for selected crewman
				if key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
					
					# no crewman in selected position
					crewman = self.player_unit.positions_list[self.selected_position].crewman
					if crewman is None:
						continue
					
					PlaySoundFor(None, 'command_select')
					
					crewman.SelectCommand(key_char == 'a' or key.vk == libtcod.KEY_LEFT)
					
					self.player_unit.positions_list[self.selected_position].UpdateVisibleHexes()
					
					self.UpdateContextCon()
					self.UpdateCrewInfoCon()
					self.UpdateGuiCon()
					self.UpdateScenarioDisplay()
					continue
				
				# toggle hatch for selected crewman (not mapped)
				elif chr(key.c).lower() == 'h':
					
					# no crewman in selected position
					crewman = self.player_unit.positions_list[self.selected_position].crewman
					if crewman is None: continue
					
					if crewman.ToggleHatch():
						PlaySoundFor(crewman, 'hatch')
						self.player_unit.positions_list[self.selected_position].UpdateVisibleHexes()
						crewman.BuildCommandList()
						if crewman.current_cmd not in crewman.cmd_list:
							text = 'Command not allowed when crewman is '
							if crewman.ce:
								text += 'CE'
							else:
								text += 'BU'
							text += '.'
							ShowMessage(text)
							crewman.current_cmd = 'Spot'
						
						self.UpdateContextCon()
						self.UpdateCrewInfoCon()
						self.UpdateGuiCon()
						self.UpdateScenarioDisplay()
						continue
				
				# button or open up all hatches
				elif key_char == 'b':
					close_all = False
					for position in self.player_unit.positions_list:
						if position.crewman is None: continue
						if not position.hatch: continue
						if position.crewman.ce:
							close_all = True
							break
					
					for position in self.player_unit.positions_list:
						if position.crewman is None: continue
						
						if close_all and not position.crewman.ce: continue
						if not close_all and position.crewman.ce: continue
						
						if position.crewman.ToggleHatch():
							PlaySoundFor(position.crewman, 'hatch')
							position.UpdateVisibleHexes()
							position.crewman.BuildCommandList()
							if position.crewman.current_cmd not in position.crewman.cmd_list:
								position.crewman.current_cmd = 'Spot'
					self.UpdateContextCon()
					self.UpdateCrewInfoCon()
					self.UpdateGuiCon()
					self.UpdateScenarioDisplay()
					continue
				
				# set default hatch status and command
				elif key_char == 'x':
					# no crewman in selected position
					crewman = self.player_unit.positions_list[self.selected_position].crewman
					if crewman is None: continue
					
					# crewman is KIA
					if not crewman.alive: continue
					
					crewman.default_start = (crewman.ce, crewman.current_cmd)
					ShowMessage('Default hatch status and command set for this crewman.')
					continue
				
				# open crewman menu
				elif key_char == 'e':
					crewman = self.player_unit.positions_list[self.selected_position].crewman
					if crewman is None: continue
					crewman.ShowCrewmanMenu()
					self.UpdateCrewInfoCon()
					self.UpdateScenarioDisplay()
					continue
			
			# crew action phase only
			elif self.phase == PHASE_CREW_ACTION:
				
				if self.selected_position is None: continue
				position = self.player_unit.positions_list[self.selected_position]
				if position.crewman is None: continue
				
				# ready rack commands
				if position.crewman.current_cmd == 'Manage Ready Rack':
					
					# find the weapon that would be managed by this crewman
					rr_weapon = None
					for weapon in scenario.player_unit.weapon_list:
						if weapon.GetStat('type') != 'Gun': continue
						if weapon.GetStat('mount') is None: continue
						if weapon.GetStat('mount') != position.location: continue
						rr_weapon = weapon
						break
					if rr_weapon is None: continue
					
					# try to move a shell into or out of Ready Rack
					if key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
						
						if key_char == 'a' or key.vk == libtcod.KEY_LEFT:
							add_num = -1
						else:
							add_num = 1
						
						if rr_weapon.ManageRR(add_num):
							self.UpdateContextCon()
							self.UpdateScenarioDisplay()
						continue
					
					# cycle active ammo type
					elif key_char == 'c':
						
						if rr_weapon.CycleAmmo():
							self.UpdateContextCon()
							self.UpdateScenarioDisplay()
						continue
					
					# hotkeys: fill RR with a given ammo type
					elif key_char in ['t', 'g', 'b', 'n']:
						
						i = ['t', 'g', 'b', 'n'].index(key_char)
						if i > len(rr_weapon.stats['ammo_type_list']) - 1: continue
						
						# save current ammo type so we can switch back
						old_ammo_type = rr_weapon.ammo_type
						rr_weapon.ammo_type = rr_weapon.stats['ammo_type_list'][i]
						rr_weapon.ManageRR(rr_weapon.rr_size)
						rr_weapon.ammo_type = old_ammo_type	
						self.UpdateContextCon()
						self.UpdateScenarioDisplay()
						continue
					
			# Movement phase only
			elif scenario.phase == PHASE_MOVEMENT:
				
				# move forward/backward (may also end the phase)
				if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					self.MovePlayer(key_char == 'w' or key.vk == libtcod.KEY_UP)
					self.UpdateContextCon()
					self.UpdateUnitInfoCon()
					self.UpdateScenarioDisplay()
					continue
				
				# pivot hull
				elif key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
					self.PivotPlayer(key_char == 'd' or key.vk == libtcod.KEY_LEFT)
					self.UpdatePlayerInfoCon()
					self.UpdateContextCon()
					self.UpdateUnitInfoCon()
					self.UpdateScenarioDisplay()
					continue
				
				# attempt HD
				elif key_char == 'h':
					
					# already in HD position
					if len(self.player_unit.hull_down) > 0:
						if self.player_unit.hull_down[0] == self.player_unit.facing:
							ShowMessage('You are already Hull Down.')
							continue
					
					# set statuses and play sound
					self.player_unit.moving = True
					self.player_unit.ClearAcquiredTargets()
					PlaySoundFor(self.player_unit, 'movement')
					
					if self.player_unit.BreakdownCheck():
						ShowMessage('Your vehicle stalls, making you unable to move further.')
						self.advance_phase = True
						continue
					
					result = self.player_unit.CheckForHD(driver_attempt=True)
					if result:
						ShowMessage('You move into a Hull Down position')
					else:
						ShowMessage('You were unable to move into a Hull Down position')
					self.UpdatePlayerInfoCon()
					self.UpdateUnitInfoCon()
					self.UpdateScenarioDisplay()
					
					# check for extra move
					if self.player_unit.ExtraMoveCheck():
						ShowMessage('You have moved swiftly enough to take another move action.')
						continue
					self.advance_phase = True
					continue
				
				# reposition
				elif key_char == 'r':
					self.MovePlayer(False, reposition=True)
					self.UpdateUnitCon()
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
					continue
				
				# conceal/reveal self
				elif key_char == 'c':
					self.ConcealOrRevealPlayer()
					self.UpdateUnitCon()
					self.UpdateScenarioDisplay()
					libtcod.console_flush()
					continue
				
			# Shooting phase
			elif scenario.phase == PHASE_SHOOTING:
				
				# select player weapon or ammo type
				if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
					self.SelectWeapon(key_char == 's' or key.vk == libtcod.KEY_DOWN)
					self.UpdateGuiCon()
					self.UpdateContextCon()
					self.UpdateScenarioDisplay()
					continue
				
				# cycle player target
				elif key_char in ['a', 'd'] or key.vk in [libtcod.KEY_LEFT, libtcod.KEY_RIGHT]:
					self.CycleTarget(key_char == 'd' or key.vk == libtcod.KEY_RIGHT)
					self.UpdateGuiCon()
					self.UpdateContextCon()
					self.UpdateScenarioDisplay()
					continue
				
				# rotate turret
				elif key_char in ['q', 'e']:
					self.RotatePlayerTurret(key_char == 'e')
					self.UpdateContextCon()
					self.UpdateScenarioDisplay()
					continue
				
				# toggle ready rack use
				elif key_char == 'r':
					scenario.selected_weapon.using_rr = not scenario.selected_weapon.using_rr
					self.UpdateContextCon()
					self.UpdateScenarioDisplay()
					continue
				
				# player fires active weapon at selected target
				elif key_char == 'f':
					result = scenario.player_unit.Attack(scenario.selected_weapon,
						scenario.selected_weapon.selected_target)
					if result:
						self.UpdateUnitInfoCon()
						self.UpdateContextCon()
						self.UpdateScenarioDisplay()
					continue




# Session: stores data that is generated for each game session and not stored in the saved game
class Session:
	def __init__(self):
		
		# dictionary for game's local copy of current user stats
		self.user_stats = {}
		
		# flag for when player is exiting from game
		self.exiting = False
		
		# flag: the last time the keyboard was polled, a key was pressed
		self.key_down = False
		
		# load debug flags if in debug mode
		self.debug = {}
		if DEBUG:
			try:
				with open(DATAPATH + 'debug.json', encoding='utf8') as data_file:
					self.debug = json.load(data_file)
			except:
				print('ERROR: Game is running in debug mode but no debug settings file was found!')
				sys.exit()
		
		# store player crew command defintions
		with open(DATAPATH + 'crew_command_defs.json', encoding='utf8') as data_file:
			self.crew_commands = json.load(data_file)
		
		# load and store nation definition info
		with open(DATAPATH + 'nation_defs.json', encoding='utf8') as data_file:
			self.nations = json.load(data_file)
		# run through nations and load national flag images
		self.flags = {}
		for nation_name, data in self.nations.items():
			self.flags[nation_name] = LoadXP(data['flag_image'])
			# some nations inherit data from others
			if 'inherit' in data:
				[inherit_from, field_list] = data['inherit']
				for field_name in field_list:
					if field_name in self.nations[inherit_from]:
						data[field_name] = self.nations[inherit_from][field_name]
		
		# load background for attack console
		self.attack_bkg = LoadXP('attack_bkg.xp')
		
		# field of view highlight on scenario hex map
		self.scen_hex_fov = LoadXP('scen_hex_fov.xp')
		libtcod.console_set_key_color(self.scen_hex_fov, KEY_COLOR)
		
		# animation timer, used by both the campaign day and the scenario object
		self.anim_timer = 0.0
		
		# pop-up message console
		self.msg_con = None
		self.msg_location = None
		
		# unit types
		with open(DATAPATH + 'unit_type_defs.json', encoding='utf8') as data_file:
			self.unit_types = json.load(data_file)
		
		# check for modded unit types
		for filename in os.listdir(MODPATH):
			if not filename.endswith('.json'): continue
			try:
				# try to load and add the modded units to the master list
				with open(MODPATH + filename, encoding='utf8') as data_file:
					mod_data = json.load(data_file)
					for k, v in mod_data.items():
						self.unit_types[k] = v
				print('Mod loaded: ' + filename)
				
			except Exception as e:
				ShowNotification('Error: Unable to parse modded unit file ' + filename + ': ' +
					str(e))
				continue
		
		# tank portrait for main menu
		self.tank_portrait = None
		for tries in range(300):
			unit_id = choice(list(self.unit_types.keys()))
			if 'portrait' not in self.unit_types[unit_id]: continue
			if self.unit_types[unit_id]['class'] not in ['Tankette', 'Light Tank', 'Medium Tank', 'Heavy Tank', 'Tank Destroyer']: continue
			if not os.path.exists(DATAPATH + self.unit_types[unit_id]['portrait']): continue
			self.tank_portrait = LoadXP(self.unit_types[unit_id]['portrait'])
			break
		
		# campaign day map player unit animation offset
		self.cd_x_offset = 0
		self.cd_y_offset = 0
		
		# try to load morgue file, create if it doesn't exist yet
		if not os.path.exists(DATAPATH + 'morguefile.dat'):
			self.morgue = []
			with shelve.open(DATAPATH + 'morguefile', 'n') as save:
				save['morgue'] = self.morgue
		else:
			with shelve.open(DATAPATH + 'morguefile') as save:
				self.morgue = save['morgue']
	
	
	# modify a Steam user stat, and upload all current stats to the Steam servers
	def ModifySteamStat(self, stat_name, amount):
		if not steam_active: return
		
		steamworks.UserStats.RequestCurrentStats()
		steamworks.run_callbacks()
		value = steamworks.UserStats.GetStatInt(stat_name.encode('ascii'))
		
		#if DEBUG:
		#	print('DEBUG: Current Steam stat ' + stat_name + ' value: ' + str(value))
		
		if not steamworks.UserStats.SetStat(stat_name.encode('ascii'), value + amount):
			print('ERROR: Could not set Steam user stat ' + stat_name + '!')
			return
		
		steamworks.UserStats.StoreStats()
		steamworks.run_callbacks()
		#if DEBUG:
		#	print('DEBUG: Set Steam stat ' + stat_name + ' to: ' + str(value + amount))
		
	
	# update morguefile with a new entry and save
	def UpdateMorguefile(self, entry):
		self.morgue.append(entry)
		self.morgue.sort(key=lambda tup: tup[2], reverse=True)
		with shelve.open(DATAPATH + 'morguefile', 'n') as save:
			save['morgue'] = self.morgue
	
	
	# try to initialize SDL2 mixer
	def InitMixer(self):
		mixer.Mix_Init(mixer.MIX_INIT_OGG)
		if mixer.Mix_OpenAudio(48000, mixer.MIX_DEFAULT_FORMAT,	2, 1024) == -1:
			return False
		mixer.Mix_AllocateChannels(32)
		self.SetMasterVolume(config['ArmCom2'].getint('master_volume'))
		return True
	
	
	# load the main theme music
	def LoadMainTheme(self):
		global main_theme
		main_theme = mixer.Mix_LoadMUS((SOUNDPATH + 'armcom2_theme.ogg').encode('ascii'))


	# set the master volume for sound effects (1-10)
	def SetMasterVolume(self, new_volume):
		mixer.Mix_Volume(-1, new_volume * 12)
		mixer.Mix_VolumeMusic(new_volume * 6)




# Personnel Class: represents an individual person within a unit 
class Personnel:
	def __init__(self, unit, nation, position):
		self.unit = unit				# pointer to which unit they belong
		self.nation = nation				# nationality of person
		self.is_player_commander = False		# represents a Player Commander
		self.current_position = position		# pointer to current position in a unit
		
		self.default_start = None			# default hatch status and command at start of scenario
		
		# core data
		self.alive = True				# is crewman alive or not
		self.fatigue = BASE_FATIGUE			# current crew fatigue points
		self.condition = 'Good Order'			# current mental and physical condition
		self.injury = {					# injuries to different body system
			'Head & Neck' : None,
			'Torso & Groin' : None,
			'Right Arm & Hand' : None,
			'Left Arm & Hand' : None,
			'Right Leg & Foot' : None,
			'Left Leg & Foot' : None
		}
		self.field_hospital = None			# crewman must be send to field hospital if set
		
		self.first_name = ''				# placeholders for first and last name
		self.last_name = ''				#   set by GenerateName()
		self.GenerateName()				# generate random first and last name
		self.nickname = ''				# player-set nickname
		self.age = 20					# age in years
		self.rank = 0					# rank level
		
		self.stats = {					# default stat values
			'Perception' : 1,			# used for spotting enemy units
			'Grit' : 1,				# reduced chance of injury or condition getting worse
			'Knowledge' : 1,			# increases rate of XP gain
			'Morale' : 1				# resist fatigue and recover from negative condition
		}
		
		# randomly increase two stats to 3
		for i in sample(range(3), 2):
			self.stats[CREW_STATS[i]] = 3
		
		self.skills = []				# list of skills
		
		# check for national skills
		if self.unit == campaign.player_unit:
			if 'campaign_skills' in campaign.stats:
				for skill in campaign.stats['campaign_skills']:
					if 'position_list' in campaign.skills[skill]:
						if self.current_position.name not in campaign.skills[skill]['position_list']:
							continue
					self.skills.append(skill)
		
		# check for skill effects on stats
		for skill in self.skills:
			if skill in ['Defend the Motherland', 'Imperial Ambitions']:
				self.stats['Morale'] += 3
			elif skill == 'To Victory!':
				self.stats['Grit'] += 3
			elif skill == 'Audacia':
				self.stats['Perception'] += 3
			elif skill == 'Baptism of Fire':
				self.stats['Knowledge'] += 3
		
		# check for position training skills
		if self.current_position is not None:
			if self.current_position.name == 'Commander':
				self.skills.append('Experienced Commander')
				self.skills.append('Trained Gunner')
				self.skills.append('Trained Driver')
			elif self.current_position.name == 'Commander/Gunner':
				self.skills.append('Experienced Commander')
				self.skills.append('Experienced Gunner')
				self.skills.append('Trained Driver')
			elif self.current_position.name in ['Gunner', 'Gunner/Loader']:
				self.skills.append('Experienced Gunner')
				self.skills.append('Trained Driver')
			elif self.current_position.name in ['Driver']:
				self.skills.append('Experienced Driver')
		
		# current level, exp, and advance points
		self.level = 1
		self.exp = 0
		self.adv = 1
		
		# commanders start higher
		if self.current_position is not None:
			if self.current_position.name in ['Commander', 'Commander/Gunner']:
				self.level = 4
				self.exp = GetExpRequiredFor(self.level)
				self.adv = 4
				self.age += libtcod.random_get_int(0, 3, 9)
				self.rank = 2
			
			# gunners a little higher
			elif self.current_position.name in ['Gunner', 'Gunner/Loader']:
				self.level = 2
				self.exp = GetExpRequiredFor(self.level)
				self.adv = 2
				self.age += libtcod.random_get_int(0, 2, 5)
				self.rank = 1
		
		# give current age, set random birthday
		year = int(campaign.today.split('.')[0].lstrip('0')) - self.age
		month = libtcod.random_get_int(0, 1, 12)
		day = libtcod.random_get_int(0, 1, monthrange(year, month)[1])
		self.birthday = str(year) + '.' + str(month).zfill(2) + '.' + str(day).zfill(2)
		
		# exposed / buttoned up status
		self.ce = False					# crewman is exposed in a vehicle
		self.SetCEStatus()				# set CE status
		
		self.cmd_list = []				# list of possible commands
		self.current_cmd = 'Spot'			# currently assigned command in scenario
		
		self.action_list = [('None', 0.0)]		# list of possible actions, eg. in bail-out
		self.current_action = self.action_list[0]	# currently assigned action
	
	
	# re-calculate crewman age based on current day in campaign calendar
	def CalculateAge(self):
		(year1, month1, day1) = self.birthday.split('.')
		(year2, month2, day2) = campaign.today.split('.')
		self.age = int(year2) - int(year1)
		if int(month2) >= int(month1):
			if int(day2) >= int(day1):
				self.age += 1
		
	
	# return the crewman's full name
	def GetName(self):
		return self.first_name + ' ' + self.last_name
	
	
	# resolve current injuries - called at end of campaign day
	def ResolveInjuries(self):
		
		hospital_min = 0
		hospital_max = 0
		hospital_chance = 0.0
		
		# run through injuries
		for (k, v) in self.injury.items():
			if v is None: continue
			
			if v == 'Heavy':
				hospital_chance += 50.0
				if hospital_min == 0:
					hospital_min = 3
				else:
					hospital_min += libtcod.random_get_int(0, 0, 1)
				if hospital_max < 7:
					hospital_max = 7
				else:
					hospital_max += libtcod.random_get_int(0, 0, 2)
			
			elif v == 'Serious':
				hospital_chance += 80.0
				if hospital_min < 7:
					hospital_min = 7
				else:
					hospital_min += libtcod.random_get_int(0, 2, 4)
				if hospital_max < 21:
					hospital_max = 21
				else:
					hospital_max += libtcod.random_get_int(0, 2, 4)
		
		# crewman grit effect
		grit_effect = int(self.stats['Grit'] / 2)
		if hospital_min > 0:
			hospital_min -= libtcod.random_get_int(0, 0, grit_effect)
			if hospital_min < 0:
				hospital_min = 0
		if hospital_max > 0:
			hospital_max -= libtcod.random_get_int(0, 0, grit_effect)
			if hospital_max < 0:
				hospital_max = 0
		if hospital_min > hospital_max:
			hospital_min = hospital_max
		
		if hospital_chance > 97.0:
			hospital_chance = 97.0
		
		# injuries require field hospital roll
		if hospital_min != 0 and hospital_max != 0:
			roll = GetPercentileRoll()
			
			if roll <= hospital_chance:
				self.field_hospital = (hospital_min, hospital_max)
			else:
				self.field_hospital = None
		
		# clear injuries
		# show a message when a crewman recovers from an injury, and is not headed to the hospital
		for k in self.injury.keys():
			
			if self.injury[k] is None: continue
			
			if self.field_hospital is None:
				text = 'Your crewman recovers from his ' + self.injury[k] + ' ' + k + ' injury:'
				ShowMessage(text, crewman=self)
			self.injury[k] = None
		
	
	# returns true if this crewmen is currently working a position for which they lack training
	# only used for player for now
	def UntrainedPosition(self):
		if self.unit != campaign.player_unit: return False
		
		# check for required skills
		if self.current_position.name == 'Commander':
			if 'Trained Commander' not in self.skills and 'Experienced Commander' not in self.skills:
				return True
		if self.current_position.name == 'Commander/Gunner':
			if 'Trained Commander' not in self.skills and 'Experienced Commander' not in self.skills:
				return True
			if 'Trained Gunner' not in self.skills and 'Experienced Gunner' not in self.skills:
				return True
		if self.current_position.name in ['Gunner', 'Gunner/Loader']:
			if 'Trained Gunner' not in self.skills and 'Experienced Gunner' not in self.skills:
				return True
		if self.current_position.name in ['Driver']:
			if 'Trained Driver' not in self.skills and 'Experienced Driver' not in self.skills:
				return True
		
		return False
		
	
	# resolve an incoming attack on this personnel
	# returns a string if there was a change in injury or status, otherwise returns None
	def ResolveAttack(self, attack_profile, explosion=False, show_messages=True):
		
		# randomly determine body location hit
		def GetHitLocation(attack_profile):
			
			roll = GetPercentileRoll()
			
			# location modifiers for sniper attack or landmine hit
			if 'sniper' in attack_profile:
				roll -= 21.0
			elif 'landmine' in attack_profile:
				roll += 16.0
			
			if roll <= 15.0:
				return 'Head & Neck'
			elif roll <= 50.0:
				return 'Torso & Groin'
			elif roll <= 65.0:
				return 'Right Arm & Hand'
			elif roll <= 80.0:
				return 'Left Arm & Hand'
			elif roll <= 90.0:
				return 'Right Leg & Foot'
			return 'Left Leg & Foot'
			
		
		# crewman is already dead, can't get worse
		if not self.alive:
			return None
		
		# check for debug flag here
		if DEBUG:
			if 'ko_hit' in attack_profile and session.debug['Player Crew Safe in Bail Out']:
				return None
		
		# don't show messages if this is not the player unit
		if self.unit != scenario.player_unit:
			show_messages = False
		
		# final injury roll modifier
		modifier = 0
		
		# exposed to a firepower attack
		if 'firepower' in attack_profile:
			
			# currently in an armoured vehicle
			if self.unit.GetStat('armour') is not None:
				
				# not exposed
				if not self.ce:
					return None
				
				# unconscious crewman are assumed to be slumped down and are protected
				if self.condition == 'Unconscious':
					return None
			
			# determine chance of injury based on total incoming firepower
			fp = attack_profile['firepower']
			
			if fp <= 2:
				modifier -= 45.0
			elif fp <= 4:
				modifier -= 25.0
			elif fp <= 6:
				modifier -= 5.0
			elif fp <= 8:
				modifier += 15.0
			elif fp <= 10:
				modifier += 25.0
			elif fp <= 12:
				modifier += 30.0
			else:
				modifier += 35.0
			
			if campaign.options['realistic_injuries']:
				modifier += 20.0
		
		# spalling
		elif 'spalling' in attack_profile:
			if not campaign.options['realistic_injuries']:
				modifier -= (libtcod.random_get_int(0, 1, 40) * 1.0)
		
		# initial KO hit on vehicle
		elif 'ko_hit' in attack_profile:
			
			# if tank exploded and Realistic Explosions campaign option is active, automatic KIA
			if explosion and campaign.options['explosion_kills']:
				self.KIA()
				return 'KIA'
			
			# additional risk if attack was close combat and crewman is CE
			if attack_profile['weapon'] is not None:
				if attack_profile['weapon'].GetStat('type') == 'Close Combat' and self.ce:
					modifier += 25.0
			
			# additional risk if in area of tank that was hit
			if attack_profile['location'] is not None and self.current_position.location is not None:
				if attack_profile['location'] == self.current_position.location:
					modifier += 20.0
			
			# tank explosion modifier
			if explosion:
				modifier += 80.0
			
			else:
			
				# additional risk from extra ammo from each gun
				for weapon in campaign_day.gun_list:
					total_ammo = 0
					for ammo_type in AMMO_TYPES:
						if ammo_type in weapon.ammo_stores:
							total_ammo += weapon.ammo_stores[ammo_type]
					
					if total_ammo > weapon.max_ammo:
						if weapon.stats['calibre'] is not None:
							if int(weapon.stats['calibre']) <= 37:
								mod = 1.0 * (total_ammo - weapon.max_ammo)
							else:
								mod = 2.0 * (total_ammo - weapon.max_ammo)
							modifier += mod
		
		# part of bail-out - caught in burning vehicle
		elif 'burn_up' in attack_profile:
			modifier += (libtcod.random_get_int(0, 1, 4) * 5.0)
		
		# landmine hit
		elif 'landmine' in attack_profile:
			modifier = -20.0
		
		# skill checks
		if 'firepower' in attack_profile:
			if self.condition != 'Unconscious':
				if 'Lightning Reflexes' in self.skills:
					modifier = round(modifier * 0.75, 1)
				elif 'Quick Reflexes' in self.skills:
					modifier = round(modifier * 0.90, 1)
		
		# crewman grit modifier
		modifier -= self.stats['Grit'] * 3.0
		
		# shaken modifier
		if self.condition == 'Shaken':
			modifier += 15.0
		
		# do injury roll
		roll = GetPercentileRoll()
		
		# check for debug flag
		if DEBUG:
			if session.debug['Player Crew Hapless']:
				roll = 100.0
		
		# unmodified high roll always counts as KIA, otherwise modifier is applied
		if roll <= 99.5: roll += modifier
		
		# determine location
		location = GetHitLocation(attack_profile)
		
		# if crewman is exposed in an AFV and leg/foot location is rolled, no effect
		if 'firepower' in attack_profile and location in ['Right Leg & Foot', 'Left Leg & Foot']:
			return None
		
		# determine effect
		
		# miss - no effect
		if roll < 35.0:
			return None
		
		# near miss - possible change in condition
		elif roll <= 45.0:
			if self.condition != 'Good Order': return None
			if self.DoMoraleCheck(0.0): return None
			self.condition = 'Shaken'
			if show_messages:
				if self.current_position.name in PLAYER_POSITIONS:
					ShowMessage('You had a near miss and are now Shaken.')
				else:
					ShowMessage('Your crewman had a near miss and is now Shaken:', crewman=self)
			return 'Shaken'
		
		# grazing hit, no injury but possible stun
		elif roll <= 65.0:
			if self.condition not in ['Good Order', 'Stunned']:
				if show_messages:
					if self.current_position.name in PLAYER_POSITIONS:
						ShowMessage('You suffer a grazing hit but are no worse for wear.')
					else:
						ShowMessage('Your crewman suffers a grazing hit but is no worse for wear:', crewman=self)
				return None
			if self.DoMoraleCheck(0.0):
				self.condition = 'Shaken'
				self.DoFatigueCheck()
				if show_messages:
					if self.current_position.name in PLAYER_POSITIONS:
						ShowMessage('You suffer a grazing hit and are now Shaken.')
					else:
						ShowMessage('Your crewman suffers a grazing hit and is now Shaken:', crewman=self)
				return 'Shaken'
			else:
				self.condition = 'Stunned'
				self.DoFatigueCheck()
				if show_messages:
					if self.current_position.name in PLAYER_POSITIONS:
						ShowMessage('You suffer a grazing hit and are now Stunned.')
					else:
						ShowMessage('Your crewman suffers a grazing hit and is now Stunned:', crewman=self)
				return 'Stunned'
		
		# hit in a non-critical location
		elif roll <= 80.0:
			injury_roll = GetPercentileRoll()
			if injury_roll <= 50.0:
				injury = 'Light'
			elif injury_roll <= 80.0:
				injury = 'Heavy'
			else:
				injury = 'Serious'
			
		# hit in a possibly critical location
		elif roll <= 90.0:
			injury_roll = GetPercentileRoll()
			if injury_roll <= 40.0:
				injury = 'Light'
			elif injury_roll <= 60.0:
				injury = 'Heavy'
			elif injury_roll <= 85.0:
				injury = 'Serious'
			else:
				injury = 'Critical'
		
		# critical injury
		elif roll <= 98.9:
			injury = 'Critical'
		
		# KIA
		else:
			
			# check for fate point use
			if self.is_player_commander and campaign_day.fate_points > 0:
				campaign_day.fate_points -= 1
				return None
			
			self.KIA()
			
			if self.is_player_commander:
				text = 'You have been hit in the ' + location + ' and killed. Your campaign is over.'
				if show_messages: ShowMessage(text)
				campaign.AddJournal(text)
			else:
				text = 'Your crewman has been hit in the ' + location + ' and killed:'
				if show_messages: ShowMessage(text, crewman=self)
				campaign.AddJournal(text)
			
			return 'KIA'
		
		# apply injury
		
		injury_change = False
		# no previous injury in this location
		if self.injury[location] is None:
			self.injury[location] = injury
			injury_change = True
		else:
			# light injury: chance of worsening to Heavy
			if injury == 'Light':
				if self.injury[location] == 'Light':
					if GetPercentileRoll() <= 50.0:
						self.injury[location] = 'Heavy'
						injury_change = True
			
			# heavy injury: chance of worsening to Serious
			elif injury == 'Heavy':
				if self.injury[location] == 'Light':
					self.injury[location] = 'Heavy'
					injury_change = True
				elif self.injury[location] == 'Heavy':
					if GetPercentileRoll() <= 50.0:
						self.injury[location] = 'Serious'
						injury_change = True
			
			# serious injury
			elif injury == 'Serious':
				if self.injury[location] in ['Light', 'Heavy']:
					self.injury[location] = 'Serious'
					injury_change = True
				elif self.injury[location] == 'Serious':
					if GetPercentileRoll() <= 50.0:
						self.injury[location] = 'Critical'
						injury_change = True
			
			# critical injury
			elif injury == 'Critical':
				if self.injury[location] != 'Critical':
					self.injury[location] = 'Critical'
					injury_change = True
		
		if injury_change:
			self.DoFatigueCheck()
			if self.current_position.name in PLAYER_POSITIONS:
				text = 'You were hit in the ' + location + ' and suffer a ' + injury + ' injury.'
			else:
				text = 'Your crewman was hit in the ' + location + ' and suffers a ' + injury + ' injury:'
		else:
			if self.current_position.name in PLAYER_POSITIONS:
				text = 'You were hit in the ' + location + ' but suffer no further injury.'
			else:
				text = 'Your crewman was hit in the ' + location + ' but suffers no further injury:'
		if show_messages:
			if self.current_position.name not in PLAYER_POSITIONS:
				ShowMessage(text, crewman=self)
			else:
				ShowMessage(text)
		campaign.AddJournal(text)
		
		if not injury_change:
			return injury + ' injury'
		
		# check for condition change (to Shaken, Stunned, or Unconscious) as a result of injury
		condition_change = None
		if location == 'Head & Neck':
			if not self.DoGritCheck(20.0):
				condition_change = 'Stunned'
			elif not self.DoGritCheck(0.0):
				condition_change = 'Unconscious'
			else:
				condition_change = 'Shaken'
		
		elif location == 'Torso & Groin':
			if not self.DoGritCheck(15.0):
				condition_change = 'Stunned'
			elif not self.DoGritCheck(-10.0):
				condition_change = 'Unconscious'
		
		if condition_change is None:
			return injury + ' injury'
		
		if condition_change == 'Shaken' and self.condition != 'Good Order': return injury + ' injury'
		if condition_change == 'Stunned' and self.condition in ['Stunned', 'Unconscious']: return injury + ' injury'
		if condition_change == 'Unconscious' and self.condition == 'Unconscious': return injury + ' injury'
		
		self.condition = condition_change
		
		if self.current_position.name in PLAYER_POSITIONS:
			text = 'As a result of your injury, you are now ' + condition_change + '.'
		else:
			# bit of a kludge, but prevents a crash during the bailout procedure
			if self.current_position.name is None:
				text = 'As a result of injury, your crewman is now ' + condition_change + '.'
			else:
				text = 'As a result of injury, your ' + self.current_position.name + ' is now ' + condition_change + '.'
		if show_messages:
			ShowMessage(text)
		campaign.AddJournal(text)
		return injury + ' injury, ' + condition_change
	
	
	# do a grit test for this crewman
	def DoGritCheck(self, modifier):
		if GetPercentileRoll() + modifier <= self.stats['Grit'] * 9.0: return True
		return False
		
	
	# do a morale check for this crewman
	def DoMoraleCheck(self, modifier):
		if self.unit.is_player:
			if 'Natural Leader' not in self.skills and campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Natural Leader'):
				modifier -= 15.0
		if GetPercentileRoll() + modifier <= self.stats['Morale'] * 9.0: return True
		return False
	
	
	# do a stun check for this crewman
	def DoStunCheck(self, modifier):
		if self.condition not in ['Good Order', 'Shaken']: return True
		if GetPercentileRoll() + modifier <= self.stats['Grit'] * 9.0: return True
		return False
	
	
	# check for change in condition or injury status, called at start of turn
	def DoInjuryCheck(self, condition_only=False):
		
		# no need to check
		if not self.alive: return
		
		# check for critical injuries either stabilizing or causing death
		for (k, v) in self.injury.items():
			if v is None: continue
			if v != 'Critical': continue
			
			roll = GetPercentileRoll()
			
			# injury worsens and causes death
			if roll > 97.0:
				
				self.KIA()
				if self.is_player_commander:
					text = 'You succumb to your ' + k + ' injury and die. Your campaign is over.'
					ShowMessage(text)
					campaign.AddJournal(text)
				else:
					text = 'Your crewman succumbed to their ' + k + ' injury and has died:'
					ShowMessage(text, crewman=self)
					campaign.AddJournal(text)
				return
			
			# injury may improve
			# check for fellow crewmen on First Aid command
			for position in self.unit.positions_list:
				if position.crewman is None: continue
				if position.crewman == self: continue
				if position.crewman.current_cmd == 'First Aid':
					roll -= 15.0
			
			if self.condition == 'Unconscious': roll += 15.0
			
			if roll <= self.stats['Grit'] * 9.0:
				self.injury[k] = 'Serious'
				if self.current_position.name in PLAYER_POSITIONS:
					text = 'Your ' + k + ' injury has stabilized and is now Serious.'
					ShowMessage(text)
					campaign.AddJournal(text)
				else:
					text = "Your crewman's " + k + ' injury has stabilized and is now Serious:'
					ShowMessage(text, crewman=self)
					campaign.AddJournal(text)
			
		# check for recovery from negative conditions
		if self.condition == 'Good Order': return
		
		if self.condition == 'Shaken':
			if self.DoMoraleCheck(0.0):
				self.condition = 'Good Order'
				if self.current_position.name in PLAYER_POSITIONS:
					text = 'You recover from being Shaken.'
					ShowMessage(text)
				else:
					text = 'Your crewman recovers from being Shaken:'
					ShowMessage(text, crewman=self)
			return
		
		if self.condition == 'Stunned':
			if self.DoMoraleCheck(15.0):
				self.condition = 'Good Order'
				if self.current_position.name in PLAYER_POSITIONS:
					text = 'You recover from being Stunned.'
					ShowMessage(text)
				else:
					text = 'Your crewman recovers from being Stunned:'
					ShowMessage(text, crewman=self)
			return
		
		if self.condition == 'Unconscious':
			if self.DoGritCheck(25.0):
				self.condition = 'Stunned'
				if self.current_position.name in PLAYER_POSITIONS:
					text = 'You regain consciousness and are now Stunned.'
					ShowMessage(text)
				else:
					text = 'Your crewman regains consciousness and is now Stunned:'
					ShowMessage(text, crewman=self)
			return
		
	
	# crewman dies
	def KIA(self):
		self.alive = False
		self.condition = 'Dead'
		self.fatigue = 0
		
		# check for player commander death
		if self.is_player_commander:
			scenario.finished = True
			campaign_day.ended = True
			campaign.ended = True
			campaign.player_oob = True
		
		# rest of player crew may be shaken
		elif self.unit.is_player:
			
			for position in self.unit.positions_list:
				if position.crewman is None: continue
				if not position.crewman.alive: continue
				if position.crewman.condition != 'Good Order': continue
				if position.crewman.DoMoraleCheck(-50): continue
				position.crewman.condition = 'Shaken'
				# don't show message if during bail-out
				if self.unit.alive:
					ShowMessage('Your crewman is Shaken by the loss of a crewmate:',crewman=position.crewman)
	
	
	# award a number of exp to this crewman, modified by Knowledge stat
	def AwardExp(self, exp):
		exp = int(float(exp) * EXP_MULTIPLIER)
		exp += int(float(exp) * (float(self.stats['Knowledge']) / 10.0))
		self.exp += exp


	# check to see whether crewman is promoted, called for player crew once per week
	def PromotionCheck(self):
		
		if self.rank == 6: return
		
		for (k, v) in LEVEL_RANK_LIST.items():
			if int(k) <= self.level:
				if v > self.rank:
					if GetPercentileRoll() <= PROMOTION_CHANCE:
						self.rank = v
						text = ('Your crewman has been promoted to ' +
							session.nations[self.nation]['rank_names'][str(self.rank)] + '!')
						text += ' They also receive 2 advance points.'
						ShowMessage(text,crewman=self)
						self.adv += 2
					
					# don't check again this week
					return
	
	
	# display a menu for this crewman, used for members of player's unit
	def ShowCrewmanMenu(self):
		
		# update the crewman menu console
		def UpdateCrewmanMenuCon():
			libtcod.console_clear(crewman_menu_con)
			
			# frame and section dividers
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.grey)
			libtcod.console_hline(crewman_menu_con, 8, 48, 74)
			DrawFrame(crewman_menu_con, 8, 0, 74, 60)
			DrawFrame(crewman_menu_con, 29, 0, 32, 49)
			libtcod.console_hline(crewman_menu_con, 30, 4, 30)
			libtcod.console_hline(crewman_menu_con, 30, 6, 30)
			libtcod.console_hline(crewman_menu_con, 30, 8, 30)
			libtcod.console_hline(crewman_menu_con, 30, 10, 30)
			libtcod.console_hline(crewman_menu_con, 30, 12, 30)
			libtcod.console_hline(crewman_menu_con, 30, 15, 30)
			libtcod.console_hline(crewman_menu_con, 30, 20, 30)
			libtcod.console_hline(crewman_menu_con, 30, 23, 30)
			#libtcod.console_hline(crewman_menu_con, 61, 23, 20)
			
			# main title and decorations
			libtcod.console_set_default_background(crewman_menu_con, libtcod.darker_blue)
			libtcod.console_rect(crewman_menu_con, 30, 1, 30, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(crewman_menu_con, libtcod.black)
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.lightest_blue)
			libtcod.console_print(crewman_menu_con, 38, 2, 'Crewman Report')
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.yellow)
			for y in range(1, 4):
				for x in [31, 32]:
					libtcod.console_put_char(crewman_menu_con, x, y, 174)
					libtcod.console_put_char(crewman_menu_con, x+26, y, 175)
			
			# section titles
			libtcod.console_set_default_foreground(crewman_menu_con, TITLE_COL)
			libtcod.console_print(crewman_menu_con, 30, 5, 'Name')
			libtcod.console_print(crewman_menu_con, 30, 7, 'Nickname')
			libtcod.console_print(crewman_menu_con, 30, 9, 'Age')
			libtcod.console_print(crewman_menu_con, 30, 11, 'Rank')
			libtcod.console_print(crewman_menu_con, 30, 13, 'Current')
			libtcod.console_print(crewman_menu_con, 30, 14, 'Position')
			libtcod.console_print(crewman_menu_con, 30, 16, 'Stats')
			libtcod.console_print(crewman_menu_con, 30, 21, 'Status')
			libtcod.console_print(crewman_menu_con, 30, 22, 'Fatigue')
			libtcod.console_print(crewman_menu_con, 30, 24, 'Skills')
			
			# name
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
			if self.is_player_commander:
				libtcod.console_set_default_foreground(crewman_menu_con, libtcod.gold)
			PrintExtended(crewman_menu_con, 39, 5, self.GetName())
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
			
			# nickname if any
			if self.nickname == '':
				text = '[None]'
			else:
				text = self.nickname
			libtcod.console_print(crewman_menu_con, 39, 7, text)
			
			# age, birthday and rank
			libtcod.console_print(crewman_menu_con, 39, 9, str(self.age))
			libtcod.console_print_ex(crewman_menu_con, 59, 9, libtcod.BKGND_NONE,
				libtcod.RIGHT, '(' + self.birthday + ')')
			libtcod.console_print(crewman_menu_con, 39, 11, session.nations[self.nation]['rank_names'][str(self.rank)])
			
			
			# current unit and position if any
			if self.field_hospital is not None:
				libtcod.console_print(crewman_menu_con, 39, 13, 'Field Hospital')
			else:
				if not self.unit.alive:
					libtcod.console_print(crewman_menu_con, 39, 13, 'None')
				else:
					libtcod.console_print(crewman_menu_con, 39, 13, self.unit.unit_id)
					if self.current_position.name is not None:
						if self.UntrainedPosition():
							libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_red)
						libtcod.console_print(crewman_menu_con, 39, 14, self.current_position.name)
						libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
			
			# stats
			libtcod.console_put_char_ex(crewman_menu_con, 39, 16, chr(4), libtcod.yellow, libtcod.black)
			libtcod.console_put_char_ex(crewman_menu_con, 39, 17, chr(3), libtcod.red, libtcod.black)
			libtcod.console_put_char_ex(crewman_menu_con, 39, 18, chr(5), libtcod.blue, libtcod.black)
			libtcod.console_put_char_ex(crewman_menu_con, 39, 19, chr(6), libtcod.green, libtcod.black)
			
			y = 16
			for t in CREW_STATS:
				libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
				libtcod.console_print(crewman_menu_con, 41, y, t)
				libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_grey)
				libtcod.console_print_ex(crewman_menu_con, 53, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(self.stats[t]))
				y += 1
			
			libtcod.console_set_default_background(crewman_menu_con, libtcod.darkest_grey)
			libtcod.console_rect(crewman_menu_con, 39, 17, 15, 1, False, libtcod.BKGND_SET)
			libtcod.console_rect(crewman_menu_con, 39, 19, 15, 1, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(crewman_menu_con, libtcod.black)
			
			# current condition and fatigue level
			libtcod.console_print(crewman_menu_con, 39, 21, self.condition)
			if self.fatigue <= 0:
				libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_grey)
				text = '-'
			else:
				libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_red)
				text = '-' + str(self.fatigue) + '%'
			libtcod.console_print(crewman_menu_con, 39, 22, text)
			
			# list of crew skills
			y = 24
			number_of_skills = 0
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
			for skill in self.skills:
				libtcod.console_print(crewman_menu_con, 37, y, skill)
				y += 1
				number_of_skills += 1
			if self.alive and self.field_hospital is None:
				libtcod.console_print(crewman_menu_con, 37, y, '[Add New Skill]')
			
			# highlight selected skill
			if self.alive and self.field_hospital is None:
				libtcod.console_set_default_background(crewman_menu_con, HIGHLIGHT_MENU_COL)
				libtcod.console_rect(crewman_menu_con, 37, 24 + selected_skill, 23, 1, False, libtcod.BKGND_SET)
				libtcod.console_set_default_background(crewman_menu_con, libtcod.black)
			
			# display info about selected skill or info about adding a new skill
			#libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_grey)
			y = 24
			if not self.alive or self.field_hospital is not None:
				text = ''
			elif selected_skill == number_of_skills:
				text = 'Select this option to spend an advance point and add a new skill'
			else:
				# grab skill description from campaign.skills dictionary
				text = campaign.skills[self.skills[selected_skill]]['desc']
				
				if 'campaign_skill' in campaign.skills[self.skills[selected_skill]]:
					text += ' (Campaign Skill)'
				
			for line in wrap(text, 18):
				libtcod.console_print(crewman_menu_con, 62, y, line)
				y+=1	
			
			# current level, exp, points
			libtcod.console_set_default_background(crewman_menu_con, libtcod.darkest_grey)
			libtcod.console_rect(crewman_menu_con, 35, 45, 21, 3, False, libtcod.BKGND_SET)
			libtcod.console_set_default_background(crewman_menu_con, libtcod.black)
			
			libtcod.console_set_default_foreground(crewman_menu_con, TITLE_COL)
			libtcod.console_print(crewman_menu_con, 35, 45, 'Level')
			libtcod.console_print(crewman_menu_con, 35, 46, 'Exp')
			libtcod.console_print(crewman_menu_con, 35, 47, 'Advance Points')
			
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
			libtcod.console_print_ex(crewman_menu_con, 55, 45, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(self.level))
			libtcod.console_print_ex(crewman_menu_con, 55, 46, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(self.exp))
			libtcod.console_print_ex(crewman_menu_con, 55, 47, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(self.adv))
			
			# injuries if any
			if self.alive:
				libtcod.console_set_default_background(crewman_menu_con, libtcod.darker_blue)
				libtcod.console_rect(crewman_menu_con, 9, 49, 72, 1, False, libtcod.BKGND_SET)
				libtcod.console_set_default_background(crewman_menu_con, libtcod.black)
				libtcod.console_set_default_foreground(crewman_menu_con, TITLE_COL)
				libtcod.console_print_ex(crewman_menu_con, WINDOW_XM, 49, libtcod.BKGND_NONE,
					libtcod.CENTER, 'Injuries')
				
				x = 9
				y = 51
				for (k, v) in self.injury.items():
					libtcod.console_set_default_foreground(crewman_menu_con, libtcod.white)
					libtcod.console_print(crewman_menu_con, x, y, k)
					
					if v is None:
						libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_grey)
						libtcod.console_print(crewman_menu_con, x, y+1, 'None')
					else:
						libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_red)
						libtcod.console_print(crewman_menu_con, x, y+1, v)
					
					if y == 51:
						y = 55
					else:
						y = 51
						x += 24
			
			# player commands
			libtcod.console_set_default_foreground(crewman_menu_con, ACTION_KEY_COL)
			if self.alive and self.field_hospital is None:
				libtcod.console_print(crewman_menu_con, 10, 22, '1')
				libtcod.console_print(crewman_menu_con, 10, 23, '2')
				libtcod.console_print(crewman_menu_con, 10, 24, '3')
				libtcod.console_print(crewman_menu_con, 10, 25, '4')
				libtcod.console_print(crewman_menu_con, 10, 27, EnKey('w').upper() + '/' + EnKey('s').upper())
				if selected_skill == number_of_skills:
					libtcod.console_print(crewman_menu_con, 10, 28, EnKey('e').upper())
				libtcod.console_print(crewman_menu_con, 10, 30, EnKey('f').upper())
				libtcod.console_print(crewman_menu_con, 10, 31, EnKey('l').upper())
				libtcod.console_print(crewman_menu_con, 10, 32, EnKey('n').upper())
			libtcod.console_print(crewman_menu_con, 10, 34, 'Esc')
			
			libtcod.console_set_default_foreground(crewman_menu_con, libtcod.light_grey)
			if self.alive and self.field_hospital is None:
				libtcod.console_print(crewman_menu_con, 14, 22, 'Increase')
				libtcod.console_print(crewman_menu_con, 14, 23, 'Increase')
				libtcod.console_print(crewman_menu_con, 14, 24, 'Increase')
				libtcod.console_print(crewman_menu_con, 14, 25, 'Increase')
				libtcod.console_put_char_ex(crewman_menu_con, 23, 22, chr(4), libtcod.yellow, libtcod.black)
				libtcod.console_put_char_ex(crewman_menu_con, 23, 23, chr(3), libtcod.red, libtcod.black)
				libtcod.console_put_char_ex(crewman_menu_con, 23, 24, chr(5), libtcod.blue, libtcod.black)
				libtcod.console_put_char_ex(crewman_menu_con, 23, 25, chr(6), libtcod.green, libtcod.black)
				libtcod.console_print(crewman_menu_con, 14, 27, 'Select Skill')
				if selected_skill == number_of_skills:
					libtcod.console_print(crewman_menu_con, 14, 28, 'Add New Skill')
				libtcod.console_print(crewman_menu_con, 14, 30, 'First Name')
				libtcod.console_print(crewman_menu_con, 14, 31, 'Last Name')
				libtcod.console_print(crewman_menu_con, 14, 32, 'Nickname')
			libtcod.console_print(crewman_menu_con, 14, 34, 'Exit Menu')
			
			libtcod.console_blit(crewman_menu_con, 0, 0, 0, 0, con, 0, 0)
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			
			return number_of_skills
			
		
		global crewman_menu_con
		crewman_menu_con = NewConsole(WINDOW_WIDTH, WINDOW_HEIGHT, libtcod.black, libtcod.white)
		
		selected_skill = 0				# which crew skill is currently selected
		number_of_skills = 0				# how many skills this crewman has
		
		# draw screen for first time (also counts current number of crewman skills)
		number_of_skills = UpdateCrewmanMenuCon()
		
		exit_menu = False
		while not exit_menu:
			libtcod.console_flush()
			keypress = GetInputEvent()
			
			if not keypress: continue
			
			# exit menu
			if key.vk == libtcod.KEY_ESCAPE:
				exit_menu = True
				continue
			
			# limited options if crewman is dead or in hospital
			if not self.alive or self.field_hospital is not None: continue
			
			key_char = DeKey(chr(key.c).lower())
			
			# increase stat
			if key_char in ['1', '2', '3', '4']:
				
				stat_name = CREW_STATS[int(key_char) - 1]
				
				if self.stats[stat_name] == 10:
					ShowNotification('Stat already at maximum level.')
					continue
				
				# make sure crewman has 1+ advance point available
				pt_cost = 1
				if DEBUG:
					if session.debug['Free Crew Advances']:
						pt_cost = 0
				
				if self.adv - pt_cost < 0:
					ShowNotification('Crewman has no Advance Points remaining.')
					continue
				
				# determine increase amount
				if self.stats[stat_name] < 5:
					increase = 2
				else:
					increase = 1
				
				if ShowNotification('Spend an advance point and increase ' + stat_name + ' by ' + str(increase) + '?', confirm=True):
					self.adv -= pt_cost
					self.stats[stat_name] += increase
					UpdateCrewmanMenuCon()
					PlaySoundFor(None, 'add skill')
					SaveGame()
				
				continue
			
			# change selected skill
			elif key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if selected_skill == 0:
						selected_skill = number_of_skills
					else:
						selected_skill -= 1
				else:
					if selected_skill == number_of_skills:
						selected_skill = 0
					else:
						selected_skill += 1
				PlaySoundFor(None, 'menu_select')
				UpdateCrewmanMenuCon()
				continue
			
			# display add skill menu
			elif key_char == 'e' and selected_skill == number_of_skills:
				result = ShowSkillMenu(self)
				if result != '':
					# spend an advance point and add the skill
					if DEBUG:
						if session.debug['Free Crew Advances']:
							self.adv += 1
					self.adv -= 1
					self.skills.append(result)
					PlaySoundFor(None, 'add skill')
					
					# advanced skills can replace earlier ones
					if 'replaces' in campaign.skills[result]:
						old_skill = campaign.skills[result]['replaces']
						if old_skill in self.skills:
							self.skills.remove(old_skill)
					
					SaveGame()
					number_of_skills = UpdateCrewmanMenuCon()
				continue
			
			# set first, last, or nickname
			elif key_char in ['f', 'l', 'n']:
				
				# first name
				if key_char == 'f':
					current_text = self.first_name
					prompt = 'Enter a new first name for this crewman'
					max_length = MAX_CREW_NAME_LENGTH - len(self.last_name) - 1
					random_list = session.nations[self.nation]['first_names']
				elif key_char == 'l':
					current_text = self.last_name
					prompt = 'Enter a new last name for this crewman'
					max_length = MAX_CREW_NAME_LENGTH - len(self.first_name) - 1
					random_list = session.nations[self.nation]['surnames']
				else:
					current_text = self.nickname
					prompt = 'Enter a new nickname for this crewman'
					max_length = MAX_NICKNAME_LENGTH
					random_list = []
				
				new_text = ShowTextInputMenu(prompt, current_text, max_length, random_list)
				if new_text != '':
					if key_char == 'f':
						self.first_name = new_text
					elif key_char == 'l':
						self.last_name = new_text
					else:
						self.nickname = new_text
				
				UpdateCrewmanMenuCon()
				continue
				
	
	# generate a random first and last name for this person
	def GenerateName(self):
		name_okay = False
		while not name_okay:
			first_name = choice(session.nations[self.nation]['first_names'])
			last_name = choice(session.nations[self.nation]['surnames'])
			if first_name == last_name:
				continue
			if len(first_name + ' ' + last_name) > MAX_CREW_NAME_LENGTH: continue
			name_okay = True
		self.first_name = first_name
		self.last_name = last_name
	
	
	# return a given skill or action modifier according to the crewman's current status
	def GetSkillMod(self, modifier):
		if not self.alive or self.condition in ['Unconscious', 'Critical']: return 0.0
		if self.condition == 'Stunned':		# stunned status
			modifier = modifier * 0.5
		if self.fatigue > 0:
			modifier -= float(self.fatigue * 2)		# impact of crew fatigue
		modifier = round(modifier, 1)
		if modifier <= 0.0:
			modifier = 0.0
		return modifier
	
	
	# check to see whether this crewman gains a fatigue point
	def DoFatigueCheck(self):
		if not self.alive or self.condition in ['Unconscious', 'Critical']: return
		if self.fatigue == 10: return
		
		roll = GetPercentileRoll()
		if campaign_day.weather['Temperature'] in ['Cold', 'Hot']:
			roll += 10.0
		elif campaign_day.weather['Temperature'] == 'Extreme Cold':
			if 'Acclimatized (Nordic)' in self.skills:
				roll += 5.0
			else:
				roll += 15.0
		elif campaign_day.weather['Temperature'] == 'Extreme Hot':
			if 'Acclimatized (Desert)' in self.skills:
				roll += 5.0
			else:
				roll += 15.0
		
		if roll <= float(self.stats['Morale']) * 8.5:
			return
		
		self.fatigue += libtcod.random_get_int(0, 1, 2)
		if self.fatigue > 10:
			self.fatigue = 10
	
	
	# crew recovers some fatigue from rest
	def Rest(self):
		if not self.alive: return
		if self.fatigue == BASE_FATIGUE: return
		max_loss = int(self.stats['Morale'] / 2)
		if max_loss == 0:
			max_loss = 1
		i = libtcod.random_get_int(0, 0, max_loss)
		self.fatigue -= i
		if self.fatigue < BASE_FATIGUE:
			self.fatigue = BASE_FATIGUE
	
	
	# (re)build a list of possible commands for this turn
	def BuildCommandList(self):
		self.cmd_list = []
		
		# unconscious and dead crewmen cannot act
		if not self.alive or self.condition == 'Unconscious':
			self.cmd_list.append('None')
			return
		
		for (k, d) in session.crew_commands.items():
			
			# don't add "None" automatically
			if k == 'None': continue
			
			# some commands not allowed for CE crew in turret
			if 'rst_ce_na' in d:
				if self.unit.GetStat('turret') is not None:
					if self.current_position.location == 'Turret' and self.ce and self.unit.GetStat('turret') == 'RST':
						continue
			
			# weapon operation needs a weapon in the unit
			if k in ['Operate Gun', 'Operate MG']:
				for weapon in self.unit.weapon_list:
					if k == 'Operate Gun' and weapon.GetStat('type') != 'Gun': continue
					if k == 'Operate MG' and weapon.GetStat('type') not in MG_WEAPONS: continue
					if weapon.GetStat('fired_by') is None: continue
					if self.current_position.name not in weapon.GetStat('fired_by'):
						continue
					# check that position is in same location as weapon mount if any
					if weapon.GetStat('mount') is not None:
						if weapon.GetStat('mount') != self.current_position.location: continue
					if k == 'Operate MG' and weapon.GetStat('type') == 'AA MG' and not self.ce:
						continue
					
					# add the command to fire this weapon
					self.cmd_list.append(k)
					break
					
				continue
			
			# unjam weapon needs a jammed weapon
			if k == 'Unjam Weapon':
				for weapon in self.unit.weapon_list:
					if weapon.broken: continue
					if not weapon.jammed: continue
					if weapon.GetStat('mount') is not None:
						if weapon.GetStat('mount') != self.current_position.location: continue
					self.cmd_list.append(k)
					break
				continue
			
			# manage ready rack needs at least one gun
			if k == 'Manage Ready Rack':
				for weapon in self.unit.weapon_list:
					if weapon.GetStat('type') != 'Gun': continue
					# check that position is in same location as weapon mount if any
					if weapon.GetStat('mount') is not None:
						if weapon.GetStat('mount') != self.current_position.location: continue
					crewman_ok = False
					if weapon.GetStat('fired_by') is not None:
						if self.current_position.name in weapon.GetStat('fired_by'):
							crewman_ok = True
					if weapon.GetStat('reloaded_by') is not None:
						if self.current_position.name in weapon.GetStat('reloaded_by'):
							crewman_ok = True
					if crewman_ok:
						self.cmd_list.append(k)
				continue
			
			if 'position_list' in d:
				if self.current_position.name not in d['position_list']:
					continue
			
			if k == 'Abandon Tank':
				can_abandon = False
				if self.unit.immobilized:
					can_abandon = True 
				for position in self.unit.positions_list:
					if position.crewman is None: continue
					if not position.crewman.alive:
						can_abandon = True
						break
				for weapon in self.unit.weapon_list:
					if weapon.broken:
						can_abandon = True
						break
				# allow abandoning tank if debug flag is active
				if DEBUG:
					can_abandon = True
				if not can_abandon:
					continue
			
			# can't drive if vehicle is immobilized or bogged
			elif k in ['Drive', 'Drive Into Terrain', 'Withdraw']:
				if self.unit.immobilized: continue
				if self.unit.bogged: continue
			
			# must be mobile and have 1+ enemy infantry/cavalry/gun units in forward adjacent hex
			elif k == 'Overrun':
				if self.unit.immobilized: continue
				if self.unit.bogged: continue
				
				defending_units = False
				for unit in scenario.hex_dict[(0,-1)].unit_stack:
					if unit.owning_player != 1: continue
					if not unit.spotted: continue
					if unit.GetStat('category') not in ['Infantry', 'Cavalry', 'Gun']: continue
					if unit.GetStat('category') == 'Cavalry' and unit.moving: continue
					defending_units = True
					break
				
				if not defending_units: continue
			
			# can only unbog if vehicle is already bogged
			elif k == 'Attempt Unbog':
				if not self.unit.bogged: continue
			
			# check that a mortar is attached and is fired by this position
			elif k == 'Fire Smoke Mortar':
				position_name = self.unit.GetStat('smoke_mortar')
				if position_name is None: continue
				if campaign_day.smoke_mortar_rounds == 0: continue
				if self.current_position.name != position_name: continue
			
			# smoke grenade
			elif k == 'Smoke Grenade':
				if not self.ce: continue
				if campaign_day.smoke_grenades == 0: continue
			
			# add the command
			self.cmd_list.append(k)
	
	# select a new command from command list
	def SelectCommand(self, reverse):
		
		c = 1
		if reverse:
			c = -1
		
		# find current command in list
		i = self.cmd_list.index(self.current_cmd)
		
		# find new command
		if i+c > len(self.cmd_list) - 1:
			i = 0
		elif i+c < 0:
			i = len(self.cmd_list) - 1
		else:
			i += c
		
		self.current_cmd = self.cmd_list[i]
	
	
	# attempt to toggle current hatch status
	def ToggleHatch(self):
		if not self.alive or self.condition == 'Unconscious': return False
		if not self.current_position.TogglePositionHatch(): return False
		self.SetCEStatus()
		return True
	
	
	# set crewman BU/CE status based on position status
	def SetCEStatus(self):
		if self.current_position is None:
			self.ce = True
			return
		if self.current_position.open_top or self.current_position.crew_always_ce:
			self.ce = True
		elif not self.current_position.hatch:
			self.ce = False
		elif self.current_position.hatch_open:
			self.ce = True
		else:
			self.ce = False

		
	

# Position class: represents a personnel position within a unit
class Position:
	def __init__(self, unit, position_dict):
		
		self.unit = unit
		self.name = position_dict['name']
		
		self.location = None
		if 'location' in position_dict:
			self.location = position_dict['location']
		
		self.hatch = False
		if 'hatch' in position_dict:
			self.hatch = True
		
		self.hatch_group = None
		if 'hatch_group' in position_dict:
			self.hatch_group = int(position_dict['hatch_group'])
		
		self.open_top = False
		if 'open_top' in position_dict:
			self.open_top = True
		
		self.crew_always_ce = False
		if 'crew_always_exposed' in position_dict:
			self.crew_always_ce = True
		
		self.ce_visible = []
		if 'ce_visible' in position_dict:
			for direction in position_dict['ce_visible']:
				self.ce_visible.append(int(direction))
		
		self.bu_visible = []
		if 'bu_visible' in position_dict:
			for direction in position_dict['bu_visible']:
				self.bu_visible.append(int(direction))
		
		# person currently in this position
		self.crewman = None
		
		# current hatch open/closed status
		self.hatch_open = False
		
		# list of map hexes visible to this position
		self.visible_hexes = []
	
	
	# update the list of hexes currently visible from this position
	def UpdateVisibleHexes(self):
		
		self.visible_hexes = []
		
		if self.crewman is None: return
		
		# can always spot in own hex
		self.visible_hexes.append((self.unit.hx, self.unit.hy))
		
		# current crew command does not allow spotting
		if not session.crew_commands[self.crewman.current_cmd]['spotting_allowed']:
			return
		
		if self.crew_always_ce or self.open_top:
			direction_list = self.ce_visible
		elif self.hatch_open:
			direction_list = self.ce_visible
		else:
			direction_list = self.bu_visible
		
		# rotate based on hull or turret facing
		rotate = 0
		if self.location == 'Hull':
			if self.unit.facing is not None:
				rotate = self.unit.facing
		elif self.location == 'Turret':
			if self.unit.turret_facing is not None:
				rotate = self.unit.turret_facing
		
		for direction in direction_list:
			hextant_hex_list = GetCoveredHexes(self.unit.hx, self.unit.hy, ConstrainDir(direction + rotate))
			for (hx, hy) in hextant_hex_list:
				# hex is off map
				if (hx, hy) not in scenario.hex_dict: continue
				# already in list
				if (hx, hy) in self.visible_hexes: continue
				# too far away for BU crew
				if not self.hatch_open and not (self.crew_always_ce or self.open_top):
					if GetHexDistance(self.unit.hx, self.unit.hy, hx, hy) > MAX_BU_LOS:
						continue
				self.visible_hexes.append((hx, hy))


	# toggle the open/closed status of a hatch in this position
	def TogglePositionHatch(self):
		if not self.hatch: return False
		if self.open_top: return False
		if self.crew_always_ce: return False
		
		self.hatch_open = not self.hatch_open
		
		# toggle other linked hatches too
		if self.hatch_group is not None:
			for position in self.unit.positions_list:
				if position == self: continue
				if position.hatch_group is None: continue
				if position.hatch_group != self.hatch_group: continue
				position.hatch_open = self.hatch_open
				if position.crewman is not None:
					position.crewman.SetCEStatus()
		
		return True


# Weapon Class: represents a weapon mounted on or carried by a unit
class Weapon:
	def __init__(self, unit, stats):
		self.unit = unit			# unit that owns this weapon
		self.stats = stats.copy()		# dictionary of weapon stats
		
		# some weapons need a descriptive name generated
		if 'name' not in self.stats:
			if self.GetStat('type') == 'Gun':
				text = self.GetStat('calibre')
				if self.GetStat('long_range') is not None:
					text += self.GetStat('long_range')
				self.stats['name'] = text
			
			# high calibre MG
			elif self.GetStat('type') in MG_WEAPONS and self.GetStat('calibre') is not None:
				text = self.GetStat('calibre') + 'mm MG'
				self.stats['name'] = text
			
			else:
				self.stats['name'] = self.GetStat('type')
		
		# save maximum range as an local int
		self.max_range = 3
		if 'max_range' in self.stats:
			self.max_range = int(self.stats['max_range'])
			del self.stats['max_range']
		else:
			if self.stats['type'] in ['Turret MG', 'Co-ax MG']:
				self.max_range = 2
			elif self.stats['type'] in ['Hull MG', 'AA MG']:
				self.max_range = 1
		
		self.ammo_type = None
		
		# if weapon is a gun, set up ammo stores and ready rack
		self.ammo_stores = None
		self.rr_size = 0
		self.using_rr = False
				
		if self.GetStat('type') == 'Gun' and 'ammo_type_list' in self.stats:
			self.ammo_stores = {}
			self.ready_rack = {}
			self.max_ammo = int(self.stats['max_ammo'])
			self.max_plus_extra_ammo = self.max_ammo + int(floor(float(self.max_ammo) * 0.15))
			
			# set maximum ready rack capacity
			if 'rr_size' in self.stats:
				self.rr_size = int(self.stats['rr_size'])
			else:
				self.rr_size = 6
			
			# set up empty categories first, also ready rack contents
			for ammo_type in self.stats['ammo_type_list']:
				self.ammo_stores[ammo_type] = 0
				self.ready_rack[ammo_type] = 0
			
			# if AI unit, automatically generate rare ammo and load
			# (player is handled through AmmoReloadMenu)
			if not self.unit.is_player:
				self.GenerateRareAmmo()
				self.AddDefaultAmmoLoad()
		
		# weapon statuses
		self.covered_hexes = []			# map hexes that could be targeted by this weapon
		self.fired = False
		self.maintained_rof = False
		self.jammed = False			# weapon is jammed and cannot be fired
		self.broken = False			# weapon has broken and cannot be used
		self.selected_target = None		# for player unit
		self.acquired_target = None		# acquired target status and target unit
	
	
	# check for the value of a stat, return None if stat not present
	def GetStat(self, stat_name):
		if stat_name not in self.stats:
			return None
		return self.stats[stat_name]
	
	
	# load this gun with a default ammo loadout
	def AddDefaultAmmoLoad(self):
		
		# try to add x number of shells to the general stores or RR, return the number that was added
		def AddAmmo(ammo_type, use_rr, add_amount):
			
			if ammo_type not in self.ammo_stores: return 0
			
			# check that ammo is not limited
			if ammo_type in self.rare_ammo:
				max_add_amount = self.rare_ammo[ammo_type] - self.ammo_stores[ammo_type] - self.ready_rack[ammo_type]
				if add_amount > max_add_amount:
					add_amount = max_add_amount
				if add_amount <= 0:
					return 0
			
			if use_rr:
				# no ready rack on this gun
				if ammo_type not in self.ready_rack: return 0
				
				if rr_num + add_amount > self.rr_size:
					add_amount = self.rr_size - rr_num
					if add_amount < 0: add_amount = 0
				self.ready_rack[ammo_type] += add_amount
			else:
				if ammo_num + add_amount > self.max_ammo:
					add_amount = self.max_ammo - ammo_num
					if add_amount < 0: add_amount = 0
				self.ammo_stores[ammo_type] += add_amount
			return add_amount
		
		if self.stats['type'] != 'Gun': return
		
		# clear current load
		for ammo_type in AMMO_TYPES:
			if ammo_type in self.ammo_stores:
				self.ammo_stores[ammo_type] = 0
			if ammo_type in self.ready_rack:
				self.ready_rack[ammo_type] = 0
		ammo_num = 0
		rr_num = 0
		
		# replace with default load
		
		# add max amount of any APDS or APCR
		if 'special_ammo' in self.stats:
			for ammo_type in list(self.stats['special_ammo']):
				if self.rare_ammo[ammo_type] > 0:
					ammo_num += AddAmmo(ammo_type, False, self.rare_ammo[ammo_type])
					
		# HE and Smoke
		if 'AP' not in self.ammo_stores and 'HE' in self.ammo_stores and 'Smoke' in self.ammo_stores:
			ammo_num += AddAmmo('HE', False, int(float(self.max_ammo) * 0.85))
			ammo_num += AddAmmo('Smoke', False, self.max_ammo)
			rr_num += AddAmmo('HE', True, int(float(self.rr_size) * 0.8))
			rr_num += AddAmmo('Smoke', True, self.rr_size)
		
		# HE only
		elif 'HE' in self.ammo_stores and 'AP' not in self.ammo_stores:
			ammo_num += AddAmmo('HE', False, self.max_ammo)
			rr_num += AddAmmo('HE', True, self.rr_size) 
			
		# AP only
		elif 'AP' in self.ammo_stores and 'HE' not in self.ammo_stores:
			ammo_num += AddAmmo('AP', False, self.max_ammo)
			rr_num += AddAmmo('AP', True, self.rr_size) 
		
		# HE, AP, and Smoke
		elif 'AP' in self.ammo_stores and 'HE' in self.ammo_stores and 'Smoke' in self.ammo_stores:
			ammo_num += AddAmmo('HE', False, int(float(self.max_ammo) * 0.65))
			ammo_num += AddAmmo('Smoke', False, int(float(self.max_ammo) * 0.1))
			ammo_num += AddAmmo('AP', False, self.max_ammo)
			rr_num += AddAmmo('HE', True, int(float(self.rr_size) * 0.75))
			rr_num += AddAmmo('AP', True, self.rr_size)
		
		# HE and AP
		else:
			ammo_num += AddAmmo('HE', False, int(float(self.max_ammo) * 0.75))
			ammo_num += AddAmmo('AP', False, self.max_ammo)
			rr_num += AddAmmo('HE', True, int(float(self.rr_size) * 0.75))
			rr_num += AddAmmo('AP', True, self.rr_size)
		
		# fill up any remaining spots with HE or AP
		ammo_num += AddAmmo('HE', False, self.max_ammo)
		rr_num += AddAmmo('HE', True, self.max_ammo)
		ammo_num += AddAmmo('AP', False, self.max_ammo)
		rr_num += AddAmmo('AP', True, self.max_ammo)
		
		# select first ammo type as default
		for ammo_type in AMMO_TYPES:
			if ammo_type in self.ammo_stores:
				self.ammo_type = ammo_type
				break
		
		return(ammo_num, rr_num)
	
	
	# generate a rare ammo supply for this weapon
	def GenerateRareAmmo(self, resupply=False):
		self.rare_ammo = {}
		self.rare_ammo_na = []
		if 'special_ammo' not in self.stats: return
		
		for ammo_type in list(self.stats['special_ammo']):
			
			# if resupplying and ammo type is scarce, no more available today
			if resupply and ammo_type not in ['APCR', 'APDS']:
				self.rare_ammo[ammo_type] = 0
				continue
			
			max_available = None
			for date, amount in self.stats['special_ammo'][ammo_type].items():
				
				if max_available is None:
					if date > campaign.today:
						break
					max_available = int(amount)
					continue
				
				# break if this date is later than current date
				if date > campaign.today: break
			
			# not yet available at this date
			if max_available is None:
				self.rare_ammo[ammo_type] = 0
				self.rare_ammo_na.append(ammo_type)
				continue
			
			# roll for amount available today
			amount_available = 0
			for i in range(3):
				roll = libtcod.random_get_int(0, 1, max_available)
				if roll > amount_available:
					amount_available = roll
			
			# check for player crew skill
			if self.unit.is_player:
				if self.unit.CrewmanHasSkill(['Loader'], 'Ammo Scrounger'):
					amount_available += int(ceil(amount_available / 3))
			
			# add entry
			self.rare_ammo[ammo_type] = amount_available
		
		# if player unit, check for saved rare ammo from current stores and add to current max
		if self.unit.is_player:
			for ammo_type in list(self.rare_ammo):
				if self.ammo_stores[ammo_type] > 0:
					self.rare_ammo[ammo_type] += self.ammo_stores[ammo_type]
				if self.ready_rack[ammo_type] > 0:
					self.rare_ammo[ammo_type] += self.ready_rack[ammo_type]
		
	
	# do a jam test for this weapon
	def JamTest(self):
		
		# already jammed
		if self.jammed: return False
		
		roll = GetPercentileRoll()
		chance = WEAPON_JAM_CHANCE
		
		if self.GetStat('reloaded_by') is not None:
			for position in self.GetStat('reloaded_by'):
				crewman = self.unit.GetPersonnelByPosition(position)
				if crewman is None: continue
				if crewman.current_cmd != 'Reload': continue
				if 'Gun Maintenance' in crewman.skills:
					chance = round(chance * 0.50, 2)
					break
		
		if roll > chance: return False
		
		self.jammed = True
		return True
	
	
	# see if this weapon becomes unjammed
	def AttemptUnjam(self, crewman):
		roll = GetPercentileRoll()
		if 'Mechanic' in crewman.skills or 'Gun Maintenance' in crewman.skills:
			roll -= 15.0
		if roll > WEAPON_UNJAM_CHANCE: return False
		self.jammed = False
		return True
	
	
	# do a break test for this weapon, taken after firing
	def BreakTest(self):
		
		if self.GetStat('unreliable') is not None:
			chance = 1.0
		else:
			chance = 0.3
		
		if campaign_day.weather['Temperature'] in ['Extreme Cold', 'Extreme Hot']:
			chance += 1.0
		
		if self.GetStat('reloaded_by') is not None:
			for position in self.GetStat('reloaded_by'):
				crewman = self.unit.GetPersonnelByPosition(position)
				if crewman is None: continue
				if crewman.current_cmd != 'Reload': continue
				if 'Gun Maintenance' in crewman.skills:
					chance = round(chance * 0.5, 2)
					break
		
		roll = GetPercentileRoll()
		if roll > chance: return False
		
		self.broken = True
		return True
	
	
	# move a shell into or out of Ready Rack
	def ManageRR(self, add_num):
		
		# calculate current total general stores and RR load
		total_num = 0
		for ammo_type in AMMO_TYPES:
			if ammo_type in self.ammo_stores:
				total_num += self.ammo_stores[ammo_type]
		rr_num = 0
		for ammo_type in AMMO_TYPES:
			if ammo_type in self.ready_rack:
				rr_num += self.ready_rack[ammo_type]
		
		# no room in RR
		if rr_num + add_num > self.rr_size:
			# try to add as many as possible
			add_num = self.rr_size - rr_num
			if add_num <= 0:
				return False
		
		# adding to RR
		if add_num > 0:
		
			# none remaining in stores
			if self.ammo_stores[self.ammo_type] == 0:
				return False
			
			# not enough remaining in stores, add as many as possible
			if self.ammo_stores[self.ammo_type] < add_num:
				add_num = self.ammo_stores[self.ammo_type]
		
		# removing from RR
		else:
		
			# none remaining in RR
			if self.ready_rack[self.ammo_type] == 0:
				return False
			
			# not enough remaining in RR, remove as many as possible
			if self.ready_rack[self.ammo_type] + add_num < 0:
				add_num = 0 - self.ready_rack[self.ammo_type]
		
			# no room in general stores
			# allow one more shell here just to give some room to rearrange ready rack
			if total_num - add_num > self.max_plus_extra_ammo + 1:
				return False
		
		self.ready_rack[self.ammo_type] += add_num
		self.ammo_stores[self.ammo_type] -= add_num
		
		PlaySoundFor(None, 'move_1_shell')
		
		return True
		
	
	# calculate the odds for maintain RoF with this weapon
	def GetRoFChance(self):
		
		# no RoF chance if weapon is gun and unit has moved that turn
		if self.GetStat('type') == 'Gun' and self.unit.moving:
			return 0.0
		
		# some guns are so slow-firing they can never maintain RoF
		if self.GetStat('rof_na') is not None: return 0.0
		
		# guns must have at least one shell of the current type available
		if self.GetStat('type') == 'Gun':
			if self.ammo_type is not None:
				if self.using_rr:
					if self.ready_rack[self.ammo_type] == 0:
						return 0.0
				else:
					if self.ammo_stores[self.ammo_type] == 0:
						return 0.0
		
		# NEW: no RoF for guns if any other weapon on unit has already fired
		if self.GetStat('type') == 'Gun':
			for weapon in self.unit.weapon_list:
				if weapon == self: continue
				if weapon.fired:
					return 0.0
		
		# get base RoF, set default value if none
		chance = self.GetStat('rof')
		if chance is None:
			if self.GetStat('type') in MG_WEAPONS:
				chance = 16.7
			else:
				chance = 5.0
		else:
			chance = float(chance)
		modifier = 0.0
		
		# weapon is turret mounted and turret was rotated
		if self.GetStat('mount') == 'Turret':
			if self.unit.turret_facing is not None:
				if self.unit.turret_facing != self.unit.previous_turret_facing:
					if self.unit.GetStat('turret') == 'FT':
						chance = chance * 0.75
					elif self.unit.GetStat('turret') == 'VST':
						chance = chance * 0.25
					else:
						chance = chance * 0.5
		
		# weapon is hull mounted and hull was pivoted
		elif self.GetStat('mount') == 'Hull':
			if self.unit.facing is not None:
				if self.unit.facing != self.unit.previous_facing:
					if unit.GetStat('turntable') is not None:
						chance = chance * 0.75
					else:
						chance = chance * 0.5
		
		# gun modifiers
		if self.GetStat('type') == 'Gun':
			
			# small gun bonus
			if self.stats['name'] == 'AT Rifle':
				calibre = 20
			else:
				calibre = int(self.stats['calibre'])
			if 15 <= calibre <= 40:
				chance = chance * 2.0

			# if weapon has a dedicated loader, loader must be on Reload command
			position_list = self.GetStat('reloaded_by')
			if position_list is not None:
				crewman_found = False
				for position in position_list:
					crewman = self.unit.GetPersonnelByPosition(position)
					if crewman is None: continue
					if crewman.current_cmd != 'Reload': continue
					
					# check that position is in same location as weapon mount if any
					if self.GetStat('mount') is not None:
						if crewman.current_position.location != self.GetStat('mount'):
							continue
					
					crewman_found = True
					
					# Loader skill bonus
					if 'Fast Hands' in crewman.skills:
						modifier += crewman.GetSkillMod(15.0)
					break
				if not crewman_found:
					chance = chance * 0.5
		
			# guns also need to be using RR for full benefit
			if not self.using_rr:
				
				# check for crewman passing ammo
				mod = 0.4
				for position in self.unit.positions_list:
					if position.crewman is None: continue
					if position.crewman.current_cmd == 'Pass Ammo':
						if 'Shell Tosser' in position.crewman.skills:
							mod = 0.8
						else:
							mod = 0.6
						break
				
				chance = chance * mod
		
		# firing crewman modifiers
		position_list = self.GetStat('fired_by')
		if position_list is not None:
			for position in position_list:
				
				if self.unit.GetStat('crew_positions') is None: continue
				
				# check that position is in same location as weapon mount if any
				if self.GetStat('mount') is not None:
					mount = self.GetStat('mount')
					same_location = False
					for position2 in self.unit.GetStat('crew_positions'):
						if position2['name'] != position: continue
						if position2['location'] == mount:
							same_location = True
							break
					if not same_location: continue
				
				crewman = self.unit.GetPersonnelByPosition(position)
				if crewman is None: continue
				
				if self.GetStat('type') == 'Gun':
					if 'Quick Trigger' in crewman.skills:
						modifier += crewman.GetSkillMod(5.0)
					if self.selected_target is not None:
						if 'Time on Target' in crewman.skills:
							modifier += crewman.GetSkillMod(10.0)
				
				elif self.GetStat('type') in MG_WEAPONS:
					if 'Burst Fire' in crewman.skills:
						modifier += crewman.GetSkillMod(10.0)
		
		# campaign skill bonus
		if self.unit == scenario.player_unit and self.GetStat('type') in MG_WEAPONS:
			if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Superior Firepower'):
				modifier += 25.0
		
		# acquired target modifiers
		if self.acquired_target is None:
			modifier -= 5.0
		else:
			modifier += 10.0
		
		# apply modifier and round final chance
		chance += modifier
		chance = round(chance, 1)
		
		# minimum gun/mg RoF chances
		if self.GetStat('type') == 'Gun':
			if self.using_rr:
				if chance <= 5.0:
					chance = 5.0
			else:
				if chance <= 2.0:
					chance = 2.0
		
		# absolute minimum and maximum RoF chances
		if chance < 0.0:
			chance = 0.0
		elif chance > 65.0:
			chance = 65.0
		
		return chance
		
	
	# display information about current available ammo to a console
	def DisplayAmmo(self, console, x, y, skip_active=False):
		
		# highlight if RR is in use
		if self.using_rr:
			libtcod.console_set_default_foreground(console, libtcod.white)
		else:
			libtcod.console_set_default_foreground(console, libtcod.grey)
		libtcod.console_print_ex(console, x+11, y, libtcod.BKGND_NONE,
			libtcod.RIGHT, 'RR')
		
		y += 1
		total_general = 0
		# general stores and RR contents
		for ammo_type in self.stats['ammo_type_list']:
			if ammo_type in self.ammo_stores:
				
				# highlight if this ammo type currently active
				if self.ammo_type is not None and not skip_active:
					if self.ammo_type == ammo_type:
						libtcod.console_set_default_background(console, libtcod.darker_blue)
						libtcod.console_rect(console, x, y, 12, 1, True, libtcod.BKGND_SET)
						libtcod.console_set_default_background(console, libtcod.darkest_grey)
				
				libtcod.console_set_default_foreground(console, libtcod.white)
				libtcod.console_print(console, x, y, ammo_type)
				libtcod.console_set_default_foreground(console, libtcod.light_grey)
				libtcod.console_print_ex(console, x+8, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(self.ammo_stores[ammo_type]))
				total_general += self.ammo_stores[ammo_type]
				
				libtcod.console_print_ex(console, x+11, y, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(self.ready_rack[ammo_type]))
				
				y += 1
		
		y += 1
		libtcod.console_print(console, x, y, 'Max')
		libtcod.console_set_default_foreground(console, libtcod.light_grey)
		libtcod.console_print_ex(console, x+8, y, libtcod.BKGND_NONE,
			libtcod.RIGHT, self.stats['max_ammo'])
		libtcod.console_print_ex(console, x+11, y, libtcod.BKGND_NONE,
			libtcod.RIGHT, str(self.rr_size))
		
		# show if current total exceeds safe maximum
		extra_ammo = total_general - int(self.stats['max_ammo'])
		if extra_ammo > 0:
			libtcod.console_set_default_foreground(console, libtcod.light_red)
			libtcod.console_print(console, x, y+1, 'Extra')
			libtcod.console_print_ex(console, x+8, y+1, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(extra_ammo))
	
	
	# add a target as the current acquired target, or add one level
	def AddAcquiredTarget(self, target):
		
		# target is not yet spotted
		if target.owning_player == 1 and not target.spotted: return
		
		# no target previously acquired
		if self.acquired_target == None:
			self.acquired_target = (target, 0)
		
		# adding one level
		elif self.acquired_target == (target, 0):
			self.acquired_target = (target, 1)
		
		# already at max
		elif self.acquired_target == (target, 1):
			return
		
		# same or new target
		else:
			self.acquired_target = (target, 0)
	
	
	# calculate the map hexes covered by this weapon
	def UpdateCoveredHexes(self):
		
		def AddAllAround():
			for r in range(1, self.max_range + 1):
				ring_list = GetHexRing(self.unit.hx, self.unit.hy, r)
				for (hx, hy) in ring_list:
					# make sure hex is on map
					if (hx, hy) in scenario.hex_dict:
						self.covered_hexes.append((hx, hy))
		
		self.covered_hexes = []
		
		# can always fire in own hex
		self.covered_hexes.append((self.unit.hx, self.unit.hy))
		
		# infantry and cavalry can fire all around
		if self.unit.GetStat('category') in ['Infantry', 'Cavalry']:
			AddAllAround()
			return
		
		# AA MGs normally can fire in any direction
		if self.GetStat('type') == 'AA MG':
			if self.GetStat('front_only') is None and self.GetStat('rear_facing') is None:
				AddAllAround()
				return
		
		# hull-mounted weapons fire in hull facing direction, also weapons mounted high on the hull
		# if no rotatable turret present
		if self.GetStat('mount') == 'Hull' or self.unit.turret_facing is None:
			hextant_hex_list = GetCoveredHexes(self.unit.hx, self.unit.hy, self.unit.facing)
			
			# hull-mounted weapons can add additional covered hexes
			if self.GetStat('extra_facings_covered') is not None:
				for text in self.GetStat('extra_facings_covered'):
					facing = ConstrainDir(self.unit.facing + int(text))
					for (hx, hy) in GetCoveredHexes(self.unit.hx, self.unit.hy, facing):
						
						# skip if out of range
						if GetHexDistance(self.unit.hx, self.unit.hy, hx, hy) > self.max_range:
							continue
						
						# add if not already in the list
						if (hx, hy) not in hextant_hex_list:
							hextant_hex_list.append((hx, hy))
			
		# turret-mounted weapons fire in turret direction
		elif self.GetStat('mount') == 'Turret':
			
			# possible for weapons to be mounted on rear of turret
			if self.GetStat('rear_facing') is not None:
				facing = ConstrainDir(self.unit.turret_facing + 3)
			else:
				facing = self.unit.turret_facing
			hextant_hex_list = GetCoveredHexes(self.unit.hx, self.unit.hy, facing)
		
		else:
			print('ERROR: Could not set covered hexes for weapon: ' + self.stats['name'])
			return
		
		for (hx, hy) in hextant_hex_list:
			if (hx, hy) not in scenario.hex_dict: continue		# hex is off map
			# out of range
			if GetHexDistance(self.unit.hx, self.unit.hy, hx, hy) > self.max_range:
				continue
			self.covered_hexes.append((hx, hy))
	
	
	# set/reset all scenario statuses for a new turn
	def ResetMe(self):
		self.fired = False
		self.maintained_rof = False
		self.UpdateCoveredHexes()
	
	
	# try to select the previous or next ammo type
	def SelectAmmoType(self, forward):
		if self.GetStat('ammo_type_list') is None: return False
		
		# ammo type not yet selected!
		if self.ammo_type is None:
			self.ammo_type = self.stats['ammo_type_list'][0]
			return True
		
		# no other types possible
		if len(self.stats['ammo_type_list']) == 1:
			return False
		
		if forward:
			m = 1
		else:
			m = -1
		i = self.stats['ammo_type_list'].index(self.ammo_type)
		i += m
		
		# don't cycle
		if i < 0:
			return False
		elif i > len(self.stats['ammo_type_list']) - 1:
			return False
		self.ammo_type = self.stats['ammo_type_list'][i]
		return True
	
	
	# cycle to use next available ammo type
	def CycleAmmo(self):
		
		# don't attempt if this weapon is not a gun
		if self.GetStat('ammo_type_list') is None: return False
		
		# no other types possible
		if len(self.stats['ammo_type_list']) == 1:
			return False
		
		i = self.stats['ammo_type_list'].index(self.ammo_type)
		if i == len(self.stats['ammo_type_list']) - 1:
			i = 0
		else:
			i += 1
		
		self.ammo_type = self.stats['ammo_type_list'][i]
		
		return True
	
	
	# return the effective FP of an HE/HEAT hit from this weapon
	def GetEffectiveFP(self):
		
		if self.GetStat('type') != 'Gun':
			print('ERROR: ' + self.stats['name'] + ' is not a gun, cannot generate effective FP')
			return 1
		
		# some weapons might have a higher base firepower
		if self.GetStat('fp') is not None:
			return int(self.GetStat('fp'))
		
		for (calibre, fp) in HE_FP_EFFECT:
			if calibre <= int(self.GetStat('calibre')):
				if self.ammo_type == 'HEAT':
					return fp - 2
				return fp
		
		print('ERROR: Could not find effective FP for: ' + self.stats['name'])
		return 1



# AI: controller for enemy and player-allied units
class AI:
	def __init__(self, owner):
		self.owner = owner			# pointer to owning Unit
		self.attitude = ''			# can be Advance, Hold, Withdraw
		self.state = ''				# can be Lax, Alert, Heroic, Stunned
		self.previous_action = ''		# action that was executed last activation
		self.intended_target = None		# intended enemy target for future

	# set up initial AI state, called during spawn
	def Reset(self):
		
		# player squad member
		if self.owner in campaign.player_unit.squad:
			self.attitude = 'Hold'
			self.state = 'Alert'
			return
		
		# enemy unit
		if self.owner.owning_player == 1:
			if campaign_day.mission in ['Fighting Withdrawal', 'Counterattack']:
				self.attitude = 'Advance'
			else:
				self.attitude = 'Hold'
			if campaign_day.mission in ['Fighting Withdrawal', 'Counterattack']:
				self.state = 'Alert'
			else:
				if GetPercentileRoll() <= 75.0:
					self.state = 'Alert'
				else:
					self.state = 'Lax'
			return
		
		# friendly unit
		self.attitude = 'Advance'
		self.state = 'Alert'


	# do activation for this unit
	def DoActivation(self, defensive_fire=False):
		
		# show a debug message if debug flag enabled
		def AISpyMsg(text):
			if not DEBUG: return
			if not session.debug['AI Spy']: return
			print('AI SPY: ' + text)
		
		
		if not self.owner.alive: return
		
		# check for debug flags
		if DEBUG:
			if self.owner.owning_player == 1 and session.debug['No Enemy AI Actions']:
				return
			elif self.owner in scenario.player_unit.squad and session.debug['No Player Squad Actions']:
				return
			elif self.owner not in scenario.player_unit.squad and self.owner.owning_player == 0 and session.debug['No Unit Support Actions']:
				return
		
		# check for all enemies dead and do nothing if so
		all_enemies_dead = True
		for unit in scenario.units:
			if unit.owning_player != self.owner.owning_player and unit.alive:
				all_enemies_dead = False
				break
		if all_enemies_dead: return
		
		if DEBUG:
			if session.debug['AI Spy']:
				print('\n')
		
		AISpyMsg(self.owner.unit_id + ' now acting')
					
		
		# 0) Build basic situational info
		#################################
		current_distance = GetHexDistance(0, 0, self.owner.hx, self.owner.hy)
		spotted_enemies = 0
		adjacent_enemies = 0
		has_los_to_enemy = False
		for unit in scenario.units:
			if unit.owning_player == self.owner.owning_player: continue
			if not unit.spotted: continue
			spotted_enemies += 1
			if GetHexDistance(unit.hx, unit.hy, self.owner.hx, self.owner.hy) <= 1:
				adjacent_enemies += 1
			if self.owner.los_table[unit]:
				has_los_to_enemy = True
		player_crew_vulnerable = False
		if len(scenario.player_unit.VulnerableCrew()) > 0:
			player_crew_vulnerable = True
		
		# TODO: build list of enemy units that have AC on this one instead
		is_ac = False
		if scenario.player_unit.los_table[self.owner]:
			for weapon in scenario.player_unit.weapon_list:
				if weapon.broken: continue
				if weapon.acquired_target is not None:
					if weapon.acquired_target[0] == self.owner:
						is_ac = True
						break
		
		# 1) Determine if a state change is required
		#############################################
		if self.state == 'Lax':
			if spotted_enemies > 0:
				roll = GetPercentileRoll()
				
				if not campaign.options['realistic_ai']:
					roll += 20.0
				
				if roll <= float(spotted_enemies) * 3.0:
					self.state = 'Alert'
					ShowMessage(self.owner.GetName() + ' is now Alert.', scenario_highlight=(self.owner.hx, self.owner.hy))
					return
			AISpyMsg(self.owner.unit_id + ' is Lax, no action taken.')
			return
		
		elif self.state == 'Stunned':
			roll = GetPercentileRoll()
			if roll <= 15.0:
				self.state = 'Alert'
				ShowMessage(self.owner.GetName() + ' has recovered from being Stunned.', scenario_highlight=(self.owner.hx, self.owner.hy))
				return
		
		elif self.state == 'Alert' and not defensive_fire:
			if adjacent_enemies >= 1:
				roll = GetPercentileRoll()
				
				if roll <= float(adjacent_enemies) * 1.0:
					self.state = 'Heroic'
					ShowMessage(self.owner.GetName() + ' is now Heroic.', scenario_highlight=(self.owner.hx, self.owner.hy))
		
		
		# 2) Determine if a attitude change is triggered
		################################################
		if self.attitude != 'Withdraw' and not defensive_fire:
			if campaign_day.ended and self.owner.owning_player == 1:
				if GetPercentileRoll() <= 25.0:
					self.attitude = 'Withdraw'
					AISpyMsg(self.owner.unit_id + ' now withdrawing')
		elif self.owner.routed:
			self.attitude = 'Withdraw'
		
		
		# 3) Determine if a compulsary action is required
		#################################################
		if self.attitude == 'Withdraw' and not defensive_fire:
			if GetPercentileRoll() <= 10.0:
				ShowMessage(self.owner.GetName() + ' withdraws from the battlefield.', scenario_highlight=(self.owner.hx, self.owner.hy))
				self.owner.DestroyMe(no_vp=True)
				return
		
		
		# 4) Score all possible actions
		###############################
		
		action_list = []
		
		# Surrender - enemy only for now
		if self.owner.owning_player == 1 and not defensive_fire:
			
			score = 0.0
			
			if self.owner.routed:
				score += 25.0
			elif self.owner.reduced:
				score += 15.0
			elif self.owner.immobilized:
				score += 10.0
			
			if self.attitude == 'Withdraw' and not campaign_day.ended:
				score += 10.0
			
			if self.state == 'Stunned':
				score += 15.0
			
			if self.owner.entrenched or self.owner.fortified:
				score = round(score * 0.5, 2)
			
			if adjacent_enemies == 0:
				score = round(score * 0.25, 2)
			else:
				score += score * (float(adjacent_enemies) * 0.5)
			
			if self.state == 'Heroic':
				score = round(score * 0.1, 2)
			
			if self.owner.GetStat('category') == 'Train Car':
				score = 0.0
			
			if score > 0.0:
				action_list.append((score, ['Surrender']))
		
		
		# Dig-in
		if self.owner.GetStat('category') in ['Infantry', 'Gun'] and not defensive_fire:
			if not self.owner.dug_in and not self.owner.entrenched and not self.owner.fortified:
				score = (adjacent_enemies * 15.0) + float(libtcod.random_get_int(0, 0, 5))
				
				if self.attitude != 'Hold':
					score -= 20.0
				
				if score > AI_ACTION_MIN:
					action_list.append((score, ['Dig In']))
		
		
		# Unload passengers
		if self.owner.transport is not None and not defensive_fire and self.state != 'Stunned':
			if self.owner.owning_player == 0 or current_distance <= 1:
				action_list.append((90.0, ['Unload Passengers']))
		
		
		# Fire attacks
		enemies_out_of_range = True
		if len(self.owner.weapon_list) > 0 and current_distance <= 3 and not self.owner.routed and self.state != 'Stunned':
			
			# build list of possible targets
			target_list = []
			for unit in scenario.units:
				if not unit.alive: continue
				if unit.owning_player == self.owner.owning_player: continue
				target_list.append(unit)
			
			if len(target_list) == 0:
				AISpyMsg('No possible targets for ' + self.owner.unit_id)
			else:
				
				for target in target_list:

					# skip any other possible targets if this is a defensive fire attack
					if defensive_fire:
						if not target.is_player and target not in scenario.player_unit.squad:
							continue
					
					for weapon in self.owner.weapon_list:
						
						# don't allow ballistic weapons to fire in defensive fire
						if defensive_fire:
							if weapon.GetStat('ballistic_attack') is not None:
								continue
						
						# CC weapons need to have a spotted target
						if weapon.GetStat('type') == 'Close Combat' and not target.spotted:
							continue
						
						# make sure that target is in range
						distance = GetHexDistance(self.owner.hx, self.owner.hy, target.hx, target.hy)
						if distance > weapon.max_range:
							continue
						
						enemies_out_of_range = False
						
						# make sure there is LoS if required
						if not self.owner.los_table[target]:
							if weapon.GetStat('ballistic_attack') is None:
								continue
						
						# determine if a pivot or turret rotation would be required
						pivot_req = False
						turret_rotate_req = False
						mount = weapon.GetStat('mount')
						if mount is not None:
							if mount == 'Turret' and self.owner.turret_facing is not None:
								if (target.hx, target.hy) not in weapon.covered_hexes:
									turret_rotate_req = True
							else:
								if (target.hx, target.hy) not in weapon.covered_hexes:
									pivot_req = True
						
						if turret_rotate_req:
							turret = self.owner.GetStat('turret')
							if turret is not None:
								if turret == 'FIXED':
									continue
						if pivot_req:
							if self.owner.immobilized:
								continue
							
							# player squadmates may have already moved with player and can't pivot now
							if self.owner.moving:
								AISpyMsg('Skipped an attack because needed to pivot, and unit moved already')
								continue
							
							# pivot NA during defensive fire
							if defensive_fire:
								continue
						
						ammo_type_list = []
						
						# gun weapons need to check multiple ammo type combinations
						if weapon.GetStat('type') != 'Gun':
							ammo_type_list.append('')
						else:
							ammo_list = weapon.stats['ammo_type_list']
							for ammo_type in ammo_list:
								# skip smoke for now
								if ammo_type == 'Smoke': continue
								
								# make sure 1+ shells are available
								if weapon.ready_rack[ammo_type] == 0 and weapon.ammo_stores[ammo_type] == 0:
									AISpyMsg('Out of ' + ammo_type + ' ammo')
									continue
								
								ammo_type_list.append(ammo_type)
						
						# finally, run through each ammo type (for non-Guns, this will be just '')
						ammo_attack_list = []
						for ammo_type in ammo_type_list:
							
							if ammo_type != '':
								weapon.ammo_type = ammo_type
							
							profile = scenario.CalcAttack(self.owner, weapon, target,
								pivot=pivot_req, turret_rotate=turret_rotate_req)
							
							# attack not possible
							if profile is None:
								text = 'Attack not possible: '
								text += str(weapon.stats['name']) + ' against ' + target.unit_id
								if ammo_type != '':
									text += ' with: ' + ammo_type
								AISpyMsg(text)
								continue
							
							score = profile['final_chance']
							score -= 10.0
							score += float(libtcod.random_get_int(0, 0, 20))
							
							# if target is armoured, apply armour penetration chance to score
							if (weapon.GetStat('type') in ['Gun', 'AT Rifle', 'Close Combat'] or weapon.GetStat('type') in MG_WEAPONS) and target.GetStat('armour') is not None:
								
								# assume best case for ballistic attacks
								if profile['ballistic_attack']:
									profile['result'] = 'CRITICAL HIT'
								
								# check for both hull and turret hit
								profile['location'] = 'Hull'
								hull_profile = scenario.CalcAP(profile)
								hull_hit_modifier = round(hull_profile['final_chance'] / 65.0, 2)
								AISpyMsg('Hull AP modifier: ' + str(hull_hit_modifier))
								
								profile['location'] = 'Turret'
								turret_profile = scenario.CalcAP(profile)
								turret_hit_modifier = round(turret_profile['final_chance'] / 65.0, 2)
								AISpyMsg('Turret AP modifier: ' + str(turret_hit_modifier))
								
								# choose the higher of the two
								modifier = turret_hit_modifier
								if hull_hit_modifier > turret_hit_modifier:
									modifier = hull_hit_modifier
								
								# if little or no chance of penetration, still make it possible to try for a critical hit
								if modifier < 0.15:
									modifier = 0.15
								
								# might be able to injure exposed crew
								if target.is_player and player_crew_vulnerable:
									if ammo_type == 'HE' or weapon.GetStat('type') == 'Close Combat' or weapon.GetStat('type') in MG_WEAPONS:
										modifier = modifier * 3.0
								
								score = score * modifier
							
							
							# apply final score modifiers
							
							# if part of player squad, tend to favour acquired targets of player
							if self.owner in scenario.player_unit.squad:
								for weapon2 in scenario.player_unit.weapon_list:
									if weapon2.acquired_target is None: continue
									if weapon2.acquired_target[0] == target:
										score += 20.0
										break
							
							# avoid small arms on armoured targets and MG attacks unless within AP range
							if not (target.is_player and player_crew_vulnerable):
								if weapon.GetStat('type') not in ['Gun', 'Close Combat'] and target.GetStat('armour') is not None:
									if weapon.GetStat('type') not in MG_WEAPONS:
										score -= 40.0
									elif GetHexDistance(self.owner.hx, self.owner.hy, target.hx, target.hy) > MG_AP_RANGE:
										score -= 40.0
							
							# avoid AP or HEAT attacks on unarmoured targets
							if (ammo_type in AP_AMMO_TYPES or ammo_type == 'HEAT') and target.GetStat('armour') is None:
								if target.GetStat('category') != 'Vehicle':
									score = 0.0
								else:
									# if HE is an option
									if 'HE' in ammo_type_list:
										score -= 25.0
							
							# avoid HE attacks on armoured targets
							if ammo_type == 'HE' and target.GetStat('armour') is not None:
								if not (target.is_player and player_crew_vulnerable):
									score -= 15.0
							
							# avoid close combat attacks if already in a good position
							if weapon.GetStat('type') == 'Close Combat':
								if self.owner.fortified:
									score -= 45.0
								elif self.owner.entrenched:
									score -= 30.0
								elif self.owner.dug_in:
									score -= 20.0
							
							# heroic units more likely to attack
							if self.state == 'Heroic':
								if weapon.GetStat('type') == 'Close Combat':
									score += 30.0
								else:
									score += 15.0
							
							# if ambush is in progress, much more likely to attack
							if scenario.ambush and score > AI_ACTION_MIN:
								score += float(libtcod.random_get_int(0, 30, 50))
							
							# if withdrawing, much less likely to attack
							if self.attitude == 'Withdraw':
								score -= 35.0
							
							# if an acquired target of player, more likely to attack player
							if is_ac and target.is_player:
								if score > 0.0:
									score += 25.0
							
							if DEBUG:
								if target.is_player and session.debug['AI Hates Player']:
									if score > 0.0:
										score += 70.0
							
							# not sure if this is required, but seems to work
							score = round(score, 2)
							
							# add this attack, even if it has a very low score
							ammo_attack_list.append((score, ['Attack', (weapon, target, ammo_type)]))
						
						# choose best ammo to use for this attack
						if len(ammo_attack_list) > 0:
							ammo_attack_list.sort(key=lambda x:x[0], reverse=True)
							action_list.append(ammo_attack_list[0])
		
		
		
		# Move Actions
		if not defensive_fire and self.state != 'Stunned':
			
			# build list of possible destinations
			hex_list = []
			for (hx, hy) in GetHexRing(self.owner.hx, self.owner.hy, 1):
				if (hx, hy) not in scenario.hex_dict: continue
				# don't move into player's hex if enemy
				if self.owner.owning_player == 1 and hx == 0 and hy == 0: continue
				dist = GetHexDistance(0, 0, hx, hy)
				if dist == 4:
					if GetPercentileRoll() <= 75.0:
						continue
				hex_list.append((hx, hy))
			
			move_list = []
			for (hx, hy) in hex_list:
				
				# occupied by enemy unit(s)
				if len(scenario.hex_dict[(hx,hy)].unit_stack) > 0:
					if scenario.hex_dict[(hx,hy)].unit_stack[0].owning_player != self.owner.owning_player:
						AISpyMsg('Avoided an enemy-held hex: ' + str(hx) + ',' + str(hy))
						continue
			
				# base score
				if self.owner.GetStat('category') in ['Vehicle', 'Cavalry']:
					score = 20.0
				else:
					score = 5.0
				score += float(libtcod.random_get_int(0, 0, 5))
				
				# enemy unit
				if self.owner.owning_player == 1:
				
					# moving closer to player
					if dist < current_distance:
				
						if self.owner.GetStat('close_combat_team') is not None:
							score += 70.0
						elif self.owner.transport is not None:
							score += 55.0
						
						if current_distance <= 1:
							score = 0.0
						elif self.attitude == 'Withdraw':
							score = 0.0
					
					# moving away from the player
					elif dist > current_distance:
						
						if current_distance == 3:
							score -= 15.0
						if scenario.ambush:
							score -= 15.0
						
						if self.attitude == 'Withdraw':
							score = 90.0
						if self.state == 'Heroic':
							score -= 25.0
					
					# Move laterally around the player
					else:
						
						if self.attitude == 'Withdraw':
							score -= 10.0
						elif scenario.player_unit.facing is not None:
							if GetFacing(self.owner, scenario.player_unit) == 'Front':
								score += 20.0
				
				# player squadmates don't move on their own
				elif self.owner in scenario.player_unit.squad:
					score = 0.0
				
				# allied unit (not squadmate)
				else:
					
					# units may want to move toward enemy targets
					if ('close_combat_team' in self.owner.stats or enemies_out_of_range) and adjacent_enemies == 0:
						for unit in scenario.units:
							if unit.owning_player == 0: continue
							if GetHexDistance(unit.hx, unit.hy, self.owner.hx, self.owner.hy) == 1: continue
							score += round(30.0 / float(GetHexDistance(unit.hx, unit.hy, hx, hy)), 2)
					
				
				# general movement modifiers
				if self.owner.unit_id == 'HMG Team':
					score -= 20.0
				elif self.owner.dug_in or self.owner.entrenched or self.owner.fortified:
					score -= 20.0
				
				if self.owner.GetStat('category') == 'Gun':
					score = 0.0
				elif self.owner.pinned or self.owner.immobilized:
					score = 0.0
				elif self.owner.GetStat('immobile') is not None:
					score = 0.0
			
				if score > AI_ACTION_MIN:
					move_list.append((score, ['Move', (hx, hy)]))
			
			# if 1+ move actions are possible, copy over the top two
			if len(move_list) > 0:
				move_list.sort(key=lambda x:x[0], reverse=True)
				for entry in move_list[:2]:
					action_list.append(entry)
			
			if not self.owner.routed:
			
				# Reposition in place
				score = 0.0
				if not has_los_to_enemy:
					score += 25.0
				if self.owner.unit_id == 'HMG Team' or self.owner.GetStat('category') == 'Gun':
					score -= 15.0
				
				# modify by current terrain TEM
				tem = self.owner.GetTEM()
				if tem != 0.0:
					score -= round(tem * 0.25, 2)
				
				# non-combat unit
				if len(self.owner.weapon_list) == 0:
					score -= 25.0
				
				if self.owner.dug_in or self.owner.entrenched or self.owner.fortified:
					score = 0.0
				elif self.owner.pinned or self.owner.immobilized:
					score = 0.0
				elif self.owner.GetStat('immobile') is not None:
					score = 0.0
				
				if score > AI_ACTION_MIN:
					action_list.append((score, ['Reposition']))
				
				# pivot to face player
				if self.owner.owning_player == 1:
					if self.owner.facing is not None and GetFacing(scenario.player_unit, self.owner) != 'Front':
					
						score = 25.0 + float(libtcod.random_get_int(0, 0, 5))
						if self.owner.pinned or self.owner.immobilized:
							score = 0.0
						elif self.owner.GetStat('immobile') is not None:
							score = 0.0
						elif len(self.owner.weapon_list) == 0:
							score = 0.0
						if score > AI_ACTION_MIN:
							action_list.append((score, ['Pivot to Player']))
				
				# pivot to face intended target
				elif self.owner.facing is not None:
					if self.intended_target is not None:
						if GetFacing(self.intended_target, self.owner) != 'Front':
							score = 25.0 + float(libtcod.random_get_int(0, 0, 5))
							if self.owner.pinned or self.owner.immobilized:
								score = 0.0
							elif self.owner.GetStat('immobile') is not None:
								score = 0.0
							elif len(self.owner.weapon_list) == 0:
								score = 0.0
							
							if score > AI_ACTION_MIN:
								action_list.append((score, ['Pivot toward', (self.intended_target.hx, self.intended_target.hy)]))
				
						
		# no possible actions
		if len(action_list) == 0:
			AISpyMsg('No possible actions for ' + self.owner.unit_id)
			return
		
		# 5) Rank possible actions, determine winning action, and execute
		#################################################################
		
		AISpyMsg(str(len(action_list)) + ' possible actions for ' + self.owner.unit_id + ':')
		action_list.sort(key=lambda x:x[0], reverse=True)
		if DEBUG:
			n = 1
			for (score, action) in action_list:
				text = '#' + str(n) + ' (' + str(score) + '%): ' + action[0]
				if len(action) > 1:
					
					if action[0] == 'Attack':
						(weapon, target, ammo_type) = action[1]
						text += ' with ' + str(weapon.stats['name']) + ' against ' + target.unit_id
						if ammo_type != '':
							text += ' with: ' + ammo_type
					
					elif action[0] == 'Move':
						(hx, hy) = action[1]
						text += ' to ' + str(hx) + ',' + str(hy)
					
				AISpyMsg(text)
				n += 1
		
		# clear any intended target - would have been used in action calculations
		self.intended_target = None
		
		# run through actions from best to worst, rolling for activation for each one
		for (score, action) in action_list:
			
			# for attack actions, the score might not be high, but we may want to try in a future turn
			if action[0] == 'Attack':
				if score <= AI_ACTION_MIN:
					if self.intended_target is None:
						(weapon, target, ammo_type) = action[1]
						self.intended_target = target
						AISpyMsg('Set intended target as: ' + target.unit_id)
					continue
			
			roll = GetPercentileRoll()
			
			if self.owner.owning_player == 0:
				roll -= 25.0
			elif not campaign.options['realistic_ai']:
				roll += 15.0
			
			if roll > score:
				pass_chance = AI_PASS_TURN_CHANCE
				if self.owner.owning_player != 0 and not campaign.options['realistic_ai']:
					pass_chance += 5.0
				if GetPercentileRoll() <= pass_chance:
					return
				continue
			
			AISpyMsg('Executing action: ' + action[0])
			
			##########################################################
			# Surrender
			
			if action[0] == 'Surrender':
				
				ShowMessage(self.owner.unit_id + ' has surrendered to you.',
					scenario_highlight=(self.owner.hx, self.owner.hy))
				self.owner.DestroyMe(surrender=True)
				
			
			##########################################################
			# Dig In
			
			elif action[0] == 'Dig In':
				
				if self.owner.AttemptDigIn():
					ShowMessage(self.owner.unit_id + ' is now dug-in.',
						scenario_highlight=(self.owner.hx, self.owner.hy))
				
			
			##########################################################
			# Move action
			
			elif action[0] == 'Move':
				
				(hx, hy) = action[1]
				
				# if destination is off-map, remove from game
				if (hx, hy) not in scenario.hex_dict:
					self.owner.RemoveFromPlay()
					return
					
				# turn hull to face destination if required
				if self.owner.facing is not None:
					direction = GetDirectionToAdjacent(self.owner.hx, self.owner.hy, hx, hy)
					self.owner.facing = direction
					if self.owner.turret_facing is not None:
						self.owner.turret_facing = direction
				
				# set statuses
				self.owner.moving = True
				self.owner.dug_in = False
				self.owner.entrenched = False
				self.owner.fortified = False
				self.owner.ClearAcquiredTargets()
				
				# do landmine check
				if self.owner.DoLandmineCheck():
					return
				
				# do movement roll
				chance = self.owner.forward_move_chance + self.owner.forward_move_bonus
				roll = GetPercentileRoll()
				
				# move was successful
				if roll <= chance:
					
					# move was successful but may be cancelled by a breakdown
					if self.owner.BreakdownCheck():
						return
					
					# guns don't move (for now), they are abandoned instead
					if self.owner.GetStat('category') == 'Gun':
						ShowMessage(self.owner.unit_id + ' crew has abandoned their gun.',
							scenario_highlight=(self.owner.hx, self.owner.hy))
						self.owner.DestroyMe(no_vp=True)
						return
					
					# do sound effect
					PlaySoundFor(self.owner, 'movement')
					
					# show message to player
					text = self.owner.GetName() + ' moves'
					dist1 = GetHexDistance(0, 0, self.owner.hx, self.owner.hy)
					dist2 = GetHexDistance(0, 0, hx, hy)
					if dist2 > dist1:
						text += ' further away.'
					elif dist2 < dist1:
						text += ' closer.'
					else:
						text += '.'
					ShowMessage(text, scenario_highlight=(self.owner.hx, self.owner.hy))
					
					# show movement animation if destination is on board
					if dist2 <= 3:
						(x1, y1) = scenario.PlotHex(self.owner.hx, self.owner.hy)
						(x2, y2) = scenario.PlotHex(hx, hy)
						self.owner.animation_cells = GetLine(x1, y1, x2, y2)
						
						# animate movement
						for i in range(6):
							if len(self.owner.animation_cells) > 0:
								self.owner.animation_cells.pop(0)
							scenario.UpdateUnitCon()
							scenario.UpdateScenarioDisplay()
							Wait(15)
						self.owner.animation_cells = []
					
					# clear any bonus and move into new hex
					self.owner.forward_move_chance = BASE_FORWARD_MOVE_CHANCE
					self.owner.forward_move_bonus = 0.0
					scenario.hex_dict[(self.owner.hx, self.owner.hy)].unit_stack.remove(self.owner)
					self.owner.hx = hx
					self.owner.hy = hy
					scenario.hex_dict[(hx, hy)].unit_stack.append(self.owner)
					for weapon in self.owner.weapon_list:
						weapon.UpdateCoveredHexes()
				
				# move was not successful
				else:
					PlaySoundFor(self.owner, 'movement')
					if self.owner.spotted:
						text = self.owner.GetName() + ' moves but not far enough to enter a new hex.'
						ShowMessage(text, scenario_highlight=(self.owner.hx, self.owner.hy))
					self.owner.forward_move_bonus += BASE_MOVE_BONUS
				
				# whether successful or not, generate new terrain, LoS, etc.
				self.owner.GenerateTerrain()
				scenario.GenerateUnitLoS(self.owner)
				self.owner.CheckForHD()
				self.owner.SetSmokeDustLevel()
				
			
			##########################################################
			# Unload passengers action
			
			elif action[0] == 'Unload Passengers':
				
				# spawn passenger unit
				unit = Unit(self.owner.transport)
				unit.owning_player = self.owner.owning_player
				unit.nation = self.owner.nation
				unit.ai = AI(unit)
				unit.GenerateNewPersonnel()
				unit.SpawnAt(self.owner.hx, self.owner.hy)
				scenario.GenerateUnitLoS(unit)
				
				if self.owner.spotted:
					unit.spotted = True
					ShowMessage(self.owner.GetName() + ' has unloaded a ' + unit.GetName() + '!',
						scenario_highlight=(self.owner.hx, self.owner.hy))
				self.owner.transport = None
			
			
			##########################################################
			# Reposition action
			
			elif action[0] == 'Reposition':
				
				if self.owner not in scenario.player_unit.squad and self.owner.spotted:
					ShowMessage(self.owner.GetName() + ' repositions itself.', 
						scenario_highlight=(self.owner.hx, self.owner.hy))
				
				# set statuses
				self.owner.moving = True
				self.owner.dug_in = False
				self.owner.entrenched = False
				self.owner.fortified = False
				self.owner.ClearAcquiredTargets()
				
				if self.owner.BreakdownCheck(): return
				
				self.owner.GenerateTerrain()
				scenario.GenerateUnitLoS(self.owner)
				self.owner.CheckForHD()
				self.owner.SetSmokeDustLevel()
			
			
			##########################################################
			# Pivot to Face Player Action
			
			elif action[0] == 'Pivot to Player':
				
				if self.owner.spotted:
					ShowMessage(self.owner.GetName() + ' pivots to face you.', 
						scenario_highlight=(self.owner.hx, self.owner.hy))
				direction = GetDirectionToward(self.owner.hx, self.owner.hy, 0, 0)
				self.owner.facing = direction
				if self.owner.turret_facing is not None:
					self.owner.turret_facing = direction
				self.owner.ClearAcquiredTargets(no_enemy=True)
			
			
			##########################################################
			# Pivot toward an enemy unit
			
			elif action[0] == 'Pivot toward':
				(hx, hy) = action[1]
				direction = GetDirectionToward(self.owner.hx, self.owner.hy, hx, hy)
				self.owner.facing = direction
				if self.owner.turret_facing is not None:
					self.owner.turret_facing = direction
				self.owner.ClearAcquiredTargets(no_enemy=True)
				AISpyMsg('Pivoted to face: ' + str(hx) + ',' + str(hy))
			
			
			##########################################################
			# Attack action
			
			elif action[0] == 'Attack':
				
				(weapon, target, ammo_type) = action[1]
				
				# pivot or rotate turret if required
				mount = weapon.GetStat('mount')
				if mount is not None and (target.hx, target.hy) not in weapon.covered_hexes:
					
					direction = GetDirectionToward(self.owner.hx, self.owner.hy, target.hx, target.hy)
					
					if mount == 'Turret' and self.owner.turret_facing is not None:
						self.owner.turret_facing = direction
						AISpyMsg('Unit rotated turret to fire') 
					
					elif mount == 'Hull' and self.owner.facing is not None:
						self.owner.facing = direction
						if self.owner.turret_facing is not None:
							self.owner.turret_facing = direction
						self.owner.ClearAcquiredTargets(no_enemy=True)
						AISpyMsg('Unit pivoted hull to fire') 
					
					scenario.UpdateUnitCon()
					scenario.UpdateScenarioDisplay()
					for weapon in self.owner.weapon_list:
						weapon.UpdateCoveredHexes()
				
				# check for need for hull pivot due to blocked firing direction
				# TODO: incorporate this into action scoring
				if mount is not None:
					if mount == 'Turret':
						blocked_dirs = weapon.GetStat('blocked_hull_dirs')
						if blocked_dirs is not None:
							direction = ConstrainDir(self.owner.turret_facing - self.owner.facing)
							if str(direction) in blocked_dirs:
								self.owner.facing = ConstrainDir(self.owner.facing + 3)
								self.owner.ClearAcquiredTargets(no_enemy=True)
								for weapon in self.owner.weapon_list:
									weapon.UpdateCoveredHexes()
				
				# move target to top of hex stack and re-draw screen
				target.MoveToTopOfStack()
				scenario.UpdateUnitCon()
				
				# set ammo type if any
				if weapon.GetStat('type') == 'Gun' and ammo_type != '':
					weapon.ammo_type = ammo_type
					
					# use RR if possible
					if 'ammo_type_list' in weapon.stats:
						weapon.using_rr = False
						if ammo_type in weapon.ready_rack:
							if weapon.ready_rack[ammo_type] > 0:
								weapon.using_rr = True
								AISpyMsg('AI unit using Ready Rack!') 
				
				# show LoS on GUI layer
				scenario.UpdateGuiCon(los_highlight=(self.owner, target))
				scenario.UpdateScenarioDisplay()
				libtcod.console_flush()
				Wait(40)
				
				# do the attack!
				result = self.owner.Attack(weapon, target)
				
				if not result:
					AISpyMsg('ERROR: Tried to attack but it was not possible')
				
			else:
				AISpyMsg('ERROR: Unrecognized action: ' + action[0])
				return
			
			# record this action and return
			self.previous_action = action
			return
		
		AISpyMsg('No actions executed.')
		return
		



# Unit Class: represents a single vehicle or gun, or a squad or small team of infantry
class Unit:
	def __init__(self, unit_id, is_player=False):
		
		self.unit_id = unit_id			# unique ID for unit type
		self.nick_name = ''			# nickname for model, eg. Sherman
		self.unit_name = ''			# name of tank, etc.
		self.owning_player = 0			# unit is allied to 0:player 1:enemy
		self.nation = None			# nationality of unit and personnel
		self.ai = None				# AI controller if any
		self.is_player = is_player		# unit is controlled by player
		self.squad = None			# list of units in player squad
		
		self.positions_list = []		# list of crew/personnel positions
		
		# load unit stats
		if unit_id not in session.unit_types:
			print('ERROR: Could not find unit id: ' + unit_id)
			self.unit_id = None
			return
		self.stats = session.unit_types[unit_id].copy()
		
		if 'nick_name' in self.stats:
			self.nick_name = self.stats['nick_name']
		
		if 'crew_positions' in self.stats:
			for position_dict in self.stats['crew_positions']:
				self.positions_list.append(Position(self, position_dict))
		
		# roll for HVSS if any
		if 'HVSS' in self.stats:
			chance = float(self.stats['HVSS'])
			if GetPercentileRoll() <= chance:
				self.stats['HVSS'] = True
			else:
				del self.stats['HVSS']
		
		# set up weapons
		self.weapon_list = []			# list of unit weapons
		if 'weapon_list' in self.stats:
			for weapon_dict in self.stats['weapon_list']:
				self.weapon_list.append(Weapon(self, weapon_dict))
		
		# placeholders for transport
		self.transport = None
		
		# set up initial scenario statuses
		self.ResetMe()
	
	
	# set/reset all scenario statuses for this unit
	def ResetMe(self):
		
		self.alive = True			# unit is alive
		
		self.hx = 0				# location in scenario hex map
		self.hy = 0
		self.terrain = None			# surrounding terrain
		self.terrain_seed = 0			# seed for terrain depiction greebles
		self.dest_hex = None			# destination hex for move
		self.animation_cells = []		# list of x,y unit console locations for animation
		
		self.los_table = {}			# other units to which this one has line of sight
		self.spotted = False			# unit has been spotted by opposing side
		self.smoke = 0				# unit smoke level
		self.dust = 0				# unit dust level
		
		self.hull_down = []			# list of directions unit in which Hull Down
		self.moving = False
		self.immobilized = False		# vehicle or gun unit is immobilized
		self.overrun = False			# unit is doing an overrun attack (player and player squad only)
		self.bogged = False			# unit is bogged down, cannot move or pivot
		self.fired = False
		self.hit_by_fp = False			# was hit by an effective fp attack this turn
		
		self.facing = None
		self.previous_facing = None
		self.turret_facing = None
		self.previous_turret_facing = None
		
		self.pinned = False
		self.deployed = False
		self.unit_fatigue = 0			# unit fatigue points
		self.reduced = False			# unit has been reduced through casualites
		self.routed = False			# unit has been routed
		
		self.dug_in = False			# unit is dug-in
		self.entrenched = False			# " entrenched
		self.fortified = False			# " fortified
		
		self.forward_move_chance = 0.0		# set by CalculateMoveChances()
		self.reverse_move_chance = 0.0
		self.bog_chance = 0.0			# "
		
		self.forward_move_bonus = 0.0
		self.reverse_move_bonus = 0.0
		
		self.fp_to_resolve = 0			# fp from attacks to be resolved
		self.ap_hits_to_resolve = []		# list of unresolved AP hits
		self.he_hits_to_resolve = []		# " HE hits
		
		for weapon in self.weapon_list:
			weapon.selected_target = None
			weapon.acquired_target = None
	
	
	# reset this unit for new turn
	def ResetForNewTurn(self, skip_smoke=False):
		
		# check for smoke and dust dispersal
		if not skip_smoke:
		
			if self.smoke > 0:
				roll = GetPercentileRoll()
				
				if self.moving:
					roll -= 5.0
				
				if campaign_day.weather['Precipitation'] == 'Rain':
					roll -= 5.0
				elif campaign_day.weather['Precipitation'] == 'Heavy Rain':
					roll -= 15.0
				
				if roll <= 5.0:
					self.smoke -= 1
					
					# show message if player
					if self == scenario.player_unit:
						if self.smoke > 0:
							ShowMessage('Some of the smoke nearby disperses somewhat.')
						else:
							ShowMessage('The smoke nearby has completely dispersed.')
						scenario.UpdatePlayerInfoCon()
			
			if self.dust > 0:
				roll = GetPercentileRoll()
				if not self.moving:
					roll -= 20.0
				if campaign_day.weather['Precipitation'] == 'Rain':
					roll -= 35.0
				elif campaign_day.weather['Precipitation'] == 'Heavy Rain':
					roll -= 55.0
				
				if roll <= 5.0:
					self.dust -= 1
					if self == scenario.player_unit:
						if self.dust > 0:
							ShowMessage('Some of the dust around you has settled.')
						else:
							ShowMessage('The dust around you has completely settled.')
						scenario.UpdatePlayerInfoCon()
		
		self.moving = False
		self.previous_facing = self.facing
		self.previous_turret_facing = self.turret_facing
		
		self.fired = False
		for weapon in self.weapon_list:
			weapon.ResetMe()
		
		# select first player weapon if none selected so far
		if self == scenario.player_unit:
			if scenario.selected_weapon is None:
				scenario.selected_weapon = self.weapon_list[0]
		
		# update crew positions
		for position in self.positions_list:
			
			# update visible hexes
			position.UpdateVisibleHexes()
			
			if position.crewman is None: continue
			
			# check for crew condition or injury change
			position.crewman.DoInjuryCheck()

	
	# check for the value of a stat, return None if stat not present
	def GetStat(self, stat_name):
		if stat_name not in self.stats:
			return None
		return self.stats[stat_name]
	
	
	# returns true if any personel in the list have the given skill
	# for now, player unit only
	def CrewmanHasSkill(self, position_list, skillname):
		if not self.is_player: return False
		for position in self.positions_list:
			if len(position_list) > 0:
				if position.name not in position_list: continue
			if position.crewman is None: continue
			if not position.crewman.alive: continue
			if position.crewman.condition == 'Unconscious': continue
			if skillname in position.crewman.skills:
				return True
		return False
	
	
	# returns the location on the screen of this unit
	def GetScreenLocation(self):
		(x,y) = scenario.PlotHex(self.hx, self.hy)
		if self.overrun: y -= 1
		return (x,y)
	
	
	# check to see whether this unit regains concealment as a result of being out of LoS
	def DoConcealmentCheck(self):
		
		if not self.spotted: return
		if not self.alive: return
		
		# skip if no enemy units remaining
		all_enemies_dead = True
		for unit in scenario.units:
			if unit.owning_player != self.owning_player and unit.alive:
				all_enemies_dead = False
				break
		if all_enemies_dead: return
		
		for unit, los in self.los_table.items():
			if not unit.alive: continue
			if unit.owning_player == self.owning_player: continue
			# unit has LoS to at least one enemy unit
			if los: return
		
		# no LoS to any alive enemy units, may regain concealment
		chance = BASE_RECONCEAL_CHANCE
		if campaign_day.weather['Precipitation'] == 'Rain':
			chance += 10.0
		elif campaign_day.weather['Precipitation'] in ['Heavy Rain', 'Snow']:
			chance += 15.0
		elif campaign_day.weather['Precipitation'] == 'Blizzard':
			chance += 20.0
		roll = GetPercentileRoll()
		if roll <= chance:
			if self.is_player:
				text = 'You are now Unspotted.'
			else:
				text = self.GetName() + ' is now Unspotted.'
			ShowMessage(text, portrait=self.GetStat('portrait'),
				scenario_highlight=(self.hx, self.hy))
			self.spotted = False
			
	
	# clear all ammo loads for all guns in this unit
	def ClearGunAmmo(self):
		for weapon in self.weapon_list:
			if weapon.GetStat('type') != 'Gun': continue
			for ammo_type in AMMO_TYPES:
				if ammo_type in weapon.ammo_stores:
					weapon.ammo_stores[ammo_type] = 0
	
	
	# see if this unit has moved quickly enough to take another move action
	# player only for now
	def ExtraMoveCheck(self):
		chance = 0.0
		if self.GetStat('movement_class') not in ['Fast Tank', 'Fast Wheeled']:
			return False
		chance += 10.0
		
		if self.GetStat('recce') is None:
			return False
		chance += 10.0
		
		if GetPercentileRoll() <= chance:
			return True
		return False

	
	# attempt to dig-in; infantry and guns only
	def AttemptDigIn(self):
		if self.GetStat('category') not in ['Infantry', 'Gun']: return False
		if self.dug_in or self.entrenched or self.fortified: return False
		if 'dug_in_na' in SCENARIO_TERRAIN_EFFECTS[self.terrain]: return False
				
		# determine chance of success
		if self.terrain in ['Wooden Buildings', 'Woods', 'Rubble']:
			chance = 50.0
		elif self.terrain in ['Brush', 'Broken Ground']:
			chance = 30.0
			if campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
				chance = 10.0
		else:
			chance = 15.0
			if campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
				chance = 3.0
		
		# do roll and apply result
		if GetPercentileRoll() <= chance:
			self.dug_in = True
			return True
		return False
	
	
	# do a bog check
	def DoBogCheck(self, forward, pivot=False, reposition=False):
		
		if self.GetStat('category') not in ['Vehicle', 'Gun']:
			return
		
		chance = self.bog_chance
		
		if pivot:
			chance = chance * 0.25
		elif reposition:
			chance = chance * 0.5
		elif not forward:
			chance = chance * 1.5 
		chance = round(chance, 1)
		
		if GetPercentileRoll() <= chance:
			self.bogged = True
	
	
	# attempt to unbog unit
	def DoUnbogCheck(self):
		if not self.bogged: return
		self.moving = True
		if GetPercentileRoll() > self.bog_chance:
			self.bogged = False
			return True
		return False
		
	
	# do a vehicle breakdown check
	def BreakdownCheck(self):
		if self.GetStat('category') not in ['Vehicle']:
			return False
		
		if 'unreliable' in self.stats:
			chance = 3.0
		else:
			chance = 0.8
		
		if campaign_day.weather['Temperature'] == 'Extreme Hot':
			chance += 2.0
		
		# winter weather modifiers
		winter_modifier = True
		if self.nation == 'Finland':
			winter_modifier = False
		elif self.nation == 'Soviet Union' and campaign.today >= '1941.01.01':
			winter_modifier = False
		
		if winter_modifier:
			if campaign_day.weather['Temperature'] == 'Extreme Cold':
				chance += 2.0
			if campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
				chance += 3.0
		
		if chance > 5.0:
			chance = 5.0
		
		roll = GetPercentileRoll()
		if self.CrewmanHasSkill('Driver', 'Mechanic'):
			roll += 1.5
		
		if roll <= chance:
			return True
		return False
	
	
	# check for a landmine hit
	def DoLandmineCheck(self):
		
		if self.GetStat('category') not in ['Vehicle']: return False
		
		if not campaign_day.map_hexes[campaign_day.player_unit_location].landmines:
			return False
		
		roll = GetPercentileRoll()
		
		if self.CrewmanHasSkill(['Driver'], 'Cautious Driver'):
			roll -= 2.0
		
		if roll > LANDMINE_CHANCE:
			return False
		
		# sound effect
		if not (self.owning_player == 1 and not self.spotted):
			PlaySoundFor(self, 'landmine')
		
		# unarmoured vehicles are destroyed here
		if self.GetStat('armour') is None:
			self.DestroyMe(no_vp=True)
			if self.is_player:
				ShowMessage('You have hit a landmine! The explosion rips your ' +
					'vehicle apart.')
			elif self.owning_player == 1 and self.spotted:
				ShowMessage(self.GetName() + ' was destroyed by a landmine.')
			return True
		
		roll = GetPercentileRoll()
		
		if roll > LANDMINE_KO_CHANCE:
			if self.is_player:
				ShowMessage('You have hit a landmine! The explosion shakes your ' +
					'tank but there was no damage.')
			elif self.owning_player == 1 and self.spotted:
				ShowMessage(self.GetName() + ' hit a landmine but appears to have ' +
					'suffered no damage.')
			return False
		
		# tank immobilized
		if self.is_player:
			ShowMessage('You have hit a landmine! The explosion shakes your tank and ' +
				'you stop suddenly. Your tank is immobilized.', longer_pause=True)
		elif self.owning_player == 1 and self.spotted:
			ShowMessage(self.GetName() + ' hit a landmine and was immobilized.')
		self.ImmobilizeMe()
		
		# check for crew injury on player unit
		if self.is_player:
			for position in self.positions_list:
				if position.crewman is None: continue
				if position.location is not None:
					if position.location != 'Hull': continue
				position.crewman.ResolveAttack({'landmine' : True})
				scenario.UpdateCrewInfoCon()
		return True
	
	
	# set a random smoke level for this unit, upon spawn or after move
	# also check for dust generation
	def SetSmokeDustLevel(self):
		
		# smoke
		roll = GetPercentileRoll()
		
		if roll <= 98.0:
			self.smoke = 0
		elif roll <= 99.5:
			self.smoke = 1
		else:
			self.smoke = 2
		
		# dust
		if campaign_day.weather['Ground'] != 'Dry': return
		
		roll = GetPercentileRoll()
		
		if campaign_day.weather['Temperature'] in ['Hot', 'Extreme Hot']:
			if self.moving:
				roll += 25.0
			else:
				roll += 20.0
		if self.terrain in ['Sand', 'Hamada', 'Broken Ground']:
			if self.moving:
				roll += 30.0
			else:
				roll += 15.0
		
		if self.GetStat('category') != 'Vehicle':
			roll -= 25.0
		
		if roll <= 90.0:
			self.dust = 0
		elif roll <= 95.0:
			self.dust = 1
		else:
			self.dust = 2	

	
	# returns list of crew in this unit that are vulnerable to small-arms fire
	def VulnerableCrew(self):
		crew_list = []
		for position in self.positions_list:
			if position.crewman is None: continue
			if not position.crewman.ce: continue
			if not position.crewman.alive: continue
			if position.crewman.condition == 'Unconscious': continue
			crew_list.append(position.crewman)
		return crew_list
		
	
	# return a to-hit modifier given current terrain
	def GetTEM(self):
		
		if self.terrain not in SCENARIO_TERRAIN_EFFECTS: return 0.0
		terrain_dict = SCENARIO_TERRAIN_EFFECTS[self.terrain]
		if 'TEM' not in terrain_dict: return 0.0
		tem_dict = terrain_dict['TEM']
		
		if 'All' in tem_dict: return tem_dict['All']
		
		if self.GetStat('category') == 'Vehicle':
			if 'Vehicle' in tem_dict:
				return tem_dict['Vehicle']
		
		if self.GetStat('category') == 'Infantry':
			if 'Infantry' in tem_dict:
				return tem_dict['Infantry']
		
		# Cavalry use different TEM depending on if they are moving or not
		if self.GetStat('category') == 'Cavalry':
			if self.moving:
				if 'Vehicle' in tem_dict:
					return tem_dict['Vehicle']
			else:
				if 'Infantry' in tem_dict:
					return tem_dict['Infantry']
		
		if self.GetStat('category') == 'Gun':
			if self.deployed:
				if 'Deployed Gun' in tem_dict:
					return tem_dict['Deployed Gun']
		
		return 0.0
	
	
	# get a descriptive name of this unit
	def GetName(self):
		if self.owning_player == 1 and not self.spotted:
			return 'Unspotted Unit'
		return self.unit_id
	
	
	# return the person in the given position
	def GetPersonnelByPosition(self, position_name):
		for position in self.positions_list:
			if position.crewman is None: continue
			if position.name == position_name:
				return position.crewman
		return None
	
	
	# clear any acquired target from this unit, and clear it from any enemy unit
	# if no_enemy, enemy units retain AC on this unit
	def ClearAcquiredTargets(self, no_enemy=False):
		for weapon in self.weapon_list:
			weapon.acquired_target = None
		if no_enemy: return
		for unit in scenario.units:
			if unit.owning_player == self.owning_player: continue
			for weapon in unit.weapon_list:
				if weapon.acquired_target is None: continue
				(ac_target, level) = weapon.acquired_target
				if ac_target == self:
					weapon.acquired_target = None
		
	
	# calculate chances of a successful forward/reverse move action for this unit
	# also calculate bog chances
	# Infantry and Cavalry will never be Bogged Down
	def CalculateMoveChances(self):
		
		# set values to base values
		self.forward_move_chance = BASE_FORWARD_MOVE_CHANCE
		self.reverse_move_chance = BASE_REVERSE_MOVE_CHANCE
		self.bog_chance = 0.3
		
		# apply modifier from unit movement type
		movement_class = self.GetStat('movement_class')
		if movement_class == 'Slow Tank':
			self.forward_move_chance -= 15.0
			self.bog_chance += 1.0
		elif movement_class == 'Fast Tank':
			self.forward_move_chance += 10.0
		elif movement_class == 'Half-Tracked':
			self.forward_move_chance += 5.0
			self.bog_chance -= 0.5
		elif movement_class == 'Wheeled':
			self.forward_move_chance += 5.0
			self.bog_chance += 2.0
		elif movement_class == 'Fast Wheeled':
			self.forward_move_chance += 15.0
			self.bog_chance += 3.0
		elif movement_class == 'Cavalry':
			self.forward_move_chance += 25.0
			self.bog_chance = 0.0
		
		if self.GetStat('powerful_engine') is not None:
			self.forward_move_chance += 5.0
			self.bog_chance -= 0.5
		if self.GetStat('HVSS') is not None:
			self.forward_move_chance += 10.0
			self.reverse_move_chance += 10.0
			self.bog_chance -= 1.5
		
		# apply modifier from current terrain type
		if self.terrain is not None:
			
			# off-road vehicles not affected by terrain
			if self.GetStat('off_road') is None:
			
				if 'Movement Mod' in SCENARIO_TERRAIN_EFFECTS[self.terrain]:
					mod = SCENARIO_TERRAIN_EFFECTS[self.terrain]['Movement Mod']
					self.forward_move_chance += mod
					self.reverse_move_chance += mod
				if 'Bog Mod' in SCENARIO_TERRAIN_EFFECTS[self.terrain]:
					mod = SCENARIO_TERRAIN_EFFECTS[self.terrain]['Bog Mod']
					self.bog_chance += mod

		# apply modifiers for ground conditions
		if campaign_day.weather['Ground'] != 'Dry':
			mod = 0.0
			bog_mod = 0.0
			if campaign_day.weather['Ground'] == 'Deep Snow':
				if movement_class in ['Fast Wheeled', 'Wheeled']:
					mod = -45.0
					bog_mod = 4.0
				elif movement_class == 'Half-Tracked':
					mod = -20.0
					bog_mod = 1.0
				else:
					mod = -30.0
					bog_mod = 2.0
			elif campaign_day.weather['Ground'] in ['Muddy', 'Snow']:
				if movement_class in ['Fast Wheeled', 'Wheeled']:
					mod = -25.0
					bog_mod = 2.0
				elif movement_class == 'Half-Tracked':
					mod = -10.0
					bog_mod = 0.5
				else:
					mod = -15.0
					bog_mod = 1.0
			
			if campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
				if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Motti'):
					bog_mod = round(bog_mod * 0.5, 1)
			
			self.forward_move_chance += mod
			self.reverse_move_chance += mod
			self.bog_chance += bog_mod
		
		# ground pressure modifier
		gp = self.GetStat('ground_pressure')
		if gp is not None:
			if gp == 'Light':
				self.bog_chance = round(self.bog_chance * 0.8, 1)
			elif gp == 'Heavy':
				self.bog_chance = round(self.bog_chance * 1.2, 1)
				
		# add bonuses from previous moves
		self.forward_move_chance += self.forward_move_bonus
		self.reverse_move_chance += self.reverse_move_bonus
		
		if self.GetStat('category') == 'Vehicle':
		
			# add bonuses from commander direction
			for position in ['Commander', 'Commander/Gunner']:
				crewman = self.GetPersonnelByPosition(position)
				if crewman is not None:
					if crewman.current_cmd == 'Direct Movement':
						mod = crewman.GetSkillMod(15.0)
						if not crewman.ce: mod = mod * 0.5
						self.forward_move_chance += mod
						mod = crewman.GetSkillMod(10.0)
						if not crewman.ce: mod = mod * 0.5
						self.reverse_move_chance += mod
					break
			
			# apply modifier for untrained driver
			crewman = self.GetPersonnelByPosition('Driver')
			if crewman is not None:
				if crewman.UntrainedPosition():
					self.forward_move_chance = self.forward_move_chance * 0.4
					self.reverse_move_chance = self.reverse_move_chance * 0.4
				
				# driver skill
				elif 'Cautious Driver' in crewman.skills:
					self.bog_chance = self.bog_chance * 0.5
				
				# penalty for moving into specific terrain
				if crewman.current_cmd == 'Drive Into Terrain':
					self.forward_move_chance = self.forward_move_chance * 0.8
					self.reverse_move_chance = self.reverse_move_chance * 0.8
				
				# crew fatigue modifier
				if crewman.fatigue > 0:
					self.bog_chance += 0.5 * crewman.fatigue
					
		
		# limit chances
		self.forward_move_chance = RestrictChance(self.forward_move_chance)
		self.reverse_move_chance = RestrictChance(self.reverse_move_chance)
		self.bog_chance = round(self.bog_chance, 1)
		
		if self.bog_chance < 0.1:
			self.bog_chance = 0.1
		elif self.bog_chance > 97.0:
			self.bog_chance = 97.0
	
	
	# calculate current chance of this unit gaining Hull Down
	def GetHDChance(self, driver_attempt=False):
		
		# unit not eligible for HD
		if self.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']: return 0.0
		if self.overrun: return 0.0
		
		# calculate base chance of HD
		if self.terrain not in SCENARIO_TERRAIN_EFFECTS: return 0.0
		chance = SCENARIO_TERRAIN_EFFECTS[self.terrain]['HD Chance']
		
		# apply size modifier
		size_class = self.GetStat('size_class')
		if size_class is not None:
			chance += HD_SIZE_MOD[size_class]
		
		# bonus for driver action and commander direction if any
		if driver_attempt:
			crewman = self.GetPersonnelByPosition('Driver')
			if crewman is not None:
				
				# check for operating crewman in untrained position
				if crewman.UntrainedPosition():
					mod = -20.0
				else:
					mod = crewman.GetSkillMod(6.0)
					if not crewman.ce: mod = mod * 0.5
				chance += mod
			
			for position in ['Commander', 'Commander/Gunner']:
				crewman = self.GetPersonnelByPosition(position)
				if crewman is None: continue
				if crewman.current_cmd == 'Direct Movement':
					if 'Lay of the Land' in crewman.skills:
						mod = crewman.GetSkillMod(15.0)
						if not crewman.ce: mod = mod * 0.5
						chance += mod
					else:
						mod = crewman.GetSkillMod(5.0)
						if not crewman.ce: mod = mod * 0.5
						chance += mod
				break
		
		# regular move action
		else:
			crewman = self.GetPersonnelByPosition('Driver')
			if crewman is not None:
				if 'Eye for Cover' in crewman.skills and not crewman.UntrainedPosition():
					mod = crewman.GetSkillMod(5.0)
					if not crewman.ce: mod = mod * 0.5
					chance += mod
		
		return RestrictChance(chance)
	
	
	# upon spawning into a scenario map hex, or after moving or repositioning, roll to
	# see if this unit gains HD status
	# if driver_attempt is True, then the driver is actively trying to get HD
	def CheckForHD(self, driver_attempt=False):
		
		if self.GetStat('category') != 'Vehicle': return
		
		# clear any previous HD status
		self.hull_down = []
		
		chance = self.GetHDChance(driver_attempt=driver_attempt)
		
		if chance == 0.0: return False
		
		roll = GetPercentileRoll()
		
		# check for debug flag
		if self == scenario.player_unit and DEBUG:
			if session.debug['Player Always HD']:
				roll = 1.0
		
		if roll > chance: return False
		
		if driver_attempt:
			direction = self.facing
		else:
			direction = choice(range(6))
		self.hull_down = [direction]
		self.hull_down.append(ConstrainDir(direction + 1))
		self.hull_down.append(ConstrainDir(direction - 1))
		return True
	
	
	# build lists of possible commands for each personnel in this unit
	def BuildCmdLists(self):
		for position in self.positions_list:
			if position.crewman is None: continue
			position.crewman.BuildCommandList()
			
			# cancel current command if no longer possible
			if position.crewman.current_cmd not in position.crewman.cmd_list:
				position.crewman.current_cmd = position.crewman.cmd_list[0]
	
	
	# do a round of spotting from the player unit
	def DoSpotChecks(self):
			
		# unit out of play range
		if GetHexDistance(0, 0, self.hx, self.hy) > 3:
			return
		
		# create a local list of crew positions in a random order
		position_list = sample(self.positions_list, len(self.positions_list))
		
		for position in position_list:
			
			# no crewman in position
			if position.crewman is None:
				continue
			
			# build list of units that it's possible to spot
			spot_list = []
			for unit in scenario.units:
				if unit.owning_player == self.owning_player: continue
				if not unit.alive: continue
				if unit.spotted: continue
				if (unit.hx, unit.hy) not in position.visible_hexes: continue
				if not self.los_table[unit]: continue
				spot_list.append(unit)
			
			# no units possible to spot from this position
			if len(spot_list) == 0: continue
			
			# select a random target unit and attempt to reveal it
			unit = choice(spot_list)
			chance = scenario.CalcSpotChance(self, unit, crewman=position.crewman)
			if GetPercentileRoll() > chance: continue
			
			unit.SpotMe()
			scenario.UpdateUnitCon()
			scenario.UpdateScenarioDisplay()
			
			# display message
			# FUTURE: use special pop-up display for player crew spotting enemies
			
			# specify if it was an allied unit that did the spotting
			if self != scenario.player_unit:
				text = 'A squadmate reports: '
			else:
				text = ''
			text += unit.GetName() + ' spotted!'
			ShowMessage(text, portrait=unit.GetStat('portrait'),
				scenario_highlight=(unit.hx, unit.hy))
	
	
	# reveal this unit after being spotted
	def SpotMe(self):
		self.spotted = True
		if self.is_player: DisplayTimeInfo(scen_time_con)
	
	
	# generate new personnel sufficent to fill all personnel positions
	def GenerateNewPersonnel(self):
		for position in self.positions_list:
			if position.crewman is not None: continue
			position.crewman = Personnel(self, self.nation, position)
		
		# check for player commander
		if not self.is_player: return
		if not campaign.options['permadeath']: return
		
		player_commander_present = False
		for position in self.positions_list:
			if position.crewman is None: continue
			if position.crewman.is_player_commander:
				player_commander_present = True
				break
		if player_commander_present: return
		
		for position in self.positions_list:
			if position.crewman is None: continue
			if position.name not in PLAYER_POSITIONS: continue
			position.crewman.is_player_commander = True
			return
		
	
	# spawn this unit into the given scenario map hex
	def SpawnAt(self, hx, hy):
		self.hx = hx
		self.hy = hy
		
		scenario.units.append(self)
		for map_hex in scenario.map_hexes:
			if map_hex.hx == hx and map_hex.hy == hy:
				map_hex.unit_stack.append(self)
				break
		
		self.GenerateTerrain()
		self.CheckForHD()
		self.SetSmokeDustLevel()
	
	
	# randomly determine what kind of terrain this unit is in
	# possible to set a target terrain type
	def GenerateTerrain(self, target_terrain=None):
		
		if target_terrain is not None:
			(terrain, odds) = target_terrain
			if GetPercentileRoll() <= odds:
				self.terrain = terrain
				self.terrain_seed = libtcod.random_get_int(0, 1, 128)
				if self.is_player:
					ShowSimpleMessage('Success, moving into terrain: ' + self.terrain)
				return
		
		self.terrain = None
		self.terrain_seed = 0
		
		if scenario is None: return
		
		self.terrain_seed = libtcod.random_get_int(0, 1, 128)
		odds_dict = CD_TERRAIN_TYPES[scenario.cd_map_hex.terrain_type]['scenario_terrain_odds']
		
		# keep rolling until we find a suitable terrain type
		for tries in range(300):
			terrain, odds = choice(list(odds_dict.items()))
			
			# some scenario terrain is never used in some regions
			if campaign.stats['region'] == 'North Africa':
				if terrain in ['Woods', 'Wooden Buildings', 'Fields', 'Marsh']: continue
			
			if GetPercentileRoll() <= odds:
				self.terrain = terrain
				
				# check to see if dug-in is N/A in this terrain and cancel
				if self.dug_in:
					if 'dug_in_na' in SCENARIO_TERRAIN_EFFECTS[self.terrain]:
						self.dug_in = False
				
				if target_terrain is not None and self.is_player:
					# got lucky!
					if target_terrain[0] == self.terrain:
						ShowSimpleMessage('Success, moving into terrain: ' + self.terrain)
					else:
						ShowSimpleMessage('Check failed, moving into terrain: ' + self.terrain)
				
				return
		
		# if we get here, something has gone wrong, so hopefully the first terrain type is always ok
		for terrain, odds in odds_dict.items():
			self.terrain = terrain
			return
	
	
	# move this unit to the top of its current hex stack
	def MoveToTopOfStack(self):
		map_hex = scenario.hex_dict[(self.hx, self.hy)]
		if len(map_hex.unit_stack) == 1: return
		if self not in map_hex.unit_stack: return
		map_hex.unit_stack.remove(self)
		map_hex.unit_stack.insert(0, self)
	
	
	# remove this unit from the scenario
	def RemoveFromPlay(self):
		scenario.hex_dict[(self.hx, self.hy)].unit_stack.remove(self)
		scenario.units.remove(self)
	
	
	# return the display character to use on the map viewport
	def GetDisplayChar(self):
		# player unit
		if self.is_player: return '@'
		
		# unknown enemy unit
		if self.owning_player == 1 and not self.spotted: return '?'
		
		if 'Team' in self.GetStat('class'): return 178
		
		unit_category = self.GetStat('category')
		if unit_category == 'Infantry': return 176
		if unit_category == 'Cavalry': return 252
		if unit_category == 'Train Car': return 7
		
		# gun, set according to deployed status / hull facing
		if unit_category == 'Gun':
			if self.facing is None:		# facing not yet set
				return '!'
			if not self.deployed:
				return 124
			elif self.facing in [5, 0, 1]:
				return 232
			elif self.facing in [2, 3, 4]:
				return 233
			else:
				return '!'		# should not happen
		
		# vehicle
		if unit_category == 'Vehicle':
			
			# turretless vehicle
			if self.turret_facing is None:
				return 249
			return 9

		# default
		return '!'
	
	
	# draw this unit to the scenario unit layer console
	def DrawMe(self, x_offset, y_offset):
		
		# don't display if not alive any more
		if not self.alive: return
		
		# determine draw location
		if len(self.animation_cells) > 0:
			(x,y) = self.animation_cells[0]
		else:
			(x,y) = scenario.PlotHex(self.hx, self.hy)
		
		if self.overrun:
			y -= 1
		
		# armoured trains have to be drawn in middle of hex, no room otherwise
		if self.GetStat('class') != 'Armoured Train Car':
			x += x_offset
			y += y_offset
		
		# determine background colour to use
		distance = GetHexDistance(0, 0, self.hx, self.hy)
		if 4 - distance <= campaign_day.weather['Fog']:
			bg_col = libtcod.Color(128,128,128)
		elif campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
			bg_col = libtcod.Color(158,158,158)
		elif campaign.stats['region'] == 'North Africa':
			bg_col = libtcod.Color(102,82,51)
		else:
			bg_col = libtcod.Color(0,64,0)
		
		# draw terrain greebles - don't draw if currently moving or offset
		if x_offset == 0 and len(self.animation_cells) == 0 and self.terrain is not None and not (self.owning_player == 1 and not self.spotted):
			generator = libtcod.random_new_from_seed(self.terrain_seed)
			
			if self.terrain == 'Open Ground':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if campaign.stats['region'] == 'North Africa':
						break
					if libtcod.random_get_int(generator, 1, 9) <= 2: continue
					c_mod = libtcod.random_get_int(generator, 0, 20)
					col = libtcod.Color(30+c_mod, 90+c_mod, 20+c_mod)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, 46, col, bg_col)
				
			elif self.terrain == 'Broken Ground':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) <= 2: continue
					c_mod = libtcod.random_get_int(generator, 10, 40)
					col = libtcod.Color(70+c_mod, 60+c_mod, 40+c_mod)
					if libtcod.random_get_int(generator, 1, 10) <= 4:
						char = 247
					else:
						char = 240
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, char, col, bg_col)

			elif self.terrain == 'Brush':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) <= 3: continue
					if campaign.stats['region'] == 'North Africa':
						col = libtcod.Color(32,64,0)
					else:
						col = libtcod.Color(0,libtcod.random_get_int(generator, 80, 120),0)
					if libtcod.random_get_int(generator, 1, 10) <= 6:
						char = 15
					else:
						char = 37
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, char, col, bg_col)
				
			elif self.terrain == 'Woods':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) == 1: continue
					col = libtcod.Color(0,libtcod.random_get_int(generator, 100, 170),0)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, 6, col, bg_col)
					
			elif self.terrain in ['Wooden Buildings', 'Stone Buildings']:
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					c_mod = libtcod.random_get_int(generator, 10, 40)
					if self.terrain == 'Wooden Buildings':
						col = libtcod.Color(70+c_mod, 60+c_mod, 40+c_mod)
					else:
						col = libtcod.Color(190+c_mod, 170+c_mod, 140+c_mod)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, 249, col, bg_col)
			
			elif self.terrain == 'Hills':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) <= 3: continue
					if campaign.stats['region'] == 'North Africa':
						c_mod = libtcod.random_get_int(generator, -15, 15)
						col = libtcod.Color(160+c_mod,130+c_mod,100+c_mod)
					else:
						c_mod = libtcod.random_get_int(generator, 10, 40)
						col = libtcod.Color(20+c_mod, 110+c_mod, 20+c_mod)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, 220, col, bg_col)
				
			elif self.terrain == 'Fields':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) == 1: continue
					if campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
						c = libtcod.random_get_int(generator, 20, 90)
					else:
						c = libtcod.random_get_int(generator, 120, 190)
					col = libtcod.Color(c, c, 0)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod,
						176, col, bg_col)
			
			elif self.terrain == 'Marsh':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) == 1: continue
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, 176,
						libtcod.Color(45,0,180), bg_col)
			
			elif self.terrain == 'Rubble':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) <= 2: continue
					if libtcod.random_get_int(generator, 1, 3) == 1:
						char = 249
					else:
						char = 250
					c = libtcod.random_get_int(generator, 120, 190)
					col = libtcod.Color(c, c, c)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, char,
						col, bg_col)
			
			elif self.terrain == 'Hamada':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					if libtcod.random_get_int(generator, 1, 9) <= 2: continue
					if libtcod.random_get_int(generator, 1, 3) <= 2:
						char = 177
					else:
						char = 250
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, char,
						libtcod.Color(51,51,51), bg_col)
			
			elif self.terrain == 'Sand':
				for (xmod, ymod) in GREEBLE_LOCATIONS:
					c = libtcod.random_get_int(generator, 130, 150)
					libtcod.console_put_char_ex(unit_con, x+xmod, y+ymod, 176,
						libtcod.Color(c,c,0), bg_col)
		
		# determine foreground color to use
		if self.owning_player == 1:
			col = ENEMY_UNIT_COL
			if self in scenario.player_unit.los_table:
				if not scenario.player_unit.los_table[self]:
					col = libtcod.Color(32,32,32)	
		else:	
			if self == scenario.player_unit:
				col = libtcod.white
			else:
				col = ALLIED_UNIT_COL
		
		# armoured trains have more display characters
		if self.GetStat('class') == 'Armoured Train Car' and not (self.owning_player == 1 and not self.spotted):
			for x1 in range(x-4, x+5):
				libtcod.console_put_char_ex(unit_con, x1, y, 35, libtcod.dark_grey, bg_col)
			for x1 in range(x-1, x+2):
				libtcod.console_put_char_ex(unit_con, x1, y, 219, libtcod.grey, bg_col)
			
		# draw main display character
		libtcod.console_put_char_ex(unit_con, x, y, self.GetDisplayChar(), col, bg_col)
		
		# draw smoke or dust,but don't draw if currently moving
		if x_offset == 0 and len(self.animation_cells) == 0:
			if self.smoke > 0:
				if self.smoke == 1:
					smoke_col = libtcod.dark_grey
				else:
					smoke_col = libtcod.darker_grey
				libtcod.console_put_char_ex(unit_con, x-1, y-1, 247, libtcod.light_grey, smoke_col)
				libtcod.console_put_char_ex(unit_con, x+1, y-1, 247, libtcod.light_grey, smoke_col)
				libtcod.console_put_char_ex(unit_con, x-1, y+1, 247, libtcod.light_grey, smoke_col)
				libtcod.console_put_char_ex(unit_con, x+1, y+1, 247, libtcod.light_grey, smoke_col)
		
			elif self.dust > 0:
				if self.dust == 1:
					dust_col = libtcod.sepia
				else:
					dust_col = libtcod.light_sepia
				libtcod.console_put_char_ex(unit_con, x-1, y-1, 247, dust_col, bg_col)
				libtcod.console_put_char_ex(unit_con, x+1, y-1, 247, dust_col, bg_col)
				libtcod.console_put_char_ex(unit_con, x-1, y+1, 247, dust_col, bg_col)
				libtcod.console_put_char_ex(unit_con, x+1, y+1, 247, dust_col, bg_col)
		
		
		# don't draw anything else for concealed enemy units
		if self.owning_player == 1 and not self.spotted: return
		
		# determine if we need to display a turret / gun depiction
		draw_turret = True
		
		if self.GetStat('category') in ['Infantry', 'Cavalry']: draw_turret = False
		if self.GetStat('category') == 'Gun' and not self.deployed: draw_turret = False
		if len(self.weapon_list) == 0: draw_turret = False
		
		if draw_turret:
			# use turret facing if present, otherwise hull facing
			if self.turret_facing is not None:
				facing = self.turret_facing
			else:
				facing = self.facing
			
			# determine location to draw turret/gun character
			x_mod, y_mod = PLOT_DIR[facing]
			char = TURRET_CHAR[facing]
			libtcod.console_put_char_ex(unit_con, x+x_mod, y+y_mod, char, col, bg_col)
		
		# not top of stack
		if x_offset != 0: return
		
		# draw depiction of dug-in, entrenched, or fortified here
		if not self.dug_in and not self.entrenched and not self.fortified: return
		
		if self.dug_in:
			libtcod.console_put_char_ex(unit_con, x-1, y, 174, libtcod.dark_sepia, bg_col)
			libtcod.console_put_char_ex(unit_con, x+1, y, 175, libtcod.dark_sepia, bg_col)
		elif self.entrenched:
			libtcod.console_put_char_ex(unit_con, x-1, y, 91, libtcod.dark_sepia, bg_col)
			libtcod.console_put_char_ex(unit_con, x+1, y, 93, libtcod.dark_sepia, bg_col)
		else:
			libtcod.console_put_char_ex(unit_con, x-1, y, 249, libtcod.grey, bg_col)
			libtcod.console_put_char_ex(unit_con, x+1, y, 249, libtcod.grey, bg_col)
	
	
	# calculate the effective firepower from a hit from this unit
	def CalcHEEffectiveFP(self, profile):
		
		effective_fp = float(profile['weapon'].GetEffectiveFP())
						
		# ballistic attack - normally an indirect hit
		if profile['ballistic_attack']:
			if profile['result'] == 'HIT':
				effective_fp = effective_fp * BALLISTIC_HE_FP_MOD
		
		# apply critical hit multiplier
		if profile['result'] == 'CRITICAL HIT':
			effective_fp = effective_fp * 2.0
		
		target = profile['target']
		
		# apply modifiers unless this was a direct hit from a ballistic attack
		if not (profile['ballistic_attack'] and profile['result'] == 'CRITICAL HIT'):
		
			# apply fortified, entrenched, or dug-in modifier
			if target.fortified:
				
				# possible that fortifications are destroyed by impact
				roll = GetPercentileRoll()
				if roll <= effective_fp:
					target.fortified = False
					target.terrain = 'Rubble'
					if target.owning_player == 0 or (target.owning_player == 1 and target.spotted):
						ShowMessage(target.unit_id + "'s fortification has been destroyed.", scenario_highlight=(target.hx, target.hy))
					effective_fp = effective_fp * 4.0
				else:
					effective_fp = effective_fp * 0.1
					profile['modifier'] = 'Target Fortified'
			elif target.entrenched:
				if profile['ballistic_attack'] and profile['result'] == 'CRITICAL HIT':
					effective_fp = effective_fp * 1.25
				else:
					effective_fp = effective_fp * 0.25
				profile['modifier'] = 'Target Entrenched'
			elif target.dug_in:
				if profile['ballistic_attack'] and profile['result'] == 'CRITICAL HIT':
					effective_fp = effective_fp * 1.5
				else:
					effective_fp = effective_fp * 0.5
				profile['modifier'] = 'Target Dug-In'
			
			# Check for HE airburst or hamada effect
			elif target.terrain == 'Woods':
				profile['modifier'] = 'Airburst Effect'
				effective_fp = effective_fp * 1.25
			elif target.terrain == 'Hamada':
				profile['modifier'] = 'Hamada Effect'
				effective_fp = effective_fp * 1.25
			
			# apply ground conditions modifier
			elif campaign_day.weather['Ground'] == 'Deep Snow':
				profile['modifier'] = 'Deep Snow Effect'
				effective_fp = effective_fp * 0.5
			elif campaign_day.weather['Ground'] in ['Muddy', 'Snow']:
				profile['modifier'] = campaign_day.weather['Ground'] + ' Effect'
				effective_fp = effective_fp * 0.75
		
		# round up final effective fp
		effective_fp = int(ceil(effective_fp))
		
		# minimum 1 fp
		if effective_fp < 1:
			effective_fp = 1
		
		return (profile, effective_fp)
		
	
	# initiate an attack from this unit with the specified weapon against the specified target
	def Attack(self, weapon, target):
		
		# make sure correct information has been supplied
		if weapon is None or target is None: return False
		
		# make sure attack is possible
		result = scenario.CheckAttack(self, weapon, target)
		if result != '':
			return False
		
		# if firing weapon is mounted on turret and turret has rotated, all weapons on turret lose acquired target
		if weapon.GetStat('Mount') == 'Turret' and self.turret_facing is not None:
			if self.turret_facing != self.previous_turret_facing:
				for weapon2 in self.weapon_list:
					if weapon2.GetStat('Mount') == 'Turret':
						if weapon2.GetStat('firing_group') == weapon.GetStat('firing_group'):
							weapon2.acquired_target = None
		
		# display message for player
		if not self.is_player:
			text = self.GetName() + ' attacks '
			if target == scenario.player_unit:
				text += 'you'
			else:
				text += target.GetName()
			text += ' with '
			
			if weapon.GetStat('type') == 'Gun' and weapon.GetStat('calibre') is not None:
				text += weapon.GetStat('calibre') + 'mm'
				if weapon.GetStat('long_range') is not None:
					text += ' ' + weapon.GetStat('long_range')
				text += ' Gun'
			else:
				text += weapon.stats['name']

			if weapon.ammo_type is not None:
				text += ' (' + weapon.ammo_type + ')'
			ShowMessage(text, scenario_highlight=(self.hx, self.hy))
				
		# determine if attack profile should be displayed on screen
		display_profile = False
		if self == scenario.player_unit:
			display_profile = True
		elif self.spotted and target == scenario.player_unit:
			display_profile = True
		
		# attack loop, possible to maintain RoF and do multiple attacks within this loop
		attack_finished = False
		while not attack_finished:
			
			fate_point_used = False
			
			# automatically switch to reload from general stores if RR is empty
			if self == scenario.player_unit:
				if weapon.GetStat('type') == 'Gun' and weapon.ammo_type is not None:
					if weapon.using_rr and weapon.ready_rack[weapon.ammo_type] == 0:
						weapon.using_rr = False
						scenario.UpdateContextCon()
						scenario.UpdateScenarioDisplay()
						libtcod.console_flush()
			
			# calculate attack profile
			profile = scenario.CalcAttack(self, weapon, target)
			
			# attack not possible for some reason
			if profile is None:
				print('ERROR: Unable to calculate attack!')
				attack_finished = True
				continue
			
			# display attack profile on screen if player is involved
			if display_profile:
				scenario.DisplayAttack(profile)
				# activate the attack console and display to screen
				scenario.attack_con_active = True
				scenario.UpdateScenarioDisplay()
				
				# wait for player input:
				# player can cancel attack if they were the attacker, or
				# possibly use a fate point if they are the target
				if not weapon.maintained_rof:
					result = WaitForAttackInput(campaign_day.fate_points > 0 and profile['fate_point_allowed'] is True)
					
					if target != scenario.player_unit and result == 'cancel':
						scenario.attack_con_active = False
						return True
					
					if result == 'fate_point':
						fate_point_used = True
			
			# set weapon and unit fired flags
			weapon.fired = True
			self.fired = True
			
			# set flags if initiating a close combat attack
			if profile['type'] == 'Close Combat':
				self.moving = True
				self.dug_in = False
				self.entrenched = False
				self.fortified = False
				self.ClearAcquiredTargets()
			
			# do weapon jam test for player
			if self == scenario.player_unit:
				if weapon.JamTest():
					ShowMessage(weapon.GetStat('name') + ' has jammed!')
					attack_finished = True
					continue
			
			# expend a shell if gun weapon is firing
			if weapon.GetStat('type') == 'Gun' and weapon.ammo_type is not None:
				if weapon.using_rr:
					if weapon.ready_rack[weapon.ammo_type] > 0:
						weapon.ready_rack[weapon.ammo_type] -= 1
					else:
						# if no more RR ammo, default to general stores
						weapon.ammo_stores[weapon.ammo_type] -= 1
						weapon.using_rr = False
				else:
					weapon.ammo_stores[weapon.ammo_type] -= 1
				scenario.UpdateContextCon()
				scenario.UpdateScenarioDisplay()
				libtcod.console_flush()
				
			
			##### Attack Animation and Sound Effects #####
			
			# skip if in fast mode
			if not (DEBUG and session.debug['Fast Mode']):
				
				FlushKeyboardEvents()
				
				if weapon.GetStat('type') == 'Gun':
					scenario.animation['gun_fire_active'] = True
					(x1, y1) = self.GetScreenLocation()
					(x2, y2) = target.GetScreenLocation()
					scenario.animation['gun_fire_line'] = GetLine(x1,y1,x2,y2)
					PlaySoundFor(weapon, 'fire')
					while scenario.animation['gun_fire_active']:
						libtcod.console_flush()
						CheckForAnimationUpdate()
					
					# add explosion effect if HE or HEAT ammo
					# FUTURE: separate animations for each
					if weapon.ammo_type in ['HE', 'HEAT']:
						scenario.animation['bomb_effect'] = (x2, y2)
						scenario.animation['bomb_effect_lifetime'] = 7
						PlaySoundFor(weapon, 'he_explosion')
						while scenario.animation['bomb_effect']:
							libtcod.console_flush()
							CheckForAnimationUpdate()
				
				elif weapon.GetStat('type') == 'Small Arms' or weapon.GetStat('type') in MG_WEAPONS:
					scenario.animation['small_arms_fire_action'] = True
					(x1, y1) = self.GetScreenLocation()
					(x2, y2) = target.GetScreenLocation()
					scenario.animation['small_arms_fire_line'] = GetLine(x1,y1,x2,y2)
					scenario.animation['small_arms_lifetime'] = 12
					PlaySoundFor(weapon, 'fire')
					while scenario.animation['small_arms_fire_action']:
						libtcod.console_flush()
						CheckForAnimationUpdate()
				
				elif weapon.GetStat('type') == 'Close Combat':
					
					if weapon.GetStat('name') == 'Grenades':
						(x, y) = target.GetScreenLocation()
						scenario.animation['grenade_effect'] = (x, y)
						scenario.animation['grenade_effect_lifetime'] = 3
						PlaySoundFor(weapon, 'fire')
						while scenario.animation['grenade_effect'] is not None:
							libtcod.console_flush()
							CheckForAnimationUpdate()
					
					elif weapon.GetStat('name') == 'Flame Thrower':
						(x, y) = target.GetScreenLocation()
						scenario.animation['ft_effect'] = (x, y)
						scenario.animation['ft_effect_lifetime'] = 9
						PlaySoundFor(weapon, 'fire')
						while scenario.animation['ft_effect'] is not None:
							libtcod.console_flush()
							CheckForAnimationUpdate()
					
					elif weapon.GetStat('name') == 'Panzerschreck':
						scenario.animation['psk_fire_action'] = True
						(x1, y1) = self.GetScreenLocation()
						(x2, y2) = target.GetScreenLocation()
						scenario.animation['psk_fire_line'] = GetLine(x1,y1,x2,y2)
						PlaySoundFor(weapon, 'fire')
						while scenario.animation['psk_fire_action']:
							libtcod.console_flush()
							CheckForAnimationUpdate()
			
			# fate point was spent
			if fate_point_used:
				campaign_day.fate_points -= 1
				ShowMessage('The attack missed and had no effect.')
				scenario.attack_con_active = False
				scenario.UpdatePlayerInfoCon()
				scenario.UpdateScenarioDisplay()
				return True
			
			# again, automatically switch to reload from general stores if RR is empty, for RoF
			if self == scenario.player_unit:
				if weapon.GetStat('type') == 'Gun' and weapon.ammo_type is not None:
					if weapon.using_rr and weapon.ready_rack[weapon.ammo_type] == 0:
						weapon.using_rr = False
						scenario.UpdateContextCon()
						scenario.UpdateScenarioDisplay()
						libtcod.console_flush()
			
			# do the roll, display results to the screen, and modify the attack profile
			# also checks for RoF for the player
			profile = scenario.DoAttackRoll(profile)
			
			# add one level of acquired target if firing gun or MG
			if weapon.GetStat('type') == 'Gun' or weapon.GetStat('type') in MG_WEAPONS:
				weapon.AddAcquiredTarget(target)
			
			# breakdown check for player weapons
			if self == scenario.player_unit:
				if weapon.BreakTest():
					PlaySoundFor(None, 'weapon_break')
					ShowNotification(weapon.GetStat('name') + ' has broken down! It may not be used again for the rest of the day.')
					scenario.UpdatePlayerInfoCon()
					attack_finished = True
					weapon.maintained_rof = False
			
			# wait for the player if the attack was displayed
			# if RoF is maintained, may choose to attack again
			attack_finished = True
			if display_profile:
				scenario.UpdateScenarioDisplay()
				
				end_pause = False
				while not end_pause:
					CheckForAnimationUpdate()
					libtcod.console_flush()
					if not GetInputEvent(): continue
					
					key_char = DeKey(chr(key.c).lower())
					
					if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
						end_pause = True
					
					if self == scenario.player_unit:
						if key_char == 'f' and weapon.maintained_rof:
							attack_finished = False
							end_pause = True
			
			# apply results of this attack if any
			
			# check for debug flag
			if DEBUG:
				if session.debug['Attacks Have No Effect']:
					scenario.attack_con_active = False
					scenario.UpdateScenarioDisplay()
					weapon.maintained_rof = False
					return True
			
			# area fire attack
			if profile['type'] == 'Area Fire':
					
				if profile['result'] in ['CRITICAL EFFECT', 'FULL EFFECT', 'PARTIAL EFFECT']:
					target.fp_to_resolve += profile['effective_fp']
					target.hit_by_fp = True
				
				# possible it was converted into an AP MG hit
				elif profile['result'] in ['HIT', 'CRITICAL HIT']:	
					target.ap_hits_to_resolve.append(profile)
					
					# also applies fp
					target.fp_to_resolve += profile['effective_fp']
					target.hit_by_fp = True
				
				# chance that a miss will still reveal a concealed unit
				elif profile['result'] == 'NO EFFECT' and not target.hit_by_fp:
					if GetPercentileRoll() <= MISSED_FP_REVEAL_CHANCE:
						target.hit_by_fp = True
			
			# close combat hit
			elif profile['type'] == 'Close Combat':
				
				if profile['result'] in ['CRITICAL HIT', 'HIT']:
					
					# apply firepower to target
					fp = int(weapon.GetStat('fp'))
					if profile['result'] == 'CRITICAL HIT':
						fp = fp * 2
					target.fp_to_resolve += fp
					target.hit_by_fp = True
					
					# apply an AP hit to an armoured target
					if target.GetStat('armour') is not None:
						target.ap_hits_to_resolve.append(profile)
			
			# point fire hit
			elif profile['type'] == 'Point Fire':
				
				if profile['result'] in ['CRITICAL HIT', 'HIT']:
				
					# record if player scored a hit
					if self == scenario.player_unit:
						campaign_day.AddRecord('Gun Hits', 1)
					
					# add stat if player was hit
					elif target == scenario.player_unit and profile['ammo_type'] != 'Smoke':
						session.ModifySteamStat('hits_taken', 1)
					
					# smoke round
					if profile['ammo_type'] == 'Smoke':
						target.smoke = 2
					
					# infantry, cavalry, or gun target
					elif target.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']:
						
						# if HE hit, apply effective FP
						if profile['ammo_type'] in ['HE', 'HEAT']:
							(profile, effective_fp) = self.CalcHEEffectiveFP(profile)
							target.fp_to_resolve += effective_fp
							target.hit_by_fp = True
						
						# AP hits are very ineffective against infantry/guns, and
						# have no spotting effect
						elif profile['ammo_type'] in AP_AMMO_TYPES:
							target.fp_to_resolve += 1
					
					# unarmoured vehicle target, slightly different procedure
					elif target.GetStat('armour') is None:
						if profile['ammo_type'] in AP_AMMO_TYPES:
							target.ap_hits_to_resolve.append(profile)
						else:
							target.he_hits_to_resolve.append(profile)
							target.hit_by_fp = True
					
					# armoured target
					elif target.GetStat('armour') is not None:
						target.ap_hits_to_resolve.append(profile)
						
						# HE/HEAT also applies firepower to target
						if profile['ammo_type'] in ['HE', 'HEAT']:
							(profile, effective_fp) = self.CalcHEEffectiveFP(profile)
							target.fp_to_resolve += effective_fp
							target.hit_by_fp = True
				
				# chance that a miss will still reveal a concealed unit
				elif profile['ammo_type'] == 'HE' and profile['result'] == 'MISS' and not target.hit_by_fp:
					if GetPercentileRoll() <= MISSED_FP_REVEAL_CHANCE:
						target.hit_by_fp = True
			
			# if player was target but attacker was not spotted, display result as a pop-up message
			if not display_profile and target == scenario.player_unit:
				text = 'Result: ' + profile['result']
				ShowMessage(text, scenario_highlight=(self.hx, self.hy))
			
			# update context console in case we maintained RoF
			scenario.UpdateContextCon()
			scenario.UpdateScenarioDisplay()
			
		# turn off attack console display if any
		scenario.attack_con_active = False
		scenario.UpdateScenarioDisplay()
		
		# reset weapon RoF
		weapon.maintained_rof = False
		
		# check for special weapon depletion
		if weapon.stats['name'] in ['Panzerfaust', 'Panzerfaust Klein', 'Demolition Charge', 'Molotovs']:
			if libtcod.random_get_int(0, 1, 10) > 3:
				self.weapon_list.remove(weapon)
		
		# alert target if lax
		if target.ai is not None:
			if target.ai.state == 'Lax':
				target.ai.state = 'Alert'
		
		# attack is finished
		return True
	
	
	# resolve all unresolve HE hits on this unit - unarmoured vehicles only
	def ResolveHEHits(self):
		if not self.alive: return
		if len(self.he_hits_to_resolve) == 0: return
		if self.GetStat('category') not in ['Vehicle']:
			self.he_hits_to_resolve = []
			return
		if self.GetStat('armour') is not None:
			self.he_hits_to_resolve = []
			return
		
		# determine base odds
		for profile in self.he_hits_to_resolve:
			
			calibre = profile['weapon'].GetStat('calibre')
			if calibre is None:
				continue
			
			profile['type'] = 'he'
			
			calibre = int(calibre)
			if calibre >= 150:
				base_score = 20
			elif calibre >= 120:
				base_score = 18
			elif calibre >= 100:
				base_score = 16
			elif calibre >= 80:
				base_score = 14
			elif calibre >= 70:
				base_score = 12
			elif calibre >= 50:
				base_score = 10
			elif calibre >= 40:
				base_score = 9
			elif calibre >= 30:
				base_score = 8
			elif calibre >= 20:
				base_score = 6
			else:
				continue
			
			if profile['result'] == 'CRITICAL HIT':
				base_score = base_score * 2
			elif profile['ballistic_attack']:
				base_score = int(ceil(base_score * 0.5))
			
			profile['base_chance'] = base_score
			profile['modifier_list'] = []
			profile['final_score'] = base_score
			
			# determine final destruction odds and roll
			if base_score >= 12:
				chance = 100.0
			else:
				chance = Get2D6Odds(base_score)
			profile['final_chance'] = chance
			
			fate_point_used = False
			
			# display and wait if player is involved
			if profile['attacker'] == scenario.player_unit or self == scenario.player_unit:
				scenario.DisplayAttack(profile)
				scenario.attack_con_active = True
				scenario.UpdateScenarioDisplay()
				
				# only wait if outcome is not automatic
				if profile['final_chance'] not in [0.0, 100.0]:
					result = WaitForAttackInput(campaign_day.fate_points > 0 and profile['fate_point_allowed'] is True)
					if result == 'fate_point':
						fate_point_used = True
					
			# fate point was spent
			if fate_point_used:
				campaign_day.fate_points -= 1
				ShowMessage('The HE hit only caused minor damage, no effect.')
				scenario.attack_con_active = False
				scenario.UpdatePlayerInfoCon()
				scenario.UpdateScenarioDisplay()
				continue
			
			# do the attack roll; modifies the attack profile
			profile = scenario.DoAttackRoll(profile)
			
			# wait if player is involved
			if profile['attacker'] == scenario.player_unit or self == scenario.player_unit:
				scenario.UpdateScenarioDisplay()
				WaitForContinue()
			
			# turn off attack console display if any
			scenario.attack_con_active = False
			scenario.UpdateScenarioDisplay()
			
			# no effect
			if profile['result'] == 'NO EFFECT': continue
			
			# show message
			if profile['result'] == 'IMMOBILIZED':
				result_text = 'immobilized'
				
			elif profile['result'] == 'STUNNED':
				result_text = 'stunned'
			else:
				result_text = 'destroyed'
			
			if self == scenario.player_unit:
				text = 'You were '
			else:
				text = self.GetName() + ' was '
			text += result_text + ' by an HE hit from '
			if profile['attacker'] == scenario.player_unit:
				text += 'you.'
			else:
				text += profile['attacker'].GetName() + '.'
			ShowMessage(text)
			
			# apply result
			if profile['result'] == 'IMMOBILIZED':
				self.ImmobilizeMe()
				if self == scenario.player_unit:
					campaign.AddJournal('Tank was immobilized')
					scenario.UpdatePlayerInfoCon()
				scenario.UpdateUnitInfoCon()
				continue
			
			if profile['result'] == 'STUNNED':
				self.ai.state = 'Stunned'
				scenario.UpdateUnitInfoCon()
				continue
			
			if profile['attacker'] == scenario.player_unit:
				campaign.AddJournal('Destroyed a ' + self.GetName() + ' with HE.')
			
			self.DestroyMe(location=profile['location'], dest_weapon=profile['weapon'])
			break
				
		# clear resolved hits
		self.he_hits_to_resolve = []
			
	
	# resolve all unresolved AP hits on this unit
	def ResolveAPHits(self):
		if not self.alive: return
		
		# no hits to resolve! doing fine!
		if len(self.ap_hits_to_resolve) == 0: return
		
		# no effect if infantry, cavalry or gun
		if self.GetStat('category') in ['Infantry', 'Cavalry', 'Gun']:
			self.ap_hits_to_resolve = []
			return
		
		# move to top of hex stack
		self.MoveToTopOfStack()
		scenario.UpdateUnitCon()
		
		# handle AP hits
		for profile in self.ap_hits_to_resolve:
			
			# ballistic hits don't penetrate unless they are a direct hit
			if profile['ballistic_attack'] and profile['result'] != 'CRITICAL HIT':
				continue
			
			profile = scenario.CalcAP(profile)
			
			fate_point_used = False
			
			# display and wait if player is involved
			if profile['attacker'] == scenario.player_unit or self == scenario.player_unit:
				scenario.DisplayAttack(profile)
				scenario.attack_con_active = True
				scenario.UpdateScenarioDisplay()
				
				# only wait if outcome is not automatic
				if profile['final_chance'] not in [0.0, 100.0]:
					result = WaitForAttackInput(campaign_day.fate_points > 0 and profile['fate_point_allowed'] is True)
					if result == 'fate_point':
						fate_point_used = True
					
			# fate point was spent
			if fate_point_used:
				campaign_day.fate_points -= 1
				ShowMessage('The hit did not penetrate.')
				scenario.attack_con_active = False
				scenario.UpdatePlayerInfoCon()
				scenario.UpdateScenarioDisplay()
				continue
			
			# do the attack roll; modifies the attack profile
			profile = scenario.DoAttackRoll(profile)
			
			if profile['result'] == 'NO PENETRATION':
				PlaySoundFor(self, 'armour_save')
			elif profile['result'] == 'PENETRATED':
				PlaySoundFor(self, 'armour_penetrated')
			
			# wait if player is involved
			if profile['attacker'] == scenario.player_unit or self == scenario.player_unit:
				scenario.UpdateScenarioDisplay()
				WaitForContinue()
			
			# turn off attack console display if any
			scenario.attack_con_active = False
			scenario.UpdateScenarioDisplay()
			
			# shock test
			if profile['result'] == 'NO PENETRATION':
				
				# check to see if unit had any acquired targets to begin with
				had_acquired_target = False
				for weapon in self.weapon_list:
					if weapon.acquired_target is not None:
						had_acquired_target = True
						break
				
				if had_acquired_target:
					if GetPercentileRoll() <= profile['final_chance']:
						for weapon in self.weapon_list:
							weapon.acquired_target = None
						if self == scenario.player_unit:
							ShowMessage('The impact has knocked your weapons off target. All acquired targets lost.')
			
			# apply result
			if profile['result'] == 'NO PENETRATION':
				
				# check for stun or recall check
				difference = profile['roll'] - profile['final_chance']
				if profile['final_chance'] == 0.0 or difference < 0.0: continue
				
				# stun check, player unit only
				if self == scenario.player_unit:
					if difference <= AP_STUN_MARGIN:
						for position in self.positions_list:
							if position.crewman is None: continue
							if not position.crewman.DoStunCheck(AP_STUN_MARGIN - difference):
								position.crewman.condition = 'Stunned'
								ShowMessage('Your crewman is Stunned from the impact:',crewman=position.crewman)
				
				# recall check, enemy units only
				elif self.owning_player == 1:
					if profile['location'] == 'Turret' and difference <= AP_RECALL_MARGIN and self.ai.attitude != 'Withdraw':
						roll = GetPercentileRoll()
						if self.GetStat('turret') is not None:
							if self.GetStat('turret') == 'RST':
								roll = round(roll * 0.5, 1)
						if roll <= AP_RECALL_CHANCE :
							self.ai.attitude = 'Withdraw'
					
			elif profile['result'] == 'PENETRATED':
				
				# if the player unit has been penetrated, multiple outcomes are possible
				if self == scenario.player_unit:
					
					# possible outcomes: minor damage, spalling, immobilized, knocked out
					
					# apply roll penalty based on how much original roll passed by
					difference = round((profile['final_chance'] - profile['roll']) * 0.25, 2)
					roll = GetPercentileRoll() + difference
					
					if DEBUG:
						if session.debug['Player Always Penetrated']:
							roll = 100.0
					
					# minor damage
					if roll <= 7.0:
						ShowMessage('Your tank suffers minor damage but is otherwise unharmed.')
						continue
					
					# immobilized
					elif roll <= 25.0 and not scenario.player_unit.immobilized:
						ShowMessage('The hit damages the engine and drivetrain, immobilizing your tank.')
						campaign.AddJournal('Tank was immobilized')
						scenario.player_unit.ImmobilizeMe()
						scenario.UpdatePlayerInfoCon()
						continue
					
					# spalling
					elif roll <= 40.0:
						text = 'The hit shatters the armour plate, sending shards of hot metal into the ' + profile['location']
						ShowMessage(text)
						campaign.AddJournal('Suffered spalling from a hit')
						for position in scenario.player_unit.positions_list:
							
							if position.crewman is None: continue
							
							# only affects turret or hull
							if position.location is not None:
								if position.location != profile['location']: continue
							
							# check for crew injury
							position.crewman.ResolveAttack({'spalling' : True})
							
							scenario.UpdateCrewInfoCon()
						
						continue
					
					# otherwise: destroyed
				
				# display message
				if self == scenario.player_unit:
					text = 'You were'
				else:
					text = self.GetName() + ' was'
				text += ' destroyed by '
				if profile['attacker'] == scenario.player_unit:
					text += 'you.'
				else:
					text += profile['attacker'].GetName() + '.'
				ShowMessage(text)
				
				if profile['attacker'] == scenario.player_unit:
					campaign.AddJournal('Destroyed a ' + self.GetName())
				
				# destroy the unit
				self.DestroyMe(location=profile['location'], dest_weapon=profile['weapon'])
				
				# don't resolve any further hits
				break

		# clear resolved hits
		self.ap_hits_to_resolve = []
	
	
	# resolve FP on this unit if any
	def ResolveFP(self):
		if not self.alive: return
		if self.fp_to_resolve == 0: return
		
		# if unit is not player and fully armoured, skip this
		# FUTURE: will have effect on armoured AI units too
		if not self.is_player and self.GetStat('armour') is not None:
			self.fp_to_resolve = 0
			return
		
		# move to top of hex stack
		self.MoveToTopOfStack()
		scenario.UpdateUnitCon()
		
		# highlight unit and show initial message
		text = 'Resolving ' + str(self.fp_to_resolve) + ' firepower on '
		if self.is_player:
			text += 'you.'
		else:
			text += self.GetName() + '.'
		ShowMessage(text, scenario_highlight=(self.hx, self.hy))
		
		# only do if unit is unarmoured
		if self.GetStat('armour') is None:
		
			concealed = False
			if self.owning_player == 1 and not self.spotted:
				concealed = True
			
			if not concealed:
			
				# create pop-up window
				window_con = libtcod.console_new(26, 30)
				libtcod.console_set_default_background(window_con, libtcod.black)
				libtcod.console_set_default_foreground(window_con, libtcod.white)
				DrawFrame(window_con, 0, 0, 26, 30)
				
				# window title and portrait if any
				libtcod.console_set_default_background(window_con, libtcod.darker_blue)
				libtcod.console_rect(window_con, 1, 1, 24, 2, False, libtcod.BKGND_SET)
				libtcod.console_set_default_background(window_con, libtcod.black)
				
				libtcod.console_print_ex(window_con, 13, 1, libtcod.BKGND_NONE, libtcod.CENTER,
					'Resolving ' + str(self.fp_to_resolve) + ' firepower')
				libtcod.console_print_ex(window_con, 13, 2, libtcod.BKGND_NONE, libtcod.CENTER,
					'on ' + self.GetName())
				
				portrait = self.GetStat('portrait')
				if portrait is not None:
					libtcod.console_blit(LoadXP(portrait), 0, 0, 0, 0, window_con, 1, 3)
				
				# list of possible outcomes
				libtcod.console_print_ex(window_con, 13, 12, libtcod.BKGND_NONE, libtcod.CENTER,
					'Outcome Odds:')
				
				# player can skip pause
				libtcod.console_set_default_foreground(window_con, ACTION_KEY_COL)
				libtcod.console_print(window_con, 8, 28, 'Tab')
				libtcod.console_set_default_foreground(window_con, libtcod.light_grey)
				libtcod.console_print(window_con, 15, 28, 'Continue')
			
			destroy_odds = 0.0
			rout_odds = 0.0
			reduction_odds = 0.0
			
			# fp has a different type of effect on vehicles and armoured trains
			if self.GetStat('category') in ['Vehicle', 'Train Car']:
				
				if self.GetStat('armour') is None:
					for (fp, score) in VEH_FP_TK:
						if fp <= self.fp_to_resolve:
							destroy_odds = score
							break
				else:
					# FUTURE: if vehicle has any unarmoured area, possible that it will be destroyed
					pass
			
			else:
			
				# calculate chance of destruction
				destroy_odds = RESOLVE_FP_BASE_CHANCE
				for i in range(2, self.fp_to_resolve + 1):
					destroy_odds += RESOLVE_FP_CHANCE_STEP * (RESOLVE_FP_CHANCE_MOD ** (i-1)) 
				if self.unit_fatigue > 0:
					destroy_odds += float(self.unit_fatigue) * 5.0
				destroy_odds = RestrictChance(destroy_odds)
				
				# calculate reduction odds if possible
				if 'Team' in self.GetStat('class'):
					destroy_odds += round(destroy_odds * 0.85, 1)
					destroy_odds = RestrictChance(destroy_odds)
				elif self.reduced:
					destroy_odds = RestrictChance(destroy_odds * 1.2)
					destroy_odds = RestrictChance(destroy_odds)
				else:
					reduction_odds = round(destroy_odds * 0.85, 1)
				
				# calculate rout odds if possible
				if not self.routed:
					rout_odds = reduction_odds * 0.50
					if self.fortified:
						rout_odds -= 15.0
					elif self.entrenched:
						rout_odds -= 10.0
					elif self.dug_in:
						rout_odds -= 5.0
					elif self.terrain in ['Wooden Buildings', 'Woods']:
						rout_odds -= 10.0
					if rout_odds < 0.0:
						rout_odds = 0.0
					rout_odds = round(rout_odds, 1)
				else:
					destroy_odds = RestrictChance(destroy_odds * 3.0)
				
				# make sure total is <= 100%
				if destroy_odds + rout_odds + reduction_odds > 100.0:
					if rout_odds > 0.0:
						rout_odds = 100.0 - destroy_odds - reduction_odds
						if rout_odds < 0.0:
							rout_odds = 0.0
				
				if destroy_odds + rout_odds + reduction_odds > 100.0:
					if reduction_odds > 0.0:
						reduction_odds = 100.0 - destroy_odds - rout_odds
						if reduction_odds < 0.0:
							reduction_odds = 0.0
				
				# round final odds
				destroy_odds = round(destroy_odds, 1)
				reduction_odds = round(reduction_odds, 1)
				rout_odds = round(rout_odds, 1)
				
				# add unit fatigue
				self.unit_fatigue += 1
			
			# only display if there are odds of any effect
			if not concealed and destroy_odds + rout_odds + reduction_odds > 0.0:
				
				y = 14
				if destroy_odds > 0.0:
					libtcod.console_print(window_con, 1, y, 'Destroy:')
					libtcod.console_print_ex(window_con, 24, y, libtcod.BKGND_NONE,
						libtcod.RIGHT, str(destroy_odds) + '%')
					y += 1
				
				if reduction_odds > 0.0:
					libtcod.console_print(window_con, 1, y, 'Reduce:')
					libtcod.console_print_ex(window_con, 24, y, libtcod.BKGND_NONE,
						libtcod.RIGHT, str(reduction_odds) + '%')
					y += 1
				
				if rout_odds > 0.0:
					libtcod.console_print(window_con, 1, y, 'Rout:')
					libtcod.console_print_ex(window_con, 24, y, libtcod.BKGND_NONE,
						libtcod.RIGHT, str(rout_odds) + '%')
					y += 1
				
				# blit window to screen and wait
				libtcod.console_blit(window_con, 0, 0, 0, 0, con, WINDOW_XM, WINDOW_YM-14)
				libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
				libtcod.console_flush()
				Wait(300 + (40 * config['ArmCom2'].getint('message_pause')), allow_skip=True, ignore_animations=True)
			
			text = ''
			if destroy_odds + rout_odds + reduction_odds > 0.0:
			
				# do roll
				roll = GetPercentileRoll()
				
				text = ''
				if roll <= destroy_odds:
					text = 'Destroyed'
					campaign.AddJournal(self.GetName() + ' was destroyed.')
				
				elif roll <= destroy_odds + reduction_odds:
					text = 'Reduced'
					campaign.AddJournal(self.GetName() + ' was reduced.')
				
				elif roll <= destroy_odds + reduction_odds + rout_odds:
					text = 'Routed'
					campaign.AddJournal(self.GetName() + ' was routed.')
				
				else:
					# guns, cavalry, and infantry test for pin here
					if self.GetStat('category') in ['Gun', 'Cavalry', 'Infantry'] and not self.pinned:
						self.PinTest(self.fp_to_resolve)
						if self.pinned:
							text = 'Pinned'
						else:
							text = 'No effect'
					else:
						text = 'No effect'
				
				if not concealed:
					libtcod.console_print_ex(window_con, 13, 24, libtcod.BKGND_NONE,
						libtcod.CENTER, 'Roll: ' + str(roll))
					libtcod.console_print_ex(window_con, 13, 25, libtcod.BKGND_NONE,
						libtcod.CENTER, text)
					
					# blit window to screen again and wait
					libtcod.console_blit(window_con, 0, 0, 0, 0, con, WINDOW_XM, WINDOW_YM-14)
					libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
					libtcod.console_flush()
					Wait(400 + (40 * config['ArmCom2'].getint('message_pause')), allow_skip=True, ignore_animations=True)
			
			else:
				ShowMessage('No Effect', scenario_highlight=(self.hx, self.hy))
				self.fp_to_resolve = 0
				return
			
			# pop-up message if unit was concealed
			if concealed:
				ShowMessage('Result: ' + text, scenario_highlight=(self.hx, self.hy))
			
			# apply effect - we wait until here so that messages don't pop up before the window is finished
			if text == 'Destroyed':
				self.DestroyMe()
			elif text == 'Reduced':
				self.ReduceMe()
			elif text == 'Routed':
				self.RoutMe()
		
		# if player unit, check for crew injury
		# FUTURE: also apply to AI units?
		if self == scenario.player_unit:
			result = False
			for position in self.positions_list:
				if position.crewman is None: continue
				if position.crewman.ResolveAttack({'firepower' : self.fp_to_resolve}) is not None:
					scenario.UpdateCrewInfoCon()
					result = True
			if not result:
				ShowMessage('No Effect', scenario_highlight=(self.hx, self.hy))
		
		# clear fp to resolve and return
		self.fp_to_resolve = 0
	
	
	# do a morale check for this unit to recover from Pinned status
	def MoraleCheck(self, modifier):
		
		chance = MORALE_CHECK_BASE_CHANCE + modifier
		
		# apply modifiers
		if self.fortified:
			chance += 50.0
		elif self.entrenched:
			chance += 30.0
		elif self.dug_in:
			chance += 20.0
		elif self.terrain in ['Wooden Buildings', 'Woods']:
			chance += 15.0
		
		chance = RestrictChance(chance)
		
		roll = GetPercentileRoll()
		if roll <= chance:
			return True
		return False
	
	
	# do a pin test on this unit
	def PinTest(self, fp):
		
		# only infantry, cavalry, and guns are subject to pinning
		if self.GetStat('category') not in ['Infantry', 'Cavalry', 'Gun']:
			return False
		
		if self.pinned: return False
		
		chance = float(fp) * 8.0
		
		# apply modifiers
		if self.fortified:
			chance -= 35.0
		elif self.entrenched:
			chance -= 20.0
		elif self.dug_in:
			chance -= 15.0
		elif self.terrain in ['Wooden Buildings', 'Woods']:
			chance -= 10.0
		
		chance = RestrictChance(chance)
		
		roll = GetPercentileRoll()

		if roll <= chance:
			self.PinMe()
			return True
		return False
	
	
	# pin this unit
	def PinMe(self):
		self.pinned = True
		self.ClearAcquiredTargets(no_enemy=True)
		scenario.UpdateUnitCon()
		scenario.UpdateScenarioDisplay()


	# reduce this unit
	def ReduceMe(self):
		if self.GetStat('category') not in ['Gun', 'Cavalry', 'Infantry']: return
		self.reduced = True
		self.pinned = True
		self.ClearAcquiredTargets(no_enemy=True)
		scenario.UpdateUnitCon()
		scenario.UpdateScenarioDisplay()
	
	
	# rout this unit
	def RoutMe(self):
		self.routed = True
		self.pinned = False
		scenario.UpdateUnitCon()
		scenario.UpdateScenarioDisplay()


	# immobilize this unit
	def ImmobilizeMe(self):
		if self.GetStat('category') not in ['Vehicle']: return
		self.moving = False
		self.immobilized = True
		self.bogged = False
	
	
	# destroy this unit and remove it from the game
	# if location is set, that was the location of the knock-out hit for vehicles
	def DestroyMe(self, location=None, dest_weapon=None, no_vp=False, surrender=False):
		
		# check for debug flag
		if self == scenario.player_unit and DEBUG:
			if session.debug['Player Immortality']:
				ShowMessage('Debug powers save you from death!')
				self.ap_hits_to_resolve = []
				return
		
		# set flag
		self.alive = False
		
		# play sound if not surrendering
		if not surrender:
			PlaySoundFor(self, 'unit_ko')
		
		# remove from hex stack
		map_hex = scenario.hex_dict[(self.hx, self.hy)]
		if self in map_hex.unit_stack:
			map_hex.unit_stack.remove(self)
			
		# remove from scenario unit list
		if self in scenario.units:
			scenario.units.remove(self)
		
		# squad member was destroyed, remove from list
		if self in scenario.player_unit.squad:
			scenario.player_unit.squad.remove(self)
			campaign.AddJournal('A ' + self.unit_id + ' from our squad was knocked out.')
			
			# player crew may be shaken
			for position in scenario.player_unit.positions_list:
				if position.crewman is None: continue
				if position.crewman.condition != 'Good Order': continue
				if position.crewman.DoMoraleCheck(-50): continue
				position.crewman.condition = 'Shaken'
				ShowMessage('Your crewman is Shaken by the loss of a squadmate:',crewman=position.crewman)
		
		# remove as selected target from all player weapons, and remove from target list
		for weapon in scenario.player_unit.weapon_list:
			if weapon.selected_target == self:
				weapon.selected_target = None
		if self in scenario.target_list:
			scenario.target_list.remove(self)
		
		# award VP to player for unit destruction
		if self.owning_player == 1:
			
			if not no_vp:
				
				# add unit id to day records
				if self.unit_id in campaign_day.enemies_destroyed:
					campaign_day.enemies_destroyed[self.unit_id] += 1
				else:
					campaign_day.enemies_destroyed[self.unit_id] = 1
				
				# determine vp award amount and add to day records
				category = self.GetStat('category')
				
				if category in ['Infantry', 'Cavalry']:
					campaign_day.AddRecord('Infantry Destroyed', 1)
					vp_amount = 1
				elif category == 'Gun':
					campaign_day.AddRecord('Guns Destroyed', 1)
					vp_amount = 2
				elif category == 'Vehicle':
					campaign_day.AddRecord('Vehicles Destroyed', 1)
					if self.GetStat('class') in ['Truck', 'Tankette']:
						vp_amount = 1
					elif self.GetStat('class') == 'Heavy Tank':
						vp_amount = 4
					else:
						vp_amount = 3
				elif category == 'Train Car':
					vp_amount = 3
				
				if self.transport is not None:
					vp_amount += 1
					text = self.GetStat('class') + ' was transporting a ' + self.transport + ' unit, '
					if surrender:
						text += 'which also surrenders.'
					else:
						text += 'also destroyed.'
					ShowMessage(text, scenario_highlight=(self.hx, self.hy))
				
				if campaign.stats['region'] == 'North Africa':
					vp_amount = int(float(vp_amount) * DESERT_DESTROY_MULTIPLER)
				
				if campaign_day.mission in ['Fighting Withdrawal', 'Patrol']:
					vp_amount += 1
				
				if campaign.player_unit.CrewmanHasSkill(PLAYER_POSITIONS, 'Defensive Strategy'):
					vp_amount += 1
				
				if surrender and category in ['Gun', 'Vehicle']:
					vp_amount += int(float(vp_amount) * 0.5)
				
				campaign.AwardVP(vp_amount)
		
		# friendly unit destroyed
		else:
		
			# player unit has been destroyed
			if self == scenario.player_unit:
				
				campaign.AddJournal('Our ' + self.unit_id + ' tank was knocked out')
				session.ModifySteamStat('knocked_out', 1)
				
				# set end-scenario flag
				scenario.finished = True
				
				# do bail-out procedure
				scenario.PlayerBailOut(location=location, weapon=dest_weapon)
		
		scenario.UpdateUnitCon()
		scenario.UpdateScenarioDisplay()
	
	
	# do an explosion roll on a vehicle that has been destroyed
	def DoExplosionRoll(self, location, weapon):
		
		if self.GetStat('category') != 'Vehicle': return False
		
		chance = 0.0
		
		# hull hit
		if location is not None:
			if location == 'Hull':
				chance += 3.0
		
		# large-calibre gun hit
		if weapon is not None:
			if weapon.GetStat('type') == 'Gun':
				if weapon.GetStat('calibre') is not None:
					if int(weapon.GetStat('calibre')) >= 88:
						chance += 3.0
		
		# extra ammo bring carried
		extra_ammo = 0
		for weapon in self.weapon_list:
			if weapon.stats['type'] != 'Gun': continue
			total_loaded = 0
			for ammo_type in AMMO_TYPES:
				if ammo_type in weapon.ammo_stores:
					total_loaded += weapon.ammo_stores[ammo_type]
			if total_loaded > weapon.max_ammo:
				extra_ammo += weapon.max_ammo - total_loaded
		
		if extra_ammo > 0:
			chance += 0.5 * float(extra_ammo)
		
		if self.GetStat('wet_stowage') is None:
			chance += 3.0
		
		roll = GetPercentileRoll()
		
		if roll <= chance:
			return True
		return False
	
	
	# attempt to recover from pinned status at the end of an activation
	def DoRecoveryRoll(self):
		if not self.pinned: return
		
		# can't test to recover if hit by fp this turn
		if self.hit_by_fp:
			self.hit_by_fp = False
			return
		
		if not self.MoraleCheck(0): return
		self.pinned = False
		scenario.UpdateUnitCon()
		scenario.UpdateScenarioDisplay()
		ShowMessage(self.GetName() + ' is no longer Pinned.', scenario_highlight=(self.hx, self.hy))



# MapHex: a single hex on the scenario map
class MapHex:
	def __init__(self, hx, hy):
		self.hx = hx
		self.hy = hy
		self.unit_stack = []				# list of units present in this map hex
		


##########################################################################################
#                                  General Functions                                     #
##########################################################################################	

# display a string of text with extended characters to a console
# has options for formatting crew names
def PrintExtended(console, x, y, text, firstname_only=False, lastname_only=False, first_initial=False, center=False):
	
	# static character mapping for extended characters
	CHAR_MAP = {
			'Ą' : 256,
			'Ć' : 257,
			'Ę' : 258,
			'Ł' : 259,
			'Ń' : 260,
			'Ó' : 261,
			'Ś' : 262,
			'Ź' : 263,
			'Ż' : 264,
			'ą' : 265,
			'ć' : 266,
			'ę' : 267,
			'ł' : 268,
			'ń' : 269,
			'ó' : 270,
			'ś' : 271,
			'ź' : 272,
			'ż' : 273
		}
	
	# determine if string needs to be re-formatted
	if firstname_only:
		display_text = text.split(' ')[0]
	elif lastname_only:
		display_text = text.split(' ')[1]
	elif first_initial:
		display_text = text.split(' ')[0][0]
		display_text += '. '
		display_text += text.split(' ')[1]
	else:
		display_text = text
	
	if center:
		cx = x - int(len(text) / 2)
	else:
		cx = x
	for char in display_text:
		if char in CHAR_MAP:
			char_code = CHAR_MAP[char]
		else:
			char_code = ord(char.encode('IBM850'))
		libtcod.console_put_char(console, cx, y, char_code)
		cx += 1
	

# return the amount of EXP required for a personel to be at a given level
def GetExpRequiredFor(level):
	exp = 0
	for l in range(1, level):
		exp += int(ceil(BASE_EXP_REQUIRED * (pow(float(l), EXP_EXPONENT))))
	return exp


# generate and return a console image of a plane
def GeneratePlaneCon(direction):
	temp_con = libtcod.console_new(3, 3)
	libtcod.console_set_default_background(temp_con, libtcod.black)
	libtcod.console_set_default_foreground(temp_con, libtcod.light_grey)
	libtcod.console_clear(temp_con)
	
	libtcod.console_put_char(temp_con, 0, 1, chr(196))
	libtcod.console_put_char(temp_con, 1, 1, chr(197))
	libtcod.console_put_char(temp_con, 2, 1, chr(196))
	if direction == -1:
		libtcod.console_put_char(temp_con, 1, 2, chr(193))
	else:
		libtcod.console_put_char(temp_con, 1, 0, chr(194))
	return temp_con


# export the campaign log to a text file, normally done at the end of a campaign
def ExportLog():
	
	# make sure that the game directory exists first
	home_path = str(Path.home()) + os.sep + 'ArmCom2'
	if not os.path.isdir(home_path): os.mkdir(home_path)
	
	filename = home_path + os.sep + 'ArmCom2_Campaign_Log_' + datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + '.txt'
	with open(filename, 'w', encoding='utf-8') as f:
			
		# campaign information
		f.write(campaign.stats['name'] + '\n')
		f.write(GetDateText(campaign.stats['start_date']) + ' - ' + GetDateText(campaign.today) + '\n')
		f.write('\n')
		
		# final player tank and crew information
		f.write(campaign.player_unit.unit_id + '\n')
		if campaign.player_unit.unit_name != '':
			f.write('"' + campaign.player_unit.unit_name + '"\n')
		f.write('\n')
		
		for position in campaign.player_unit.positions_list:
			f.write(position.name + ':\n')
			if position.crewman is None:
				f.write('  [Empty]\n\n')
				continue
			f.write('  ' + position.crewman.GetName() + '\n')
			if not position.crewman.alive:
				f.write('  KIA\n')
			else:
				f.write('  Injuries:\n')
				injured = False
				for (k, v) in position.crewman.injury.items():
					if not v: continue
					f.write('  ' + k + ': ' + v + '\n')
					injured = True
				if not injured:
					f.write('  None\n')
			f.write('\n')
		f.write('\n')
		
		# list of campaign day records and journal entries
		for day, value in campaign.logs.items():
			f.write(GetDateText(day) + ':\n')
			for record in RECORD_LIST:
				f.write('  ' + record + ': ' + str(value[record]) + '\n')
			f.write('\n')
			
			if day in campaign.journal:
				for (time, text) in campaign.journal[day]:
					f.write(time + ' - ' + text + '\n')
			f.write('\n')


# show a menu for selecting a new crewman skill
def ShowSkillMenu(crewman):
	
	# build list of skills that can be added
	skill_list = []
	for k, value in campaign.skills.items():
		
		# campaign skill
		if 'campaign_skill' in value: continue
		
		# crewman already has this skill
		if k in crewman.skills: continue
		
		# restricted to one or more positions
		if 'position_list' in value:
			if crewman.current_position.name not in value['position_list']: continue
		
		# crewman does not have prerequisite skill
		if 'prerequisite' in value:
			if value['prerequisite'] not in crewman.skills: continue
		
		# crewman has an antirequistie skill
		if 'antirequisites' in value:
			has_anti = False
			for skill_name in value['antirequisites']:
				if skill_name in crewman.skills:
					has_anti = True
					break
			if has_anti: continue
		
		# skill ok, add to list
		skill_list.append(k) 
	
	# no more skills can be added
	if len(skill_list) == 0:
		ShowMessage('No further skills available for this crewman.')
		return ''
	
	# create a local copy of the current screen to re-draw when we're done
	temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
	libtcod.console_blit(con, 0, 0, 0, 0, temp_con, 0, 0)
	
	# darken background 
	libtcod.console_blit(darken_con, 0, 0, 0, 0, con, 0, 0, 0.0, 0.7)
	
	# create display console
	skill_menu_con = NewConsole(53, 46, libtcod.black, libtcod.white)
	
	selected_skill = 0
	result = ''
	exit_menu = False
	while not exit_menu:
		
		# update the display console
		libtcod.console_clear(skill_menu_con)
		libtcod.console_set_default_foreground(skill_menu_con, libtcod.grey)
		DrawFrame(skill_menu_con, 0, 0, 53, 46)
		
		libtcod.console_set_default_background(skill_menu_con, libtcod.darkest_blue)
		libtcod.console_rect(skill_menu_con, 1, 1, 51, 3, True, libtcod.BKGND_SET)
		libtcod.console_set_default_background(skill_menu_con, libtcod.black)
		
		libtcod.console_set_default_foreground(skill_menu_con, TITLE_COL)
		libtcod.console_print(skill_menu_con, 23, 2, 'Add Skill')
		
		# list of skills
		libtcod.console_set_default_foreground(skill_menu_con, libtcod.white)
		y = 8
		n = 0
		for skill_name in skill_list:
			libtcod.console_set_default_foreground(skill_menu_con, libtcod.white)
			libtcod.console_print(skill_menu_con, 2, y, skill_name)
			if n == selected_skill:
				
				# highlight selected skill
				libtcod.console_set_default_background(skill_menu_con, HIGHLIGHT_MENU_COL)
				libtcod.console_rect(skill_menu_con, 2, y, 22, 1, False, libtcod.BKGND_SET)
				libtcod.console_set_default_background(skill_menu_con, libtcod.black)
				
				# description of skill
				lines = wrap(campaign.skills[skill_name]['desc'], 19)
				y1 = 15
				libtcod.console_set_default_foreground(skill_menu_con, libtcod.light_grey)
				for line in lines:
					libtcod.console_print(skill_menu_con, 30, y1, line)
					y1 += 1
				
				# replaces other skill if any
				if 'replaces' in campaign.skills[skill_name]:
					libtcod.console_set_default_foreground(skill_menu_con, libtcod.white)
					libtcod.console_print(skill_menu_con, 30, y1+1, 'Replaces:')
					libtcod.console_set_default_foreground(skill_menu_con, libtcod.light_grey)
					libtcod.console_print(skill_menu_con, 30, y1+2, campaign.skills[skill_name]['replaces'])
				
			y += 1
			n += 1
		
		# player commands
		libtcod.console_set_default_foreground(skill_menu_con, ACTION_KEY_COL)
		libtcod.console_print(skill_menu_con, 18, 40, EnKey('w').upper() + '/' + EnKey('s').upper())
		libtcod.console_print(skill_menu_con, 18, 41, EnKey('e').upper())
		libtcod.console_print(skill_menu_con, 18, 42, 'Esc')
		
		libtcod.console_set_default_foreground(skill_menu_con, libtcod.light_grey)
		libtcod.console_print(skill_menu_con, 25, 40, 'Select Skill')
		libtcod.console_print(skill_menu_con, 25, 41, 'Add Skill')
		libtcod.console_print(skill_menu_con, 25, 42, 'Cancel')
		
		libtcod.console_blit(skill_menu_con, 0, 0, 0, 0, con, 19, 10)
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
		refresh_menu = False
		while not refresh_menu:
			libtcod.console_flush()
			keypress = GetInputEvent()
			
			if not keypress: continue
			
			# exit menu
			if key.vk == libtcod.KEY_ESCAPE:
				exit_menu = True
				refresh_menu = True
				continue
			
			key_char = DeKey(chr(key.c).lower())
			
			# change selected skill
			if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
				
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					if selected_skill == 0:
						selected_skill = len(skill_list) - 1
					else:
						selected_skill -= 1
				else:
					if selected_skill == len(skill_list) - 1:
						selected_skill = 0
					else:
						selected_skill += 1
				
				refresh_menu = True
				continue
			
			# add skill
			elif key_char == 'e':
				
				# make sure crewman has 1+ advance point to spend
				adv_pt = False
				if DEBUG:
					if session.debug['Free Crew Advances']:
						adv_pt = True
				if crewman.adv > 0:
					adv_pt = True
				
				if not adv_pt:
					ShowNotification('Crewman has no Advance Points remaining.')
					refresh_menu = True
					continue
				
				# get confirmation from player before adding skill
				if ShowNotification('Spend one advance point to gain the skill: ' + skill_list[selected_skill] + '?', confirm=True):
					result = skill_list[selected_skill]
					exit_menu = True
				refresh_menu = True
				continue
	
	# re-draw original screen
	libtcod.console_blit(temp_con, 0, 0, 0, 0, con, 0, 0)
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	del temp_con
	
	return result


# shortcut for generating consoles
def NewConsole(x, y, bg, fg, key_colour=False):
	new_con = libtcod.console_new(x, y)
	libtcod.console_set_default_background(new_con, bg)
	libtcod.console_set_default_foreground(new_con, fg)
	if key_colour:
		libtcod.console_set_key_color(new_con, KEY_COLOR)
	libtcod.console_clear(new_con)
	return new_con


# return a text description of a given calendar date
def GetDateText(text):
	date_list = text.split('.')
	return (MONTH_NAMES[int(date_list[1].lstrip('0'))] + ' ' + str(date_list[2].lstrip('0')) + 
		', ' + date_list[0])


# display date, time, and phase information to a console
# console should be 21x6
def DisplayTimeInfo(console):
	libtcod.console_clear(console)
	libtcod.console_set_default_foreground(console, libtcod.white)
	
	if campaign is None: return
	
	libtcod.console_print_ex(console, 10, 0, libtcod.BKGND_NONE, libtcod.CENTER, GetDateText(campaign.today))
	
	if campaign_day is None: return
	
	# depiction of time remaining in day
	libtcod.console_set_default_background(console, libtcod.darker_yellow)
	libtcod.console_rect(console, 0, 1, 21, 1, True, libtcod.BKGND_SET)
	
	hours = campaign_day.day_clock['hour'] - campaign_day.start_of_day['hour']
	minutes = campaign_day.day_clock['minute'] - campaign_day.start_of_day['minute']
	if minutes < 0:
		hours -= 1
		minutes += 60
	minutes += (hours * 60)
	x = int(21.0 * float(minutes) / float(campaign_day.day_length))
	libtcod.console_set_default_background(console, libtcod.dark_yellow)
	libtcod.console_rect(console, 0, 1, x, 1, True, libtcod.BKGND_SET)
	libtcod.console_set_default_background(console, libtcod.black)
	
	text = str(campaign_day.day_clock['hour']).zfill(2) + ':' + str(campaign_day.day_clock['minute']).zfill(2)
	libtcod.console_print_ex(console, 10, 1, libtcod.BKGND_NONE, libtcod.CENTER, text)
	
	# no scenario active, but may display the current number of maps traversed
	if scenario is None:
		libtcod.console_set_default_foreground(console, libtcod.light_grey)
		libtcod.console_print_ex(console, 10, 2, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Map Area: ' + str(campaign_day.maps_traversed + 1))
		return
	if not scenario.init_complete: return
	
	# current phase
	libtcod.console_set_default_foreground(console, SCEN_PHASE_COL[scenario.phase])
	libtcod.console_print_ex(console, 10, 2, libtcod.BKGND_NONE, libtcod.CENTER, 
		SCEN_PHASE_NAMES[scenario.phase] + ' Phase')
	
	# current spotted status
	if scenario.player_unit.spotted:
		libtcod.console_set_default_foreground(console, libtcod.light_grey)
		text = 'Spotted'
	else:
		libtcod.console_set_default_foreground(console, libtcod.grey)
		text = 'Unspotted'
	libtcod.console_print_ex(console, 10, 5, libtcod.BKGND_NONE, libtcod.CENTER, 
		text)
	


# display weather conditions info to a console, 18x12
def DisplayWeatherInfo(console):
	
	libtcod.console_clear(console)
	
	if campaign_day is None: return
	
	# cloud conditions on first two lines
	libtcod.console_set_default_background(console, libtcod.dark_blue)
	libtcod.console_rect(console, 0, 0, 18, 2, False, libtcod.BKGND_SET)
	
	if campaign_day.weather['Cloud Cover'] == 'Scattered':
		num = 8
	elif campaign_day.weather['Cloud Cover'] == 'Heavy':
		num = 12
	elif campaign_day.weather['Cloud Cover'] ==  'Overcast':
		num = 18
	else:
		# clear
		num = 0
	
	cell_list = (sample(list(range(18)), 18) + sample(list(range(18)), 18))
	for i in range(num):
		libtcod.console_set_char_background(console, cell_list[i], 0, libtcod.dark_grey,
			libtcod.BKGND_SET)
	for i in range(num):
		libtcod.console_set_char_background(console, cell_list[i+num], 1, libtcod.dark_grey,
			libtcod.BKGND_SET)
	
	libtcod.console_set_default_foreground(console, libtcod.white)
	libtcod.console_print_ex(console, 9, 0, libtcod.BKGND_NONE, libtcod.CENTER,
		campaign_day.weather['Cloud Cover'])
	if campaign_day.weather['Cloud Cover'] not in ['Clear', 'Overcast']:
		libtcod.console_print_ex(console, 9, 1, libtcod.BKGND_NONE, libtcod.CENTER,
			'Clouds')
	
	# precipitation
	if campaign_day.weather['Precipitation'] in ['Rain', 'Heavy Rain']:
		char = 250
		libtcod.console_set_default_foreground(console, libtcod.light_blue)
		libtcod.console_set_default_background(console, libtcod.dark_blue)
	elif campaign_day.weather['Precipitation'] in ['Mist', 'Light Snow', 'Snow', 'Blizzard']:
		char = 249
		libtcod.console_set_default_foreground(console, libtcod.light_grey)
		libtcod.console_set_default_background(console, libtcod.dark_grey)
	else:
		char = 0
	libtcod.console_rect(console, 0, 2, 18, 8, False, libtcod.BKGND_SET)
	
	if campaign_day.weather['Precipitation'] in ['Rain', 'Light Snow']:
		num = 18
	elif campaign_day.weather['Precipitation'] in ['Heavy Rain', 'Snow']:
		num = 28
	elif campaign_day.weather['Precipitation'] == 'Blizzard':
		num = 34
	else:
		num = 0
	
	for i in range(num):
		x = libtcod.random_get_int(0, 0, 18)
		y = libtcod.random_get_int(0, 2, 8)
		libtcod.console_put_char(console, x, y, char)
	
	libtcod.console_set_default_foreground(console, libtcod.white)
	if campaign_day.weather['Precipitation'] != 'None':
		libtcod.console_print_ex(console, 9, 3, libtcod.BKGND_NONE, libtcod.CENTER,
			campaign_day.weather['Precipitation'])
	
	# temperature
	if campaign_day.weather['Temperature'] == 'Extreme Hot':
		libtcod.console_set_default_foreground(console, libtcod.light_yellow)
	elif campaign_day.weather['Temperature'] == 'Extreme Cold':
		libtcod.console_set_default_foreground(console, libtcod.lighter_blue)
	libtcod.console_print_ex(console, 9, 6, libtcod.BKGND_NONE, libtcod.CENTER,
		campaign_day.weather['Temperature'])
	
	# fog
	if campaign_day.weather['Fog'] > 0:
		libtcod.console_set_default_background(console, libtcod.light_grey)
		libtcod.console_rect(console, 0, 8, 18, 2, True, libtcod.BKGND_SET)
		
		libtcod.console_set_default_foreground(console, libtcod.darker_grey)
		text = ''
		if campaign_day.weather['Fog'] == 1:
			text = 'Light'
		elif campaign_day.weather['Fog'] == 3:
			text = 'Heavy'
		libtcod.console_print_ex(console, 9, 8, libtcod.BKGND_NONE, libtcod.CENTER,
			text + ' Fog')
	
	# ground conditions
	if campaign_day.weather['Ground'] in ['Dry', 'Wet']:
		libtcod.console_set_default_foreground(console, libtcod.light_grey)
		libtcod.console_set_default_background(console, libtcod.dark_sepia)
	elif campaign_day.weather['Ground'] == 'Muddy':
		libtcod.console_set_default_foreground(console, libtcod.grey)
		libtcod.console_set_default_background(console, libtcod.darker_sepia)
	elif campaign_day.weather['Ground'] in ['Snow', 'Deep Snow']:
		libtcod.console_set_default_foreground(console, libtcod.light_blue)
		libtcod.console_set_default_background(console, libtcod.grey)
	libtcod.console_rect(console, 0, 10, 18, 3, False, libtcod.BKGND_SET)
	
	text = campaign_day.weather['Ground']
	if campaign_day.weather['Ground'] not in ['Snow', 'Deep Snow']:
		text += ' Ground'
	libtcod.console_print_ex(console, 9, 11, libtcod.BKGND_NONE, libtcod.CENTER,
		text)


# draw an ArmCom2-style frame to the given console
# if h==0, draw a horizontal line
def DrawFrame(console, x, y, w, h):
	libtcod.console_put_char(console, x, y, 249)
	libtcod.console_put_char(console, x+w-1, y, 249)
	if h > 0:
		libtcod.console_put_char(console, x, y+h-1, 249)
		libtcod.console_put_char(console, x+w-1, y+h-1, 249)
	for x1 in range(x+1, x+w-1):
		libtcod.console_put_char(console, x1, y, 196)
		if h > 0:
			libtcod.console_put_char(console, x1, y+h-1, 196)
	if h == 0: return
	for y1 in range(y+1, y+h-1):
		libtcod.console_put_char(console, x, y1, 179)
		libtcod.console_put_char(console, x+w-1, y1, 179)


# display a message window on the screen, pause, and then clear message from screen
# possible to highlight a CD/scenario hex, and have message appear near highlighed hex but not covering it
def ShowMessage(text, longer_pause=False, portrait=None, cd_highlight=None, scenario_highlight=None,
	ignore_animations=False, crewman=None):
	
	# if scenario_highlight is off-map, don't show anything
	if scenario_highlight is not None:
		(hx, hy) = scenario_highlight
		if GetHexDistance(0, 0, hx, hy) > 3: return
	
	# determine size of console
	if portrait is not None:
		width = 27
		height = 12
	else:
		width = 21
		height = 4
	
	lines = wrap(text, width-4)
	height += len(lines)
	
	if crewman is not None:
		height += 2
	
	if config['ArmCom2'].getboolean('message_prompt'):
		height += 2
	
	# determine display location of console on screen
	
	# if we are highlighting a hex, position the console close to but not obscuring the hex
	if cd_highlight is not None:
		(hx, hy) = cd_highlight
		(x,y) = campaign_day.PlotCDHex(hx, hy)
		
		x += 29 - int(width/2)
		
		# make sure window is not too far to the right
		if x + width > WINDOW_WIDTH:
			x = WINDOW_WIDTH - width
		
		if hy <= 4:
			y += 11
		else:
			y -= (height - 2)
	
	elif scenario_highlight is not None:
		(hx, hy) = scenario_highlight
		(x,y) = scenario.PlotHex(hx, hy)
		
		x += 32 - int(width/2)
		# make sure window is not too far to the right
		if x + width > WINDOW_WIDTH:
			x = WINDOW_WIDTH - width
		
		if y >= 24:
			y -= (height - 6)
		else:
			y += 13
	
	else:
		
		# generic location in centre of map
		x = WINDOW_XM + 1 - int(width / 2)
		
		if scenario is not None:
			if not scenario.finished:
				x += 12
		
		y = WINDOW_YM - int(height / 2)
	
	# adjust for fullscreen
	x += window_x
	y += window_y
	
	# set the console display location
	session.msg_location = (x, y)
	
	# create message console
	session.msg_con = NewConsole(width, height, libtcod.darkest_grey, libtcod.white) 
	DrawFrame(session.msg_con, 0, 0, width, height)
	
	# display portrait if any
	if portrait is not None:
		libtcod.console_set_default_background(session.msg_con, PORTRAIT_BG_COL)
		libtcod.console_rect(session.msg_con, 1, 1, 25, 8, True, libtcod.BKGND_SET)
		libtcod.console_blit(LoadXP(portrait), 0, 0, 0, 0, session.msg_con, 1, 1)
		libtcod.console_set_default_background(session.msg_con, libtcod.black)
	
	# display message
	# try to center message vertically within console
	x = int(width / 2)
	y = int(height / 2) - int(len(lines) / 2)
	if portrait is not None:
		y += 4
	
	for line in lines:
		libtcod.console_print_ex(session.msg_con, x, y, libtcod.BKGND_NONE, libtcod.CENTER, line.encode('IBM850'))
		if y == height-1: break
		y += 1
	
	# display crewman name if any
	if crewman is not None:
		y += 1
		text = crewman.GetName()
		x = int(width / 2) - int(len(text) / 2)
		PrintExtended(session.msg_con, x, y, text)
		y += 1
	
	if config['ArmCom2'].getboolean('message_prompt'):
		libtcod.console_print_ex(session.msg_con, x, y+1, libtcod.BKGND_NONE, libtcod.CENTER,
			'Tab to Continue')
	
	# start hex highlight if any
	if cd_highlight is not None:
		campaign_day.animation['hex_highlight'] = (hx, hy)
		campaign_day.animation['hex_flash'] = 1
	elif scenario_highlight is not None:
		scenario.animation['hex_highlight'] = (hx, hy)
		scenario.animation['hex_flash'] = 1
	
	# game option to have all messages need to be dismissed manually
	if config['ArmCom2'].getboolean('message_prompt'):
		WaitForContinue()
		
	else:
	
		# allow the message (and animation) to be viewed by player
		if longer_pause:
			wait_time = 200
		else:
			wait_time = 130
		Wait(wait_time + (40 * config['ArmCom2'].getint('message_pause')), ignore_animations=ignore_animations)
	
	FlushKeyboardEvents()
	
	# clear hex highlight if any
	if cd_highlight is not None:
		campaign_day.animation['hex_highlight'] = False
		campaign_day.UpdateAnimCon()
	elif scenario_highlight is not None:
		scenario.animation['hex_highlight'] = False
		scenario.UpdateAnimCon()
	
	# erase console and re-draw screen
	session.msg_con = None
	session.msg_location = None
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()


# display a simple message on the root console, no animations, just one option
def ShowSimpleMessage(text, crewman=None):
	width = 21
	lines = wrap(text, width-4)
	height = 4 + len(lines)
	if crewman is not None:
		height += 2
	if config['ArmCom2'].getboolean('message_prompt'):
		height += 2
	x = WINDOW_XM + 1 - int(width / 2) + window_x
	y = WINDOW_YM - int(height / 2) + window_y
	temp_con = NewConsole(width, height, libtcod.darkest_grey, libtcod.white)
	DrawFrame(temp_con, 0, 0, width, height)
	text_x = int(width / 2)
	text_y = int(height / 2) - int(len(lines) / 2)
	for line in lines:
		libtcod.console_print_ex(temp_con, text_x, text_y, libtcod.BKGND_NONE,
			libtcod.CENTER, line.encode('IBM850'))
		if text_y == height-1: break
		text_y += 1
	if crewman is not None:
		text_y += 1
		text = crewman.GetName()
		text_x = int(width / 2) - int(len(text) / 2)
		PrintExtended(temp_con, text_x, text_y, text)
		text_y += 1
	if config['ArmCom2'].getboolean('message_prompt'):
		libtcod.console_print_ex(temp_con, text_x, text_y+1, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Tab to Continue')
	libtcod.console_blit(temp_con, 0, 0, 0, 0, 0, x, y)
	libtcod.console_flush()
	if config['ArmCom2'].getboolean('message_prompt'):
		WaitForContinue(ignore_animations=True)
	else:
		Wait(130 + (40 * config['ArmCom2'].getint('message_pause')), ignore_animations=True)
	FlushKeyboardEvents()
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()


# get keyboard and/or mouse event; returns False if no new key press
def GetInputEvent():
	event = libtcod.sys_check_for_event(libtcod.EVENT_KEY_RELEASE|libtcod.EVENT_KEY_PRESS|libtcod.EVENT_MOUSE,
		key, mouse)
	if session.key_down:
		if event != libtcod.EVENT_KEY_RELEASE:
			return False
		session.key_down = False
	if event != libtcod.EVENT_KEY_PRESS:
		return False
	session.key_down = True
	return True


# clear all keyboard events
def FlushKeyboardEvents():
	exit = False
	while not exit:
		libtcod.console_flush()
		event = libtcod.sys_check_for_event(libtcod.EVENT_KEY_PRESS, key, mouse)
		if event != libtcod.EVENT_KEY_PRESS: exit = True
	session.key_down = False


# wait for a specified amount of miliseconds, refreshing the screen in the meantime
def Wait(wait_time, allow_skip=False, ignore_animations=False):
	
	# check for debug fast mode
	if DEBUG:
		if session.debug['Fast Mode']:
			wait_time = int(wait_time/4)
	
	wait_time = wait_time * 0.01
	start_time = time.time()
	while time.time() - start_time < wait_time:
		
		# check for animation update in scenario or campaign day or layer
		if not ignore_animations:
			CheckForAnimationUpdate()
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		if allow_skip:
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				return
		
		FlushKeyboardEvents()


# wait for player to press continue key
# option to allow backspace pressed instead, returns True if so 
def WaitForContinue(allow_cancel=False, ignore_animations=False):
	end_pause = False
	cancel = False
	while not end_pause:
		
		# check for animation update in scenario or campaign day or layer
		if not ignore_animations:
			CheckForAnimationUpdate()
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		if key.vk in [libtcod.KEY_BACKSPACE, libtcod.KEY_ESCAPE] and allow_cancel:
			end_pause = True
			cancel = True
		elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
			end_pause = True
	if allow_cancel and cancel:
		return True
	return False


# wait for player input during an attack roll
def WaitForAttackInput(fate_point_allowed):
	end_pause = False
	while not end_pause:
		CheckForAnimationUpdate()
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		if key.vk in [libtcod.KEY_BACKSPACE, libtcod.KEY_ESCAPE]:
			return 'cancel'
		elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
			return 'continue'
		key_char = chr(key.c).lower()
		if key_char == 'f' and fate_point_allowed:
			if ShowNotification('Spend a Fate Point to save yourself?', confirm=True):
				return 'fate_point'


# check for animation frame update and console update
def CheckForAnimationUpdate():
	
	anim_update_timer = 0.05 + (0.10 * config['ArmCom2'].getint('animation_speed'))
	
	if scenario is not None:
		if scenario.init_complete:
			if time.time() - session.anim_timer >= anim_update_timer:
				scenario.UpdateAnimCon()
				scenario.UpdateScenarioDisplay()
		
	elif campaign_day is not None:
		if campaign_day.started and not campaign_day.ended:
			if time.time() - session.anim_timer >= anim_update_timer:
				campaign_day.UpdateAnimCon()
				campaign_day.UpdateCDDisplay()	
	
	# display message console overtop if any
	if session.msg_con is not None:
		(x, y) = session.msg_location
		libtcod.console_blit(session.msg_con, 0, 0, 0, 0, 0, x, y)


# load a console image from an .xp file
def LoadXP(filename):
	# make sure that required file exists and, if not, return a placeholder console
	if not os.path.exists(DATAPATH + filename):
		print('ERROR: could not find required xp file: ' + filename)
		console = libtcod.console_new(1, 1)
		libtcod.console_put_char_ex(console, 0, 0, '?', libtcod.red, libtcod.black)
		return console
	xp_file = gzip.open(DATAPATH + filename)
	raw_data = xp_file.read()
	xp_file.close()
	xp_data = xp_loader.load_xp_string(raw_data)
	console = libtcod.console_new(xp_data['width'], xp_data['height'])
	xp_loader.load_layer_to_console(console, xp_data['layer_data'][0])
	return console


# Bresenham's Line Algorithm (based on an implementation on the roguebasin wiki)
# returns a series of x, y points along a line
def GetLine(x1, y1, x2, y2):
	points = []
	issteep = abs(y2-y1) > abs(x2-x1)
	if issteep:
		x1, y1 = y1, x1
		x2, y2 = y2, x2
	rev = False
	if x1 > x2:
		x1, x2 = x2, x1
		y1, y2 = y2, y1
		rev = True
	deltax = x2 - x1
	deltay = abs(y2-y1)
	error = int(deltax / 2)
	y = y1
	
	if y1 < y2:
		ystep = 1
	else:
		ystep = -1
	for x in range(x1, x2 + 1):
		if issteep:
			points.append((y, x))
		else:
			points.append((x, y))
		error -= deltay
		if error < 0:
			y += ystep
			error += deltax
	if rev:
		points.reverse()
	return points


# constrain a direction to a value 0-5
def ConstrainDir(direction):
	while direction < 0:
		direction += 6
	while direction > 5:
		direction -= 6
	return direction


# transforms an hx, hy hex location to cube coordinates
def GetCubeCoords(hx, hy):
	x = int(hx - (hy - hy&1) / 2)
	z = hy
	y = 0 - hx - z
	return (x, y, z)


# returns distance in hexes between two hexes
def GetHexDistance(hx1, hy1, hx2, hy2):
	(x1, y1, z1) = GetCubeCoords(hx1, hy1)
	(x2, y2, z2) = GetCubeCoords(hx2, hy2)
	return int((abs(x1-x2) + abs(y1-y2) + abs(z1-z2)) / 2)


# rotates a hex location around 0,0 clockwise r times
def RotateHex(hx, hy, r):
	# convert to cube coords
	(xx, yy, zz) = GetCubeCoords(hx, hy)
	for r in range(r):
		xx, yy, zz = -zz, -xx, -yy
	# convert back to hex coords
	return(int(xx + (zz - zz&1) / 2), zz)


# returns the adjacent hex in a given direction
def GetAdjacentHex(hx, hy, direction):
	direction = ConstrainDir(direction)
	(hx_mod, hy_mod) = DESTHEX[direction]
	return (hx+hx_mod, hy+hy_mod)


# returns arrow character used to indicate given direction
def GetDirectionalArrow(direction):
	if direction == 0:
		return chr(24)
	elif direction == 1:
		return chr(228)
	elif direction == 2:
		return chr(229)
	elif direction == 3:
		return chr(25)
	elif direction == 4:
		return chr(230)
	elif direction == 5:
		return chr(231)
	return '*'


# return a list of hexes along a line from hex1 to hex2
# adapted from http://www.redblobgames.com/grids/hexagons/implementation.html#line-drawing
def GetHexLine(hx1, hy1, hx2, hy2):
	
	def Lerp(a, b, t):
		a = float(a)
		b = float(b)
		return a + (b - a) * t
	
	def CubeRound(x, y, z):
		rx = round(x)
		ry = round(y)
		rz = round(z)
		x_diff = abs(rx - x)
		y_diff = abs(ry - y)
		z_diff = abs(rz - z)
		if x_diff > y_diff and x_diff > z_diff:
			rx = 0 - ry - rz
		elif y_diff > z_diff:
			ry = 0 - rx - rz
		else:
			rz = 0 - rx - ry
		return (int(rx), int(ry), int(rz))

	# get cube coordinates and distance between start and end hexes
	# (repeated here from GetHexDistance because we need more than just the distance)
	(x1, y1, z1) = GetCubeCoords(hx1, hy1)
	(x2, y2, z2) = GetCubeCoords(hx2, hy2)
	distance = int((abs(x1-x2) + abs(y1-y2) + abs(z1-z2)) / 2)
	
	hex_list = []
	
	for i in range(distance+1):
		t = 1.0 / float(distance) * float(i)
		x = Lerp(x1, x2, t)
		y = Lerp(y1, y2, t)
		z = Lerp(z1, z2, t)
		(x,y,z) = CubeRound(x,y,z)
		# convert from cube to hex coordinates and add to list
		hex_list.append((x, z))

	return hex_list


# returns a ring of hexes around a center point for a given radius
def GetHexRing(hx, hy, radius):
	if radius == 0: return [(hx, hy)]
	hex_list = []
	# get starting point
	hx -= radius
	hy += radius
	direction = 0
	for hex_side in range(6):
		for hex_steps in range(radius):
			hex_list.append((hx, hy))
			(hx, hy) = GetAdjacentHex(hx, hy, direction)
		direction += 1
	return hex_list


# returns the direction to an adjacent hex
def GetDirectionToAdjacent(hx1, hy1, hx2, hy2):
	hx_mod = hx2 - hx1
	hy_mod = hy2 - hy1
	if (hx_mod, hy_mod) in DESTHEX:
		return DESTHEX.index((hx_mod, hy_mod))
	# hex is not adjacent
	return -1


# returns the best facing to point in the direction of the target hex
def GetDirectionToward(hx1, hy1, hx2, hy2):
	(x1, y1) = scenario.PlotHex(hx1, hy1)
	(x2, y2) = scenario.PlotHex(hx2, hy2)
	bearing = GetBearing(x1, y1, x2, y2)
	
	if bearing >= 330 or bearing <= 30:
		return 0
	elif bearing <= 90:
		return 1
	elif bearing >= 270:
		return 5
	elif bearing <= 150:
		return 2
	elif bearing >= 210:
		return 4
	return 3


# return a list of hexes covered by the given hextant in direction d from hx, hy
# max range is 3
def GetCoveredHexes(hx, hy, d):
	hex_list = []
	hex_list.append((hx, hy))
	for i in range(2):
		(hx, hy) = GetAdjacentHex(hx, hy, d)
	hex_list.append((hx, hy))
	hex_list += GetHexRing(hx, hy, 1)
	return hex_list


# returns the compass bearing from x1, y1 to x2, y2
def GetBearing(x1, y1, x2, y2):
	return int((degrees(atan2((y2 - y1), (x2 - x1))) + 90.0) % 360)


# returns a bearing from 0-359 degrees
def RectifyBearing(h):
	while h < 0: h += 360
	while h > 359: h -= 360
	return h


# get the bearing from unit1 to unit2, rotated for unit1's facing
def GetRelativeBearing(unit1, unit2):
	(x1, y1) = scenario.PlotHex(unit1.hx, unit1.hy)
	(x2, y2) = scenario.PlotHex(unit2.hx, unit2.hy)
	bearing = GetBearing(x1, y1, x2, y2)
	return RectifyBearing(bearing - (unit1.facing * 60))


# get the relative facing of one unit from the point of view of another unit
# unit1 is the observer, unit2 is being observed
def GetFacing(attacker, target, turret_facing=False):
	bearing = GetRelativeBearing(target, attacker)
	if turret_facing and target.turret_facing is not None:
		turret_diff = target.turret_facing - target.facing
		bearing = RectifyBearing(bearing - (turret_diff * 60))
	if bearing >= 330 or bearing <= 30:
		return 'Front'
	if 150 <= bearing <= 210:
		return 'Rear'
	return 'Side'


# return a random float between 0.0 and 100.0
def GetPercentileRoll():
	return float(libtcod.random_get_int(0, 0, 1000)) / 10.0


# return a percentage chance based on a given 2d6 score
def Get2D6Odds(score):
	if score == 2:
		return 2.7
	elif score == 3:
		return 8.3
	elif score == 4:
		return 16.7
	elif score == 5:
		return 27.8
	elif score == 6:
		return 41.8
	elif score == 7:
		return 58.3
	elif score == 8:
		return 72.2
	elif score == 9:
		return 83.3
	elif score == 10:
		return 91.7
	else:
		return 97.2


# round and restrict odds to between 3.0 and 97.0
def RestrictChance(chance):
	chance = round(chance, 1)
	if chance < 3.0: return 3.0
	if chance > 97.0: return 97.0
	return chance


# newer, more restrictive restrict chance
def RestrictChanceNew(chance):
	chance = round(chance, 1)
	if chance < 0.5: return 0.5
	if chance > 99.5: return 99.5
	return chance


# save the current campaign to a backup
def BackupGame():
	if DEBUG:
		if session.debug['Suspend Save']: return
	
	path = SAVEPATH + campaign.filename + os.sep
	backup_path = BACKUP_PATH + campaign.filename + os.sep
	
	# previous backup already exists
	if os.path.isdir(backup_path):
		os.remove(backup_path + 'savegame.dat')
		os.remove(backup_path + 'savegame.dir')
		os.remove(backup_path + 'savegame.bak')
	else:
		os.mkdir(backup_path)
	
	copyfile(path + 'savegame.dat', backup_path + 'savegame.dat')
	copyfile(path + 'savegame.dir', backup_path + 'savegame.dir')
	copyfile(path + 'savegame.bak', backup_path + 'savegame.bak')
	

# save the current campaign in progress
def SaveGame():
	if DEBUG:
		if session.debug['Suspend Save']: return
	
	path = SAVEPATH + campaign.filename + os.sep
	if not os.path.isdir(path):
		os.mkdir(path)
	
	save = shelve.open(path + 'savegame', 'n')
	save['campaign'] = campaign
	save['campaign_day'] = campaign_day
	save['scenario'] = scenario
	save['version'] = VERSION
	save['datetime'] = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
	save.close()


# load a saved game
def LoadGame(directory):
	global campaign, campaign_day, scenario
	
	libtcod.console_clear(con)
	libtcod.console_print_ex(con, WINDOW_XM, WINDOW_YM, libtcod.BKGND_NONE, libtcod.CENTER,
		'Loading...')
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()
	
	save = shelve.open(SAVEPATH + directory + os.sep + 'savegame')
	campaign = save['campaign']
	campaign_day = save['campaign_day']
	scenario = save['scenario']
	save.close()


# check the saved game to see if it is compatible with the current game version
def CheckSavedGameVersion(saved_version):
	
	for text in ['Alpha', 'Beta', 'RC']:
		if text in saved_version or text in VERSION:
			if saved_version != VERSION:
				return saved_version
	
	# Semantic Versioning https://semver.org/
	# allow loading the saved game if the first component of the version numbers match
	if saved_version.split('.')[0] == VERSION.split('.')[0]:
		return ''
	return saved_version


# remove a saved game
def EraseGame(directory):
	if not os.path.isdir(SAVEPATH + directory): return
	if DEBUG:
		if session.debug['Suspend Save']: return
	os.remove(SAVEPATH + directory + os.sep + 'savegame.dat')
	os.remove(SAVEPATH + directory + os.sep + 'savegame.dir')
	os.remove(SAVEPATH + directory + os.sep + 'savegame.bak')
	os.rmdir(SAVEPATH + directory)
	

# try to load game settings from config file
def LoadCFG():
	
	CONFIG_KEYS = [
		'large_display_font',
		'sounds_enabled',
		'fullscreen',
		'master_volume',
		'unit_stack_display',
		'message_pause',
		'message_prompt',
		'animation_speed',
		'keyboard'
		]
	
	global config
	
	config = ConfigParser()
	
	# try to load config file if present
	if os.path.exists(DATAPATH + 'armcom2.cfg'):
		try:
			config.read(DATAPATH + 'armcom2.cfg')
			for k in CONFIG_KEYS:
				if k not in config['ArmCom2']:
					raise Exception('Missing config key: ' + k)
			return
		except:
			print('ERROR: Unable to read config file, creating a new one.')
	
	# create a new config file and write to disk
	config['ArmCom2'] = {
		'large_display_font' : 'true',
		'sounds_enabled' : 'true',
		'fullscreen' : 'false',
		'master_volume' : '7',
		'unit_stack_display' : 'false',
		'message_pause' : '1',
		'message_prompt' : 'false',
		'animation_speed' : '1',
		'keyboard' : '0'
	}
	with open(DATAPATH + 'armcom2.cfg', 'w', encoding='utf8') as configfile:
		config.write(configfile)
	

# save current config to file
def SaveCFG():
	with open(DATAPATH + 'armcom2.cfg', 'w', encoding='utf8') as configfile:
		config.write(configfile)


# display a pop-up message on the root console
# can be used for yes/no confirmation
def ShowNotification(text, confirm=False, add_pause=False):
	
	# dfon't pause if in debug mode, we should know what we're doing!
	if DEBUG: add_pause = False
	
	# determine window x, height, and y position
	x = WINDOW_XM - 30
	lines = wrap(text, 56)
	h = len(lines) + 6
	y = WINDOW_YM - int(h/2)
	
	# create a local copy of the current screen to re-draw when we're done
	temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
	libtcod.console_blit(con, 0, 0, 0, 0, temp_con, 0, 0)
	
	# darken background 
	libtcod.console_blit(darken_con, 0, 0, 0, 0, con, 0, 0, 0.0, 0.5)
	
	# draw a black rect and an outline
	libtcod.console_rect(con, x, y, 60, h, True, libtcod.BKGND_SET)
	
	DrawFrame(con, x, y, 60, h)
	
	# display message
	libtcod.console_set_default_foreground(con, libtcod.white)
	ly = y+2
	for line in lines:
		libtcod.console_print_ex(con, WINDOW_XM, ly, libtcod.BKGND_NONE,
			libtcod.CENTER, line)
		ly += 1
	
	# can add a pause to prevent accidental input
	if add_pause:
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		libtcod.console_flush()
		Wait(200, ignore_animations=True)
	
	# if asking for confirmation, display yes/no choices, otherwise display a simple message
	if confirm:
		text = 'Proceed? Y/N'
	else:
		text = 'Tab to Continue'
	libtcod.console_print_ex(con, WINDOW_XM, y+h-2, libtcod.BKGND_NONE, libtcod.CENTER,
		text)
	
	# show to screen
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()
	
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		key_char = chr(key.c).lower()
		
		if confirm:
			if key_char in ['y', 'n']:
				libtcod.console_blit(temp_con, 0, 0, 0, 0, con, 0, 0)
				libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
				del temp_con
				if key_char == 'y':
					return True
				else:
					return False
		else:
			if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
				libtcod.console_blit(temp_con, 0, 0, 0, 0, con, 0, 0)
				libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
				del temp_con
				return


# display the swap crew position menu, can be accessed from the scenario, campaign day, or
# campaign calendar layer
def ShowSwapPositionMenu():
	
	# draw the menu console
	def DrawMenuCon():
		libtcod.console_clear(con)
		
		libtcod.console_set_default_foreground(con, libtcod.white)
		DrawFrame(con, 32, 0, 27, 60)
		DrawFrame(con, 32, 17, 27, 35)
		
		# display player unit
		DisplayUnitInfo(con, 33, 1, unit.unit_id, unit, status=False)
		
		# display list of player crew
		DisplayCrew(unit, con, 33, 19, None)
		
		# display currently selected position 1 and 2
		libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
		y1 = 19 + position_1 * 5
		y2 = 19 + position_2 * 5
		libtcod.console_print(con, 60, y1, '<' + chr(191))
		for y in range(y1+1, y2):
			libtcod.console_put_char(con, 61, y, 179)
		libtcod.console_print(con, 60, y2, '<' + chr(217))
		
		# main commands
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 34, 53, EnKey('q').upper() + '/' + EnKey('a').upper())
		libtcod.console_print(con, 34, 54, EnKey('w').upper() + '/' + EnKey('s').upper())
		libtcod.console_print(con, 34, 55, EnKey('e').upper())
		libtcod.console_print(con, 34, 57, 'Tab')
		
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		libtcod.console_print(con, 40, 53, 'Select Position 1')
		libtcod.console_print(con, 40, 54, 'Select Position 2')
		libtcod.console_print(con, 40, 55, 'Swap Positions')
		libtcod.console_print(con, 40, 57, 'Finish & Exit Menu')
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	
	# determine which object we're working with
	if scenario is not None:
		unit = scenario.player_unit
	else:
		unit = campaign.player_unit
	
	# no positions to switch!
	if len(unit.positions_list) <= 1: return
	
	# record original crewman in each position
	original_crew = []
	for position in unit.positions_list:
		original_crew.append(position.crewman)
	
	# select first and second position as default
	position_1 = 0
	position_2 = 1
	
	# generate menu console for the first time and blit to screen
	DrawMenuCon()
	
	# get input from player
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		# continue
		if key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
			exit_menu = True
			continue
		
		key_char = DeKey(chr(key.c).lower())
		
		# swap selected positions
		if key_char == 'e':
		
			# do the swap
			temp = unit.positions_list[position_1].crewman
			unit.positions_list[position_1].crewman = unit.positions_list[position_2].crewman
			if unit.positions_list[position_1].crewman is not None:
				unit.positions_list[position_1].crewman.current_position = unit.positions_list[position_1]
				unit.positions_list[position_1].crewman.SetCEStatus()
				
			unit.positions_list[position_2].crewman = temp
			if unit.positions_list[position_2].crewman is not None:
				unit.positions_list[position_2].crewman.current_position = unit.positions_list[position_2]
				unit.positions_list[position_2].crewman.SetCEStatus()
			
			DrawMenuCon()
			continue
		
		# select position 1
		elif key_char in ['q', 'a']:
			
			new_position = position_1
			if key_char == 'q':
				new_position -= 1
			else:
				new_position += 1
			if new_position < 0: continue
			if new_position >= position_2: continue
			position_1 = new_position
			PlaySoundFor(None, 'menu_select')
			DrawMenuCon()
			continue
		
		# select position 2
		elif key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
			
			new_position = position_2
			if key_char == 'w' or key.vk == libtcod.KEY_UP:
				new_position -= 1
			else:
				new_position += 1
			if new_position <= position_1: continue
			if new_position >= len(unit.positions_list): continue
			position_2 = new_position
			PlaySoundFor(None, 'menu_select')
			DrawMenuCon()
			continue
	
	# if we're in a scenario right now, any crewman that swapped positions has their current
	# command set to None
	if scenario is not None:
		i = 0
		for position in unit.positions_list:
			if position.crewman is None:
				i += 1
				continue
			
			if position.crewman != original_crew[i]:
				position.crewman.current_cmd = 'None'
			i += 1


# display the in-game menu: 84x54
def ShowGameMenu():
	
	# draw the menu console
	def DrawMenuCon():
		
		libtcod.console_clear(game_menu_con)
		
		# draw a frame to the game menu console
		libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
		DrawFrame(game_menu_con, 0, 0, 84, 54)
		
		# display game name and version number
		libtcod.console_set_default_background(game_menu_con, libtcod.darker_grey)
		libtcod.console_rect(game_menu_con, 30, 2, 25, 7, True, libtcod.BKGND_SET)
		libtcod.console_set_default_background(game_menu_con, libtcod.black)
		DrawFrame(game_menu_con, 30, 2, 25, 7)
		
		libtcod.console_print_ex(game_menu_con, 42, 4, libtcod.BKGND_NONE,
			libtcod.CENTER, NAME)
		libtcod.console_print_ex(game_menu_con, 42, 6, libtcod.BKGND_NONE,
			libtcod.CENTER, VERSION)
		
		# section titles
		libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
		libtcod.console_print_ex(game_menu_con, 42, 12, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Game Commands')
		libtcod.console_print_ex(game_menu_con, 42, 20, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Game Options')
		libtcod.console_set_default_background(game_menu_con, libtcod.darkest_blue)
		libtcod.console_rect(game_menu_con, 30, 12, 25, 1, False, libtcod.BKGND_SET)
		libtcod.console_rect(game_menu_con, 30, 20, 25, 1, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(game_menu_con, libtcod.darker_blue)
		libtcod.console_rect(game_menu_con, 32, 12, 21, 1, False, libtcod.BKGND_SET)
		libtcod.console_rect(game_menu_con, 32, 20, 21, 1, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(game_menu_con, libtcod.black)
		
		# main commands
		libtcod.console_set_default_foreground(game_menu_con, ACTION_KEY_COL)
		libtcod.console_print(game_menu_con, 30, 14, 'Esc')
		libtcod.console_print(game_menu_con, 30, 15, 'Q')
		libtcod.console_set_default_foreground(game_menu_con, libtcod.lighter_grey)
		libtcod.console_print(game_menu_con, 35, 14, 'Close Menu')
		libtcod.console_print(game_menu_con, 35, 15, 'Save and Quit')
		
		# display game options
		DisplayGameOptions(game_menu_con, WINDOW_XM-19, 22, skip_esc=True)
		
		# display quote
		libtcod.console_set_default_foreground(game_menu_con, libtcod.grey)
		libtcod.console_print(game_menu_con, 25, 44, 'We are the Dead. Short days ago')
		libtcod.console_print(game_menu_con, 25, 45, 'We lived, felt dawn, saw sunset glow,')
		libtcod.console_print(game_menu_con, 25, 46, 'Loved and were loved, and now we lie')
		libtcod.console_print(game_menu_con, 25, 47, 'In Flanders fields.')
		libtcod.console_print(game_menu_con, 25, 49, 'John McCrae (1872-1918)')
		
		libtcod.console_blit(game_menu_con, 0, 0, 0, 0, con, 3, 3)
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
	
	# create a local copy of the current screen to re-draw when we're done
	temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
	libtcod.console_blit(con, 0, 0, 0, 0, temp_con, 0, 0)
	
	# darken screen background
	libtcod.console_blit(darken_con, 0, 0, 0, 0, con, 0, 0, 0.0, 0.7)
	
	# generate menu console for the first time and blit to screen
	DrawMenuCon()
	
	# get input from player
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		if key.vk == libtcod.KEY_ESCAPE:
			exit_menu = True
			continue
		
		key_char = DeKey(chr(key.c).lower())
		
		if chr(key.c).lower() == 'q':
			
			libtcod.console_clear(con)
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print_ex(con, WINDOW_XM, WINDOW_YM, libtcod.BKGND_NONE, libtcod.CENTER,
				'Saving Game...')
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			libtcod.console_flush()
			
			SaveGame()
			session.exiting = True
			exit_menu = True
			continue
		
		ChangeGameSettings(key_char)
		DrawMenuCon()
		continue
	
	# re-draw original screen
	libtcod.console_blit(temp_con, 0, 0, 0, 0, con, 0, 0)
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)


# display a list of game options and current settings
def DisplayGameOptions(console, x, y, skip_esc=False):
	for (char, text) in [('F', 'Font Size'), ('U', 'Fullscreen'), ('S', 'Sound Effects'),
	('V', 'Master Volume'), ('P', 'Message Pause'), ('M', 'Must Dismiss Messages'), ('A', 'Animation Speed'),
	('D', 'Unit Stack Display'), ('K', 'Keyboard'), ('Esc', 'Return to Main Menu')]:
		
		if char == 'Esc' and skip_esc: continue
		
		# extra spacing
		if char == 'Esc': y += 1
		
		# option disabled
		if char == 'V' and not config['ArmCom2'].getboolean('sounds_enabled'):
			libtcod.console_set_default_foreground(console, libtcod.darker_grey)
		else:
			libtcod.console_set_default_foreground(console, ACTION_KEY_COL)
		libtcod.console_print(console, x, y, char)
		
		if char == 'V' and not config['ArmCom2'].getboolean('sounds_enabled'):
			libtcod.console_set_default_foreground(console, libtcod.darker_grey)
		else:
			libtcod.console_set_default_foreground(console, libtcod.lighter_grey)
		libtcod.console_print(console, x+4, y, text)
		
		# current option settings
		libtcod.console_set_default_foreground(console, libtcod.light_blue)
		
		# toggle font size
		if char == 'F':
			if config['ArmCom2'].getboolean('large_display_font'):
				text = '16x16'
			else:
				text = '8x8'
		
		# fullscreen
		elif char == 'U':
			if config['ArmCom2'].getboolean('fullscreen'):
				text = 'ON'
			else:
				text = 'OFF'
		
		# sound effects
		elif char == 'S':
			if config['ArmCom2'].getboolean('sounds_enabled'):
				text = 'ON'
			else:
				text = 'OFF'
		
		# Master Volume
		elif char == 'V':
			text = str(config['ArmCom2'].getint('master_volume'))
		
		# message pause length
		elif char == 'P':
			text = ['Short', 'Normal', 'Long', 'Very Long', 'Extra Long'][config['ArmCom2'].getint('message_pause')]
		
		# messages must be dismissed manually
		elif char == 'M':
			if config['ArmCom2'].getboolean('message_prompt'):
				text = 'ON'
			else:
				text = 'OFF'
		
		# animation speed
		elif char == 'A':
			text = ['Fast', 'Normal', 'Slow'][config['ArmCom2'].getint('animation_speed')]
		
		# unit stack display
		elif char == 'D':
			if config['ArmCom2'].getboolean('unit_stack_display'):
				text = 'ON'
			else:
				text = 'OFF'
		
		# keyboard settings
		elif char == 'K':
			text = KEYBOARDS[config['ArmCom2'].getint('keyboard')]
		
		# return
		elif char == 'Esc':
			text = ''
		
		libtcod.console_print(console, x+26, y, text)
		
		y += 1


# take a keyboard input and change game settings
def ChangeGameSettings(key_char, main_menu=False):
	
	global main_theme, scenario
	global window_x, window_y

	# switch font size
	if key_char == 'f':
		if config.getboolean('ArmCom2', 'large_display_font'):
			config['ArmCom2']['large_display_font'] = 'false'
			fontname = 'c64_8x8_ext.png'
		else:
			config['ArmCom2']['large_display_font'] = 'true'
			fontname = 'c64_16x16_ext.png'
		libtcod.console_set_custom_font(DATAPATH+fontname,
			libtcod.FONT_LAYOUT_ASCII_INROW, 16, 18)
		if config.getboolean('ArmCom2', 'fullscreen'):
			libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, WINDOW_NAME,
				fullscreen=True, renderer=RENDERER, order='F', vsync=True)
			window_x, window_y = 15, 4
		else:
			libtcod.console_init_root(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_NAME,
				fullscreen=False, renderer=RENDERER, order='F', vsync=True)
			window_x, window_y = 0, 0
		FlushKeyboardEvents()
	
	# toggle fullscreen mode on/off
	elif key_char == 'u':
		if config.getboolean('ArmCom2', 'fullscreen'):
			config['ArmCom2']['fullscreen'] = 'false'
			libtcod.console_init_root(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_NAME,
				fullscreen=False, renderer=RENDERER, order='F', vsync=True)
			window_x, window_y = 0, 0
		else:
			config['ArmCom2']['fullscreen'] = 'true'
			libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, WINDOW_NAME,
				fullscreen=True, renderer=RENDERER, order='F', vsync=True)
			window_x, window_y = 15, 4
		FlushKeyboardEvents()
	
	# toggle sound effects on/off
	elif key_char == 's':
		if config['ArmCom2'].getboolean('sounds_enabled'):
			config['ArmCom2']['sounds_enabled'] = 'false'
			# stop main theme if in main menu
			if main_menu:
				mixer.Mix_FreeMusic(main_theme)
			main_theme = None
		else:
			if not session.InitMixer():
				print('Not able to init mixer, sounds remain disabled')
				return False
			config['ArmCom2']['sounds_enabled'] = 'true'
			# load main menu theme and play if in main menu
			session.LoadMainTheme()
			if main_menu:
				mixer.Mix_PlayMusic(main_theme, -1)
	
	# cycle master volume level
	elif key_char == 'v':
		if config['ArmCom2'].getboolean('sounds_enabled'):
			i = config['ArmCom2'].getint('master_volume')
			if i == 10:
				i = 1
			else:
				i += 1
			config['ArmCom2']['master_volume'] = str(i)
			session.SetMasterVolume(i)
	
	# cycle message pause length
	elif key_char == 'p':
		i = config['ArmCom2'].getint('message_pause')
		if i == 4:
			i = 0
		else:
			i += 1
		config['ArmCom2']['message_pause'] = str(i)
	
	# toggle messages must be dismissed
	elif key_char == 'm':
		if config['ArmCom2'].getboolean('message_prompt'):
			config['ArmCom2']['message_prompt'] = 'false'
		else:
			config['ArmCom2']['message_prompt'] = 'True'
	
	# cycle animation speed
	elif key_char == 'a':
		i = config['ArmCom2'].getint('animation_speed')
		if i == 2:
			i = 0
		else:
			i += 1
		config['ArmCom2']['animation_speed'] = str(i)
	
	# toggle unit stack display
	elif key_char == 'd':
		if config.getboolean('ArmCom2', 'unit_stack_display'):
			config['ArmCom2']['unit_stack_display'] = 'false'
		else:
			config['ArmCom2']['unit_stack_display'] = 'true'
		if scenario is not None:
			scenario.UpdateUnitCon()
			
	# switch keyboard layout
	elif key_char == 'k':
		
		i = config['ArmCom2'].getint('keyboard')
		if i == len(KEYBOARDS) - 1:
			i = 0
		else:
			i += 1
		config['ArmCom2']['keyboard'] = str(i)
		GenerateKeyboards()

	SaveCFG()


# display a pop-up window with a prompt and allow player to enter a text string
# can also generate randomly selected strings from a given list
# returns the final string
def ShowTextInputMenu(prompt, original_text, max_length, string_list):
	
	# display the most recent text string to screen
	def ShowText(text):
		libtcod.console_rect(0, 28, 30, 32, 1, True, libtcod.BKGND_SET)
		PrintExtended(0, 45, 30, text, center=True)
	
	# start with the original text string, can cancel input and keep this
	text = original_text
	
	# create a local copy of the current screen to re-draw when we're done
	temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
	libtcod.console_blit(0, 0, 0, 0, 0, temp_con, 0, 0)
	
	# darken screen background
	libtcod.console_blit(darken_con, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.7)
	
	# draw the text input menu to screen
	libtcod.console_rect(0, 27, 20, 34, 20, True, libtcod.BKGND_SET)
	DrawFrame(0, 27, 20, 34, 20)
	lines = wrap(prompt, 24)
	y = 23
	libtcod.console_set_default_foreground(0, libtcod.light_grey)
	for line in lines:
		libtcod.console_print_ex(0, 45, y, libtcod.BKGND_NONE, libtcod.CENTER, line.encode('IBM850'))
		y += 1
	
	libtcod.console_print_ex(0, 45, 32, libtcod.BKGND_NONE, libtcod.CENTER,
		'Max Length: ' + str(max_length) + ' chars')
	
	libtcod.console_set_default_foreground(0, ACTION_KEY_COL)
	libtcod.console_print(0, 31, 34, 'Esc')
	libtcod.console_print(0, 31, 35, 'Del')
	libtcod.console_print(0, 31, 37, 'Tab')
	
	libtcod.console_set_default_foreground(0, libtcod.white)
	libtcod.console_print(0, 37, 34, 'Cancel')
	libtcod.console_print(0, 37, 35, 'Clear')
	libtcod.console_print(0, 37, 37, 'Confirm and Continue')
	
	if len(string_list) > 0:
		libtcod.console_set_default_foreground(0, ACTION_KEY_COL)
		libtcod.console_print(0, 31, 36, 'F1')
		libtcod.console_set_default_foreground(0, libtcod.white)
		libtcod.console_print(0, 37, 36, 'Generate Random')
	
	# display current text string
	ShowText(text)
	
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		# ignore shift key being pressed
		if key.vk == libtcod.KEY_SHIFT:
			session.key_down = False
		
		# cancel text input
		if key.vk == libtcod.KEY_ESCAPE:
			# re-draw original screen and return original text string
			libtcod.console_blit(temp_con, 0, 0, 0, 0, 0, 0, 0)
			del temp_con
			return original_text
		
		# confirm and return
		elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
			exit_menu = True
			continue
		
		# select random string from list if any
		elif key.vk == libtcod.KEY_F1:
			if len(string_list) == 0: continue
			for tries in range(300):
				new_text = choice(string_list)
				if len(new_text) <= max_length:
					text = new_text
					break
		
		# clear string
		elif key.vk == libtcod.KEY_DELETE:
			text = ''
		
		# delete last character in string
		elif key.vk == libtcod.KEY_BACKSPACE:
			if len(text) == 0: continue
			text = text[:-1]
		
		# enter a new character
		else:
			
			# can't get any longer
			if len(text) == max_length: continue
			
			# accented character
			if key.vk == libtcod.KEY_TEXT:
				
				if len(key.text) > 1:
					print('Multi-character input, skipping')
					FlushKeyboardEvents()
					continue
				
				# make sure this would be a valid character to display
				encoded_text = key.text.encode('IBM850', 'ignore')
				if len(encoded_text) == 0:
					print('Character not supported')
					FlushKeyboardEvents()
					continue
				
				key_code = ord(encoded_text)
				if not (128 <= key_code <= 168):
					print('Character not supported')
					FlushKeyboardEvents()
					continue
				
				key_char = key.text
				
			else:
			
				# not a valid character
				if key.c == 0:
					print('Not a printable character')
					FlushKeyboardEvents()
					continue
				
				key_char = chr(key.c)
				if key.shift: key_char = key_char.upper()
				
				# filter key input
				if not (32 <= key.c <= 122):
					print('Character not supported')
					FlushKeyboardEvents()
					continue
			
			text += key_char
		
		FlushKeyboardEvents()
		ShowText(text)
		
	libtcod.console_blit(temp_con, 0, 0, 0, 0, 0, 0, 0)
	del temp_con
	return text


# allow the player to select one option from a list
# TODO: Need to divide list into sections of max 26 items
def GetOption(option_list, menu_title=None):
	
	def DrawOptionMenu():
		
		libtcod.console_clear(menu_con)
		
		if menu_title is not None:
			lines = wrap(menu_title, 35)
			y = 18
			for line in lines[:6]:
				libtcod.console_print_ex(menu_con, WINDOW_XM, y, libtcod.BKGND_NONE,
					libtcod.CENTER, line)
				y += 1
		
		# show list of options
		c = 65
		x = 25
		y = 21
		for text in chunk_list[selected_chunk]:
			libtcod.console_set_default_foreground(menu_con, ACTION_KEY_COL)
			libtcod.console_put_char(menu_con, x, y, chr(c))
			libtcod.console_set_default_foreground(menu_con, libtcod.light_grey)
			libtcod.console_print(menu_con, x+2, y, text)
			y += 1
			c += 1
		
		if len(chunk_list) < 1:
			y += 2
			libtcod.console_set_default_foreground(menu_con, ACTION_KEY_COL)
			libtcod.console_print(menu_con, x, y, 'Tab')
			libtcod.console_set_default_foreground(menu_con, libtcod.light_grey)
			libtcod.console_print(menu_con, x+4, y, 'Next Page')
		
		libtcod.console_blit(menu_con, 0, 0, 0, 0, 0, window_x, window_y)
	
	# divide the list of options into blocks of 26 options each
	chunk_list = []
	for i in range(0, len(option_list), 26):
		chunk_list.append(list(option_list[i:i+26]))
	
	selected_chunk = 0
	
	# create the menu console
	menu_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
	libtcod.console_set_default_background(menu_con, libtcod.black)
	libtcod.console_set_default_foreground(menu_con, libtcod.white)
	
	# draw menu console for first time
	DrawOptionMenu()
	
	option = None
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		if key.vk == libtcod.KEY_ESCAPE:
			exit_menu = True
			continue
		
		elif key.vk == libtcod.KEY_TAB:
			selected_chunk += 1
			if selected_chunk > len(chunk_list) - 1:
				selected_chunk = 0
			DrawOptionMenu()
			continue
		
		option_code = key.c - 97
		if 0 <= option_code < len(chunk_list[selected_chunk]):
			option = chunk_list[selected_chunk][option_code]
			exit_menu = True
	
	# re-draw original screen console
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()
	return option
	

# display the debug menu, not enabled in distribution versions
def ShowDebugMenu():
	
	# draw the debug menu to screen
	def DrawDebugMenu():
		libtcod.console_clear(con)
		libtcod.console_set_default_foreground(con, libtcod.light_red)
		libtcod.console_print_ex(con, WINDOW_XM, 2, libtcod.BKGND_NONE, libtcod.CENTER, 'DEBUG MENU')
		
		libtcod.console_set_default_foreground(con, TITLE_COL)
		libtcod.console_print(con, 6, 6, 'Flags')
		
		y = 8
		n = 1
		for k, value in session.debug.items():
			libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, 6, y, chr(n+64))
			if value:
				libtcod.console_set_default_foreground(con, libtcod.white)
			else:
				libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			libtcod.console_print(con, 8, y, k)
			y += 2
			n += 1
		
		# special commands
		libtcod.console_set_default_foreground(con, TITLE_COL)
		libtcod.console_print(con, 50, 6, 'Commands')
		x = 50
		y = 8
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		for xm in range(len(DEBUG_OPTIONS)):
			libtcod.console_print(con, x, y+(xm*2), str(xm+1))
		
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		for text in DEBUG_OPTIONS:
			libtcod.console_print(con, x+3, y, text)
			y += 2
			
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 33, 56, 'Esc')
		libtcod.console_print(con, 33, 57, 'Tab')
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_print(con, 39, 56, 'Return to Game')
		libtcod.console_print(con, 39, 57, 'Save Flags and Return')
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
		
	# build a dictionary of ordered letter to key values
	letter_dict = {}
	n = 1
	for k, value in session.debug.items():
		letter_dict[chr(n+64)] = k
		n += 1
	
	# save the current root console
	temp_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
	libtcod.console_blit(0, 0, 0, 0, 0, temp_con, 0, 0)
	
	# draw the menu for the first time
	DrawDebugMenu()
	
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		if key.vk == libtcod.KEY_ESCAPE:
			exit_menu = True
			continue
		
		elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
			# save current debug settings
			with open(DATAPATH + 'debug.json', 'w', encoding='utf8') as data_file:
				json.dump(session.debug, data_file, indent=1)
			exit_menu = True
			continue
		
		key_char = chr(key.c).upper()
		
		if key_char in letter_dict:
			k = letter_dict[key_char]
			# flip the flag setting
			session.debug[k] = not session.debug[k]
			DrawDebugMenu()
			continue
		
		# debug menu option
		if key_char == '0':
			num = 9
		else:
			num = ord(key_char) - 49
		if num < 0 or num > len(DEBUG_OPTIONS)-1: continue
		
		text = DEBUG_OPTIONS[num]
		
		if text == 'Regenerate CD Map Roads & Rivers':
			if campaign_day is None: continue
			campaign_day.GenerateRoads()
			campaign_day.GenerateRivers()
			campaign_day.UpdateCDMapCon()
			campaign_day.UpdateCDDisplay()
			ShowMessage('Roads and rivers regenerated')
			exit_menu = True
		
		elif text == 'Regenerate Objectives':
			if campaign_day is None: continue
			for (hx, hy) in CAMPAIGN_DAY_HEXES:
				campaign_day.map_hexes[(hx, hy)].objective = None
			campaign_day.GenerateObjectives()
			campaign_day.UpdateCDControlCon()
			campaign_day.UpdateCDDisplay()
			ShowMessage('Map objectives regenerated')
			exit_menu = True
		
		elif text == 'Spawn Enemy':
			if scenario is None: continue
			nation = GetOption(campaign.current_week['enemy_nations'], menu_title='Choose Nation')
			if nation is None: return
			unit_id = GetOption(campaign.stats['enemy_unit_list'][nation], menu_title='Choose Unit')
			if unit_id is None: return
			scenario.SpawnEnemyUnits(reinforcement=True, nation=nation, unit_id=unit_id)
			scenario.UpdateUnitCon()
			scenario.UpdateScenarioDisplay()
			ShowMessage('Spawned an enemy ' + unit_id)
			exit_menu = True
		
		elif text == 'Remove Enemy':
			if scenario is None: continue
			option_list = []
			for unit in scenario.units:
				if unit.owning_player != 1: continue
				if unit.unit_id in option_list: continue
				option_list.append(unit.unit_id)
			if len(option_list) == 0: continue
			unit_id = GetOption(option_list)
			if unit_id is None: return
			for unit in scenario.units:
				if unit.unit_id == unit_id and unit.owning_player == 1:
					unit.DestroyMe(no_vp=True)
					ShowMessage('Destroyed an enemy ' + unit_id)
					break
			exit_menu = True
		
		elif text == 'Attack Selected Crewman (Scenario)':
			if scenario is None: continue
			option_list = []
			for position in scenario.player_unit.positions_list:
				if position.crewman is None: continue
				option_list.append(position.name)
			position_name = GetOption(option_list)
			if position_name is None: return
			crewman = scenario.player_unit.GetPersonnelByPosition(position_name)
			if crewman.ResolveAttack({'firepower' : 10}) is not None:
				scenario.UpdateCrewInfoCon()
			exit_menu = True
		
		elif text == 'Set Crewman Injury':
			if scenario is None:
				unit = campaign.player_unit
			else:
				unit = scenario.player_unit
			option_list = []
			for position in unit.positions_list:
				option_list.append(position.name)
			position_name = GetOption(option_list)
			if position_name is None: continue
			
			crewman = unit.GetPersonnelByPosition(position_name)
			if crewman is None: continue
			
			option_list = []
			for text in crewman.injury.keys():
				option_list.append(text)
			option_list.append('KIA')
			location_name = GetOption(option_list)
			if location_name is None: continue
			
			if location_name == 'KIA':
				crewman.KIA()
				ShowMessage('Crewman is now dead.')
				exit_menu = True
				continue
			
			option_list = ['None', 'Light', 'Heavy', 'Serious', 'Critical']
			injury_name = GetOption(option_list)
			if injury_name is None: continue
			
			# set the injury and show message
			crewman.injury[location_name] = injury_name
			ShowMessage('Crewman ' + location_name + ' injury now ' + injury_name)
			exit_menu = True
		
		elif text == 'Set Time to End of Day':
			if campaign_day is None: continue
			campaign_day.day_clock['hour'] = campaign_day.end_of_day['hour']
			campaign_day.day_clock['minute'] = campaign_day.end_of_day['minute']
			DisplayTimeInfo(time_con)
			if scenario is not None:
				DisplayTimeInfo(scen_time_con)
			text = 'Time is now ' + str(campaign_day.day_clock['hour']).zfill(2) + ':' + str(campaign_day.day_clock['minute']).zfill(2)
			ShowMessage(text)
			exit_menu = True
		
		elif text == 'End Current Scenario':
			if scenario is None: continute
			scenario.finished = True
			ShowMessage('Scenario finished flag set to True')
			exit_menu = True
		
		elif text == 'Export Campaign Log':
			if campaign is None: continue
			ExportLog()
			ShowMessage('Log exported')
			exit_menu = True
		
		elif text == 'Regenerate Weather':
			if campaign_day is None: continue
			campaign_day.GenerateWeather()
			ShowMessage('New weather conditions generated')
			DisplayWeatherInfo(cd_weather_con)
			campaign_day.InitAnimations()
			exit_menu = True
	
	# re-draw original root console
	libtcod.console_blit(temp_con, 0, 0, 0, 0, 0, 0, 0)
	del temp_con


# display a list of crew positions and their crewmen to a console
def DisplayCrew(unit, console, x, y, highlight, darken_highlight=False, show_default=False):
	
	for position in unit.positions_list:
		
		# highlight selected position and crewman
		if highlight is not None:
			if unit.positions_list.index(position) == highlight:
				if darken_highlight:
					libtcod.console_set_default_background(console, libtcod.darkest_blue)
				else:
					libtcod.console_set_default_background(console, libtcod.darker_blue)
				libtcod.console_rect(console, x, y, 24, 4, True, libtcod.BKGND_SET)
				libtcod.console_set_default_background(console, libtcod.black)
		
		# display position name and location in vehicle (eg. turret/hull)
		
		# if crewman is untrained in this position, highlight this
		libtcod.console_set_default_foreground(console, libtcod.light_blue)
		if position.crewman is not None:
			if position.crewman.UntrainedPosition():
				libtcod.console_set_default_foreground(console, libtcod.light_red)
		libtcod.console_print(console, x, y, position.name)
		
		libtcod.console_set_default_foreground(console, libtcod.white)
		libtcod.console_print_ex(console, x+23, y, libtcod.BKGND_NONE, 
			libtcod.RIGHT, position.location)
		
		# display last name of crewman and buttoned up / exposed status if any
		if position.crewman is None:
			libtcod.console_print(console, x, y+1, 'Empty')
		else:
			# display crewman nickname if any, otherwise name
			
			# if this is the player commander, use a different colour
			libtcod.console_set_default_foreground(console, libtcod.white)
			if position.crewman.is_player_commander:
				libtcod.console_set_default_foreground(console, libtcod.gold)
			if position.crewman.nickname != '':
				libtcod.console_print(console, x, y+1, '"' + position.crewman.nickname + '"')
			else:
				PrintExtended(console, x, y+1, position.crewman.GetName(), first_initial=True)
			
			libtcod.console_set_default_foreground(console, libtcod.white)
			if not position.hatch:
				text = '--'
			elif position.crewman.ce:
				text = 'CE'
			else:
				text = 'BU'
			libtcod.console_print_ex(console, x+23, y+1, libtcod.BKGND_NONE,
				libtcod.RIGHT, text)
			
			# display current condition if not Good Order
			if position.crewman.condition != 'Good Order':
				libtcod.console_set_default_foreground(console, libtcod.red)
				libtcod.console_print(console, x, y+2,
					position.crewman.condition)
			
			# display fatigue if any
			if position.crewman.fatigue > 0:
				libtcod.console_set_default_foreground(console, libtcod.red)
				libtcod.console_print_ex(console, x+23, y+2, libtcod.BKGND_NONE, libtcod.RIGHT, 
					'-' + str(position.crewman.fatigue) + '%')
			
			# display default command if any
			if show_default and position.crewman.default_start is not None:
				libtcod.console_set_default_foreground(console, libtcod.light_grey)
				text = '[' + position.crewman.default_start[1] + '] - '
				if position.crewman.default_start[0]:
					text += 'CE'
				else:
					text += 'BU'
				libtcod.console_print(console, x, y+3, text)
				
		libtcod.console_set_default_foreground(console, libtcod.white)
		y += 5


# generate keyboard encoding and decoding dictionaries
def GenerateKeyboards():
	global keyboard_decode, keyboard_encode
	keyboard_decode = {}
	keyboard_encode = {}
	with open(DATAPATH + 'keyboard_mapping.json', encoding='utf8') as data_file:
		keyboards = json.load(data_file)
	dictionary = keyboards[KEYBOARDS[config['ArmCom2'].getint('keyboard')]]
	for key, value in dictionary.items():
		keyboard_decode[key] = value
		keyboard_encode[value] = key


# turn an inputted key into a standard key input
def DeKey(key_char):
	if key_char in keyboard_decode: return keyboard_decode[key_char]
	return key_char


# turn a standard key into the one for the current keyboard layout
def EnKey(key_char):
	if key_char in keyboard_encode: return keyboard_encode[key_char]
	return key_char


# load campaign menu
def LoadCampaignMenu(continue_most_recent):
	
	def UpdateLoadCampaignScreen(selected_save):
		libtcod.console_clear(con)
		
		# menu title
		libtcod.console_set_default_foreground(con, libtcod.light_blue)
		DrawFrame(con, 33, 1, 25, 5)
		libtcod.console_set_default_foreground(con, libtcod.yellow)
		libtcod.console_print_ex(con, 45, 3, libtcod.BKGND_NONE, libtcod.CENTER,
			'Load Saved Campaign')
		
		# list of saved campaigns
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_set_default_background(con, libtcod.darker_blue)
		
		s = saved_game_list.index(selected_save)
		y = 5
		
		for i in range(s-7, s+10):
			if i < 0:
				y += 3
				continue
			elif i > len(saved_game_list) - 1:
				break
			
			if saved_game_list[i] == selected_save:
				libtcod.console_rect(con, 2, y, 23, 2, True, libtcod.BKGND_SET)
			
			lines = wrap(saved_game_list[i]['campaign_name'], 23)
			y1 = 0
			for line in lines[:2]:
				libtcod.console_print(con, 2, y+y1, line)
				y1 += 1
			
			y += 3
		
		# display details about selected saved campaign
		libtcod.console_blit(session.flags[selected_save['nation']],
			0, 0, 0, 0, con, 31, 10)
		
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_set_default_background(con, libtcod.black)
		
		y = 30
		libtcod.console_print_ex(con, WINDOW_XM, y, libtcod.BKGND_NONE, libtcod.CENTER,
			'Saved Campaign')
		libtcod.console_print_ex(con, WINDOW_XM, y+3, libtcod.BKGND_NONE, libtcod.CENTER,
			'Current VP')
		libtcod.console_print_ex(con, WINDOW_XM, y+6, libtcod.BKGND_NONE, libtcod.CENTER,
			'Current Date')
		libtcod.console_print_ex(con, WINDOW_XM, y+11, libtcod.BKGND_NONE, libtcod.CENTER,
			'Game Version')
		
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		libtcod.console_print_ex(con, WINDOW_XM, y+1, libtcod.BKGND_NONE, libtcod.CENTER,
			selected_save['campaign_name'])
		libtcod.console_print_ex(con, WINDOW_XM, y+4, libtcod.BKGND_NONE, libtcod.CENTER,
			str(selected_save['total_vp']))
		libtcod.console_print_ex(con, WINDOW_XM, y+7, libtcod.BKGND_NONE, libtcod.CENTER,
			str(selected_save['date']))
		if CheckSavedGameVersion(selected_save['version']) != '':
			libtcod.console_set_default_foreground(con, libtcod.light_red)
		libtcod.console_print_ex(con, WINDOW_XM, y+12, libtcod.BKGND_NONE, libtcod.CENTER,
			str(selected_save['version']))
		
		
		# display key commands
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 32, 51, EnKey('w').upper() + '/' + EnKey('s').upper())
		libtcod.console_print(con, 32, 52, 'Tab')
		libtcod.console_print(con, 32, 53, 'D')
		libtcod.console_print(con, 32, 54, 'Esc')
		
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_print(con, 38, 51, 'Select Saved Campaign')
		libtcod.console_print(con, 38, 52, 'Load and Continue Campaign')
		libtcod.console_print(con, 38, 53, 'Delete Saved Campaign')
		libtcod.console_print(con, 38, 54, 'Return to Main Menu')
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			
	
	# generate a list of all saved campaigns
	saved_game_list = []
	for directory in os.listdir(SAVEPATH):
		if not os.path.isdir(SAVEPATH + directory): continue
		
		game_info = {}
		
		# try to open file, prompt to try and restore backup if any
		finished_with_file = False
		path = SAVEPATH + directory + os.sep
		while not finished_with_file:
			try:
				with shelve.open(path + 'savegame') as save:
					game_info['directory'] = directory
					game_info['datetime'] = save['datetime']
					game_info['campaign_name'] = save['campaign'].stats['name']
					game_info['nation'] = save['campaign'].stats['player_nation']
					game_info['total_vp'] = save['campaign'].player_vp
					game_info['date'] = save['campaign'].today
					game_info['version'] = save['version']
				saved_game_list.append(game_info)
				finished_with_file = True
			except:
				
				# check for backup
				backup_path = BACKUP_PATH + directory + os.sep
				
				# no backup available
				if not os.path.isdir(backup_path):
					ShowNotification('Error in saved campaign: ' + directory + ', no backup available.')
					finished_with_file = True
				else:
					if not ShowNotification('Error in saved campaign: ' + directory + ', try to restore backup copy?', confirm=True):
						finished_with_file = True
					else:
						copyfile(backup_path + 'savegame.dat', path + 'savegame.dat')
						copyfile(backup_path + 'savegame.dir', path + 'savegame.dir')
						copyfile(backup_path + 'savegame.bak', path + 'savegame.bak')
						os.remove(backup_path + 'savegame.dat')
						os.remove(backup_path + 'savegame.dir')
						os.remove(backup_path + 'savegame.bak')
						os.rmdir(backup_path)
						ShowNotification('Restored backup, will attempt to load.')
	
	# make sure there's at least one saved game
	if len(saved_game_list) == 0:
		return False
	
	# sort by most recently saved
	saved_game_list = sorted(saved_game_list, key=lambda k: k['datetime'], reverse=True)
	
	# if we're continuing, try to load the most recently saved and return
	if continue_most_recent:
		if CheckSavedGameVersion(saved_game_list[0]['version']) != '':
			return False
		LoadGame(saved_game_list[0]['directory'])
		return True
	
	# otherwise, show menu and get player input
	
	# select first campaign by default
	selected_save = saved_game_list[0]
		
	# draw menu screen for first time
	UpdateLoadCampaignScreen(selected_save)
		
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		# return to main menu without loading a game
		if key.vk == libtcod.KEY_ESCAPE:
			return False
		
		# try to proceed with loading selected campaign
		elif key.vk in [libtcod.KEY_ENTER, libtcod.KEY_KPENTER, libtcod.KEY_TAB]:
			
			if CheckSavedGameVersion(selected_save['version']) != '':
				ShowNotification('Saved campaign is not compatible with current game version.')
				continue
			exit_menu = True
		
		# delete selected saved campaign (not keymapped)
		elif chr(key.c).lower() == 'd':
			if ShowNotification('Really delete this saved campaign?', confirm=True):
				EraseGame(selected_save['directory'])
				saved_game_list.remove(selected_save)
				if len(saved_game_list) == 0:
					return False
				selected_save = saved_game_list[0]
				UpdateLoadCampaignScreen(selected_save)
				continue
		
		key_char = DeKey(chr(key.c).lower())
		
		# change selected campaign
		if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN]:
			
			i = saved_game_list.index(selected_save)
			
			if key_char == 'w' or key.vk == libtcod.KEY_UP:
				if i == 0:
					selected_save = saved_game_list[-1]
				else:
					selected_save = saved_game_list[i-1]
			else:
				if i == len(saved_game_list) - 1:
					selected_save = saved_game_list[0]
				else:
					selected_save = saved_game_list[i+1]
			PlaySoundFor(None, 'menu_select')
			UpdateLoadCampaignScreen(selected_save)
			continue
	
	# load the game and return
	LoadGame(selected_save['directory'])
	return True


# display campaign records
def ShowRecordsMenu():
	
	def UpdateRecordsMenuScreen():
		libtcod.console_clear(con)
		
		libtcod.console_set_default_foreground(con, libtcod.grey)
		DrawFrame(con, 2, 2, 86, 56)
		DrawFrame(con, 2, 10, 86, 0)
		libtcod.console_set_default_background(con, libtcod.light_blue)
		libtcod.console_rect(con, 3, 3, 84, 7, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(con, libtcod.darker_green)
		libtcod.console_rect(con, 3, 9, 84, 1, False, libtcod.BKGND_SET)
		libtcod.console_rect(con, 12, 8, 75, 1, False, libtcod.BKGND_SET)
		libtcod.console_rect(con, 55, 7, 32, 1, False, libtcod.BKGND_SET)
		libtcod.console_rect(con, 60, 6, 27, 1, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(con, libtcod.black)
		libtcod.console_rect(con, 35, 5, 18, 3, False, libtcod.BKGND_SET)
		
		libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
		libtcod.console_print_ex(con, 44, 6, libtcod.BKGND_NONE,
			libtcod.CENTER, 'Campaign Records')
		
		libtcod.console_set_default_foreground(con, libtcod.darker_grey)
		libtcod.console_put_char(con, 9, 8, chr(197))
		libtcod.console_put_char(con, 14, 7, chr(197))
		libtcod.console_put_char(con, 21, 7, chr(42))
		libtcod.console_put_char(con, 66, 5, chr(197))
		
		# column headings
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_print(con, 4, 12, 'Name')
		libtcod.console_print(con, 29, 12, 'Level')
		libtcod.console_print(con, 37, 12, 'VP')
		libtcod.console_print(con, 42, 12, 'Fate')
		libtcod.console_print(con, 52, 12, 'Days')
		libtcod.console_print(con, 58, 12, 'Campaign')
		libtcod.console_print(con, 77, 12, 'Version')
		
		# list of top records, sorted by VP
		y = 15
		for (name, level, vp, fate, days, campaign, version) in session.morgue[:10]:
			libtcod.console_set_default_foreground(con, libtcod.lighter_grey)
			
			PrintExtended(con, 4, y, name)
			
			libtcod.console_print_ex(con, 32, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(level))
			libtcod.console_print_ex(con, 39, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(vp))
			libtcod.console_print(con, 42, y, fate)
			libtcod.console_print_ex(con, 54, y, libtcod.BKGND_NONE,
				libtcod.RIGHT, str(days))
			
			y1 = y
			for line in wrap(campaign, 18)[:2]:
				libtcod.console_print(con, 58, y1, line)
				y1 += 1
			
			y1 = y
			for line in wrap(version, 8)[:2]:
				libtcod.console_print(con, 77, y1, line)
				y1 += 1
			
			libtcod.console_set_default_foreground(con, libtcod.darker_grey)
			for x in range(4, 85):
				libtcod.console_put_char(con, x, y+2, chr(45))
			
			y += 3
		
		# key command
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 34, 54, 'C')
		libtcod.console_print(con, 34, 55, 'Esc')
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		libtcod.console_print(con, 40, 54, 'Clear All Records')
		libtcod.console_print(con, 40, 55, 'Return to Main Menu')
		
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	
	# draw menu screen for first time
	UpdateRecordsMenuScreen()
	
	exit_menu = False
	while not exit_menu:
		libtcod.console_flush()
		if not GetInputEvent(): continue
		
		# clear all records
		if chr(key.c).lower() == 'c':
			
			# shouldn't happen, but just check
			if not os.path.exists(DATAPATH + 'morguefile.dat'): continue
			
			if not ShowNotification('All records will be deleted forever!', confirm=True): continue
			
			os.remove(DATAPATH + 'morguefile.dat')
			session.morgue = []
			with shelve.open(DATAPATH + 'morguefile', 'n') as save:
				save['morgue'] = session.morgue
			exit_menu = True
			continue
		
		# return to main menu
		if key.vk == libtcod.KEY_ESCAPE:
			exit_menu = True
			continue


# write a line to the bootlog, used to diagnose crashes or failure to boot
def WriteBootLog(text, clear_log=False):
	home_path = str(Path.home()) + os.sep + 'ArmCom2'
	if not os.path.isdir(home_path): os.mkdir(home_path)
	filename = home_path + os.sep + 'bootlog.txt'
	if not os.path.exists(filename):
		with open(filename, 'w', encoding='utf-8') as f:
			f.write('ArmCom2 Bootlog:\n')
	elif clear_log:
		os.remove(filename)
	with open(filename, 'a', encoding='utf-8') as f:
		f.write(text + '\n')


# output a crash log before closing
def OutputCrashLog(text):
	home_path = str(Path.home()) + os.sep + 'ArmCom2'
	if not os.path.isdir(home_path): os.mkdir(home_path)
	filename = home_path + os.sep + 'crashlog_' + datetime.now().strftime("%Y-%m-%d_%H_%M_%S") + '.txt'
	with open(filename, 'w', encoding='utf-8') as f:
		f.write('ArmCom2 Crashlog, (' + VERSION + '):\n')
		f.write(text + '\n\n')


# handle continuing into a new campaign after one is completed
def ContinueCampaign():
	global campaign, campaign_day, scenario
	
	# don't allow if Player Commander is dead
	for position in campaign.player_unit.positions_list:
		if position.crewman is None: continue
		if position.crewman.is_player_commander and not position.crewman.alive:
			return False
	
	# check to see if any crew are left!
	all_dead = True
	for position in campaign.player_unit.positions_list:
		if position.crewman is None: continue
		if not position.crewman.alive: continue
		all_dead = False
		break
	
	if all_dead: return False
	
	# scan campaigns and build a list of possible ones to continue into
	campaign_list = []
	for filename in os.listdir(CAMPAIGNPATH):
		if not filename.endswith('.json'): continue
		try:
			with open(CAMPAIGNPATH + filename, encoding='utf8') as data_file:
				campaign_data = json.load(data_file)
		except Exception as e:
			continue
		if campaign_data['player_nation'] != campaign.stats['player_nation']: continue
		if campaign_data['start_date'] < campaign.stats['end_date']: continue
		campaign_list.append(filename)
	
	# no possible ones to continue into
	if len(campaign_list) == 0:
		return False
	
	# confirm with player
	if not ShowNotification('Continue on a new campaign with surviving crewmen?', confirm=True, add_pause=True):
		return False
	
	# create a new campaign object, copy over the old player unit and its crew to the
	# new campaign, and make the campaign object the new campaign
	new_campaign = Campaign()
	new_campaign.player_unit = campaign.player_unit
	(year1, month1, day1) = campaign.stats['end_date'].split('.')
	old_campaign = campaign
	campaign = new_campaign
	
	# show a restricted campaign selection menu, then the campaign options menu
	if not campaign.CampaignSelectionMenu(campaign_list=campaign_list):
		return False
	if not campaign.CampaignOptionsMenu():
		return False
	
	# apply advance bonuses to crewmen and re-calculate their age
	(year2, month2, day2) = campaign.stats['start_date'].split('.')
	a = datetime(int(year2), int(month2), int(day2), 0, 0, 0) - datetime(int(year1), int(month1), int(day1), 0, 0, 0)
	advances = int(ceil(a.days / CONTINUE_CAMPAIGN_LEVEL_UP_DAYS))
	ShowNotification('Your crewmen receive ' + str(advances) + ' advance points from training.')
	for position in campaign.player_unit.positions_list:
		if position.crewman is None: continue
		position.crewman.level += advances
		new_exp = GetExpRequiredFor(position.crewman.level)
		if position.crewman.exp < new_exp:
			position.crewman.exp = new_exp
		position.crewman.adv += advances
		position.crewman.CalculateAge()
	
	# allow player to choose a new tank
	campaign.ReplacePlayerTank()
	# generate new crewmen to fill vacant positions if required
	for position in campaign.player_unit.positions_list:
		if position.crewman is None:
			position.crewman = Personnel(campaign.player_unit, campaign.player_unit.nation, position)
	
	# finish setting up the campaign
	campaign.DoPostInitChecks()
	
	# create a new campaign day and a placeholder for the current scenario
	campaign_day = CampaignDay()
	for (hx, hy) in CAMPAIGN_DAY_HEXES:
		campaign_day.map_hexes[(hx,hy)].CalcCaptureVP()
	campaign_day.GenerateRoads()
	campaign_day.GenerateRivers()
	campaign.AddJournal('Start of day')
	
	# placeholder for the currently active scenario
	scenario = None
	
	return True


# display a Loading message on the cdouble buffer console
def DisplayLoadingMsg():
	libtcod.console_set_default_background(con, libtcod.black)
	libtcod.console_rect(con, WINDOW_XM-6, WINDOW_YM-1, 12, 3, True, libtcod.BKGND_SET)
	libtcod.console_print_ex(con, WINDOW_XM, WINDOW_YM, libtcod.BKGND_NONE, libtcod.CENTER,
		'Loading...')
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()


# show a gallery of all the unit types in the game
def UnitGallery():
	
	def UpdateUnitGalleryScreen():
		libtcod.console_clear(con)
		
		libtcod.console_set_default_background(con, libtcod.darker_blue)
		libtcod.console_rect(con, 27, 2, 35, 3, False, libtcod.BKGND_SET)
		libtcod.console_set_default_background(con, libtcod.black)
		
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print_ex(con, 45, 3, libtcod.BKGND_NONE, libtcod.CENTER,
			'Unit Gallery')
		
		libtcod.console_set_default_foreground(con, libtcod.light_grey)
		libtcod.console_print_ex(con, 45, 6, libtcod.BKGND_NONE, libtcod.CENTER,
			str(len(unit_type_list)) + ' unit types')
		
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_set_default_background(con, libtcod.dark_blue)
		
		# list of unit types
		y = 5
		s = unit_type_list.index(selected_unit)
		for i in range(s-20, s+30):
			if i < 0:
				y += 1
				continue
			elif i > len(unit_type_list) - 1:
				break
			
			# this unit type is the currently highlighted one
			if i == s:
				libtcod.console_rect(con, 2, y, 23, 1, True, libtcod.BKGND_SET)
			
			libtcod.console_print(con, 2, y, unit_type_list[i])
			
			y += 1
		
		unit_type = session.unit_types[selected_unit]
		
		# display basic info on selected unit type
		DisplayUnitInfo(con, 33, 11, selected_unit, None)
		
		# display rarity info
		if 'rarity' in unit_type:
			libtcod.console_set_default_foreground(con, libtcod.white)
			libtcod.console_print(con, 33, 40, 'Historical Availability:')
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			y = 42
			for date, chance in unit_type['rarity'].items():
				libtcod.console_print(con, 33, y, GetDateText(date) + ':')
				libtcod.console_print(con, 53, y, str(chance) + '%')
				y += 1
				
		
		# display unit positions if any
		y = 11
		if 'crew_positions' in unit_type:
			libtcod.console_set_default_foreground(con, libtcod.lighter_blue)
			libtcod.console_print(con, 63, y, 'Personnel')
			libtcod.console_set_default_foreground(con, libtcod.white)
			y += 1
			for position in unit_type['crew_positions']:
				y += 1
				libtcod.console_print(con, 64, y, position['name'])
		
		# display historical notes if any
		if 'description' in unit_type:
			text = ''
			for t in unit_type['description']:
				text += t
			lines = wrap(text, 33)
			y = 28
			libtcod.console_set_default_foreground(con, libtcod.light_grey)
			for line in lines[:20]:
				libtcod.console_print(con, 30, y, line)
				y+=1

		# menu commands
		libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
		libtcod.console_print(con, 32, 55, EnKey('w').upper() + '/' + EnKey('s').upper())
		libtcod.console_print(con, 32, 56, 'PgUp/PgDn')
		libtcod.console_print(con, 32, 57, 'Esc')
		
		libtcod.console_set_default_foreground(con, libtcod.white)
		libtcod.console_print(con, 42, 55, 'Scroll Up/Down')
		libtcod.console_print(con, 42, 56, 'Scroll 10 Up/Down')
		libtcod.console_print(con, 42, 57, 'Return to Main Menu')
		
		libtcod.console_set_default_background(con, libtcod.black)
		libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	
	# build a list of all the current unit types
	unit_type_list = []
	for k, v in session.unit_types.items():
		unit_type_list.append(k)
	
	# select the first one by default
	selected_unit = unit_type_list[0]
	
	# draw screen for first time
	UpdateUnitGalleryScreen()
	
	exit_loop = False
	while not exit_loop:
		libtcod.console_flush()
		if not GetInputEvent(): continue
	
		# exit menu
		if key.vk == libtcod.KEY_ESCAPE:
			return
		
		key_char = DeKey(chr(key.c).lower())
		
		if key_char in ['w', 's'] or key.vk in [libtcod.KEY_UP, libtcod.KEY_DOWN, libtcod.KEY_PAGEUP, libtcod.KEY_PAGEDOWN]:
			
			i = unit_type_list.index(selected_unit)
			
			if key_char == 'w' or key.vk in [libtcod.KEY_UP, libtcod.KEY_PAGEUP]:
				
				if key_char == 'w' or key.vk == libtcod.KEY_UP:
					i -= 1
				else:
					i -= 10
				if i < 0:
					i = len(unit_type_list) - 1
				
			else:
				
				if key_char == 's' or key.vk == libtcod.KEY_DOWN:
					i += 1
				else:
					i += 10
				if i > len(unit_type_list) - 1:
					i = 0
				
			selected_unit = unit_type_list[i]
			PlaySoundFor(None, 'menu_select')
			UpdateUnitGalleryScreen()
			continue


# display info on a unit type or a particular spawned unit object
def DisplayUnitInfo(console, x, y, unit_id, unit_obj, status=True):
	
	unit_type = session.unit_types[unit_id]
	
	libtcod.console_set_default_background(console, libtcod.black)
	libtcod.console_set_default_foreground(console, libtcod.lighter_blue)
	
	# unit id
	libtcod.console_print(console, x, y, unit_id)
	
	# display type nickname if any
	if 'nick_name' in unit_type:
		libtcod.console_set_default_foreground(console, libtcod.white)
		libtcod.console_print_ex(console, x+24, y, libtcod.BKGND_NONE,
			libtcod.RIGHT, unit_type['nick_name'])
	
	# unit class
	libtcod.console_set_default_foreground(console, libtcod.light_grey)
	libtcod.console_print(console, x, y+1, unit_type['class'])
	
	# draw empty portrait background
	libtcod.console_set_default_background(console, PORTRAIT_BG_COL)
	libtcod.console_rect(console, x, y+2, 25, 8, True, libtcod.BKGND_SET)
	
	# portrait if any
	if 'portrait' in unit_type:
		libtcod.console_blit(LoadXP(unit_type['portrait']), 0, 0, 0, 0, console, x, y+2)
	
	# info for spawned units
	if unit_obj is not None:
	
		# display unit name if any overtop portrait
		if unit_obj.unit_name != '':
			libtcod.console_set_default_foreground(console, libtcod.white)
			libtcod.console_print(console, x, y+2, unit_obj.unit_name)
		
		# display captured status
		if campaign is not None and scenario is not None:
			if 'enemy_captured_units' in campaign.stats:
				if unit_obj.owning_player == 1 and unit_id in campaign.stats['enemy_captured_units']:
					libtcod.console_set_default_foreground(console, libtcod.white)
					libtcod.console_print(console, x, y+2, '(Captured)')
		
		# display remaining fate points if player and in campaign day
		if campaign_day is not None and unit_obj.is_player:
			if campaign_day.fate_points > 0:
				libtcod.console_set_default_foreground(console, libtcod.darker_purple)
				libtcod.console_print_ex(console, x+24, y+2, libtcod.BKGND_NONE,
					libtcod.RIGHT, str(campaign_day.fate_points))
	
	# display default weapons; will not display any close-combat weapons added to a unit after spawn
	# display turret mounts on line 1, all others on line 2
	# keep track of x location and display in red if jammed, dark grey if broken
	libtcod.console_set_default_background(console, libtcod.darkest_red)
	libtcod.console_rect(console, x, y+10, 25, 2, True, libtcod.BKGND_SET)
	
	if 'weapon_list' in unit_type:
		x1 = x
		x2 = x
		i = 0
		for weapon_type in unit_type['weapon_list']:
			
			# set display colour
			libtcod.console_set_default_foreground(console, libtcod.white)
			
			if 'unreliable' in weapon_type:
				libtcod.console_set_default_foreground(console, libtcod.light_grey)
			
			# highlight if on a spawned unit and broken or jammed
			if unit_obj is not None:
				weapon = unit_obj.weapon_list[i]
				if weapon.broken:
					libtcod.console_set_default_foreground(console, libtcod.darker_grey)
				elif weapon.jammed:
					libtcod.console_set_default_foreground(console, libtcod.light_red)
		
			# generate weapon name text
			if 'name' in weapon_type:
				text = weapon_type['name']
			elif weapon_type['type'] == 'Gun':
				text = weapon_type['calibre']
				if 'long_range' in weapon_type:
					text += weapon_type['long_range']
			elif weapon_type['type'] in MG_WEAPONS and 'calibre' in weapon_type:
				text = weapon_type['calibre'] + 'mm MG'
			else:
				text = weapon_type['type']
			
			upper_line = True
			if 'mount' in weapon_type:
				if weapon_type['mount'] != 'Turret':
					upper_line = False
			
			if upper_line:
				if x1 != x:
					text = ', ' + text
				libtcod.console_print(console, x1, y+10, text)
				x1 += len(text)
			else:
				if x2 != x:
					text = ', ' + text
				libtcod.console_print(console, x2, y+11, text)
				x2 += len(text)
			
			i += 1
	
	# armour if any
	libtcod.console_set_default_foreground(console, libtcod.white)
	armoured = False
	if 'armour' not in unit_type:
		if unit_type['category'] == 'Vehicle':
			libtcod.console_print(console, x, y+12, 'Unarmoured')
	else:
		armoured = True
		libtcod.console_print(console, x, y+12, 'Armoured')
		libtcod.console_set_default_foreground(console, libtcod.light_grey)
		if 'no_turret' not in unit_type:
			text = 'U'
			if 'turret' in unit_type:
				if unit_type['turret'] != 'FIXED':
					text = 'T'
			text += ' ' + unit_type['armour']['turret_front'] + '/' + unit_type['armour']['turret_side']
			libtcod.console_print(console, x+1, y+13, text)
		
		text = 'H ' + unit_type['armour']['hull_front'] + '/' + unit_type['armour']['hull_side']
		libtcod.console_print(console, x+1, y+14, text)
	
	# turret traverse info
	if 'turret' in unit_type:
		if unit_type['turret'] == 'FT':
			if armoured:
				libtcod.console_print(console, x+8, y+13, '(fast)')
			else:
				libtcod.console_print(console, x+1, y+13, 'Fast Turret')
		elif unit_type['turret'] == 'VST':
			if armoured:
				libtcod.console_print(console, x+8, y+13, '(slow)')
			else:
				libtcod.console_print(console, x+1, y+13, 'Slow Turret')
		elif unit_type['turret'] == 'RST':
			if armoured:
				libtcod.console_print(console, x+8, y+13, '(restricted)')
			else:
				libtcod.console_print(console, x+1, y+13, 'Restricted Turret')
	
	# movement class, ground pressure
	text = unit_type['movement_class']
	if 'powerful_engine' in unit_type:
		text += '+'
	if 'unreliable' in unit_type:
		text += '(u)'
	libtcod.console_set_default_foreground(console, libtcod.green)
	if 'ground_pressure' in unit_type:
		if unit_type['ground_pressure'] == 'Light':
			libtcod.console_set_default_foreground(console, libtcod.lighter_green)
		elif unit_type['ground_pressure'] == 'Heavy':
			libtcod.console_set_default_foreground(console, libtcod.darker_green)
	
	# status for spawned unit objects
	if unit_obj is not None:
		if unit_obj.immobilized:
			libtcod.console_set_default_foreground(console, libtcod.light_red)
			text = 'Immobilized'
		elif unit_obj.bogged:
			libtcod.console_set_default_foreground(console, libtcod.light_red)
			text = 'Bogged Down'
	
	libtcod.console_print_ex(console, x+24, y+12, libtcod.BKGND_NONE, libtcod.RIGHT,
		text)
	
	# HVSS, recce, and/or off road
	libtcod.console_set_default_foreground(console, libtcod.dark_green)
	text = ''
	if 'HVSS' in unit_type:
		text += 'HVSS'
	if 'recce' in unit_type:
		if text != '':
			text += ' '
		text += 'Recce'
	if 'off_road' in unit_type:
		if text != '':
			text += ' '
		text += 'ATV'
	libtcod.console_print_ex(console, x+24, y+13, libtcod.BKGND_NONE, libtcod.RIGHT,
		text)
	
	# size class if any
	if 'size_class' in unit_type:
		if unit_type['size_class'] != 'Normal':
			libtcod.console_set_default_foreground(console, libtcod.white)
			libtcod.console_print_ex(console, x+24, y+14, libtcod.BKGND_NONE,
				libtcod.RIGHT, unit_type['size_class'])
	
	# return now if no spawned object or not displaying status
	if unit_obj is None or not status:
		libtcod.console_set_default_background(console, libtcod.black)
		return
	
	# Hull Down status if any
	if len(unit_obj.hull_down) > 0:
		libtcod.console_set_default_foreground(console, libtcod.sepia)
		libtcod.console_print(console, x+8, y+14, 'HD')
		char = GetDirectionalArrow(unit_obj.hull_down[0])
		libtcod.console_put_char_ex(console, x+10, y+14, char, libtcod.sepia, libtcod.black)
	
	# reduction if any
	elif unit_obj.reduced:
		libtcod.console_set_default_foreground(console, libtcod.light_red)
		libtcod.console_print(console, x, y+14, 'Reduced')
	
	# rest of unit status
	libtcod.console_set_default_foreground(console, libtcod.light_grey)
	libtcod.console_set_default_background(console, libtcod.darkest_blue)
	libtcod.console_rect(console, x, y+15, 25, 2, True, libtcod.BKGND_SET)
	
	text = ''
	if unit_obj.routed:
		text += 'Routed '
	elif unit_obj.pinned:
		text += 'Pinned '
	if unit_obj.moving:
		text += 'Moving '
	if unit_obj.fired:
		text += 'Fired '
	libtcod.console_print(console, x, y+16, text)
	
	# terrain and smoke/dust status
	libtcod.console_set_default_background(console, libtcod.darker_sepia)
	libtcod.console_rect(console, x, y+17, 25, 2, True, libtcod.BKGND_SET)
	
	if unit_obj.terrain is not None:
		libtcod.console_set_default_foreground(console, libtcod.green)
		libtcod.console_print(console, x, y+17, unit_obj.terrain)
	
	text = ''
	if unit_obj.smoke > 0:
		text += 'Smoke: ' + str(unit_obj.smoke)
	if unit_obj.dust > 0:
		if unit_obj.smoke > 0:
			text += ' '
		text += 'Dust: ' + str(unit_obj.dust)
	
	if text != '':
		libtcod.console_set_default_foreground(console, libtcod.grey)
		libtcod.console_print_ex(console, x+24, y+17, libtcod.BKGND_NONE,
			libtcod.RIGHT, text)
	
	libtcod.console_set_default_background(console, libtcod.black)


##########################################################################################
#                                     Sound Effects                                      #
##########################################################################################

# play a given sample
def PlaySound(sound_name):
	sample = mixer.Mix_LoadWAV((SOUNDPATH + sound_name + '.ogg').encode('ascii'))
	if sample is None:
		print('ERROR: Sound not found: ' + sound_name)
		return
	mixer.Mix_PlayChannel(-1, sample, 0)


# select and play a sound effect for a given situation
def PlaySoundFor(obj, action):
	
	BASIC_SOUNDS = [
		'menu_select', 'tab_select', 'weapon_break', 'player_pivot', 'player_turret',
		'landmine'
	]
	
	# sounds disabled
	if not config['ArmCom2'].getboolean('sounds_enabled'):
		return
		
	# basic sounds, no variations
	if action in BASIC_SOUNDS:
		PlaySound(action)
		return

	elif action == 'movement':
		
		# no sound effect if concealed enemy unit
		if obj.owning_player == 1 and not obj.spotted:
			return
		
		if obj.GetStat('movement_class') in ['Wheeled', 'Fast Wheeled']:
			PlaySound('wheeled_moving_0' + str(libtcod.random_get_int(0, 0, 2)))
			return
		
		elif obj.GetStat('movement_class') == 'Infantry':
			PlaySound('infantry_moving')
			return
		
		# FUTURE - these will each have their own movement sounds
		elif obj.GetStat('class') in ['Tankette', 'Light Tank', 'Medium Tank', 'Heavy Tank', 'Tank Destroyer', 'Half-Tracked', 'Assault Gun']:
			PlaySound('light_tank_moving_0' + str(libtcod.random_get_int(0, 0, 2)))
			return
		
		# no other sounds for now
		else:
			return
	
	elif action == 'fire':
		if obj.GetStat('type') == 'Gun':
			
			if obj.GetStat('name') == 'AT Rifle':
				PlaySound('at_rifle_firing')
				return
			
			# temp - used for all large guns for now
			PlaySound('37mm_firing_0' + str(libtcod.random_get_int(0, 0, 3)))
			return
			
		if obj.stats['type'] in MG_WEAPONS:
			PlaySound('zb_53_mg_00')
			return
		
		if obj.GetStat('name') == 'Rifles':
			PlaySound('rifle_fire_0' + str(libtcod.random_get_int(0, 0, 3)))
			return
		
		if obj.GetStat('name') == 'Grenades':
			PlaySound('grenades')
			return
		if obj.GetStat('name') == 'Flame Thrower':
			PlaySound('flamethrower')
			return
		
	elif action == 'unit_ko':
		if obj.GetStat('category') in ['Infantry', 'Cavalry']:
			PlaySound('ko_infantry')
		return
	
	elif action == 'he_explosion':
		PlaySound('37mm_he_explosion_0' + str(libtcod.random_get_int(0, 0, 1)))
		return
	
	elif action == 'armour_save':
		PlaySound('armour_save_0' + str(libtcod.random_get_int(0, 0, 1)))
		return
	
	elif action == 'armour_penetrated':
		PlaySound('armour_penetrated')
		return
	
	elif action == 'vehicle_explosion':
		PlaySound('vehicle_explosion_00')
		return
	
	elif action == 'plane_incoming':
		PlaySound('plane_incoming_00')
		return
	
	elif action == 'stuka_divebomb':
		PlaySound('stuka_divebomb_00')
		return
	
	elif action == 'ricochet':
		PlaySound('ricochet')
		return
	
	elif action == 'sniper_hit':
		PlaySound('sniper_hit')
		return
	
	elif action == 'move_1_shell':
		PlaySound('shell_move_1')
		return
	
	elif action == 'move_10_shell':
		PlaySound('shell_move_10')
		return
	
	elif action == 'add skill':
		PlaySound('add_skill')
		return
	
	elif action == 'command_select':
		PlaySound('command_select')
		return
	
	elif action == 'smoke':
		PlaySound('smoke')
		return
	
	elif action == 'hatch':
		PlaySound('hatch')
		return
	
	elif action == 'hull_down_save':
		PlaySound('hull_down_save')
		return
	
	print ('ERROR: Could not determine which sound to play for action: ' + action)




##########################################################################################
#                                      Main Script                                       #
##########################################################################################

global window_x, window_y
global main_title, main_theme
global campaign, campaign_day, scenario, session
global keyboard_decode, keyboard_encode
global steam_active

campaign_day = None
scenario = None

WriteBootLog('Starting ' + NAME + ' version ' + VERSION, clear_log=True)	# startup message
print(NAME + ' ' + VERSION + ' - Console Window\n')
print('Diagnostic and error messages may appear here, otherwise you can safely ignore this window while playing.\n\n')

# try to load game settings from config file, will create a new file if none present
LoadCFG()
WriteBootLog('Config file loaded')

# determine font to use based on settings file; set up custom font and create the root console
if config['ArmCom2'].getboolean('large_display_font'):
	fontname = 'c64_16x16_ext.png'
else:
	fontname = 'c64_8x8_ext.png'
libtcod.console_set_custom_font(DATAPATH+fontname, libtcod.FONT_LAYOUT_ASCII_INROW, 16, 18)

WINDOW_NAME = NAME + ' - ' + VERSION
if DEBUG: WINDOW_NAME += ' DEBUG'

# set up root console
try:
	if config.getboolean('ArmCom2', 'fullscreen'):
		libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, WINDOW_NAME,
			fullscreen=True, renderer=RENDERER, order='F', vsync=True)
		window_x, window_y = 15, 4
	else:
		libtcod.console_init_root(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_NAME,
			fullscreen=False, renderer=RENDERER, order='F', vsync=True)
		window_x, window_y = 0, 0
	#print('Renderer used is: ' + RENDERERS[libtcod.sys_get_renderer()])
except:
	WriteBootLog('ERROR: Could not create root console.')
	sys.exit()

# disable fullscreen if renderer is not SDL2 or OPENGL2
if config.getboolean('ArmCom2', 'fullscreen') and libtcod.sys_get_renderer() not in [3, 4]:
	print('Fullscreen not supported with this renderer, disabling...')
	config['ArmCom2']['fullscreen'] = 'false'
	libtcod.console_init_root(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_NAME,
		fullscreen=False, renderer=RENDERER, order='F', vsync=True)
	window_x, window_y = 0, 0

libtcod.sys_set_fps(LIMIT_FPS)
libtcod.console_set_default_background(0, libtcod.black)
libtcod.console_set_default_foreground(0, libtcod.white)
libtcod.console_clear(0)
libtcod.console_flush()

WriteBootLog('Root console created')

# create double buffer console
con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
libtcod.console_set_default_background(con, libtcod.black)
libtcod.console_set_default_foreground(con, libtcod.white)
libtcod.console_clear(con)

# display loading screen
libtcod.console_print_ex(con, WINDOW_XM, WINDOW_YM, libtcod.BKGND_NONE, libtcod.CENTER,
	'Loading...')
libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
libtcod.console_flush()

# create new session object
session = Session()

# try to init sound mixer and load sounds if successful
main_theme = None
if config['ArmCom2'].getboolean('sounds_enabled'):
	if session.InitMixer():
		session.LoadMainTheme()
	else:
		config['ArmCom2']['sounds_enabled'] = 'false'
		print('Not able to init mixer, sounds disabled')

# generate keyboard mapping dictionaries
GenerateKeyboards()

# create darken screen console
darken_con = libtcod.console_new(WINDOW_WIDTH, WINDOW_HEIGHT)
libtcod.console_set_default_background(darken_con, libtcod.black)
libtcod.console_set_default_foreground(darken_con, libtcod.black)
libtcod.console_clear(darken_con)

# create game menu console: 84x54
game_menu_con = libtcod.console_new(84, 54)
libtcod.console_set_default_background(game_menu_con, libtcod.black)
libtcod.console_set_default_foreground(game_menu_con, libtcod.white)
libtcod.console_clear(game_menu_con)

# create mouse and key event holders
mouse = libtcod.Mouse()
key = libtcod.Key()

# try to start up steamworks; if it fails, it may just mean that Steam is offline
global steam_active
steam_active = False
try:
	steamworks = STEAMWORKS()
	steamworks.initialize()
	WriteBootLog('Steamworks library loaded')
	steam_active = True
except:
	WriteBootLog('Unable to load Steamworks library')
	print('ERROR: Unable to initialize Steamworks, stats and achievements will not be recorded!')



##########################################################################################
#                                        Main Menu                                       #
##########################################################################################

# display studio logo and disclaimer
libtcod.console_clear(con)
libtcod.console_blit(LoadXP('cats.xp'), 0, 0, 0, 0, con, WINDOW_XM-15, WINDOW_YM-25)
libtcod.console_set_default_foreground(con, libtcod.white)
libtcod.console_print_ex(con, WINDOW_XM, WINDOW_YM+20, libtcod.BKGND_NONE,
	libtcod.CENTER, 'Copyright 2016-2020')
	
libtcod.console_set_default_foreground(con, libtcod.light_grey)
y = WINDOW_YM+22
lines = wrap(DISCLAIMER, 40)
for line in lines:
	libtcod.console_print_ex(con, WINDOW_XM, y, libtcod.BKGND_NONE, libtcod.CENTER, line)
	y += 1
libtcod.console_set_default_foreground(con, libtcod.white)
if not DEBUG: libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)

start_time = time.time()

# try to sync stats with Steam
if steam_active:
	steamworks.RequestCurrentStats()
	steamworks.run_callbacks()

while time.time() - start_time < 2:
	libtcod.console_flush()
	FlushKeyboardEvents()
	if DEBUG: break


# start playing main theme if loaded
if main_theme is not None:
	mixer.Mix_PlayMusic(main_theme, -1)

# load and generate main title background
main_title = LoadXP('main_title.xp')
if session.tank_portrait is not None:
	libtcod.console_blit(session.tank_portrait, 0, 0, 0, 0, main_title, 7, 6)

# display version number and program info
libtcod.console_set_default_foreground(main_title, libtcod.light_grey)
libtcod.console_print_ex(main_title, WINDOW_XM, WINDOW_HEIGHT-4, libtcod.BKGND_NONE,
	libtcod.CENTER, 'Early Access - ' + VERSION)
libtcod.console_print_ex(main_title, WINDOW_XM, WINDOW_HEIGHT-2, libtcod.BKGND_NONE,
	libtcod.CENTER, 'Copyright 2016-2020 Gregory Adam Scott')

today = datetime.today()
if today.month == 11 and 1 <= today.day <= 11:
	libtcod.console_set_default_foreground(main_title, libtcod.white)
	libtcod.console_print(main_title, 1, 52, 'Never')
	libtcod.console_print(main_title, 1, 53, 'Again')
else:
	libtcod.console_set_default_foreground(main_title, libtcod.red)
	libtcod.console_print(main_title, 1, 52, 'Never')
	libtcod.console_print(main_title, 1, 53, 'Forget')
libtcod.console_print(main_title, 3, 54, chr(250) + '-' + chr(250))
libtcod.console_print(main_title, 2, 55, chr(250) + '\\ /' + chr(250))
libtcod.console_print(main_title, 1, 56, ': ( ) :')
libtcod.console_put_char(main_title, 4, 56, chr(9))
libtcod.console_print(main_title, 2, 57, chr(250) + '/ \\' + chr(250))
libtcod.console_print(main_title, 3, 58, chr(250) + '-' + chr(250))

# gradient animated effect for main menu
GRADIENT = [
	libtcod.Color(51, 51, 51), libtcod.Color(64, 64, 64), libtcod.Color(128, 128, 128),
	libtcod.Color(192, 192, 192), libtcod.Color(255, 255, 255), libtcod.Color(192, 192, 192),
	libtcod.Color(128, 128, 128), libtcod.Color(64, 64, 64), libtcod.Color(51, 51, 51),
	libtcod.Color(51, 51, 51)
]

# set up gradient animation timing
time_click = time.time()
gradient_x = WINDOW_WIDTH + 5

# draw the main title to the screen and display menu options
# if options_menu_active, draw the options menu instead
def UpdateMainTitleCon(options_menu_active):
	
	# check to see if there is 1+ saved campaign, and whether that one is compatible
	one_compatible_game = False
	no_saved_games = True
	try:
		for directory in os.listdir(SAVEPATH):
			if not os.path.isdir(SAVEPATH + directory): continue
			with shelve.open(SAVEPATH + directory + os.sep + 'savegame') as save:
				if 'version' not in save: continue
				no_saved_games = False
				if CheckSavedGameVersion(save['version']) != '': continue
				one_compatible_game = True
				break
	except:
		print('ERROR: Corrupted saved campaign file: ' + directory)
	
	libtcod.console_blit(main_title, 0, 0, 0, 0, con, 0, 0)
	
	y = 38
	if options_menu_active:
		
		# display game options commands
		DisplayGameOptions(con, WINDOW_XM-16, 36)
		
	else:
		 
		for (char, text) in [('C', 'Continue'), ('L', 'Load Campaign'), ('N', 'New Campaign'), ('O', 'Options'), ('R', 'Campaign Records'), ('U', 'Unit Gallery'), ('Q', 'Quit')]:
			
			# grey-out option if not possible
			disabled = False
			
			if char == 'C' and not one_compatible_game:
				disabled = True
			
			elif char == 'L' and no_saved_games:
				disabled = True
			
			elif char == 'R' and len(session.morgue) == 0:
				disabled = True
			
			# add a space in the menu
			if char == 'O': y += 1
			
			if disabled:
				libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			else:
				libtcod.console_set_default_foreground(con, ACTION_KEY_COL)
			libtcod.console_print(con, WINDOW_XM-6, y, char)
			
			if disabled:
				libtcod.console_set_default_foreground(con, libtcod.dark_grey)
			else:
				libtcod.console_set_default_foreground(con, libtcod.lighter_grey)
			libtcod.console_print(con, WINDOW_XM-4, y, text)	
			
			y += 1
	
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)


# update the animation effect
def AnimateMainMenu():
	
	global gradient_x
	
	for x in range(0, 10):
		if x + gradient_x > WINDOW_WIDTH: continue
		for y in range(19, 34):
			char = libtcod.console_get_char(con, x + gradient_x, y)
			fg = libtcod.console_get_char_foreground(con, x + gradient_x, y)
			if char != 0 and fg != GRADIENT[x]:
				libtcod.console_set_char_foreground(con, x + gradient_x,
					y, GRADIENT[x])
	gradient_x -= 2
	if gradient_x <= 0: gradient_x = WINDOW_WIDTH + 10

# activate root menu to start
options_menu_active = False

# draw the main title console to the screen for the first time
UpdateMainTitleCon(options_menu_active)

# Main Menu loop
try:

	exit_game = False
	while not exit_game:
		
		# trigger animation and update screen
		if time.time() - time_click >= 0.06:
			AnimateMainMenu()
			libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
			time_click = time.time()
		
		libtcod.console_flush()
		if not GetInputEvent(): continue
		key_char = chr(key.c).lower()
		
		# options sub-menu
		if options_menu_active:
			if key.vk == libtcod.KEY_ESCAPE:
				options_menu_active = False
			else:
				ChangeGameSettings(key_char, main_menu=True)
			UpdateMainTitleCon(options_menu_active)
		
		# root main menu
		else:
			
			if key_char == 'q':
				exit_game = True
				continue
			
			elif key_char == 'o':
				options_menu_active = True
				UpdateMainTitleCon(options_menu_active)
				continue
			
			# view campaign records / morguefile
			elif key_char == 'r':
				if len(session.morgue) == 0: continue
				ShowRecordsMenu()
				UpdateMainTitleCon(options_menu_active)
				continue
			
			# unit type gallery
			elif key_char == 'u':
				if main_theme is not None:
					mixer.Mix_PauseMusic()
				UnitGallery()
				if main_theme is not None:
					mixer.Mix_ResumeMusic()
				UpdateMainTitleCon(options_menu_active)
				continue
			
			# start a new campaign, or load a saved campaign
			elif key_char in ['n', 'c', 'l']:
	
				if main_theme is not None:
					mixer.Mix_PauseMusic()
				
				# continue most recently saved campaign, or load a saved campaign
				if key_char in ['c', 'l']:
					if not LoadCampaignMenu(key_char == 'c'):
						campaign = None
						UpdateMainTitleCon(options_menu_active)
						if main_theme is not None:
							mixer.Mix_ResumeMusic()
						continue
					
				# start a new campaign
				else:
					
					# create a new campaign object and allow player to select a campaign
					campaign = Campaign()
					if not campaign.CampaignSelectionMenu():
						campaign = None
						UpdateMainTitleCon(options_menu_active)
						if main_theme is not None:
							mixer.Mix_ResumeMusic()
						continue
					
					# show campaign options menu
					if not campaign.CampaignOptionsMenu():
						campaign = None
						UpdateMainTitleCon(options_menu_active)
						if main_theme is not None:
							mixer.Mix_ResumeMusic()
						continue
					
					# allow player to select their tank and set their tank name
					(unit_id, tank_name) = campaign.TankSelectionMenu(starting_campaign=True)
					
					# cancel campaign start
					if unit_id is None:
						campaign = None
						UpdateMainTitleCon(options_menu_active)
						if main_theme is not None:
							mixer.Mix_ResumeMusic()
						continue
					
					# create the player unit
					campaign.player_unit = Unit(unit_id, is_player=True)
					campaign.player_unit.unit_name = tank_name
					campaign.player_unit.nation = campaign.stats['player_nation']
					campaign.player_unit.GenerateNewPersonnel()
					campaign.player_unit.ClearGunAmmo()
					
					# finish setting up the campaign
					campaign.DoPostInitChecks()
					
					# create a new campaign day
					campaign_day = CampaignDay()
					for (hx, hy) in CAMPAIGN_DAY_HEXES:
						campaign_day.map_hexes[(hx,hy)].CalcCaptureVP()
					campaign_day.GenerateRoads()
					campaign_day.GenerateRivers()
					campaign.AddJournal('Start of day')
					
					# placeholder for the currently active scenario
					scenario = None
				
				# go to campaign calendar loop
				campaign.DoCampaignCalendarLoop()
				
				# check for campaign continuation
				if campaign.ended:
					if ContinueCampaign():
						campaign.DoCampaignCalendarLoop()
				
				# reset exiting flag
				session.exiting = False
				
				UpdateMainTitleCon(options_menu_active)
				libtcod.console_flush()
				
				# restart or continue main theme if loaded
				if main_theme is not None:
					if mixer.Mix_PausedMusic() == 1:
						mixer.Mix_RewindMusic()
						mixer.Mix_ResumeMusic()
					else:
						mixer.Mix_PlayMusic(main_theme, -1)
				
				UpdateMainTitleCon(options_menu_active)

except Exception:
	traceback.print_exc()
	
	if DEBUG: sys.exit()
	
	OutputCrashLog(traceback.format_exc())
	
	# blank screen and display crash message
	libtcod.console_clear(con)
	libtcod.console_set_default_foreground(con, libtcod.light_red)
	libtcod.console_print_ex(con, WINDOW_XM, 2, libtcod.BKGND_NONE, libtcod.CENTER,
		'Armoured Commander II Has Crashed')
	libtcod.console_set_default_foreground(con, libtcod.white)
	libtcod.console_print_ex(con, WINDOW_XM, 3, libtcod.BKGND_NONE, libtcod.CENTER,
		'Version ' + VERSION)
	
	libtcod.console_print_ex(con, WINDOW_XM, 6, libtcod.BKGND_NONE, libtcod.CENTER,
		'A crashlog has been saved to: ' + str(Path.home()) + os.sep + 'ArmCom2')
	libtcod.console_print_ex(con, WINDOW_XM, 8, libtcod.BKGND_NONE, libtcod.CENTER,
		'Please report this on the Steam Discussion board')
	libtcod.console_print_ex(con, WINDOW_XM, 10, libtcod.BKGND_NONE, libtcod.CENTER,
		'Crashlog printed below:')
	
	y = 20
	lines = wrap(traceback.format_exc(), 40)
	for line in lines:
		libtcod.console_print(con, 25, y, line)
		y += 1
		if y == WINDOW_HEIGHT-6: break
	
	libtcod.console_print_ex(con, WINDOW_XM, WINDOW_HEIGHT-4, libtcod.BKGND_NONE,
		libtcod.CENTER, 'Press Enter to Quit')
	
	libtcod.console_blit(con, 0, 0, 0, 0, 0, window_x, window_y)
	libtcod.console_flush()
	WaitForContinue(ignore_animations=True)
	
	sys.exit()

WriteBootLog('Shutting down')

if steam_active:
	steamworks.unload()

# END #
