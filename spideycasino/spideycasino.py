from __future__ import annotations
import random
import typing as t
import asyncio
import discord
from discord import app_commands
from redbot.core import commands, bank

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

# ---------- Card/Deck/Hand ----------
class Card(t.NamedTuple):
    rank: str
    suit: str

    @property
    def value(self) -> int:
        if self.rank in {"J", "Q", "K"}:  # face cards
            return 10
        if self.rank == "A":
            return 11  # count as 11, we'll adjust aces down in Hand.total
        return int(self.rank)

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

class Deck:
    def __init__(self, num_decks: int = 4, *, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.cards: list[Card] = [Card(r, s) for _ in range(num_decks) for s in SUITS for r in RANKS]
        self.shuffle()

    def shuffle(self) -> None:
        self.rng.shuffle(self.cards)

    def draw(self) -> Card:
        if not self.cards:
            # auto-reshuffle if we run out
            self.cards = [Card(r, s) for s in SUITS for r in RANKS]
            self.shuffle()
        return self.cards.pop()

class Hand:
    def __init__(self) -> None:
        self.cards: list[Card] = []

    def add(self, card: Card) -> None:
        self.cards.append(card)

    @property
    def total(self) -> int:
        total = sum(c.value for c in self.cards)
        # adjust for aces (treat some as 1 instead of 11 if over 21)
        aces = sum(1 for c in self.cards if c.rank == "A")
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.total == 21

    def is_bust(self) -> bool:
        return self.total > 21

    def __str__(self) -> str:
        return " ".join(str(c) for c in self.cards)

# ---------- UI View ----------
class BlackjackView(discord.ui.View):
    def __init__(self, *, author_id: int, deck: Deck, player: Hand, dealer: Hand, bet: int | None, timeout: float = 90.0):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.deck = deck
        self.player = player
        self.dealer = dealer
        self.bet = bet
        self.finished = asyncio.Event()
        self.result: str | None = None  # "win", "lose", "push", "blackjack"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id != self.author_id:
            await interaction.response.send_message("This isn’t your hand.", ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        self.result = self.result or "lose"  # treat timeout as a loss by forfeit
        self.finished.set()

    def disable_all_items(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    def render_embed(self, *, reveal_dealer: bool = False) -> discord.Embed:
        dealer_cards = " ".join(str(c) for c in self.dealer.cards)
        player_cards = " ".join(str(c) for c in self.player.cards)

        if not reveal_dealer:
            if self.dealer.cards:
                dealer_cards = f"{self.dealer.cards[0]} ▮▮"  # hide hole card
            dealer_total = "?"
        else:
            dealer_total = str(self.dealer.total)

        e = discord.Embed(title="🂡 Blackjack", color=discord.Color.blurple())
        if self.bet is not None:
            e.description = f"Bet: **{self.bet}**"
        e.add_field(name="Dealer", value=f"`{dealer_cards}`\nTotal: **{dealer_total}**", inline=False)
        e.add_field(name="You", value=f"`{player_cards}`\nTotal: **{self.player.total}**", inline=False)
        return e

    async def dealer_play(self):
        # Dealer stands on 17 (including soft 17 by default). Change rule here if needed.
        while self.dealer.total < 17:
            await asyncio.sleep(0.3)
            self.dealer.add(self.deck.draw())

    def settle(self) -> str:
        p, d = self.player.total, self.dealer.total
        if self.player.is_bust():
            return "lose"
        if self.dealer.is_bust():
            return "win"
        if p > d:
            return "win"
        if p < d:
            return "lose"
        return "push"

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player.add(self.deck.draw())
        if self.player.is_bust():
            self.disable_all_items()
            self.result = "lose"
            await interaction.response.edit_message(embed=self.render_embed(reveal_dealer=True), view=self)
            self.finished.set()
            return
        # still playing
        await interaction.response.edit_message(embed=self.render_embed(reveal_dealer=False), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.secondary)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.disable_all_items()
        await self.dealer_play()
        self.result = self.settle()
        await interaction.response.edit_message(embed=self.render_embed(reveal_dealer=True), view=self)
        self.finished.set()

# ---------- Cog ----------
class SpideyCasino(commands.Cog):
    """Simple, single-hand Blackjack with Hit/Stand buttons."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rng = random.Random()

    casino = app_commands.Group(name="casino", description="Various casino games.")

    @casino.command(name="blackjack", description="Play a quick hand of Blackjack")
    @app_commands.describe(bet="Optional wager (ties to your own economy system)")
    async def blackjack(self, interaction: discord.Interaction, bet: int = None):
        
        if bet: 
            if not await bank.can_spend(interaction.user, bet):
                currency = await bank.get_currency_name(interaction.guild)
                balance = await bank.get_balance(interaction.user)
                await interaction.response.send_message(f"Your bet of {bet} {currency} exceeds your account balance of `{balance} {currency}.`", ephemeral=True)
                return

            await bank.withdraw_credits(interaction.user, bet)

        deck = Deck(num_decks=4, rng=self.rng)
        player = Hand()
        dealer = Hand()

        # initial deal
        player.add(deck.draw())
        dealer.add(deck.draw())
        player.add(deck.draw())
        dealer.add(deck.draw())

        view = BlackjackView(author_id=interaction.user.id, deck=deck, player=player, dealer=dealer, bet=bet)

        payout_done = False
        # Natural blackjacks
        if player.is_blackjack() or dealer.is_blackjack():
            view.disable_all_items()
            if player.is_blackjack() and not dealer.is_blackjack():
                view.result = "blackjack"
                # payout 3:2 by convention
                if bet:
                    await bank.deposit_credits(interaction.user, int(bet*2.5))
                    payout_done = True
            elif dealer.is_blackjack() and not player.is_blackjack():
                view.result = "lose"
                # TODO: house keeps bet
                if bet:
                    payout_done = True
            else:
                view.result = "push"
                if bet:
                    await bank.deposit_credits(interaction.user, bet)
                    payout_done = True
            await interaction.response.send_message(embed=view.render_embed(reveal_dealer=True), view=view, ephemeral=False)
            return

        await interaction.response.send_message(embed=view.render_embed(reveal_dealer=False), view=view, ephemeral=False)

        # wait on completion
        try:
            await asyncio.wait_for(view.finished.wait(), timeout=view.timeout or 90.0)
        except asyncio.TimeoutError:
            pass

        # settle economy (if any)
        # NOTE: Only do this once to avoid double-payouts on edits.
        if bet is not None and view.result is not None and not payout_done:
            # Payout table
            if view.result == "win":
                await bank.deposit_credits(interaction.user, (bet * 2))
                pass  # TODO: await self.deposit(interaction.user.id, bet * 2)
            elif view.result == "push":
                await bank.deposit_credits(interaction.user, bet)
                pass  # TODO: await self.deposit(interaction.user.id, bet)
            elif view.result == "blackjack":
                await bank.deposit_credits(interaction.user, int(bet * 2.5))
                pass  # TODO: await self.deposit(interaction.user.id, int(bet * 2.5))
            else:
                # loss: do nothing (house keeps wager already withdrawn)
                pass
        

