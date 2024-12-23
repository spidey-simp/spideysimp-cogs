BUFFS = {
    "Aggressive": {
        "Description": "Boosts offensive capabilities at the cost of defense.",
        "Effect": {"Damage": 0.2, "Defense": -0.1, "Crit Chance": 0.1, "HP": -0.05}
    },
    "Defensive": {
        "Description": "Focus on reducing incoming damage while lowering offensive power.",
        "Effect": {"Defense": 0.3, "Damage": -0.1, "Evasion": 0.05}
    },
    "Balanced": {
        "Description": "Provides a moderate boost to all attributes.",
        "Effect": {"Damage": 0.1, "Defense": 0.1, "Crit Chance": 0.05, "Speed": 0.05}
    },
    "Unprepared": {
        "Description": "A penalty incurred when switching stances mid-battle.",
        "Effect": {"Damage": -0.15, "Defense": -0.1, "Speed": -0.1},
        "Duration": 1
    },
    "Fear": {
        "Description": "Lowers the target's morale and effectiveness in combat.",
        "Effect": {"Damage": -0.2, "Evasion": -0.1},
        "Duration": 2
    },
    "Blind": {
        "Description": "Severely reduces the target's accuracy.",
        "Effect": {"Accuracy": -0.75},
        "Duration": 1
    },
    "Bleed": {
        "Description": "Inflicts damage over time from a bleeding wound.",
        "Effect": {"Damage Over Time": 0.05},  # Percentage of HP
        "Duration": 3
    },
    "Speed Up": {
        "Description": "Increases movement and attack speed temporarily.",
        "Effect": {"Speed": 0.2},
        "Duration": 3
    },
    "Crit Chance Down": {
        "Description": "Lowers the critical hit chance of the target.",
        "Effect": {"Crit Chance": -0.15},
        "Duration": 2
    },
    "High Morale": {
        "Description": "Improves the morale of allies, increasing their effectiveness.",
        "Effect": {"Damage": 0.1, "Defense Change": 0.1},
        "Duration": 4
    },
    "Energy Drain": {
        "Description": "Reduces the target's energy reserves.",
        "Effect": {"Energy": -15},
        "Duration": 1
    },
    "Healing Aura": {
        "Description": "Gradually restores health to all allies in range.",
        "Effect": {"Healing": 0.05},  # Percentage of HP per turn
        "Duration": 3
    },
    "Vulnerable": {
        "Description": "Increases all incoming damage to the target.",
        "Effect": {"Damage Taken": 0.2},
        "Duration": 2
    },
    "Healer/Support": {
        "Description": "Focuses on healing and boosting allies' stats, at the cost of reduced offense.",
        "Effect": {"Healing": 0.15, "Damage": -0.1, "Defense": 0.1, "Energy": 0.05}
        },
    "Daunting Presence": {
        "Description": "Empowers the user with an aura of fear, demoralizing enemies.",
        "Effect": {"Defense": 0.1, "HP": 0.1, "Speed": 0.05},
        "Applies": "Demoralized"
    },
    "Demoralized": {
        "Description": "Enemies lose morale and combat effectiveness while facing an opponent with Daunting Presence.",
        "Effect": {"Damage": -0.2, "Speed": -0.1, "Defense": -.15},
        "Duration": None  # Persistent while Daunting Presence is active
    },
    "Iron Fist": {
        "Description": "Boosts team stats harshly but at the cost of morale or health.",
        "Effect": {"Damage": 0.2, "Speed": 0.1, "Defense": -0.15, "HP": -0.1}
    },
    "Commander Assault": {
        "Description": "Launches powerful strikes through team coordination, but requires higher cooldowns.",
        "Effect": {"Damage": 0.25, "Speed": 0.1, "Energy": -0.2}
    },
    "Tactical": {
        "Description": "Balances offense and defense while enhancing evasion and critical hits.",
        "Effect": {"Damage": 0.1, "Defense": 0.1, "Evasion": 0.05, "Crit Chance": 0.1, "Speed": 0.05}
    },
    "Chaotic": {
        "Description": "Unpredictable style that provides high damage and evasion but reduces stability.",
        "Effect": {"Damage": 0.15, "Evasion": 0.1, "Crit Chance": 0.15, "Speed": 0.1, "HP": -0.1}
    },
    "Evasion Up": {
        "Description": "Increases evasion, making it harder for the opponent to land hits.",
        "Effect": {"Evasion": 0.2},
        "Duration": 3
    },
    "Crit Chance Up": {
        "Description": "Increases the chance to land a critical hit.",
        "Effect": {"Crit Chance": 0.15},
        "Duration": 3
    },
    "Defense Up": {
        "Description": "Increases defense, reducing incoming damage.",
        "Effect": {"Defense Change": 0.5},
        "Duration": 3
    },
    "Protected": {
        "Description": "Massive damage reduction, greatly reducing damage taken.",
        "Effect": {"Damage Taken": -0.5},
        "Duration": 3
    },
    "Crit Damage Down": {
        "Description": "Reduces the damage dealt by critical hits.",
        "Effect": {"Crit Damage": -0.3},
        "Duration": 3
    },
    "Speed Down": {
        "Description": "Reduces the target's speed, making them act slower.",
        "Effect": {"Speed": -0.2},
        "Duration": 2
    },
    "Unstable": {
        "Description": "Increases crit chance but substantially decreases accuracy.",
        "Effect": {"Crit Chance": 0.25, "Accuracy": -0.3},
        "Duration": 3
    },
    "Defense Down": {
        "Description": "Reduces the target's defense, increasing incoming damage.",
        "Effect": {"Defense Change": -0.2},
        "Duration": 3
    },
    "Crit Chance Down": {
        "Description": "Reduces the chance to land a critical hit.",
        "Effect": {"Crit Chance": -0.15},
        "Duration": 3
    },
    "Offense Down": {
        "Description": "Reduces the target's offense, decreasing their damage output.",
        "Effect": {"Damage": -0.2},
        "Duration": 3
    },
    "Energized": {
        "Description": "Lowers overall energy cost for actions.",
        "Effect": {"Energy Cost": -0.2},
        "Duration": 3
    },
    "Accuracy Down": {
        "Description": "Reduces accuracy, making it harder to land hits.",
        "Effect": {"Accuracy": -0.25},
        "Duration": 2
    },
    "Evasion Down": {
        "Description": "Reduces evasion, making it easier for opponents to land hits.",
        "Effect": {"Evasion": -0.2},
        "Duration": 2
    },
    "Counterattack": {
        "Description": "When an enemy attacks, the user attacks back, even though it's not their turn.",
        "Effect": {"Counterattack": True},
        "Duration": 3
    },
    "Burning": {
        "Description": "Deals damage over time, simulating a burning effect.",
        "Effect": {"Damage Over Time": 0.05},
        "Duration": 3
    },
    "Disarmed": {
        "Description": "Opponent loses a significant amount of offense and is forced to change weapons on their next turn. If they have no other weapon, they are automatically defeated.",
        "Effect": {"Offense": -0.4},
        "Duration": 1
    },
    "Stunned": {
        "Description": "Prevents the target from taking a turn.",
        "Effect": {"Stunned": True},
        "Duration": 1
    },
    "Amplified": {
        "Description": "Doubles the effect of all buffs temporarily.",
        "Effect": {"Buffs": "Double"},
        "Duration": 2
    },
    "Potency Up": {
        "Description": "Increases the chance of applying debuffs to enemies.",
        "Effect": {"Potency": 0.2},
        "Duration": 3
    },
    "Potency Down": {
        "Description": "Decreases the chance of applying debuffs to enemies.",
        "Effect": {"Potency": -0.2},
        "Duration": 3
    },
    "Tenacity Up": {
        "Description": "Increases the chance of resisting debuffs.",
        "Effect": {"Tenacity": 0.2},
        "Duration": 3
    },
    "Tenacity Down": {
        "Description": "Decreases the chance of resisting debuffs.",
        "Effect": {"Tenacity": -0.2},
        "Duration": 3
    },
    "Damage Over Time": {
        "Description": "Deals damage over time, similar to bleed or burning.",
        "Effect": {"Damage Over Time": 0.05},
        "Duration": 3
    },
    "Stealth": {
        "Description": "The user cannot be targeted unless there are no other allies or all allies are stealthed.",
        "Effect": {"Stealth": True},
        "Duration": 3
    },
    "Taunt": {
        "Description": "The target must be attacked, drawing the enemy's focus.",
        "Effect": {"Taunt": True},
        "Duration": 2
    },
    "Offense Up": {
        "Description": "Increases the target's offense, boosting their damage output.",
        "Effect": {"Damage": 0.2},
        "Duration": 3
    },
    "Shielded": {
        "Description": "Adds a shield that acts as HP until it is depleted.",
        "Effect": {"Shield": 0.4},
        "Duration": 3
    },
    "Confused": {
        "Description": "The target is confused and may act unpredictably, potentially harming themselves.",
        "Effect": {"Confused": True},
        "Duration": 2
    },
    "Poisoned": {
        "Description": "Deals damage over time, simulating a poisonous effect.",
        "Effect": {"Damage Over Time": 0.05},
        "Duration": 3
    },
    "Exhausted": {
        "Description": "Opposite of Energized, increasing overall energy cost for actions.",
        "Effect": {"Energy Cost": 0.25},
        "Duration": 3
    },
    "Morgul Blade Poisoning": {
        "Description": "Poison that does not expire, dealing damage over time indefinitely.",
        "Effect": {"Damage Over Time": 0.05},
    },
    "Foresight": {
        "Description": "Gives the target a much higher evasion chance, as they can anticipate enemy moves.",
        "Effect": {"Evasion": 0.5},
        "Duration": 3
    },
    "Stagger": {
        "Description": "The target is knocked off balance, reducing their movement and attack speed.",
        "Effect": {"Speed": -0.25, "Attack Speed": -0.2},
        "Duration": 2
    },
    "Fatigued": {
        "Description": "The target suffers from physical exhaustion, reducing effectiveness like Unprepared.",
        "Effect": {"Damage": -0.1, "Defense Change": -0.1, "Speed": -0.1},
        "Duration": 2
    },
    "Knocked Back": {
        "Description": "The target is pushed back, causing them to lose their position and delaying their turn.",
        "Effect": {"Position": "Back"},
        "Duration": 1
    },
    "Morale Down": {
        "Description": "Lowers the target's morale, reducing their effectiveness in combat.",
        "Effect": {"Damage": -0.1, "Defense Change": -0.1},
        "Duration": 2
    },
    "Rooted": {
        "Description": "The target is immobilized, preventing them from moving or escaping.",
        "Effect": {"Rooted": True},
        "Duration": 2
    },
    "Shocked": {
        "Description": "Electrical shock impairs the target's ability to act, reducing their accuracy and speed.",
        "Effect": {"Accuracy": -0.3, "Speed": -0.2},
        "Duration": 2
    },
    "Choked": {
        "Description": "The target is choked, reducing their ability to take actions and causing gradual damage.",
        "Effect": {"Damage Over Time": 0.1, "Speed": -0.3},
        "Duration": 2
    },
    "Undead": {
        "Description": "The target is undead, immune to certain debuffs and resistant to healing.",
        "Effect": {"Healing": -1.0, "Resistance": 0.5},
    },
    "Cursed": {
        "Description": "The target is cursed, reducing their effectiveness in combat and possibly increasing damage taken.",
        "Effect": {"Damage Taken": 0.2, "Speed": -0.2},
        "Duration": 3
    },
    "Berserk": {
        "Description": "The target enters a frenzied state, increasing damage dealt but reducing defense.",
        "Effect": {"Damage": 0.3, "Defense Change": -0.2},
        "Duration": 2
    },
    "Immunity": {
        "Description": "The target becomes immune to certain debuffs or effects for a period.",
        "Effect": {"Immunity": True},
        "Duration": 3
    },
    "Enrage": {
        "Description": "The target is enraged, increasing their attack speed and damage output.",
        "Effect": {"Speed": 0.2, "Damage": 0.25},
        "Duration": 2
    },
    "Time Slow": {
        "Description": "Slows down the target's actions, reducing their effectiveness in battle.",
        "Effect": {"Speed": -0.4},
        "Duration": 2
    },
    "Frostbite": {
        "Description": "Reduces the target's movement and speed due to freezing temperatures.",
        "Effect": {"Speed": -0.3},
        "Duration": 2
    },
    "Vampiric": {
        "Description": "The target heals for a portion of the damage dealt.",
        "Effect": {"Healing": 0.15},
        "Duration": 3
    },
    "Haste": {
        "Description": "Increases the target's attack and movement speed.",
        "Effect": {"Speed": 0.3, "Attack Speed": 0.25},
        "Duration": 3
    },
    "Fortified": {
        "Description": "Substantially increases defense and enables Counterattack for one turn.",
        "Effect": {"Defense Change": .75, "Counterattack": True},
        "Duration": 1
    }
}