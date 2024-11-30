import asyncio
from typing import List, Dict, Tuple
from .jobs import CAREEROPPOSITE

TRAITOPPOSITES = {
    "Dark-Hearted": "Kind-Hearted",
    "Kind-Hearted": "Dark-Hearted"
}

MILESTONES = {
        -100: {"title": "Master of Shadows", "effect": "TBD."},
        -75: {"title": "Champion of the Void", "effect": "TBD."},
        -50: {"title": "Harbinger of Night", "effect": "TBD."},
        -25: {"title": "Veiled Wanderer", "effect": "TBD."},
        0: {"title": "Neutral", "effect": "No bonuses or penalties; fully balanced."},
        25: {"title": "Radiant Wanderer", "effect": "TBD"},
        50: {"title": "Champion of Light", "effect": "TBD"},
        75: {"title": "Beacon of Hope", "effect": "TBD"},
        100: {"title": "Master of Radiance", "effect": "TBD"}
        }



updatetraits = None

class AlignmentManager:
    def __init__(self):
        """Initialize the AlignmentManager."""
        self.milestones = MILESTONES
        self.trait_opposites = TRAITOPPOSITES
    
    def generate_alignment_bar(self, alignment: int) -> str:
        """
        Generate a progress bar for alignment in the style:
        Evil ░░░░░ | ░░░░░ Good
        """
        total_slots = 5  # Number of slots on each side of the bar
        normalized_alignment = (alignment + 100) / 200  # Normalize to range [0, 1]

        # Calculate filled slots for each side
        if alignment < 0:
            left_filled = round(abs(alignment) / 100 * total_slots)  # Negative alignment fills the left bar
            right_filled = 0
        elif alignment > 0:
            right_filled = round(alignment / 100 * total_slots)  # Positive alignment fills the right bar
            left_filled = 0
        else:
            left_filled = right_filled = 0  # Neutral alignment leaves both sides empty

        # Create bars
        left_bar = ["░"] * (total_slots - left_filled) + ["█"] * left_filled  # Fill right-to-left
        right_bar = ["█"] * right_filled + ["░"] * (total_slots - right_filled)  # Fill left-to-right

        # Combine the parts
        bar = f"Evil {''.join(left_bar)} | {''.join(right_bar)} Good"
        return bar



    async def changealignment(
        self, ctx, direction: str, amount: int, current_alignment: int, user_traits: List[str]
    ) -> Tuple[int, str]:
        """Adjust alignment based on direction ('positive' or 'negative') and amount."""
        if direction == "positive" and "Dark-Hearted" in user_traits:
            amount *= .25

        if direction == "negative" and "Kind-Hearted" in user_traits:
            amount *= .25

        effective_amount = amount * (1 - abs(current_alignment) / 200)
        if direction == "positive":
            new_alignment = min(100, current_alignment + effective_amount)
        elif direction == "negative":
            new_alignment = max(-100, current_alignment - effective_amount)
        else:
            await ctx.send("Invalid alignment direction. Use 'positive' or 'negative'.")
            return current_alignment, None

        updatetraits = None
        new_milestone = await self.get_milestone(new_alignment)
        if new_milestone == "Neutral":
            updatetraits = await self.trait_switch(ctx, user_traits)
        
        return new_alignment, new_milestone, updatetraits
        

    async def get_milestone(self, alignment: int) -> str:
        """Determine the milestone based on the current alignment."""
        for threshold, milestone in sorted(self.milestones.items(), reverse=True):
            if alignment >= threshold:
                return milestone["title"]
        return "Neutral"

    async def trait_switch(self, ctx, user_traits: List[str]) -> None:
        """Check if the user qualifies for a trait switch at the neutral milestone."""
        updatetraits = user_traits
        for trait, opposite_trait in self.trait_opposites.items():
            if trait in user_traits:
                await ctx.send(
                    f"Your {trait} trait seems less applicable now. "
                    f"Would you like to switch it to {opposite_trait}? Reply with `yes` or `no`."
                )
                def check(m):
                    return m.author == ctx.author and m.content.lower() in ["yes", "no"]

                try:
                    response = await ctx.bot.wait_for("message", timeout=30.0, check=check)
                    if response.content.lower() == "yes":
                        updatetraits.remove(trait)
                        updatetraits.append(opposite_trait)
                        await ctx.send(f"Your {trait} trait has been switched to {opposite_trait}.")
                        return updatetraits
                    else:
                        await ctx.send("Trait change canceled.")
                except asyncio.TimeoutError:
                    await ctx.send("You took too long to respond. Trait change canceled.")
                return

