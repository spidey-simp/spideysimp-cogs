HINDRANCES = {
    "Grumpy": 
        {
            "description": "Prone to negative moods and complaints. Will have more trouble in relationships.",
            "conflicts": ["Friendly, Charismatic, Empathic, Social Butterfly"]
        },
    "Loner": 
        {
            "description": "Prefers alone time, often in deep thought. Would prefer to not be in social settings.",
            "conflicts": ["Social Butterfly", "Friendly", "Charismatic", "Party Animal", "Empathic"],
        },
    "Absent-Minded": 
        {  
            "description": "Prone to daydreaming or forgetting things. Gains bursts of creativity but struggles with focus.",
            "conflicts": ["Logical", "Disciplined", "Workaholic"],
        },
    "Messy": 
        {
            "description": "Often disorganized.",
            "conflicts": ["Neat Freak"],
        },
    "Paranoid": 
        {
            "description": "Always wary of hidden motives. Struggles with trust.",
            "conflicts": ["Empathic", "Friendly"]
        },
    "Pessimist": 
        {
            "description": "Focuses on potential downsides. Gains resistance to disappointment but lacks enthusiasm.",
            "conflicts": ["Easily Excited", "Driven Achiever"]
        },
    "Reckless": 
        {
            "description": "Often acts on impulse without thinking.",
            "conflicts": ["Logical", "Disciplined", "Thrifty"],
        },
    "Short-Fused": 
        {
            "description": "Quick to anger, but passionate.",
            "conflicts": ["Friendly", "Charismatic", "Empathic"],
        },
    "Dark-Hearted": 
        {
            "description": "Manipulates for personal gain. Evil at their core.",
            "conflicts": ["Kind-Hearted", "Empathic", "Friendly"],
        },
    "Hydrophobic": 
        {
            "description": "Don't put them in the water. Heck don't even put them atop a ship.",
            "conflicts": ["Sea-born"],
        },
    "Super Shy":
        {
            "description": "Would prefer never being seen if possible.",
            "conflicts": ["Natural-born performer", "Social Butterfly", "Charismatic", "Persuasive", "Friendly"],
        },
    "Lazy": 
        {
            "description": "Would prefer to sit around than do anything active.",
            "conflicts": ["Driven Achiever", "Workaholic", "Disciplined", "Energetic Dynamo"],
        },
    "Clumsy": 
        {
            "description": "Will struggle in endeavors that require high-coordination.",
            "conflicts": ["Quick-footed"]
        },
    "Easily Frightened": 
        {
            "description": "Will avoid risks and scary things as is possible.",
            "conflicts": ["Thrill Seeker", "Adventurous", "Valiant"],
        },
    "Unlucky":
        {
            "description": "Maybe they walked under a ladder or broke a mirror?",
            "conflicts": ["Lucky"]
        },
    "Insane": 
        {
            "description": "It might be that the marbles were never there. But they're certainly gone now.",
            "conflicts": ["Logical", "Disciplined"]
        },
    "Non-committal": 
        {
            "description": "Avoids commitment as much as possible. Not likely to accept a marriage proposal.",
            "conflicts": ["Nurturing"]
        },
    "Socially Awkward":
        {
            "description": "That awkward moment when...",
            "conflicts": ["Charismatic", "Witty Comedian", "Party Animal", "Flirtatious"]
        }
}

