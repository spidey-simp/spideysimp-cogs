
SKILLSLIST = {
    "Piano": [0, 0, ["Music Enthusiast"], ["Electric piano", "Grand piano"]],
    "Guitar": [0, 0, ["Music Enthusiast"], ["Guitar"]],
    "Singing": [0, 0, ["Music Enthusiast"]],
    "Art": [0, 0, ["Art Connoisseur", "Perfectionist", "Eccentric"], ["Easel", "Canvas"]],
    "Photography": [0, 0, ["Art Connoisseur", "Perfectionist", "Eccentric"], ["Photo camera"]],
    "Comedy": [0, 0, ["Witty Comedian", "Sarcastic"]],
    "Charisma": [0, 0, ["Charismatic", "Empathic"]],
    "Writing": [0, 0, ["Literary Aficionado", "Perfectionist"], ["Laptop", "Notebook", "Desktop"]],
    "Handiness": [0, 0, ["Skilled Craftsperson", "Perfectionist"], ["Toolbox", "Workbench"]],
    "Woodworking": [0, 0, ["Skilled Craftsperson", "Perfectionist"], ["Toolbox", "Workbench"]],
    "Programming": [0, 0, ["Tech Savant", "Logical"], ["Laptop", "Desktop"]],
    "Science": [0, 0, ["Science Savant", "Inquisitive", "Logical"], ["Science workstation", "Microscope"]],
    "Medicine": [0, 0, ["Science Savant", "Inquisitive", "Logical"], ["Skeleton study tool", "Medical textbook"]],
    "Fishing": [0, 0, ["Sea-born"], ["Fishing rod"]],
    "Gardening": [0, 0, ["Green Thumb"], ["Gardening tools"]],
    "Cooking": [0, 0, ["Culinary Artisan"], ["Stove"]],
    "Acting": [0, 0, ["Natural-born performer", "Empathic"], ["Movie script"]],
    "Baking": [0, 0, ["Culinary Artisan"], ["Stove"]],
    "Athletic": [0, 0, ["Energetic Dynamo", "Fierce Competitor"]],
    "Social Media": [0, 0, ["Charismatic", "Chronically Online"]],
    "Logic": [0, 0, ["Logical", "Inquisitive"], ["Chess board", "Logic puzzles"]],
    "Debate": [0, 0, ["Persuasive", "Charismatic"], ["Casebook"]],
    "Mischief": [0, 0, ["Mischief Maker", "Witty Comedian"], ["Whoopie cushion"]],
    "Sewing": [0, 0, ["Fashion Forward", "Perfectionist"], ["Sewing machine", "Fabric"]],
    "Force-wielding": [0, 0, ["Force-sensitive"], ["Force Tome"]],
    "Dueling": [0, 0, ["Quick footed", "Fierce Competitor"], ["Lightsaber", "Cutlass", "Broadsword", "Practice Dummy", "Plasma Blade"]],
    "Sailing": [0, 0, ["Sea-born", "Adventurous"], ["Dinghy", "Sailboat", "Frigate"]],
    "Martial Arts": [0, 0, ["Quick footed", "Athletic", "Fierce Competitor"], ["Training Mat"]],
    "Gaming": [0, 0, ["Gamer", "Fierce Competitor"], ["A PS5", "Laptop", "Desktop"]],
    "Swimming": [0, 0, ["Sea-born", "Energetic Dynamo"]],
    "Magic": [0, 0, ["Inquisitive"], ["Magic Tome"]],
    "Horse Riding": [0, 0, ["Equestrian"], ["Horse"]],
    "Marksmanship": [0, 0, ["Eagle-eyed"], ["Bow", "Rifle", "Flintlock Pistol", "Blaster"]]
}

LIGHTSABERSKILLS = {
    "Accepted Weapons": {
        "Lightsaber": {"type": "Basic", "effect": None, "acquire type": "Purchasable", "description": "The chosen weapon of both the Jedi and the Sith.", "price": {"Republic Dataries": 200000, "Galactic Credits": 400000, "Imperial Bonds": 100000, "Imperial Credits": 280000}}, 
        "Darksaber": {"type": "Legendary", "effect": {"Damage": 1.5, "Crit Chance": 1.25}, "acquire type": "Quest", "description": "Make the people of Mand'alor bow to your whims with this ancient and powerful weapon."},
        "Double-Bladed Lightsaber": {"type": "Advanced", "effect": {"Evasion": 1.1, "Damage": 1.15}, "acquire type": "Purchasable", "description": "A weapon for masters of precision and control, favored by Darth Maul.", "price": {"Republic Dataries": 300000, "Galactic Credits": 600000, "Imperial Bonds": 150000, "Imperial Credits": 420000}, 
        "Crossguard Lightsaber": {"type": "Special", "effect": {"Defense": 1.15, "Damage": 1.1}, "acquire type": "Quest", "description": "A unique weapon that burns with ancient energy, designed for both offense and defense."}},
        "Kyber-Shard Saber": {"type": "Unstable", "effect": {"Damage": 1.2, "Crit Chance": .9}, "acquire type": "Discoverable", "description": "An unstable yet powerful lightsaber, forged from raw kyber shards."},
        "Electrostaff": {"type": "Utility", "effect": {"Damage Reduction": 1.2, "Disarming Capability": "Yes"}, "acquire type": "Discoverable", "description": "A non-lethal alternative used to block lightsaber strikes, favored by Imperial guards."}
    },
    "Basic": {
        "Basic Slash": [0, "Deals Base Damage.", {"Effect": {"Damage": 1}, "Cooldown": 0}],
        "Deflect": [0, "Temporarily increases Evasion.", {"Effect": {"Buff": {"Target": "player", "Name": "Fortified"}}, "Cooldown": 2}],
        "Charge Slash": [0, "Deals high damage but applies vulnerable to the user.", {"Effect": {"Damage": 1.4, "Buff": {"Target": "player", "Name": "Vulnerable"}}, "Cooldown": 3}],
    },
    "Aggressive": {
        "Precision Strike": [2, "Increases Crit Chance for one attack.", {"Effect": {"User Buff": "Crit Chance Up", "Damage": 1.25}, "Cooldown": 1}],
        "Relentless Barrage": [4, "Three consecutive strikes.", {"Effect": {"Damage": 1.15, "Speed Stat": 5, "Times": 3}, "Cooldown": 3}],
        "Rage Strike": [7, "A powerful attack with a cost.", {"Effect": {"Damage": 1.5, "User Buff": "Vulnerable"}, "Duration": 2, "Energy Cost": 20, "Cooldown": 4}],
        "Form V: Djem So": [9, "Increases Damage at the cost of Defense.", {"Effect": {"Damage Stat": +15, "Defense Stat": -5}, "Duration": 3, "Cooldown": 5}]
    },
    "Balanced": {
        "Form I: Shii-Cho": [1, "Versatile form with balanced boosts.", {"Effect": {"Evasion": "+5", "Defense": "+5"}, "Duration": 2, "Cooldown": 2}],
        "Form II: Makashi": [3, "Reduces enemy Evasion while boosting Crit Chance.", {"Effect": {"Crit Chance": "+5", "Enemy Evasion": "-5"}, "Duration": 2, "Cooldown": 3}],
        "Form IV: Ataru": [6, "An acrobatic form increasing Speed.", {"Effect": {"Damage": "Base Damage + 15%", "Speed": "+10"}, "Duration": 2, "Energy Cost": 10, "Cooldown": 3}],
        "Form VI: Niman": [8, "Balances stats for defense and offense.", {"Effect": {"HP": "+5", "Defense": "+5", "Crit Chance": "+5"}, "Duration": 3, "Cooldown": 4}]
    },
    "Defensive": {
        "Guard Stance": [2, "Reduces incoming damage.", {"Effect": {"Defense": "+10", "Damage Reduction": "50%"}, "Duration": 1, "Cooldown": 2}],
        "Shield of Light": [4, "Defends against critical strikes.", {"Effect": {"Crit Damage Reduction": "50%", "HP": "+20"}, "Duration": 2, "Cooldown": 3}],
        "Counter Riposte": [7, "Exploit openings left by enemies.", {"Effect": {"Damage": "50% Base Damage", "Crit Chance": "+10", "Enemy Speed": "-5"}, "Duration": 1, "Cooldown": 3}],
        "Form III: Soresu": [9, "Maximizes defense at the cost of offense.", {"Effect": {"Defense": "+20", "Evasion": "+10", "Damage": "-10"}, "Duration": 2, "Cooldown": 4}]
    },
    "Chaotic": {
        "Wild Swing": [1, "Reckless slash with crit potential.", {"Effect": {"Damage": "Base Damage", "Crit Chance": "50%", "Defense": "-5"}, "Duration": 1, "Cooldown": 2}],
        "Erratic Leap": [3, "Unpredictable attack increasing Evasion.", {"Effect": {"Damage": "Base Damage", "Evasion": "+15"}, "Duration": 1, "Energy Cost": 10, "Cooldown": 3}],
        "Mad Dash": [5, "Dash through enemies with random strikes.", {"Effect": {"Damage": "30% Base Damage per strike", "Speed": "+10"}, "Duration": 1, "Cooldown": 3}],
        "Chaotic Mastery": [7, "Embrace chaos with high crit damage.", {"Effect": {"Crit Damage": "+50%", "Unstable": "50% chance to miss or crit"}, "Duration": 2, "Cooldown": 4}],
        "Storm of Blades": [9, "Unleash a whirlwind of strikes.", {"Effect": {"Damage": "5 hits of 25% Base Damage", "HP Cost": "-15"}, "Energy Cost": 30, "Cooldown": 5}]
    },
    "Tactical": {
        "Strategic Sweep": [2, "Weaken enemy defense with a calculated slash.", {"Effect": {"Damage": "Base Damage - 20%", "Enemy Defense": "-10"}, "Duration": 2, "Cooldown": 2}],
        "Force Awareness": [4, "Increases Evasion and reduces Crit Chance.", {"Effect": {"Evasion": "+15", "Enemy Crit Chance": "-10"}, "Duration": 2, "Cooldown": 3}],
        "Battlefield Control": [6, "Reduce enemy Speed.", {"Effect": {"Enemy Speed": "-10"}, "Duration": 3, "Cooldown": 3}],
        "Lightsaber Disarm": [8, "Disarm an enemy to gain the upper hand.", {"Effect": {"Damage": "50% Base Damage", "Enemy Damage": "-20"}, "Duration": 2, "Cooldown": 4}],
        "Lightsaber Ambush": [9, "A devastating surprise attack.", {"Effect": {"Damage": "Base Damage + 50%", "Crit Chance": "+15"}, "Cooldown": 4}]
    },
    "Elegant": {
        "Precision Slash": [1, "Deliver a calculated slash with minimal movement.", {"Effect": {"Damage": "Base Damage + 20%", "Energy Cost Reduction": "-10%"}, "Cooldown": 2}],
        "Deflect with Grace": [3, "Redirect enemy projectiles with exceptional control.", {"Effect": {"Deflect Success Rate": "+15%", "Damage": "Base Damage"}, "Cooldown": 3}],
        "Dazzling Flourish": [5, "Perform a captivating maneuver to disorient enemies.", {"Effect": {"Enemy Accuracy Reduction": "-20%", "Damage": "Base Damage + 10%"}, "Cooldown": 4}],
        "Flawless Sequence": [7, "Chain a series of precise strikes without error.", {"Effect": {"Damage": "4x Base Damage - 10%", "Crit Chance": "+10%"}, "Cooldown": 6}]
    },
    "Hunting/Pursuit": {
            "Focused Strike": [2, "A focused strike that becomes more powerful when the target is cornered.", {"Effect": {"Damage": "+25%"}, "Cooldown": 2}],
            "Pursuer's Slash": [4, "A quick slash that increases in speed as you close the distance.", {"Effect": {"Speed": "+15%", "Damage": "+15%"}, "Cooldown": 1}],
            "Tracking Strike": [7, "A strike that reduces the target's evasion, making it harder to escape.", {"Effect": {"Dodge": "-30%"}, "Cooldown": 3}],
            "Prey in Sight": [9, "Grants significant bonus damage and speed when your target is within range.", {"Effect": {"Damage": "+25%", "Speed": "+20%"}, "Cooldown": 4}]
    }
}

