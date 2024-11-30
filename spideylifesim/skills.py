
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
    "Basic": {
        "Basic Slash": [0, "Deals Base Damage.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 0}],
        "Deflect": [0, "Temporarily increases Evasion.", {"Effect": {"Evasion": "+10"}, "Duration": 1, "Cooldown": 2}],
        "Charge Slash": [0, "Deals Base Damage + Crit Chance%.", {"Effect": {"Damage": "Base Damage + Crit Chance%"}, "Cooldown": 3}]
    },
    "Aggressive": {
        "Precision Strike": [2, "Increases Crit Chance for one attack.", {"Effect": {"Crit Chance": "+10", "Damage": "Base Damage + 25%"}, "Cooldown": 2}],
        "Relentless Barrage": [4, "Three consecutive strikes.", {"Effect": {"Damage": "50% Base Damage per strike", "Speed": "+5"}, "Duration": 1, "Cooldown": 3}],
        "Rage Strike": [7, "A powerful attack with a cost.", {"Effect": {"Damage": "Base Damage + 50%", "Defense": "-15"}, "Duration": 2, "Energy Cost": 20, "Cooldown": 4}],
        "Form V: Djem So": [9, "Increases Damage at the cost of Defense.", {"Effect": {"Damage": "+15", "Defense": "-5"}, "Duration": 3, "Cooldown": 5}]
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

    }
}

CUTLASSSKILLS = {
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
        "Flintlock Shot": [3, "Ranged attack with the flintlock pistol.", {"Effect": {"Damage": "Base Damage + 10%", "Speed": "+5"}, "Cooldown": 3}],
        "Blade and Bullet": [6, "Combine melee and ranged attacks for burst damage.", {"Effect": {"Damage": "2x Base Damage (melee + ranged)"}, "Energy Cost": 15, "Cooldown": 4}],
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
    }
}


BROADSWORDSKILLS = {
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
    "Horseback": {
        "Mounted Combat Training": [1, "Learn to wield your broadsword effectively on horseback.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
        "Trampling Charge": [3, "Use your steed to knock down enemies in your path.", {"Effect": {"Damage": "Base Damage + 20%", "Enemy Speed Reduction": "-15"}, "Cooldown": 3}],
        "Lancer’s Precision": [6, "Combine swordplay with a lance for devastating strikes.", {"Effect": {"Damage": "Base Damage + 40%"}, "Cooldown": 4}],
        "Knightly Charge": [7, "Unleash a ferocious charge with your steed, breaking through enemy lines.", {"Effect": {"Damage": "2x Base Damage (AoE)", "Enemy Defense Reduction": "-10"}, "Cooldown": 5}],
        "Cavalry Mastery": [9, "Command the battlefield with unmatched mounted combat skills.", {"Effect": {"Speed": "+15", "Crit Chance": "+10"}, "Duration": 3, "Cooldown": 5}],
        "King's Heraldry": [9, "Lead your mounted troops with unparalleled mastery, inspiring allies.", {"Effect": {"Ally Damage": "+10", "Ally Speed": "+5"}, "Duration": 3, "Cooldown": 6}]
    },
    "Archery": {
        "Archer's Training": [1, "Learn the basics of using a bow.", {"Effect": {"Damage": "Base Damage"}, "Cooldown": 1}],
        "Quickshot Volley": [3, "Fire a rapid series of arrows.", {"Effect": {"Damage": "3 hits of Base Damage - 10%"}, "Cooldown": 2}],
        "Arrow Rain": [6, "Call down a rain of arrows to suppress foes.", {"Effect": {"Damage": "Base Damage (AoE)"}, "Cooldown": 3}],
        "Piercing Shot": [8, "An arrow that pierces through multiple enemies.", {"Effect": {"Damage": "Base Damage + 25%", "Area Damage": "50%"}, "Cooldown": 4}],
        "Marksman's Focus": [9, "Boost accuracy and critical hit chance for a short time.", {"Effect": {"Crit Chance": "+20", "Accuracy": "+15"}, "Duration": 3, "Cooldown": 5}]
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
    "Harry Potter Spells": {
        "Expelliarmus": [1, "Disarm your opponent with a flick of your wand.", {"Effect": {"Disarm Duration": "3 seconds", "Enemy Accuracy Reduction": "-10%"}, "Cooldown": 2}],
        "Protego": [3, "Summon a magical barrier to block attacks.", {"Effect": {"Damage Absorption": "25%", "Duration": "5 seconds"}, "Cooldown": 3}],
        "Stupefy": [5, "Stun your enemy with a powerful red blast.", {"Effect": {"Stun Duration": "3 seconds", "Damage": "Base Damage + 10%"}, "Cooldown": 4}],
        "Expecto Patronum": [7, "Summon a protective spirit to fend off dark forces.", {"Effect": {"Fend Off Dark Forces": "Yes", "Ally Protection": "+20%"}, "Duration": 8, "Cooldown": 6}],
        "Avada Kedavra": [9, "Unleash the Killing Curse for instant devastation.", {"Effect": {"Instant Kill": "Yes", "Energy Cost": "High"}, "Cooldown": 10}]
    }
}


MAGICSTANCES = {
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
    }
}


SKILLTREES = {
    "Lightsaber": LIGHTSABERSKILLS,
    "Cutlass": CUTLASSSKILLS,
    "Broadsword": BROADSWORDSKILLS,
    "Spells": MAGICSKILLS,
    "Magic": MAGICSTANCES,
    "Force Abilities": FORCEPOWERS,
    "Force": FORCESTANCES
}