SOCIALTRAITS = {
    "Social Butterfly": 
        {
            "description": "Enjoys meeting new people and thrives in social settings. Gains charisma quickly and loves building a network of people.",
            "conflicts": ["Loner", "Super Shy"]
        },
    "Friendly":
        {
            "description": "Friendly and approachable, often bringing positivity to those around them. Gains social trust faster.",
            "conflicts": ["Mean", "Dark-Hearted", "Mischief Maker"]
        },
    "Charismatic":
        {
            "description": "Magnetic presence that draws people in. Gains bonuses in social negotiations and influence.",
            "conflicts": ["Mean", "Humorless"],
        },
    "Flirtatious": 
        {
            "description": "Naturally inclined toward romantic interactions. Succeeds more often at romantic interactions.",
            "conflicts": ["Unflirty"],
        },
    "Empathic":
        {
            "description": "Deeply attuned to others’ emotions.",
            "conflicts": ["Sarcastic", "Mean", "Dark-Hearted", "Pessimist", "Paranoid"]
        },
    "Sarcastic": 
        {
            "description": "Sharp wit with a sarcastic edge. Gains influence in conversations but can offend easily.",
            "conflicts": ["Friendly", "Empathic", "Charismatic", "Flirtatious"]
        },
    "Animal Friend": 
        {
            "description": "Deep bond with animals.",
            "conflicts": ["Mean", "Dark-Hearted"],
        },
    "Persuasive": 
        {
            "description": "Could convince you to talk like a chicken. Excels at debating.",
        },
    "Witty Comedian": 
        {
            "description": "Always ready with a joke, bringing humor into any situation. Gains comedy skills faster and better at telling jokes.",
            "conflicts": ["Humorless"]
        },
    "Mischief Maker": 
        {
            "description": "Loves causing harmless trouble and pranks. Gains trickster-related abilities and social stealth.",
            "conflicts": ["Nurturing", "Kind-Hearted", "Empathic"]
        },
    "Childish":
        {
            "description": "Has never quite grown up. Definitely not as mature as their counterparts.",
            "conflicts": ["Elitist", "No-Nonsense", "Disciplined", "Driven Achiever"],
        },
    "Party Animal": 
        {
            "description": "Will never miss a party. You can bet they'll be the life of it too.",
            "conflicts": ["Loner", "Super Shy"]
        },
    "Nurturing": 
        {
            "description": "Will be sure to take care of others where they can.",
            "conflicts": ["Reckless", "Mean", "Dark-Hearted"]
        },
    "Mean":
        {
            "description": "Just plain mean. Will have much more trouble building relationships.",
            "conflicts": ["Friendly", "Empathic", "Kind-Hearted"]
        },
    "Humorless": 
        {
            "description": "Don't tell them a joke, because they just won't get it.",
            "conflicts": ["Witty Comedian"]
        },
    "Unflirty": 
        {
            "description": "Will avoid romance where possible and will struggle more in romantic relationships.",
            "conflicts": ["Flirtatious"]
        }
}

VALUETRAITS = {
    "No-nonsense":
        {
            "description": "Prefers getting straight to the point without any emotions slowing them down.",
            "conflicts": ["Flirtatious", "Childish", "Witty Comedian"]
        },
    "Elitist": 
        {
            "description": "Holds high standards and often looks down on “lesser” pursuits.",
            "conflicts": ["Friendly", "Social Butterfly", "Party Animal"]
        },
    "Valiant":
        {
            "description": "Brave and committed to bringing values into their lives.",
            "conflicts": ["Dark-Hearted", "Reckless", "Easily Frightened"]
        },
    "Inquisitive": 
        {
            "description": "Loves asking questions and uncovering the unknown.",
        },
    "Defiant Rebel": 
        {
            "description": "Dislikes rules and norms.",
            "conflicts": ["Workaholic", "Disciplined"]
        },
    "Pacifist": 
        {
            "description": "Strives for harmony. Will avoid a fight at all costs.",
            "conflicts": ["Mean", "Valiant"]
        },
    "Logical": 
        {
            "description": "Will make calculated decisions and excels at being logical.",
            "conflicts": ["Reckless", "Pessimist", "Impulsive", "Dramatic", "Absent-Minded"]
        },
    "Kind-Hearted": 
        {
            "description": "Strives to help and support others. Gains bonuses in nurturing and team-building.",
            "conflicts": ["Dark-Hearted", "Mischief Maker", "Mean"]
        },
    "Spiritual": 
        {
            "description": "Pursues spiritual understanding.",
            "conflicts": ["Defiant Rebel", "Dark-Hearted"]
        },
    "Driven Achiever": 
        {
            "description": "Sets high goals and works tirelessly to reach them. Gains experience faster in any career.",
            "conflicts": ["Lazy", "Pessimist"]
        },
    "Perfectionist": 
        {
            "description": "Strives for flawlessness in everything.",
            "conflicts": ["Reckless", "Lazy"]
        },
    "Workaholic": 
        {
            "description": "Invests deeply in work. Gains fast career progress but risks burnout.",
            "conflicts": ["Lazy", "Defiant Rebel"]
        },
    "Thrill Seeker": 
        {
            "description": "Loves taking risks and trying daring feats.",
            "conflicts": ["Easily Frightened", "Pessimist", "Paranoid"]
        },
    "Thrifty": 
        {
            "description": "Great at saving money and making the most of limited resources.",
            "conflicts": ["Reckless"]
        },
    "Fierce Competitor": 
        {
            "description": "Driven by winning and being the best.",
            "conflicts": ["Pacifist"]
        },
    "Disciplined": 
        {
            "description": "Loves routine and will excel at it.",
            "conflicts": ["Reckless", "Lazy"]
        }
}