CUTLASSSKILLS = {
    "Accepted Weapons": {
        "Cutlass": {"type": "Basic", "effect": None, "acquire type": "Purchasable", "description": "A trusty blade for any pirate worth their salt.", "price": {"Doubloons": 10, "Sterling Pounds Silver": 50}},
        "Golden Cutlass": {"type": "Rare", "effect": {"Damage": 1.15, "Evasion": 5}, "acquire type": "Discoverable", "description": "A blade fit for a captain, with a hilt that gleams like treasure."},
        "Bloody Buccaneer": {"type": "Legendary", "effect": {"Damage": 1.3, "Crit Damage": 1.2}, "acquire type": "Quest", "description": "This blade is soaked in the blood of its enemies, feared by all."},
        "Hook Blade": {"type": "Utility", "effect": {"Grappling Capability": True, "Damage": 1.1}, "acquire type": "Purchasable", "description": "A versatile weapon that can snag and slash with ease.", "price": {"Doubloons": 12, "Sterling Pounds Silver": 60}},
        "Blackguard's Cutlass": {"type": "Cursed", "effect": {"Crit Chance": 1.1, "Defense": -5}, "acquire type": "Discoverable", "description": "A cursed blade forged in the darkest corners of the Seven Seas."},
        "Leviathan's Fang": {"type": "Mythical", "effect": {"Damage": 1.5, "Always AOE": True}, "acquire type": "Quest", "description": "Forged in the abyss, this blade hums with the fury of the sea."}
    },
    "Basic": {
        "Basic Cut": [0, "A straightforward strike with the cutlass.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 0}],
        "Flourish": [0, "A flashy move that boosts Crit Chance.", {"Effect": {"Crit Chance": "+10"}, "Duration": 1, "Cooldown": 2}],
        "Quick Parry": [0, "Increase Evasion for one turn.", {"Effect": {"Evasion": "+10"}, "Duration": 1, "Cooldown": 3}]
    },
    "Aggressive": {
        "Reckless Swing": [2, "Powerful slash with reduced accuracy.", {"Effect": {"Damage": "Base Damage + 25%", "Evasion": "-5"}, "Cooldown": 2}],
        "Frenzied Flurry": [4, "Three rapid strikes with reduced damage.", {"Effect": {"Damage": "50% Base Damage per strike", "Speed": "+5"}, "Duration": 1, "Cooldown": 3}],
        "Bloodthirsty Slash": [7, "A devastating attack that costs HP.", {"Effect": {"Damage": "Base Damage + 50%", "HP Cost": "-15"}, "Cooldown": 4}],
        "Cutthroat's Frenzy": [9, "Enter a berserk state, increasing damage but lowering defense.", {"Effect": {"Damage": "+20", "Defense": "-10"}, "Duration": 2, "Cooldown": 5}]
    },
    "Balanced": {
        "Cutlass Strike": [1, "A clean, efficient attack.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
        "Fortress Guard": [4, "Hold your ground with an impenetrable defense.", {"Effect": {"Damage Reduction": "-25%"}, "Duration": 3, "Cooldown": 4}],
        "Ironclad Captain": [6, "A defensive stance that empowers counters and blocks.", {"Effect": {"Damage Absorption": "10%", "Counter Damage": "Base Damage"}, "Duration": 3, "Cooldown": 5}],
        "Sea Rover's Gambit": [8, "Boosts Speed and Crit Chance for tactical advantage.", {"Effect": {"Speed": "+10", "Crit Chance": "+15"}, "Duration": 2, "Cooldown": 4}]
    },
    "Defensive": {
        "Parry Stance": [2, "Increases Defense temporarily.", {"Effect": {"Defense": "+10"}, "Duration": 1, "Cooldown": 2}],
        "Riposte": [4, "Counter an enemy attack with precision.", {"Effect": {"Damage": "Base Damage + 25%", "Crit Chance": "+10"}, "Cooldown": 3}],
        "Fortress Guard": [7, "Greatly reduces damage taken for a short time.", {"Effect": {"Damage Reduction": "50%", "Defense": "+15"}, "Duration": 2, "Cooldown": 4}],
        "Ironclad Captain": [9, "Increases defense while empowering counters.", {"Effect": {"Defense": "+20", "Counter Damage": "+50%"}, "Duration": 3, "Cooldown": 5}]
    },
    "Chaotic": {
        "Pocket Sand": [1, "Blinds opponents, reducing their accuracy.", {"Effect": {"Enemy Accuracy": "-15"}, "Duration": 1, "Cooldown": 2}],
        "Boom Powder": [3, "Small explosive dealing AoE damage.", {"Effect": {"Damage": "Base Damage", "Area Damage": "50%"}, "Cooldown": 3}],
        "Cannonball Toss": [5, "A heavy ranged attack causing knockback.", {"Effect": {"Damage": "Base Damage + 30%", "Enemy Speed": "-10"}, "Cooldown": 4}],
        "Powder Keg Chaos": [7, "Explosive chain reaction causing massive damage.", {"Effect": {"Damage": "3x Base Damage (chain)", "HP Cost": "-20"}, "Cooldown": 5}],
        "Shipwrecked Fury": [9, "Unleash devastating attacks in chaotic succession.", {"Effect": {"Damage": "5 hits of 25% Base Damage", "Crit Chance": "+20"}, "Cooldown": 5}]
    },
    "Tactical": {
        "Paralyzing Slash": [2, "Disables enemy movement.", {"Effect": {"Enemy Speed": "-15"}, "Duration": 1, "Cooldown": 3}],
        "Feint and Strike": [4, "Bait the enemy into an opening before striking.", {"Effect": {"Damage": "Base Damage + 20%", "Enemy Evasion": "-10"}, "Cooldown": 3}],
        "Smoke Bomb": [6, "Hinders visibility, reducing enemy Crit Chance.", {"Effect": {"Enemy Crit Chance": "-15"}, "Duration": 2, "Cooldown": 4}],
        "Plunderer’s Trap": [9, "High damage to attacking enemies.", {"Effect": {"Damage": "Base Damage + 50%", "Enemy Damage Reduction": "-10"}, "Cooldown": 5}],
        "Sea Dog's Cunning": [9, "Temporary bonuses when outpowered.", {"Effect": {"Speed": "+15", "Evasion": "+10", "Defense": "+10"}, "Duration": 3, "Cooldown": 5}]
    },
    "Ultimate": {
        "Cutthroat's Frenzy": [8, "Unleash a berserk state, enhancing damage for a short period.", {"Effect": {"Damage Boost": "+30%", "Defense Reduction": "-10%"}, "Duration": 4, "Cooldown": 6}]
    },
    "Hunting/Pursuit": {
        "Chasing Blow": [2, "A brutal blow that increases in power when the enemy tries to run.", {"Effect": {"Damage": "+30%"}, "Cooldown": 1}],
        "Scoundrel's Slash": [4, "A quick strike to cut down any prey that dares to flee.", {"Effect": {"Speed": "+15%", "Damage": "+15%"}, "Cooldown": 1}],
        "Pirate's Pursuit": [7, "Strikes that lower the enemy's evasion while increasing yours.", {"Effect": {"Dodge": "-25%"}, "Cooldown": 3}],
        "Hunting Stance": [9, "Increases damage and evasion against a target actively being pursued.", {"Effect": {"Damage": "+30%", "Dodge": "+15%"}, "Cooldown": 4}]
    }
}


BROADSWORDSKILLS = {
    "Accepted Weapons": {
            "Broadsword": {"type": "Basic", "effect": None, "acquire type": "Purchasable", "description": "A sword befitting any knight of the realm, stalwart and true.", "price": {"Mithril Coins": 4, "Gold Coins": 10}},
            "Flamebrand": {"type": "Special", "effect": {"Damage": 1.4, "Burn Debuff": True}, "acquire type": "Discoverable", "description": "A blade wreathed in eternal fire, dangerous to wield."},
            "Knight's Honor": {"type": "Rare", "effect": {"Defense": 1.15}, "acquire type": "Quest", "description": "An heirloom sword carrying the weight of countless victories."}
        },
    "Basic": {
        "Parry": [0, "Deflect an incoming attack with precision.", {"Effect": {"Evasion": "+10"}, "Cooldown": 1}],
        "Slash": [0, "A simple yet effective horizontal strike.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
        "Thrust": [0, "A quick forward jab to exploit openings.", {"Effect": {"Damage": "Base Damage + 10%"}, "Cooldown": 1}],
        "Guard Stance": [0, "Adopt a defensive posture to reduce damage.", {"Effect": {"Damage Reduction": "20%"}, "Duration": 2, "Cooldown": 3}]
    },
    "Aggressive": {
        "Overhead Slash": [2, "A devastating two-handed swing.", {"Effect": {"Damage": "Base Damage + 25%"}, "Cooldown": 2}],
        "Crushing Blow": [4, "Channel strength into a brutal strike.", {"Effect": {"Damage": "Base Damage + 40%", "Enemy Defense Reduction": "-10"}, "Cooldown": 3}],
        "Frenzied Charge": [7, "Rush toward enemies, breaking their formation.", {"Effect": {"Damage": "Base Damage + 20%", "Enemy Evasion": "-15"}, "Cooldown": 4}],
        "Ruinous Cleave": [9, "A devastating swing that cuts through multiple enemies.", {"Effect": {"Damage": "2x Base Damage (AoE)"}, "Cooldown": 5}]
    },
    "Balanced": {
        "Sweeping Strike": [1, "A broad swing targeting multiple foes.", {"Effect": {"Damage": "Base Damage", "Area Damage": "50%"}, "Cooldown": 1}],
        "Counterstrike": [3, "Parry and immediately retaliate.", {"Effect": {"Damage": "Base Damage + 20%", "Evasion": "+10"}, "Cooldown": 2}],
        "Adaptive Combat": [6, "Gain bonuses based on your opponent's actions.", {"Effect": {"Dynamic Buff": "+10 to key stats based on the foe"}, "Duration": 2, "Cooldown": 3}],
        "Battlefield Prowess": [8, "Master battlefield tactics to dominate any situation.", {"Effect": {"Speed": "+10", "Crit Chance": "+15"}, "Duration": 3, "Cooldown": 4}]
    },
    "Defensive": {
        "Shield Bash": [2, "Strike with your shield to knock enemies back.", {"Effect": {"Damage": "Base Damage + 10%", "Enemy Speed Reduction": "-10"}, "Cooldown": 2}],
        "Shield Wall": [4, "Raise your shield to form an impenetrable defense.", {"Effect": {"Defense": "+15", "Evasion": "+10"}, "Duration": 2, "Cooldown": 3}],
        "Fortress Stance": [7, "Adopt a stance of absolute defense.", {"Effect": {"Defense": "+25", "Damage Reduction": "50%"}, "Duration": 2, "Cooldown": 4}],
        "Vanguard's Command": [9, "Inspire allies to hold their ground.", {"Effect": {"Ally Defense": "+15", "Ally Evasion": "+10"}, "Duration": 3, "Cooldown": 5}]
    },
    "Chaotic": {
        "Wild Swing": [1, "Unleash a wide, reckless strike.", {"Effect": {"Damage": "Base Damage + 15%", "Evasion": "-5"}, "Cooldown": 1}],
        "Spiked Shield Slam": [3, "Add spikes to your shield for extra brutality.", {"Effect": {"Damage": "Base Damage + 20%", "Enemy Speed Reduction": "-5"}, "Cooldown": 2}],
        "Explosive Mace": [5, "Attach explosives to your mace for chaotic destruction.", {"Effect": {"Damage": "Base Damage + 30%", "Area Damage": "50%"}, "Cooldown": 4}],
        "Unhinged Onslaught": [7, "Succumb to madness, attacking wildly.", {"Effect": {"Damage": "4 hits of Base Damage", "Crit Chance": "+10", "Evasion": "-10"}, "Cooldown": 5}]
    },
    "Tactical": {
        "Exposed Flank": [2, "Exploit gaps in the opponent's guard for extra damage.", {"Effect": {"Damage": "Base Damage + 15%", "Enemy Defense Reduction": "-5"}, "Cooldown": 2}],
        "Shield Feint": [4, "Create an opening by faking a defensive stance.", {"Effect": {"Enemy Evasion": "-15", "Crit Chance": "+10"}, "Duration": 1, "Cooldown": 3}],
        "Bastion Control": [6, "Turn defense into offense, forcing the enemy back.", {"Effect": {"Damage": "Base Damage + 25%", "Enemy Speed Reduction": "-10"}, "Cooldown": 4}],
        "Knight’s Gambit": [9, "Sacrifice defense to land a decisive blow.", {"Effect": {"Damage": "Base Damage + 50%", "Defense Reduction": "-15"}, "Cooldown": 5}],
        "Siege Strategist": [9, "Master tactics to exploit the environment and outwit opponents.", {"Effect": {"Speed": "+10", "Crit Chance": "+10", "Enemy Defense Reduction": "-10"}, "Duration": 3, "Cooldown": 5}]
    },
    "Ultimate": {
        "Ruinous Cleave": [8, "Deliver a devastating swing that cuts through multiple enemies.", {"Effect": {"AoE Damage": "Base Damage + 40%"}, "Cooldown": 6}]
    }
}




FORCEPOWERS = {
    "Good": {
        "Force Heal": [2, "Restore health to yourself and nearby allies.", {"Effect": {"Healing": "20% of max health over 5 seconds"}, "Cooldown": 3}],
        "Inspire Resolve": [4, "Strengthen the resolve of companions in battle, boosting their stats.", {"Effect": {"Ally Attack Boost": "+15%", "Ally Defense Boost": "+15%"}, "Duration": 10, "Cooldown": 4}],
        "Barrier of Light": [7, "Create a defensive field that blocks incoming attacks.", {"Effect": {"Damage Absorption": "50%"}, "Duration": 8, "Cooldown": 5}],
        "Radiant Wave": [9, "Unleash a powerful burst of light energy that purges darkness and heals allies.", {"Effect": {"AoE Damage": "Massive", "Healing": "15% of max health"}, "Cooldown": 6}],
        "Light's Redemption": [9, "Fully heal allies and remove all debuffs, at the cost of personal health.", {"Effect": {"Healing": "Transfers 30% of user health to allies"}, "Cooldown": 8}]
    },
    "Neutral": {
        "Force Push": [1, "Knock back enemies with a telekinetic shove.", {"Effect": {"Stun": "2 seconds", "Knockback": "Moderate"}, "Cooldown": 2}],
        "Mind Trick": [3, "Confuse enemies, reducing their effectiveness in combat.", {"Effect": {"Enemy Accuracy Reduction": "-20%", "Enemy Damage Reduction": "-20%"}, "Duration": 5, "Cooldown": 3}],
        "Force Leap": [6, "Enhanced agility to close distances or escape danger quickly.", {"Effect": {"Stun": "1 second upon landing"}, "Cooldown": 3}],
        "Force Balance": [8, "Draw on both sides of the Force to unleash a balanced attack and defense ability.", {"Effect": {"Attack Boost": "+10%", "Defense Boost": "+10%"}, "Duration": 8, "Cooldown": 5}],
        "Force Harmony": [9, "Achieve perfect synchronization with the Force, amplifying all abilities temporarily.", {"Effect": {"Amplify All Abilities": "Double Effectiveness"}, "Duration": 10, "Cooldown": 8}]
    },
    "Evil": {
        "Force Choke": [2, "Constrict an enemy’s airway, immobilizing them.", {"Effect": {"Immobilize": "3 seconds", "Damage Over Time": "5% per second"}, "Cooldown": 3}],
        "Force Lightning": [4, "Channel dark energy to damage multiple foes at range.", {"Effect": {"AoE Damage": "Moderate", "Enemy Speed Reduction": "-25%"}, "Duration": 5, "Cooldown": 4}],
        "Corrupt Aura": [7, "Emanate a dark presence that weakens nearby enemies.", {"Effect": {"Enemy Attack Reduction": "-15%", "Enemy Defense Reduction": "-15%"}, "Duration": 8, "Cooldown": 5}],
        "Dark Tempest": [9, "Summon a storm of dark energy to devastate enemies in a wide area.", {"Effect": {"AoE Damage": "Massive", "Burn Effect": "3 seconds"}, "Cooldown": 6}],
        "Soul Drain": [9, "Absorb the life force of enemies, dealing damage and healing yourself.", {"Effect": {"Drain Health": "20% from enemies", "Self-Healing": "20%"}, "Cooldown": 7}]
    }
}

FORCESTANCES = {
    "Basic": {
        "Force Sense": [0, "Enhance awareness to sense allies, enemies, and objects nearby.", {"Effect": {"Dodge Chance": "+10%", "Reveal Hidden": "Yes"}, "Duration": 10, "Cooldown": 2}],
        "Telekinetic Grip": [0, "Lift and hold objects or enemies in place for a short duration.", {"Effect": {"Immobilize Target": "2 seconds"}, "Cooldown": 3}],
        "Meditation": [0, "Regenerate Force energy faster when out of combat.", {"Effect": {"Energy Regeneration": "+50%"}, "Duration": 10, "Cooldown": 4}],
        "Basic Force Manipulation": [0, "Control minor objects and redirect projectiles.", {"Effect": {"Reflect Ranged Damage": "10%"}, "Duration": 5, "Cooldown": 3}]
    },
    "Aggressive": {
        "Overcharged Strikes": [2, "Force powers deal 20% more damage but cost more energy.", {"Effect": {"Damage Boost": "+20%", "Energy Cost": "Doubled"}, "Duration": 6, "Cooldown": 3}],
        "Unrelenting Assault": [4, "Gain a stacking damage boost for every consecutive attack.", {"Effect": {"Damage Increase per Stack": "+5%", "Max Stacks": 5}, "Duration": 5, "Cooldown": 4}],
        "Dark Channeling": [6, "Adds a damage-over-time effect to offensive Force powers.", {"Effect": {"Burn Damage": "5% over 3 seconds"}, "Cooldown": 3}],
        "Fury of the Force": [8, "Drastically amplify the damage of your next Force power after taking damage.", {"Effect": {"Next Attack Damage Boost": "+50%"}, "Cooldown": 5}]
    },
    "Defensive": {
        "Fortified Presence": [2, "Take 15% less damage while channeling Force powers.", {"Effect": {"Damage Reduction": "15%"}, "Duration": 6, "Cooldown": 3}],
        "Force Reflection": [4, "Reflect a portion of damage back to attackers while using defensive powers.", {"Effect": {"Reflect Damage": "10%"}, "Duration": 6, "Cooldown": 4}],
        "Energy Shield": [6, "Gain temporary shielding after using a Force power.", {"Effect": {"Damage Absorption": "20%"}, "Duration": 5, "Cooldown": 3}],
        "Guardian’s Resolve": [8, "Reduce cooldowns of all defensive powers when an ally takes damage.", {"Effect": {"Cooldown Reduction": "-2 seconds per ally hit"}, "Duration": 10, "Cooldown": 5}]
    },
    "Balanced": {
        "Focused Mind": [2, "Reduce energy cost of all Force powers slightly.", {"Effect": {"Energy Cost Reduction": "-10%"}, "Duration": 8, "Cooldown": 3}],
        "Synergy Flow": [4, "Gain a slight bonus to both attack and defense after using any Force power.", {"Effect": {"Attack Boost": "+5%", "Defense Boost": "+5%"}, "Duration": 5, "Cooldown": 4}],
        "Master of the Current": [6, "Using offensive powers improves defense and vice versa.", {"Effect": {"Attack and Defense Boost": "+10%"}, "Duration": 6, "Cooldown": 4}],
        "Harmonic Wave": [8, "Amplify both attack and defense abilities briefly after using a Force power.", {"Effect": {"Attack and Defense Boost": "+20%"}, "Duration": 5, "Cooldown": 5}]
    },
    "Utility": {
        "Tactical Advantage": [2, "Force powers apply a debuff that reduces enemy effectiveness.", {"Effect": {"Enemy Speed and Accuracy Reduction": "-10%"}, "Duration": 6, "Cooldown": 3}],
        "Momentum Boost": [4, "Gain a speed bonus for a few seconds after using a Force power.", {"Effect": {"Speed Boost": "+20%"}, "Duration": 4, "Cooldown": 3}],
        "Field Disruption": [6, "Interrupt and weaken multiple enemies with Force-based AoE attacks.", {"Effect": {"Interrupt": "Yes", "Energy Reduction for Enemies": "-20%"}, "Duration": 6, "Cooldown": 5}],
        "Battlefield Manipulation": [8, "Modify the terrain or surroundings to control combat flow.", {"Effect": {"Enemy Movement Debuff": "Yes"}, "Duration": 10, "Cooldown": 8}]
    }
}



MAGICSKILLS = {
    "Good": {
        "Blessing of Light": [2, "Heal allies and banish undead creatures.", {"Effect": {"Healing": "20% of max health", "Extra Damage to Undead": "+30%"}, "Cooldown": 3}],
        "Golden Chains": [4, "Restrain enemies with glowing magical chains.", {"Effect": {"Immobilize": "5 seconds", "Damage Reduction": "-10% for enemies"}, "Cooldown": 4}],
        "Aura of Purity": [7, "Cleanse negative effects from allies and shield them from harm.", {"Effect": {"Debuff Removal": "Yes", "Shield": "15% of max health"}, "Duration": 8, "Cooldown": 5}],
        "Divine Radiance": [9, "Call upon celestial energy to devastate evil forces and heal allies.", {"Effect": {"AoE Damage": "High", "Healing": "10% of max health"}, "Cooldown": 6}]
    },
    "Neutral": {
        "Elemental Surge": [1, "Summon fire, water, or wind for versatile attacks.", {"Effect": {"Elemental Damage": "Base Damage + 10%"}, "Cooldown": 2}],
        "Mana Shield": [3, "Absorb damage using magical energy.", {"Effect": {"Damage Absorption": "30% of max mana"}, "Duration": 6, "Cooldown": 3}],
        "Arcane Step": [6, "Teleport short distances to reposition.", {"Effect": {"Teleport": "Up to 15 meters", "Enemy Confusion": "2 seconds"}, "Cooldown": 3}],
        "Elemental Storm": [8, "Unleash a devastating combination of elemental powers.", {"Effect": {"AoE Damage": "Massive", "Burn Effect": "5 seconds"}, "Cooldown": 6}]
    },
    "Evil": {
        "Dark Pact": [2, "Sacrifice health to amplify magic power.", {"Effect": {"Magic Damage Boost": "+20%", "Health Sacrifice": "-10%"}, "Duration": 6, "Cooldown": 3}],
        "Necrotic Wave": [4, "Unleash decaying energy to harm and wither enemies.", {"Effect": {"AoE Damage": "Moderate", "Enemy Healing Reduction": "-50%"}, "Duration": 8, "Cooldown": 4}],
        "Demonic Summon": [7, "Call forth a demon to fight by your side.", {"Effect": {"Summoned Ally Damage": "Moderate", "Duration": "10 seconds"}, "Cooldown": 6}],
        "Plague of Shadows": [9, "Spread a dark curse that debilitates and corrupts all nearby foes.", {"Effect": {"Enemy Damage Reduction": "-15%", "Poison Effect": "5% over 5 seconds"}, "Duration": 10, "Cooldown": 7}]
    },
}

HARRYPOTTERSPELLS = {
    "Good": {
        "Lumos Maxima": [1, "Illuminate dark areas and dispel minor curses.", {"Effect": {"Revealed Hidden Objects": "Yes", "Dispel Darkness Effects": "Yes"}, "Cooldown": 1}],
        "Episkey": [2, "Heal minor injuries or restore health over time.", {"Effect": {"Healing": "15% of max health over 5 seconds"}, "Cooldown": 2}],
        "Finite Incantatem": [4, "End harmful spells or curses affecting allies.", {"Effect": {"Cancel Ongoing Effects": "Yes"}, "Cooldown": 3}],
        "Rennervate": [6, "Revive a stunned or unconscious ally, restoring a portion of health.", {"Effect": {"Health Restoration": "20% of max health", "Stun Removal": "Yes"}, "Cooldown": 5}],
        "Expecto Patronum": [8, "Summon a protective spirit to fend off dark forces and boost ally morale.", {"Effect": {"Boost Ally Defense": "+15%", "Negate Fear Effects": "Yes"}, "Duration": 8, "Cooldown": 6}]
    },
    "Neutral": {
        "Wingardium Leviosa": [1, "Levitate objects or enemies for strategic positioning.", {"Effect": {"Levitate Duration": "3 seconds", "Enemy Attack Delay": "2 seconds"}, "Cooldown": 1}],
        "Protego": [2, "Summon a magical barrier to block attacks.", {"Effect": {"Damage Absorption": "25%", "Duration": "5 seconds"}, "Cooldown": 3}],
        "Stupefy": [4, "Stun your enemy with a powerful red blast.", {"Effect": {"Stun Duration": "3 seconds", "Damage": "Base Damage + 10%"}, "Cooldown": 4}],
        "Accio": [5, "Summon an object or weapon to your side.", {"Effect": {"Retrieve Weapon or Object": "Yes", "Enemy Weapon Disarm": "Yes"}, "Cooldown": 2}],
        "Elemental Jinx": [7, "Harness basic elemental magic to deal moderate damage.", {"Effect": {"Damage": "15% of base health", "Burn/Freeze Effect": "5 seconds"}, "Cooldown": 3}]
    },
    "Evil": {
        "Sectumsempra": [3, "Slash your enemy with unseen blades.", {"Effect": {"Bleed Effect": "5% health over 5 seconds", "Immediate Damage": "20% of base health"}, "Cooldown": 4}],
        "Fiendfyre": [5, "Summon a massive cursed fire to attack enemies.", {"Effect": {"AoE Damage": "20% of enemy max health", "Burn Effect": "5 seconds"}, "Cooldown": 6}],
        "Crucio": [6, "Inflict unbearable pain, reducing enemy abilities.", {"Effect": {"Enemy Damage Reduction": "-20%", "Pain Stun Duration": "4 seconds"}, "Cooldown": 6}],
        "Imperio": [7, "Control an enemy’s actions temporarily.", {"Effect": {"Mind Control Duration": "5 seconds", "Enemy Damage Boost": "+10%"}, "Cooldown": 7}],
        "Avada Kedavra": [10, "Unleash the Killing Curse for instant devastation.", {"Effect": {"Instant Kill": "Yes (If no shield applied)", "Cooldown Penalty if Blocked": "+2 turns"}, "Cooldown": 10}]
    }
}



MAGICSTANCES = {
    "Accepted Weapons": {
        "Wand": {"type": "Basic", "effect": {"Accuracy": 1.1}, "acquire type": "Purchasable", "description": "A basic wand, suitable for any beginner spellcaster.", "price": {"Galleons": 7, "Sickles": 196}},
        "Staff": {"type": "Advanced", "effect": {"Energy": 1.2, "Damage": 1.1}, "acquire type": "Discoverable", "description": "A sturdy staff that enhances magical power and energy."},
        "Elder Wand": {"type": "Legendary", "effect": {"Damage": 1.5, "Crit Chance": 1.2}, "acquire type": "Quest", "description": "The most powerful wand in existence, capable of unparalleled feats of magic."},
        "Orb of Enchantment": {"type": "Advanced", "effect": {"Cooldown Reduction": 0.9, "Enemy Accuracy": 0.95}, "acquire type": "Discoverable", "description": "A mystical orb that grants its wielder control over time and enemy actions."},
        "Grimoire of Shadows": {"type": "Legendary", "effect": {"Damage": 1.3, "Potency": 1.15}, "acquire type": "Quest", "description": "An ancient book of spells imbued with dark energy, enhancing the wielder's magical potential."},
        "Staff of the White Wizard": {"type": "Legendary", "effect": {"Blinding Light": True, "Purification": True, "Energy Boost": True}, "acquire type": "Discoverable", "description": "Gandalf's staff, capable of blinding enemies and purifying the afflicted."},
        "Staff of Orthanc": {"type": "Legendary", "effect": {"Forceful Command": True, "Dark Influence": True, "Energy Drain": True, "Misty Mountain Storm": True}, "acquire type": "Quest", "description": "Saruman's staff, exuding dominance and manipulation."}
    },
    "Basic": {
        "Focused Casting": [0, "Improve spell accuracy with concentrated effort.", {"Effect": {"Accuracy Boost": "+10%"}, "Duration": 8, "Cooldown": 2}],
        "Basic Channeling": [0, "Steadily channel mana for consistent spell output.", {"Effect": {"Mana Regeneration": "+5% per turn"}, "Duration": 10, "Cooldown": 3}],
        "Defensive Focus": [0, "Improve resistance to enemy spells while maintaining basic defenses.", {"Effect": {"Magic Resistance": "+15%"}, "Duration": 6, "Cooldown": 3}],
        "Basic Ward": [0, "Create a simple magical barrier for protection.", {"Effect": {"Damage Reduction": "-10%"}, "Duration": 5, "Cooldown": 2}]
    },
    "Aggressive": {
        "Empowered Casting": [2, "Spells deal 15% more damage but consume more mana.", {"Effect": {"Damage Boost": "+15%", "Mana Cost Increase": "+10%"}, "Duration": 8, "Cooldown": 3}],
        "Unstable Focus": [4, "Gain a stacking damage boost for consecutive offensive spells.", {"Effect": {"Damage Increase per Stack": "+5%", "Max Stacks": 5}, "Duration": 10, "Cooldown": 4}],
        "Destructive Resonance": [6, "Spells have a chance to explode for extra area damage.", {"Effect": {"AoE Damage Chance": "25%", "Explosion Damage": "50% of Base Damage"}, "Duration": 8, "Cooldown": 5}],
        "Overload": [8, "Amplify your next spell, significantly increasing its damage at the cost of mana burn.", {"Effect": {"Next Spell Damage Boost": "+50%", "Mana Burn": "10%"}, "Cooldown": 6}]
    },
    "Defensive": {
        "Arcane Barrier": [2, "Reduce damage taken while casting defensive spells.", {"Effect": {"Damage Reduction": "-15%"}, "Duration": 6, "Cooldown": 3}],
        "Reflective Ward": [4, "Defensive spells reflect a portion of damage back to attackers.", {"Effect": {"Damage Reflection": "10%"}, "Duration": 6, "Cooldown": 4}],
        "Aegis of Light": [6, "Shield spells grant temporary invulnerability to allies.", {"Effect": {"Invulnerability": "3 seconds"}, "Cooldown": 5}],
        "Guardian’s Embrace": [8, "All defensive spells restore a small amount of health.", {"Effect": {"Healing per Spell": "5% of max health"}, "Duration": 8, "Cooldown": 5}]
    },
    "Balanced": {
        "Efficient Weaving": [2, "Reduce the mana cost of all spells slightly.", {"Effect": {"Mana Cost Reduction": "-10%"}, "Duration": 10, "Cooldown": 3}],
        "Flow State": [4, "Casting spells increases the effectiveness of the next spell.", {"Effect": {"Next Spell Effectiveness": "+20%"}, "Cooldown": 3}],
        "Arcane Equilibrium": [6, "Using offensive spells increases defense and vice versa.", {"Effect": {"Attack and Defense Boost": "+10%"}, "Duration": 6, "Cooldown": 4}],
        "Harmony Surge": [8, "Boost both offensive and defensive capabilities temporarily after casting a spell.", {"Effect": {"Attack and Defense Boost": "+20%"}, "Duration": 8, "Cooldown": 5}]
    },
    "Utility": {
        "Crowd Control": [2, "Spells apply a debuff that slows or hinders enemies.", {"Effect": {"Enemy Speed Reduction": "-20%"}, "Duration": 6, "Cooldown": 3}],
        "Swift Recovery": [4, "Casting defensive spells restores a small amount of mana.", {"Effect": {"Mana Restoration": "5% per Spell"}, "Cooldown": 3}],
        "Tactical Casting": [6, "Offensive spells create lingering effects that hinder enemies.", {"Effect": {"Lingering Debuff Duration": "4 seconds"}, "Cooldown": 4}],
        "Battlefield Mastery": [8, "Manipulate the battlefield, forcing enemies into disadvantageous positions.", {"Effect": {"Enemy Movement Restriction": "Yes"}, "Duration": 10, "Cooldown": 6}]
    },
    "Evil": {
        "Necrotic Touch": [2, "Strike with dark magic, applying a debilitating poison that drains life.", {"Effect": {"Damage": "+30%", "Poison": "3 turns"}, "Cooldown": 2}],
        "Fear Spell": [4, "An aura of terror that reduces the target's defense and accuracy.", {"Effect": {"Defense": "-25%", "Accuracy": "-30%"}, "Cooldown": 3}],
        "Cursed Infliction": [7, "The user curses the target, reducing their attack power.", {"Effect": {"Attack": "-20%"}, "Cooldown": 4}],
        "Dark Empowerment": [9, "Increase magic damage and speed after a successful curse.", {"Effect": {"Damage": "+30%", "Speed": "+20%"}, "Cooldown": 5}]
    }
}


ShortswordSkills = {
    "Accepted Weapons": {
        "Steel Shortsword": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A lightweight and reliable blade for quick strikes.", "price": {"Mithril Coins": 4, "Gold Coins": 12}},
        "Sting": {"type": "Legendary", "effect": {"Damage": 1.25, "Enemy Dispel Stealth": True}, "acquire type": "Quest", "description": "A famed elven blade that glows when orcs are near, wielded by Frodo Baggins."},
        "Gladius": {"type": "Intermediate", "effect": {"Damage": 1.15, "Crit Chance": 1.05}, "acquire type": "Craftable", "description": "A classic Roman sword, ideal for close-quarters combat."},
        "Assassin's Blade": {"type": "Advanced", "effect": {"Damage": 1.2, "Crit Chance": 1.1, "Self Stealth Effect": True}, "acquire type": "Quest", "description": "A sharp and lightweight blade favored by assassins for precision attacks."},
        "Morgul Blade": {"type": "Legendary", "effect": {"Morgul Blade Poisoning": True}, "acquire type": "Quest", "description": "A cursed blade that inflicts a slow, agonizing death on its victims."}
    },
    "Basic": {
        "Quick Jab": [1, "A fast strike aimed at vulnerable spots.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
        "Defensive Swipe": [2, "A sweeping slash that pushes enemies back.", {"Effect": {"Enemy Speed Reduction": "-5", "Damage": "Base Damage - 10%"}, "Cooldown": 2}]
    },
    "Aggressive": {
        "Flurry of Strikes": [3, "Deliver a rapid sequence of slashes.", {"Effect": {"Damage": "3x Base Damage - 10%"}, "Cooldown": 3}],
        "Deadly Precision": [5, "Target critical areas for enhanced damage.", {"Effect": {"Damage": "Base Damage + 25%", "Crit Chance": "+10%"}, "Cooldown": 4}]
    },
    "Defensive": {
        "Parry and Riposte": [4, "Deflect an attack and counter swiftly.", {"Effect": {"Damage": "Base Damage + 15%", "Damage Reduction": "-10%"}, "Cooldown": 3}],
        "Cunning Dodge": [6, "Evade attacks with a quick step.", {"Effect": {"Evasion Boost": "+20%"}, "Duration": 3, "Cooldown": 4}]
    },
    "Tactical": {
        "Sneak Attack": [5, "Strike from an unexpected angle for bonus damage.", {"Effect": {"Damage": "Base Damage + 30%", "Enemy Accuracy Reduction": "-10%"}, "Cooldown": 4}],
        "Blade Feint": [7, "Confuse your opponent, creating an opening.", {"Effect": {"Enemy Defense Reduction": "-15%"}, "Cooldown": 5}]
    },
    "Ultimate": {
        "Dagger Storm": [8, "Unleash a whirlwind of slashes, overwhelming enemies.", {"Effect": {"AoE Damage": "Base Damage + 40%"}, "Cooldown": 6}]
    },
    "Hunting/Pursuit": {
        "Shadow's Edge": [2, "A precise strike from the shadows that hits harder the closer you are.", {"Effect": {"Damage": "+20%", "Crit Chance": "+20%"}, "Cooldown": 1}],
        "Quick Pursuit": [4, "An immediate attack following a retreat, catching enemies off guard.", {"Effect": {"Damage": "+20%", "Speed": "+15%"}, "Cooldown": 2}],
        "Evasion Cut": [7, "A strike designed to bypass the target's defense.", {"Effect": {"Defense Reduction": "-20%"}, "Cooldown": 3}],
        "Hunted": [9, "Increases damage as your target gets closer or attempts to escape.", {"Effect": {"Damage": "+20%"}, "Cooldown": 3}]
    },
}

AxeSkills = {
    "Accepted Weapons": {
            "Battle Axe": {"type": "Basic", "effect": {"Damage": 1.2, "Crit Chance": 1.05}, "acquire type": "Purchasable", "description": "A heavy weapon favored for its sheer power.", "price": {"Mithril Coins": 6, "Gold Coins": 15}},
            "Throwing Axe": {"type": "Advanced", "effect": {"Damage": 1.15}, "acquire type": "Discoverable", "description": "A versatile axe designed for medium-range attacks."},
            "Dwarven Axe": {"type": "Legendary", "effect": {"Damage": 1.5, "Defense": 1.1}, "acquire type": "Quest", "description": "A finely crafted axe imbued with the strength of the dwarves."}
        },
    "Basic": {
        "Axe Swing": [1, "A powerful overhead swing.", {"Effect": {"Damage": "Base Damage + 10%"}, "Cooldown": 1}],
        "Chopping Blow": [2, "Strike with the axe blade, dealing additional armor damage.", {"Effect": {"Damage": "Base Damage", "Armor Penetration": "+10%"}, "Cooldown": 2}]
    },
    "Aggressive": {
        "Double Chop": [3, "Deliver two heavy strikes in quick succession.", {"Effect": {"Damage": "2x Base Damage - 15%"}, "Cooldown": 3}],
        "Raging Cleave": [5, "Unleash a brutal slash that knocks enemies back.", {"Effect": {"Damage": "Base Damage + 30%", "Knockback": "Yes"}, "Cooldown": 4}]
    },
    "Defensive": {
        "Battle Stance": [4, "Brace yourself for incoming attacks, reducing damage taken.", {"Effect": {"Damage Reduction": "-20%"}, "Duration": 3, "Cooldown": 3}],
        "Axe Guard": [6, "Use your axe to block incoming strikes, absorbing damage.", {"Effect": {"Damage Absorption": "10%"}, "Cooldown": 4}]
    },
    "Tactical": {
        "Sunder Armor": [5, "Strike to weaken an enemy’s defenses.", {"Effect": {"Enemy Defense Reduction": "-20%"}, "Cooldown": 4}],
        "Spinning Strike": [7, "Deliver a 360-degree slash, damaging all nearby enemies.", {"Effect": {"AoE Damage": "Base Damage + 20%"}, "Cooldown": 5}]
    },
    "Ultimate": {
        "Berserker Rage": [8, "Enter a frenzied state, drastically increasing damage.", {"Effect": {"Damage Boost": "+50%", "Evasion Reduction": "-10%"}, "Duration": 4, "Cooldown": 6}]
    }
}

ScimitarSkills = {
    "Accepted Weapons": {
        "Iron Scimitar": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A basic, rugged blade designed for brute force.", "price": {"Mithril Coins": 4, "Gold Coins": 14}},
        "Uruk-Hai Scimitar": {"type": "Intermediate", "effect": {"Damage": 1.2, "Enemy Stagger Effect": True}, "acquire type": "Obtainable", "description": "A brutal weapon wielded by the fearsome Uruk-Hai, built to overwhelm defenses."},
        "Blacksteel Scimitar": {"type": "Legendary", "effect": {"Damage": 1.3, "Enemy Bleed Effect": True}, "acquire type": "Quest", "description": "A dark, massive blade with unparalleled destructive power, forged for relentless strikes."}
    },
    "Basic": {
        "Brutal Strike": [1, "A heavy, crushing blow designed to overwhelm.", {"Effect": {"Damage": "Base Damage + 15%"}, "Cooldown": 1}],
        "Wide Slash": [2, "Swing your scimitar in an arc to hit multiple enemies.", {"Effect": {"AoE Damage": "Base Damage - 10%"}, "Cooldown": 2}]
    },
    "Aggressive": {
        "Overhead Cleave": [3, "Bring your scimitar down with force, cleaving through defenses.", {"Effect": {"Damage": "Base Damage + 25%", "Enemy Defense Reduction": "-10%"}, "Cooldown": 3}],
        "Rending Strike": [5, "A brutal attack that leaves lasting wounds.", {"Effect": {"Damage": "Base Damage + 30%", "Bleed Effect": "5% over 3 seconds"}, "Cooldown": 4}]
    },
    "Defensive": {
        "Braced Stance": [4, "Plant your feet and prepare for attacks, reducing damage.", {"Effect": {"Damage Reduction": "-20%"}, "Duration": 3, "Cooldown": 3}],
        "Counter Slash": [6, "Block and retaliate against an enemy’s attack.", {"Effect": {"Damage": "Base Damage + 15%", "Enemy Speed Reduction": "-10"}, "Cooldown": 4}]
    },
    "Tactical": {
        "Reckless Charge": [5, "Rush at your opponent, disrupting their stance.", {"Effect": {"Damage": "Base Damage + 20%", "Enemy Evasion Reduction": "-15%"}, "Cooldown": 4}],
        "Savage Momentum": [7, "Build up power with consecutive strikes.", {"Effect": {"Damage Boost": "+5% per hit", "Max Stacks": 5}, "Duration": 5, "Cooldown": 5}]
    },
    "Ultimate": {
        "Whirlwind of Blades": [8, "Spin in a violent arc, slashing all nearby enemies.", {"Effect": {"AoE Damage": "Base Damage + 40%"}, "Cooldown": 6}]
    }
}

LongswordSkills = {
    "Accepted Weapons": {
        "Steel Longsword": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A versatile weapon offering balance between speed and power.", "price": {"Mithril Coins": 6, "Gold Coins": 15}},
        "Knight's Blade": {"type": "Intermediate", "effect": {"Damage": 1.2, "Defense": 1.1}, "acquire type": "Craftable", "description": "A finely crafted blade favored by knights for its durability."},
        "Narsil/Andúril": {"type": "Legendary", "effect": {"Damage": 1.4, "Crit Chance": 1.15, "Ally Morale Boost": True}, "acquire type": "Quest", "description": "The legendary sword of Isildur, reforged as Andúril, a symbol of kingship and hope."},
        "Excalibur": {"type": "Legendary", "effect": {"Damage": 1.5, "Crit Chance": 1.5, "Enemy Fear Effect": True}, "acquire type": "Quest", "description": "The mythical sword of King Arthur, imbued with magical power and unmatched sharpness."}
    },
    "Basic": {
        "Defensive Stance": [1, "Increase defense temporarily while reducing attack speed.", {"Effect": {"Defense Boost": "+15%", "Attack Speed": "-10%"}, "Cooldown": 2}],
        "Measured Strike": [2, "Deliver a precise, calculated blow.", {"Effect": {"Damage": "Base Damage + 15%"}, "Cooldown": 1}]
    },
    "Aggressive": {
        "Overhead Slash": [4, "Strike downward with great force.", {"Effect": {"Damage": "Base Damage + 25%"}, "Cooldown": 3}],
        "Parry Counter": [6, "Block an attack and instantly counter.", {"Effect": {"Counter Damage": "Base Damage + 20%"}, "Cooldown": 4}]
    },
    "Ultimate": {
        "King's Command": [10, "Rally nearby allies, boosting their morale and strength.", {"Effect": {"Ally Damage Boost": "+10%", "Ally Defense Boost": "+10%"}, "Cooldown": 6}]
    }
}
SmallSwordSkills = {
    "Accepted Weapons": {
        "Naval Small Sword": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A lightweight sword favored by officers for close combat.", "price": {"Doubloons": 25, "Sterling Pounds Silver": 100}},
        "Decorated Court Blade": {"type": "Intermediate", "effect": {"Damage": 1.15}, "acquire type": "Craftable", "description": "A finely decorated blade often used for ceremonial purposes but equally deadly in skilled hands."},
        "Golden Hilt Small Sword": {"type": "Advanced", "effect": {"Damage": 1.2}, "acquire type": "Quest", "description": "A masterfully crafted weapon blending beauty and lethality, prized among naval officers."}
    },
    "Basic": {
        "Quick Feint": [1, "Fake a strike to throw off an opponent's defense.", {"Effect": {"Enemy Defense Reduction": "-10%"}, "Cooldown": 2}],
        "Point Thrust": [2, "A precise jab aimed at a weak spot.", {"Effect": {"Damage": "Base Damage + 15%"}, "Cooldown": 1}]
    },
    "Defensive": {
        "Swift Parry": [3, "Block an incoming attack and prepare for a counter.", {"Effect": {"Parry Effect": "Negate Damage", "Enemy Speed Reduction": "-5%"}, "Cooldown": 2}],
        "Evasive Footwork": [5, "Dodge backward, avoiding an attack and gaining a positioning advantage.", {"Effect": {"Dodge Effect": "Yes"}, "Cooldown": 3}]
    },
    "Aggressive": {
        "Duelist's Flourish": [7, "Perform a series of dazzling strikes.", {"Effect": {"Damage": "3x Base Damage - 5%"}, "Cooldown": 5}]
    }
}
RapierSkills = {
    "Accepted Weapons": {
        "Steel Rapier": {"type": "Basic", "effect": {"Damage": 1.1, "Crit Chance": 1.05}, "acquire type": "Purchasable", "description": "A long and slender blade designed for thrusting attacks.", "price": {"Doubloons": 12, "Sterling Pounds Silver": 52}},
        "Officer's Rapier": {"type": "Intermediate", "effect": {"Damage": 1.15, "Crit Chance": 1.1}, "acquire type": "Craftable", "description": "A finely made rapier issued to high-ranking officers in the British Navy."},
        "Silvered Rapier": {"type": "Advanced", "effect": {"Damage": 1.2, "Enemy Speed": -.1}, "acquire type": "Quest", "description": "A beautifully silvered blade known for its unmatched sharpness and balance."}
    },
    "Basic": {
        "Piercing Strike": [1, "A powerful thrust aimed at bypassing armor.", {"Effect": {"Damage": "Base Damage + 20%"}, "Cooldown": 1}],
        "Defensive Riposte": [2, "Block an attack and retaliate instantly.", {"Effect": {"Counter Damage": "Base Damage + 15%"}, "Cooldown": 2}]
    },
    "Aggressive": {
        "Fencing Lunge": [3, "A forward lunge with extended reach.", {"Effect": {"Damage": "Base Damage + 25%", "Crit Chance": "+10%"}, "Cooldown": 3}],
        "Deadly Stab": [6, "Target a critical area for massive damage.", {"Effect": {"Damage": "Base Damage + 40%"}, "Cooldown": 4}]
    },
    "Elegant": {
        "Fencing Lunge": [1, "A precise forward thrust with exceptional reach.", {"Effect": {"Damage": "Base Damage + 15%", "Crit Chance": "+5%"}, "Cooldown": 2}],
        "Defensive Riposte": [3, "Counter an incoming attack with precision.", {"Effect": {"Counter Damage": "Base Damage + 20%", "Enemy Accuracy Reduction": "-10%"}, "Cooldown": 3}],
        "Graceful Flourish": [5, "A dazzling display that confuses enemies.", {"Effect": {"Enemy Evasion": "-15%", "Damage": "Base Damage"}, "Cooldown": 4}],
        "Perfect Strike": [7, "A flawless attack targeting a weak point.", {"Effect": {"Damage": "Base Damage + 40%", "Crit Chance": "+15%"}, "Cooldown": 5}]
    }
}



StarWarsSkills = {
    "Lightsaber": LIGHTSABERSKILLS,
    "Force Abilities": {
        "Powers": FORCEPOWERS,
        "Stances": FORCESTANCES,
    },
    "Blaster": {
        "Accepted Weapons": {
            "Nubian Blaster": {"type": "Basic", "effect": {"Damage": 1.1, "Accuracy": 1.05}, "acquire type": "Purchasable", "description": "A sleek and efficient blaster, famously used by Padmé Amidala. Known for its high accuracy and quick firing rate.", "price": {"Republic Dataries": 15000, "Galactic Credits": 30000, "Imperial Bonds": 7500, "Imperial Credits": 32000}},
            "DL-44 Heavy Blaster": {"type": "Intermediate", "effect": {"Damage": 1.3, "Crit Chance": 1.1}, "acquire type": "Quest", "description": "Han Solo's signature weapon. A powerful blaster with heavy stopping power, but a slower rate of fire."},
            "EE-3 Carbine Rifle": {"type": "Legendary", "effect": {"Damage": 1.4, "Crit Damage": 1.5}, "acquire type": "Obtainable", "description": "Boba Fett's iconic carbine rifle. Offers excellent range and precision, making it perfect for bounty hunters."},
            "E-11 Blaster Rifle": {"type": "Basic", "effect": {"Damage": 1.15, "Accuracy": 1.08}, "acquire type": "Purchasable", "description": "The standard issue for Imperial Stormtroopers. A reliable and versatile blaster with moderate damage and good range.", "price": {"Republic Dataries": 17000, "Galactic Credits": 34000, "Imperial Bonds": 8000, "Imperial Credits": 35000}},
            "T-21 Heavy Blaster": {"type": "Intermediate", "effect": {"Damage": 1.35, "Speed": .8}, "acquire type": "Quest", "description": "A heavy blaster used by Imperial forces, known for its devastating firepower at the cost of slower fire rate."},
            "Westar-34 Blaster Pistol": {"type": "Advanced", "effect": {"Damage": 1.25, "Accuracy": 1.12}, "acquire type": "Quest", "description": "Used by Mandalorian bounty hunters like Jango Fett. A compact but powerful blaster pistol with excellent accuracy."},
            "A280-CFE Blaster Rifle": {"type": "Advanced", "effect": {"Damage": 1.2, "Critical Damage": 1.15}, "acquire type": "Obtainable", "description": "The blaster rifle used by the Rebellion's elite forces. High damage and effective at longer ranges."}
        },
        "Basic": {
            "Basic Shot": [0, "A single, accurate blaster shot.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
            "Rapid Fire": [2, "Fire a burst of shots in quick succession.", {"Effect": {"Damage": "3x Base Damage - 10%"}, "Cooldown": 3}],
            "Power Blast": [4, "A powerful shot with increased crit damage.", {"Effect": {"Damage": "Base Damage + 30%", "Crit Damage": "+20%"}, "Cooldown": 4}]
        },
        "Tactical": {
            "Suppression Fire": [3, "Hinder enemies with a barrage of shots.", {"Effect": {"Enemy Speed Reduction": "-10"}, "Duration": 3, "Cooldown": 4}],
            "Overload Shot": [6, "Overcharge the blaster for an explosive shot.", {"Effect": {"AoE Damage": "50% Base Damage"}, "Cooldown": 5}]
        }
    },
    "Commander": {
        "Healer/Support": {
            "Abilities": {
                "Tactical Meditation": [0, "Restore health and remove debuffs from all allies.", 
                    {"Effect": {"Heal": "30% HP", "Debuff Removal": "Yes"}, "Cooldown": 3}],
                "Rebel Aid": [2, "Increase {factionalignment} allies' speed and accuracy.", 
                    {"Effect": {"Speed Boost": "+15%", "Accuracy": "+10%"}, "Cooldown": 3}],
                "Inspiring Leadership": [4, "Reduce cooldowns on ally abilities by one turn.", 
                    {"Effect": {"Cooldown Reduction": "-1 Turn"}, "Cooldown": 4}]
            }
        },
        "Daunting Presence": {
            "Abilities": {
                "Dark Aura": [0, "Inflict fear and reduce attack on enemies.", 
                    {"Effect": {"Fear": "1 Turn", "Attack Reduction": "-10%"}, "Cooldown": 3}],
                "Force Suppression": [3, "Stagger {factiontype} enemies with a telekinetic wave.", 
                    {"Effect": {"Stagger": "Yes", "AoE Defense Reduction": "-15%"}, "Cooldown": 4}],
                "Crushing Will": [5, "Reduce enemy morale and critical chance.", 
                    {"Effect": {"Morale Loss": "-20%", "Crit Chance Reduction": "-10%"}, "Cooldown": 5}]
            }
        },
        "Iron Fist": {
            "Abilities": {
                "Command of Fear": [1, "Increase {factiontroopers} ally attack power but reduce morale.", 
                    {"Effect": {"Attack Boost": "+20%", "Morale Loss": "-10%"}, "Cooldown": 2}],
                "Relentless Assault": [3, "Increase ally speed but apply fatigue.", 
                    {"Effect": {"Speed Boost": "+15%", "Fatigue": "1 Turn"}, "Cooldown": 3}],
                "Sacrificial Strategy": [5, "Grant massive power to an ally at the cost of their health.", 
                    {"Effect": {"Power Boost": "+50%", "HP Reduction": "-25%"}, "Cooldown": 5}]
            }
        },
        "Commander Assault": {
            "Abilities": {
                "Orbital Strike": [3, "Call down a devastating bombardment from the {factionfleet}.", 
                    {"Effect": {"AoE Damage": "High"}, "Cooldown": 6}],
                "TIE Swarm": [5, "Command a swarm of {factionship}s to attack all enemies.", 
                    {"Effect": {"AoE Damage": "Moderate", "Stagger": "1 Turn"}, "Cooldown": 5}],
                "AT-AT Assault": [7, "Order the {factiontype} walkers to attack a single target for massive damage.", 
                    {"Effect": {"Damage": "Very High"}, "Cooldown": 7}]
            }
        }
    }
}
MedievalSkills = {
    "Broadsword": BROADSWORDSKILLS,
    "Longsword": LongswordSkills,
    "Mace": {
        "Accepted Weapons": {
            "Iron Mace": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A heavy mace forged from iron, capable of delivering devastating blows.",},
            "Flanged Mace": {"type": "Intermediate", "effect": {"Damage": 1.2, "Armor Penetration": 1.15}, "acquire type": "Craftable", "description": "A mace with flanged edges to penetrate armor more effectively."},
            "Warhammer": {"type": "Advanced", "effect": {"Damage": 1.3, "Enemy Stagger Effect": True}, "acquire type": "Quest", "description": "A massive, brutal weapon designed to crush armor and bones alike."},
            "Witch King's Mace": {"type": "Legendary", "effect": {"Damage": 1.4, "Enemy Fear Effect": True}, "acquire type": "Quest", "description": "The immense, terrifying mace wielded by the Witch King, capable of shattering defenses and striking fear into enemies."},
            "Sauron's Mace": {"type": "Legendary", "effect": {"Damage": 1.6, "Enemy Knockback Effect": True, "Enemy Fear Effect": True, "Always AOE": True}, "acquire type": "Quest", "description": "A massive mace imbued with dark energy, capable of crushing foes and spreading terror."}
        },
        "Basic": {
            "Mace Swing": [0, "A heavy swing dealing solid damage.", {"Effect": {"Damage": "Base Damage + 10%"}, "Cooldown": 1}],
            "Shield Slam": [2, "Use a shield to knock enemies back.", {"Effect": {"Enemy Speed Reduction": "-10"}, "Cooldown": 2}]
        },
        "Aggressive": {
            "Crushing Blow": [4, "Focus strength into a powerful strike.", {"Effect": {"Damage": "Base Damage + 40%"}, "Cooldown": 4}]
        },
        "Evil": {
            "Crushing Doom": [2, "A brutal strike with the mace that applies a fear debuff.", {"Effect": {"Damage": "+40%", "Fear": "80%"}, "Cooldown": 2}],
            "Dark Smash": [4, "A heavy blow that reduces the target's stamina and strength.", {"Effect": {"Stamina": "-25%", "Attack": "-15%"}, "Cooldown": 3}],
            "Mace of Malice": [7, "Increases damage against foes that are afraid or weakened.", {"Effect": {"Damage": "+30% against Fear targets"}, "Cooldown": 4}],
            "Deathblow": [9, "Empowers the mace with dark energy, allowing the user to strike again if the enemy falls.", {"Effect": {"Damage": "+50%"}, "Cooldown": 5}],
        }
    },
    "Horseback": {
        "Accepted Weapons": {
            "Warhorse": {"type": "Basic", "effect": {"Speed": 10, "Evasion": 5}, "acquire type": "Purchasable", "description": "A sturdy steed trained for combat scenarios.", "price": {"Mithril Coins": 100, "Gold Coins": 250}},
            "Elven Steed": {"type": "Legendary", "effect": {"Speed": 20, "Crit Chance": 10}, "acquire type": "Quest", "description": "An elegant and swift horse bred by the elves."},
            "Clydesdale": {"type": "Advanced", "effect": {"Defense": 1.15, "Damage": 10}, "acquire type": "Discoverable", "description": "A powerful and enduring horse, perfect for long battles."}
        },
        "Basic": {
            "Trampling Charge": [3, "Use your steed to knock down enemies in your path.", {"Effect": {"Damage": "Base Damage + 20%", "Enemy Speed Reduction": "-15"}, "Cooldown": 3}],
            "Lancer’s Precision": [6, "Combine swordplay with a lance for devastating strikes.", {"Effect": {"Damage": "Base Damage + 40%"}, "Cooldown": 4}],
        },
        "Aggressive": {
            "Knightly Charge": [7, "Unleash a ferocious charge with your steed, breaking through enemy lines.", {"Effect": {"Damage": "2x Base Damage (AoE)", "Enemy Defense Reduction": "-10"}, "Cooldown": 5}],
        },
        "Tactical":{ 
            "Cavalry Mastery": [9, "Command the battlefield with unmatched mounted combat skills.", {"Effect": {"Speed": "+15", "Crit Chance": "+10"}, "Duration": 3, "Cooldown": 5}],
            "King's Heraldry": [9, "Lead your mounted troops with unparalleled mastery, inspiring allies.", {"Effect": {"Ally Damage": "+10", "Ally Speed": "+5"}, "Duration": 3, "Cooldown": 6}]
        },
        "Defensive": {
            "Mounted Defense": [6, "Adopt a defensive stance on horseback to block incoming attacks.", {"Effect": {"Damage Reduction": "-20%"}, "Duration": 5, "Cooldown": 4}]
        }
    },
    "Archery": {
        "Accepted Weapons": {
            "Longbow": {"type": "Basic", "effect": {"Accuracy": 10}, "acquire type": "Purchasable", "description": "A long-range weapon favored by skilled hunters.", "price": {"Mithril Coins": 5, "Gold Coins": 13}},
            "Crossbow": {"type": "Advanced", "effect": {"Damage": 1.25, "Speed": 3}, "acquire type": "Discoverable", "description": "A powerful ranged weapon with devastating force."},
            "Elven Bow": {"type": "Legendary", "effect": {"Damage": 1.5, "Crit Chance": 1.15}, "acquire type": "Quest", "description": "A mystical bow crafted by the elves, unmatched in elegance and power."}
        },
        "Basic": {
            "Straight Shot": [1, "Fire an arrow straight and true.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
            "Quickshot Volley": [3, "Fire a rapid series of arrows.", {"Effect": {"Damage": "3 hits of Base Damage - 10%"}, "Cooldown": 2}],
        },
        "Tactical": {
            "Arrow Rain": [6, "Call down a rain of arrows to suppress foes.", {"Effect": {"Damage": "Base Damage (AoE)"}, "Cooldown": 3}],
            "Piercing Shot": [8, "An arrow that pierces through multiple enemies.", {"Effect": {"Damage": "Base Damage + 25%", "Area Damage": "50%"}, "Cooldown": 4}],
            "Marksman's Focus": [9, "Boost accuracy and critical hit chance for a short time.", {"Effect": {"Crit Chance": "+20", "Accuracy": "+15"}, "Duration": 3, "Cooldown": 5}]
        },
        "Elegant": {
            "Focused Aim": [1, "A precise shot aimed at the target's weakest point.", {"Effect": {"Damage": "Base Damage + 15%", "Crit Chance": "+10%"}, "Cooldown": 2}],
            "Silent Grace": [3, "Move silently to reposition and shoot undetected.", {"Effect": {"Stealth Bonus": "+20%", "Damage": "Base Damage"}, "Cooldown": 3}],
            "Piercing Arrow": [5, "Fire a single arrow that passes through defenses.", {"Effect": {"Armor Penetration": "+25%", "Damage": "Base Damage + 10%"}, "Cooldown": 4}],
            "Artful Volley": [7, "Release a series of precise arrows in quick succession.", {"Effect": {"Damage": "3x Base Damage - 10%"}, "Cooldown": 5}]
        }
    },
    "Shortsword": ShortswordSkills,
    "Axe": AxeSkills,
    "Scimitar": ScimitarSkills,
    "Commander": {
        "Healer/Support": {
            "Abilities": {
                "Elven Healing": [0, "Restore health and remove bleed effects from {factionalignment} allies.", 
                    {"Effect": {"Heal": "25% HP", "Bleed Removal": "Yes"}, "Cooldown": 3}],
                "Chivalric Blessing": [2, "Boost {factiontype} ally defense and resistance to debuffs.", 
                    {"Effect": {"Defense Boost": "+15%", "Debuff Resistance": "+20%"}, "Cooldown": 3}],
                "Knights' Rally": [4, "Increase ally morale and reduce cooldowns on their abilities.", 
                    {"Effect": {"Morale Boost": "+10%", "Cooldown Reduction": "-1 Turn"}, "Cooldown": 4}]
            }
        },
        "Daunting Presence": {
            "Abilities": {
                "Aura of Terror": [0, "Reduce {factiontype} enemy morale and attack power.", 
                    {"Effect": {"Morale Loss": "-15%", "Attack Reduction": "-10%"}, "Cooldown": 3}],
                "Dark Command": [3, "Inflict fear and blind on all enemies from {factionalignment}.", 
                    {"Effect": {"Fear": "1 Turn", "Blind": "1 Turn"}, "Cooldown": 4}],
                "Withering Dread": [5, "Apply bleed to all enemies and reduce their speed.", 
                    {"Effect": {"Bleed": "5% HP over 3 turns", "Speed Reduction": "-10%"}, "Cooldown": 5}]
            }
        },
        "Iron Fist": {
            "Abilities": {
                "Tyrant’s Command": [1, "Increase {factionknights} ally attack power but reduce morale.", 
                    {"Effect": {"Attack Boost": "+20%", "Morale Loss": "-10%"}, "Cooldown": 2}],
                "Force March": [3, "Increase {factiontype} ally speed but apply fatigue.", 
                    {"Effect": {"Speed Boost": "+15%", "Fatigue": "1 Turn"}, "Cooldown": 3}],
                "Overwhelming Push": [5, "Grant massive power to an ally at the cost of their defense.", 
                    {"Effect": {"Power Boost": "+50%", "Defense Reduction": "-25%"}, "Cooldown": 5}]
            }
        },
        "Commander Assault": {
            "Abilities": {
                "Catapult Strike": [3, "Command the {factionalignment} to unleash a barrage of catapult fire.", 
                    {"Effect": {"AoE Damage": "High"}, "Cooldown": 6}],
                "Flaming Arrows": [5, "Rain flaming arrows on enemy forces from the {factiontype} archers.", 
                    {"Effect": {"Burn": "5% HP over 3 turns", "AoE Damage": "Moderate"}, "Cooldown": 5}],
                "Charge of the Riders": [7, "Order the {factionknights} cavalry to charge for massive damage.", 
                    {"Effect": {"Damage": "Very High"}, "Cooldown": 7}]
            }
        }
    }
}

PirateEraSkills = {
    "Cutlass": CUTLASSSKILLS,
    "Small Sword": SmallSwordSkills,
    "Rapier": RapierSkills,
    "Rifles": {
        "Accepted Weapons": {
            "Musket": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A standard flintlock rifle used by soldiers and pirates alike.", "price": {"Doubloons": 40, "Sterling Pounds Silver": 200}},
            "Blunderbuss": {"type": "Intermediate", "effect": {"Always AOE": True, "Enemy Stagger Effect": True}, "acquire type": "Craftable", "description": "A short-range rifle that sprays pellets, devastating in close quarters."},
            "Long Rifle": {"type": "Advanced", "effect": {"Damage": 1.2}, "acquire type": "Quest", "description": "A finely crafted rifle known for its accuracy and long-range precision."}
        },
        "Basic": {
            "Steady Aim": [0, "Fire an accurate shot.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
            "Quick Reload": [2, "Reload quickly for a follow-up shot.", {"Effect": {"Speed Boost": "+5"}, "Cooldown": 2}]
        },
        "Aggressive": {
            "Piercing Shot": [4, "Fire a shot that penetrates multiple enemies.", {"Effect": {"Damage": "Base Damage + 25%", "Area Damage": "50%"}, "Cooldown": 4}]
        }
    },
    "Flintlock": {
        "Accepted Weapons": {
            "Standard Flintlock": {"type": "Basic", "effect": {"Damage": 1.1}, "acquire type": "Purchasable", "description": "A single-shot flintlock pistol, favored by pirates for its ease of use.", "price": {"Doubloons": 35, "Sterling Pounds Silver": 175}},
            "Dual Flintlocks": {"type": "Intermediate", "effect": {"Damage": 2.0, "Accuracy": -.1}, "acquire type": "Craftable", "description": "A set of twin pistols for quick and devastating volleys."},
            "Golden Flintlock": {"type": "Legendary", "effect": {"Damage": 1.25, "Crit Chance": 1.15}, "acquire type": "Quest", "description": "A rare and beautifully crafted pistol, rumored to bring luck to its wielder."}
        },
        "Basic": {
            "Quick Draw": [1, "Fire a single shot quickly.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
            "Aimed Shot": [3, "Take your time to line up a more powerful shot.", {"Effect": {"Damage": "Base Damage + 20%"}, "Cooldown": 2}]
        },
        "Aggressive": {
            "Double Tap": [5, "Fire two shots in rapid succession.", {"Effect": {"Damage": "2x Base Damage - 10%"}, "Cooldown": 3}],
            "Desperado": [7, "Unleash a flurry of shots at nearby enemies.", {"Effect": {"AoE Damage": "50% Base Damage"}, "Cooldown": 5}]
        }
    },
    "Cannon": {
        "Accepted Weapons": {
            "Standard Cannon": {"type": "Basic", "effect": {"Always AOE": True}, "acquire type": "Purchasable", "description": "A reliable cannon with a decent range and destructive power.", "price": {"Doubloons": 400, "Sterling Pounds Silver": 2000}},
            "Explosive Cannon": {"type": "Advanced", "effect": {"Always AOE": True, "Enemy Burn Effect": True}, "acquire type": "Quest", "description": "A powerful cannon that deals explosive damage on impact."},
            "Grapeshot Cannon": {"type": "Intermediate", "effect": {"Always AOE": True, "Enemy Stagger": True}, "acquire type": "Craftable", "description": "Designed to unleash a storm of small projectiles over a wide area, perfect against groups."}
        },
        "Basic": {
            "Cannon Fire": [0, "Fire a cannonball at enemies.", {"Effect": {"AoE Damage": "High"}, "Cooldown": 4}],
            "Direct Hit": [1, "Fire a single cannonball at the target.", {"Effect": {"Damage": "High AoE Damage"}, "Cooldown": 4}],
            "Blast Wave": [3, "Use a cannon shot to create a shockwave.", {"Effect": {"Enemy Knockback": "Yes", "Damage": "Moderate AoE"}, "Cooldown": 5}]
        }
    },
    "Commander": {
        "Healer/Support": {
            "Abilities": {
                "Rum Rations": [0, "Restore morale and reduce fatigue among allies.", 
                    {"Effect": {"Morale Boost": "+15%", "Fatigue Removal": "Yes"}, "Cooldown": 2}],
                "Deckmaster's Guidance": [3, "Increase ally speed and critical chance.", 
                    {"Effect": {"Speed Boost": "+10%", "Critical Chance": "+5%"}, "Cooldown": 3}],
                "Shanty of Resolve": [5, "Restore health and boost defense for all allies.", 
                    {"Effect": {"Heal": "20% HP", "Defense Boost": "+15%"}, "Cooldown": 5}]
            }
        },
        "Daunting Presence": {
            "Abilities": {
                "Black Flag": [0, "Reduce enemy morale and accuracy.", 
                    {"Effect": {"Morale Loss": "-10%", "Accuracy Reduction": "-10%"}, "Cooldown": 2}],
                "Fear the Tide": [3, "Inflict fear on enemies and stagger their attacks.", 
                    {"Effect": {"Fear": "1 Turn", "Stagger": "Yes"}, "Cooldown": 4}],
                "Dread Captain's Gaze": [5, "Apply bleed to all enemies and reduce their speed.", 
                    {"Effect": {"Bleed": "5% HP over 3 turns", "Speed Reduction": "-10%"}, "Cooldown": 5}]
            }
        },
        "Iron Fist": {
            "Abilities": {
                "Keelhaul Command": [1, "Increase ally attack power but reduce morale.", 
                    {"Effect": {"Attack Boost": "+20%", "Morale Loss": "-10%"}, "Cooldown": 2}],
                "Forced Labor": [3, "Boost ally speed but apply fatigue.", 
                    {"Effect": {"Speed Boost": "+15%", "Fatigue": "1 Turn"}, "Cooldown": 3}],
                "Plunderer's Push": [5, "Grant massive power to an ally at the cost of their defense.", 
                    {"Effect": {"Power Boost": "+50%", "Defense Reduction": "-25%"}, "Cooldown": 5}]
            }
        },
        "Commander Assault": {
            "Abilities": {
                "Broadside Barrage": [3, "Command the {factionship} to unleash a broadside on enemies.", 
                    {"Effect": {"AoE Damage": "High"}, "Cooldown": 6}],
                "Shipboarding Maneuver": [5, "Command the {factiontype} to board an enemy vessel.", 
                    {"Effect": {"Damage": "High Single Target", "Enemy Morale Loss": "-20%"}, "Cooldown": 6}],
                "Cannon Volley": [7, "Order the {factionfleet} to fire all cannons for massive damage.", 
                    {"Effect": {"AoE Damage": "Very High"}, "Cooldown": 7}]
            }
        }
    }
}

MAGICCOMMANDER = {
    "Healer/Support": {
        "Abilities": {
            "Mystic Rejuvenation": [0, "Restore health and remove magical debuffs from all allies.", 
                {"Effect": {"Heal": "25% HP", "Debuff Removal": "Yes"}, "Cooldown": 3}],
            "Arcane Shield": [3, "Grant allies increased defense and resistance to magic.", 
                {"Effect": {"Defense Boost": "+20%", "Magic Resistance": "+15%"}, "Cooldown": 4}],
            "Mana Infusion": [5, "Restore energy to allies and reduce cooldowns on their abilities.", 
                {"Effect": {"Energy Boost": "+30%", "Cooldown Reduction": "-1 Turn"}, "Cooldown": 5}]
        }
    },
    "Daunting Presence": {
        "Abilities": {
            "Cursed Aura": [0, "Reduce enemy damage and morale.", 
                {"Effect": {"Damage Reduction": "-15%", "Morale Loss": "-10%"}, "Cooldown": 2}],
            "Dark Binding": [3, "Root all enemies in place, preventing their movement.", 
                {"Effect": {"Root": "2 Turns"}, "Cooldown": 4}],
            "Enchanted Terror": [5, "Inflict fear and blind all enemies.", 
                {"Effect": {"Fear": "1 Turn", "Blind": "1 Turn"}, "Cooldown": 5}]
        }
    },
    "Iron Fist": {
        "Abilities": {
            "Dark Pact": [1, "Increase ally power but drain their health slightly.", 
                {"Effect": {"Power Boost": "+25%", "Health Reduction": "-5%"}, "Cooldown": 2}],
            "Sacrificial Magic": [3, "Boost ally speed but apply fatigue.", 
                {"Effect": {"Speed Boost": "+15%", "Fatigue": "1 Turn"}, "Cooldown": 3}],
            "Overcharged Spell": [5, "Grant massive magical power to an ally at the cost of their defenses.", 
                {"Effect": {"Magic Boost": "+50%", "Defense Reduction": "-20%"}, "Cooldown": 5}]
        }
    },
    "Commander Assault": {
        "Abilities": {
            "Meteor Swarm": [3, "Call down a fiery meteor strike from the {factiontype} wizards.", 
                {"Effect": {"AoE Damage": "High"}, "Cooldown": 6}],
            "Cataclysm": [5, "Order the {factionalignment} mages to unleash catastrophic spells on enemies.", 
                {"Effect": {"AoE Damage": "Very High"}, "Cooldown": 7}],
            "Elemental Barrage": [7, "Unleash a storm of elemental magic.", 
                {"Effect": {"AoE Damage": "High", "Burn": "5% HP over 3 turns"}, "Cooldown": 7}]
        }
    }
}


MagicSkills = {
    "Spells": MAGICSKILLS,
    "Magic Stances": MAGICSTANCES,
    "Commander": MAGICCOMMANDER
}
HarryPotterSkill = {
    "Spells": HARRYPOTTERSPELLS,
    "Magic Stances": MAGICSTANCES,
    "Commander": MAGICCOMMANDER
}

SKILLTREES = {
    "Star Wars": StarWarsSkills,
    "Medieval": MedievalSkills,
    "Pirate Era": PirateEraSkills,
    "Magic": MagicSkills
}