NATURETRAITS = {
    "Explorer":
        {
            "description": "Drawn to new experiences and places.",
            "conflicts": ["Lazy", "Easily Frightened", "Paranoid"]
        },
    "Lucky": 
        {
            "description": "Frequently lucky in events. Gains chance-based rewards more often.",
            "conflicts": ["Unlucky"]
        },
    "Brooding Thinker": 
        {
            "description": "Reflects deeply and feels deeply.",
            "conflicts": ["Social Butterfly", "Friendly"]
        },
    "Pirate":
        {
            "description": "Literally a pirate.",
            "conflicts": ["Hydrophobic", "Tech Savant", "Gamer", "Chronically Online"]
        },
    "Medieval":
        {
            "description": "Stuck in the medieval era.",
            "conflicts": ["Tech Savant", "Gamer", "Chronically Online"],
        },
    "Sea-born": 
        {
            "description": "Loves the sea and open waves. Will be better at sailing.",
            "conflicts": ["Hydrophobic"]
        },
    "Chronically Online": 
        {
            "description": "Thrives on social media fame and recognition. Will let their chronically online side show at times.",
            "conflicts": ["Pirate", "Medieval", "Socially Awkward"]
        },
    "Quirky": 
        {
            "description": "Stands out for unusual interests or behavior.",
            "conflicts": ["No-nonsense", "Elitist", "Disciplined"]
        },
    "Shadowy Operative": 
        {
            "description": "Prefers moving unseen and being elusive.",
            "conflicts": ["Social Butterfly", "Charismatic", "Friendly"]
        },
    "Neat Freak": 
        {
            "description": "Obsessed with cleanliness and order. Gains efficiency in organizational tasks.",
            "conflicts": ["Messy"]
        },
    "Night Owl": 
        {
            "description": "Most active and productive at night. Gains efficiency boosts during late hours.",
        },
    "Quick footed":
        {
            "description": "Fast on their feet and skilled. More likely to excel in skills related to dueling.",
            "conflicts": ["Clumsy"]
        },
    "Force-sensitive":
        {
            "description": "Sensitive to mysterious, otherworldly forces. Gains bonuses to force-wielding skills.",
        },
    "Easily Excited":
        {
            "description": "Will be most likely to get excited over mediocrity. Loves life.",
            "conflicts": ["Pessimist"]
        },
    "Dramatic": 
        {
            "description": "Is it the end of the world? Oh you're just going to the grocery store? Never mind.",
            "conflicts": ["No-nonsense", "Disciplined"]
        }
}

INTERESTTRAITS = {
    "Music Enthusiast": 
        {
            "description": "Loves all things music, from composing to attending concerts. Gains faster skill with music-related activities and instruments.",
        },
    "Art Connoisseur": 
        {
            "description": "Has a keen eye for beauty and aesthetics, appreciating art in all forms. Boosts creativity and gains art skills faster.",
        },
    "Science Savant": 
        {
            "description": "Thrives on scientific knowledge and experimentation. Gains science-related skills more efficiently.",
        },
    "Literary Aficionado": 
        {
            "description": "Has a deep love for literature and writing. Gains skill in writing much faster.",
        },
    "Tech Savant": 
        {
            "description": "Expert in technology and programming. Gains computer and tech-related skills quickly.",
        },    
    "Gamer": 
        {
            "description": "Put them behind a keyboard or controller and watch them enjoy. Skilled at gaming.",
        },
    "Natural-born performer": 
        {
            "description": "Loves the stage and excels in the acting skill.",
        },
    "Collector": 
        {
            "description": "Loves collecting and preserving items.",
        },
    "Skilled Craftsperson": 
        {
            "description": "Expert at building or repairing things. Gains crafting or mechanical skills at an accelerated pace.",
        },
    "Green Thumb": 
        {
            "description": "Has a natural talent for gardening and working with plants. Gains gardening skills quicker.",   
        },
    "Culinary Artisan": 
        {
            "description": "Natural talent in the kitchen, making every dish memorable. Gains cooking skills quickly.",
        },     
    "Business Tycoon": 
        {
            "description": "Natural talent for commerce and profit.",
        },
    "Fashion Forward":
        {
            "description": "Has a flair for style and trends. Gains influence in fashion.",
        }
}

ALLTRAITS = {
    **SOCIALTRAITS,
    **VALUETRAITS,
    **NATURETRAITS,
    **INTERESTTRAITS,
    **HINDRANCES
}
