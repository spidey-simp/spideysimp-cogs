from __future__ import annotations

import random
import discord
import asyncio
from discord.ext import commands
from redbot.core.bot import Red
from redbot.core import commands, Config
import wordfreq
import nltk
from nltk.corpus import words
import os
import re
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple

nltk.download("words")

all_words = words.words()

active_games = {}


def get_idioms():
    """Scrapes common idioms from this website."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(script_dir, "idioms.txt")
    idioms = []
    
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if ":" in line:
                idiom = line.split(":")[0]
                idioms.append(idiom.lower())

    return idioms

def get_filtered_words(difficulty: str):
    """Filters words based on difficulty using word frequency."""
    difficulty_settings = {
        "novice": {"freq": .0001, "min_length": 4, "max_length": 6},
        "easy": {"freq": 0.00001, "min_length": 4, "max_length": 8},
        "medium": {"freq": 0.000001, "min_length": 4, "max_length": 10},
        "hard": {"freq": 0.0000001, "min_length": 6, "max_length": 12},
        "expert": {"freq": 0.00000001, "min_length": 6, "max_length": 20},
        "impossible": {"freq": 0.000000001, "min_length": 8, "max_length": None}  # No upper limit
    }

    settings = difficulty_settings.get(difficulty, difficulty_settings["medium"])
    min_length, max_length = settings["min_length"], settings["max_length"]
    frequency_threshold = settings["freq"]
    return [
        word.lower() for word in words.words()
        if wordfreq.word_frequency(word, "en") >= frequency_threshold
        and len(word) >= min_length
        and (max_length is None or len(word) <= max_length)
    ]

def get_timeout(word: str):
    """Calculates timeout based on word length."""
    base_time = 40  # Minimum time for short words
    extra_time_per_letter = 5  # Additional seconds per letter after 6 letters
    return min(120, base_time + max(0, (len(word) - 6) * extra_time_per_letter))  # Cap at 120 sec

COLOR_NAMES = {
    "R": "Red",
    "G": "Green",
    "B": "Blue",
    "Y": "Yellow",
    "W": "Wild",
}

COLOR_EMOJIS = {
    "R": "🔴",
    "G": "🟢",
    "B": "🔵",
    "Y": "🟡",
    "W": "🌈",
}

COLOR_WORDS = {
    "RED": "R",
    "GREEN": "G",
    "BLUE": "B",
    "YELLOW": "Y",
}

ACTION_ALIASES = {
    "S": "SKIP",
    "SKIP": "SKIP",
    "REV": "REVERSE",
    "REVERSE": "REVERSE",
    "+2": "DRAW2",
    "D2": "DRAW2",
    "DRAW2": "DRAW2",
    "DRAWTWO": "DRAW2",
    "DRAW_TWO": "DRAW2",
}

VALUE_LABELS = {
    "SKIP": "Skip",
    "REVERSE": "Reverse",
    "DRAW2": "+2",
    "WILD": "Wild",
    "WILD4": "+4",
}

VALUE_SORT = {
    "0": 0,
    "1": 1,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "SKIP": 10,
    "REVERSE": 11,
    "DRAW2": 12,
    "WILD": 13,
    "WILD4": 14,
}

@dataclass(frozen=True)
class UnoCard:
    color: str
    value: str

    @property
    def is_wild(self) -> bool:
        return self.color == "W"

    @property
    def is_draw_two(self) -> bool:
        return self.value == "DRAW2"

    @property
    def is_wild_draw_four(self) -> bool:
        return self.value == "WILD4"

    def short(self) -> str:
        emoji = COLOR_EMOJIS.get(self.color, "")
        label = VALUE_LABELS.get(self.value, self.value)
        if self.color == "W":
            return f"{emoji}{label}"
        return f"{emoji}{label}"

    def long(self) -> str:
        if self.color == "W":
            return VALUE_LABELS.get(self.value, self.value)
        return f"{COLOR_NAMES[self.color]} {VALUE_LABELS.get(self.value, self.value)}"


def build_deck() -> List[UnoCard]:
    deck: List[UnoCard] = []
    for color in ["R", "G", "B", "Y"]:
        deck.append(UnoCard(color, "0"))
        for value in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            deck.append(UnoCard(color, value))
            deck.append(UnoCard(color, value))
        for action in ["SKIP", "REVERSE", "DRAW2"]:
            deck.append(UnoCard(color, action))
            deck.append(UnoCard(color, action))
    for _ in range(4):
        deck.append(UnoCard("W", "WILD"))
        deck.append(UnoCard("W", "WILD4"))
    random.shuffle(deck)
    return deck

@dataclass
class ParsedMove:
    exact_color: Optional[str] = None
    exact_value: Optional[str] = None
    broad_color: Optional[str] = None
    broad_value: Optional[str] = None
    wild_value: Optional[str] = None
    chosen_color: Optional[str] = None


class UnoGame:
    def __init__(self, channel_id: int, host_id: int):
        self.channel_id = channel_id
        self.host_id = host_id
        self.players: List[int] = [host_id]
        self.hands: Dict[int, List[UnoCard]] = {}
        self.deck: List[UnoCard] = []
        self.discard: List[UnoCard] = []
        self.started = False
        self.current_index = 0
        self.direction = 1
        self.current_color: Optional[str] = None
        self.pending_draw_amount = 0
        self.pending_draw_type: Optional[str] = None
        self.last_action = "Game created. Waiting for players."
        self.table_message_id: Optional[int] = None
        self.next_cpu_number = 1

    def add_player(self, user_id: int) -> None:
        if self.started:
            raise ValueError("This game has already started.")
        if user_id in self.players:
            raise ValueError("You are already in this game.")
        if len(self.players) >= 10:
            raise ValueError("Uno supports up to 10 players.")
        self.players.append(user_id)

    def remove_player(self, user_id: int) -> None:
        if self.started:
            raise ValueError("You cannot leave after the game has started.")
        if user_id not in self.players:
            raise ValueError("You are not in this game.")
        self.players.remove(user_id)
        if self.host_id == user_id and self.players:
            self.host_id = self.players[0]
    
    def is_cpu(self, player_id: int) -> bool:
        return player_id < 0

    def player_display(self, player_id: int) -> str:
        if self.is_cpu(player_id):
            return f"CPU {abs(player_id)}"
        return f"<@{player_id}>"

    def add_cpu(self) -> int:
        if self.started:
            raise ValueError("You cannot add a CPU after the game has started.")
        if len(self.players) >= 10:
            raise ValueError("Uno supports up to 10 players total.")

        cpu_id = -self.next_cpu_number
        self.next_cpu_number += 1
        self.players.append(cpu_id)
        self.last_action = f"{self.player_display(cpu_id)} joined the game."
        return cpu_id

    def remove_cpu(self) -> int:
        if self.started:
            raise ValueError("You cannot remove a CPU after the game has started.")

        cpu_players = [pid for pid in self.players if self.is_cpu(pid)]

        if not cpu_players:
            raise ValueError("There are no CPU players to remove.")

        cpu_id = cpu_players[-1]
        self.players.remove(cpu_id)
        self.last_action = f"{self.player_display(cpu_id)} left the lobby."
        return cpu_id

    def choose_cpu_card(self, player_id: int) -> Optional[UnoCard]:
        legal = self.legal_cards(player_id)

        if not legal:
            return None

        def cpu_priority(card: UnoCard):
            # Basic idiot-brain CPU:
            # 1. Prefer non-wilds.
            # 2. Prefer action cards before numbers.
            # 3. Use wilds last.
            is_wild = 1 if card.color == "W" else 0
            action_priority = {
                "DRAW2": 0,
                "SKIP": 1,
                "REVERSE": 2,
                "9": 3,
                "8": 4,
                "7": 5,
                "6": 6,
                "5": 7,
                "4": 8,
                "3": 9,
                "2": 10,
                "1": 11,
                "0": 12,
                "WILD": 13,
                "WILD4": 14,
            }
            return (is_wild, action_priority.get(card.value, 99), card.color)

        legal.sort(key=cpu_priority)
        return legal[0]

    def play_cpu_turn(self) -> Tuple[bool, str]:
        player_id = self.current_player_id

        if not self.is_cpu(player_id):
            raise ValueError("It is not a CPU's turn.")

        cpu_name = self.player_display(player_id)
        card = self.choose_cpu_card(player_id)

        if card:
            chosen_color = None

            if card.color == "W":
                chosen_color = self.choose_default_wild_color(player_id)

            won, message = self.play_card(player_id, card, chosen_color)
            return won, message

        won, private_msg = self.draw_until_playable(player_id)
        self.last_action = f"{cpu_name} drew until playable. {self.last_action}"
        return won, private_msg

    def start(self) -> None:
        if self.started:
            raise ValueError("This game has already started.")
        if len(self.players) < 2:
            raise ValueError("You need at least 2 players to start Uno.")

        self.deck = build_deck()
        self.hands = {pid: [] for pid in self.players}

        for _ in range(7):
            for pid in self.players:
                self.hands[pid].append(self._draw_one())

        starter_index = next(
            (i for i, card in enumerate(self.deck) if card.color != "W" and card.value.isdigit()),
            None,
        )

        if starter_index is None:
            raise ValueError("Could not find a valid starter card. Try again.")

        starter = self.deck.pop(starter_index)
        self.discard.append(starter)
        self.current_color = starter.color
        self.started = True
        self.current_index = 0
        self.direction = 1
        self.last_action = f"The starting card is {starter.short()}."

    @property
    def current_player_id(self) -> int:
        return self.players[self.current_index]

    @property
    def top_card(self) -> UnoCard:
        return self.discard[-1]

    def next_index_from(self, index: int, steps: int = 1) -> int:
        return (index + self.direction * steps) % len(self.players)

    def _draw_one(self) -> UnoCard:
        if not self.deck:
            self._reshuffle_discard_into_deck()
        if not self.deck:
            raise ValueError("No cards are available to draw.")
        return self.deck.pop()

    def _reshuffle_discard_into_deck(self) -> None:
        if len(self.discard) <= 1:
            return

        top = self.discard[-1]
        rest = self.discard[:-1]
        random.shuffle(rest)
        self.deck = rest
        self.discard = [top]

    def sort_hand(self, player_id: int) -> None:
        color_order = {"R": 0, "G": 1, "B": 2, "Y": 3, "W": 4}
        self.hands[player_id].sort(
            key=lambda c: (color_order.get(c.color, 9), VALUE_SORT.get(c.value, 99))
        )

    def draw_cards(self, player_id: int, amount: int) -> List[UnoCard]:
        drawn = []
        for _ in range(amount):
            drawn.append(self._draw_one())
        self.hands[player_id].extend(drawn)
        self.sort_hand(player_id)
        return drawn

    def is_legal(self, card: UnoCard) -> bool:
        if self.pending_draw_amount > 0:
            return card.value == "DRAW2"

        if card.color == "W":
            return True

        return card.color == self.current_color or card.value == self.top_card.value

    def legal_cards(self, player_id: int) -> List[UnoCard]:
        return [card for card in self.hands[player_id] if self.is_legal(card)]

    def choose_default_wild_color(self, player_id: int) -> str:
        counts = {"R": 0, "G": 0, "B": 0, "Y": 0}
        for card in self.hands[player_id]:
            if card.color in counts:
                counts[card.color] += 1
        return max(counts, key=counts.get)

    def find_card(self, player_id: int, parsed: ParsedMove) -> Tuple[Optional[UnoCard], Optional[str]]:
        hand = self.hands[player_id]
        legal = self.legal_cards(player_id)

        if parsed.wild_value:
            candidates = [card for card in legal if card.value == parsed.wild_value]

        elif parsed.exact_color and parsed.exact_value:
            owned = [
                card for card in hand
                if card.color == parsed.exact_color and card.value == parsed.exact_value
            ]

            if not owned:
                return None, "You do not have that card."

            candidates = [card for card in owned if self.is_legal(card)]

        elif parsed.broad_color:
            candidates = [card for card in legal if card.color == parsed.broad_color]

        elif parsed.broad_value:
            candidates = [card for card in legal if card.value == parsed.broad_value]

        else:
            return None, "I could not understand that card notation."

        if not candidates:
            return None, "That move is not legal right now."

        candidates.sort(key=lambda c: (VALUE_SORT.get(c.value, 99), c.color))
        return candidates[0], None

    def play_card(self, player_id: int, card: UnoCard, chosen_color: Optional[str]) -> Tuple[bool, str]:
        if player_id != self.current_player_id:
            raise ValueError("It is not your turn.")
        if card not in self.hands[player_id]:
            raise ValueError("You do not have that card.")
        if not self.is_legal(card):
            raise ValueError("That card is not legal right now.")

        player_name = self.player_display(player_id)

        self.hands[player_id].remove(card)
        self.discard.append(card)

        if card.color == "W":
            if chosen_color not in {"R", "G", "B", "Y"}:
                chosen_color = self.choose_default_wild_color(player_id)
            self.current_color = chosen_color
        else:
            self.current_color = card.color

        if not self.hands[player_id]:
            self.last_action = f"{player_name} played {card.short()} and won the game!"
            return True, self.last_action

        uno_note = " UNO!" if len(self.hands[player_id]) == 1 else ""
        play_index = self.current_index

        if card.value == "DRAW2":
            self.pending_draw_amount += 2
            self.pending_draw_type = "DRAW2"
            self.current_index = self.next_index_from(play_index, 1)
            self.last_action = (
                f"{player_name} played {card.short()}.{uno_note} "
                f"Draw stack is now +{self.pending_draw_amount}."
            )

        elif card.value == "WILD4":
            victim_index = self.next_index_from(play_index, 1)
            victim_id = self.players[victim_index]
            victim_name = self.player_display(victim_id)

            self.draw_cards(victim_id, 4)
            self.current_index = self.next_index_from(play_index, 2)
            self.last_action = (
                f"{player_name} played {card.short()} and chose {COLOR_NAMES[self.current_color]}.{uno_note} "
                f"{victim_name} drew 4 and was skipped."
            )

        elif card.value == "SKIP":
            skipped_id = self.players[self.next_index_from(play_index, 1)]
            skipped_name = self.player_display(skipped_id)

            self.current_index = self.next_index_from(play_index, 2)
            self.last_action = f"{player_name} played {card.short()}.{uno_note} {skipped_name} was skipped."

        elif card.value == "REVERSE":
            self.direction *= -1

            if len(self.players) == 2:
                self.current_index = play_index
                self.last_action = (
                    f"{player_name} played {card.short()}.{uno_note} "
                    f"Reverse acts like a skip with 2 players."
                )
            else:
                self.current_index = self.next_index_from(play_index, 1)
                self.last_action = f"{player_name} played {card.short()}.{uno_note} Turn order reversed."

        else:
            self.current_index = self.next_index_from(play_index, 1)

            if card.color == "W":
                self.last_action = (
                    f"{player_name} played {card.short()} and chose "
                    f"{COLOR_NAMES[self.current_color]}.{uno_note}"
                )
            else:
                self.last_action = f"{player_name} played {card.short()}.{uno_note}"

        return False, self.last_action

    def take_draw_action(self, player_id: int) -> str:
        if player_id != self.current_player_id:
            raise ValueError("It is not your turn.")

        player_name = self.player_display(player_id)

        if self.pending_draw_amount > 0:
            amount = self.pending_draw_amount
            self.draw_cards(player_id, amount)
            self.pending_draw_amount = 0
            self.pending_draw_type = None
            self.current_index = self.next_index_from(self.current_index, 1)
            self.last_action = f"{player_name} drew {amount} cards from the +2 stack and was skipped."
            return self.last_action

        drawn = self.draw_cards(player_id, 1)[0]
        self.current_index = self.next_index_from(self.current_index, 1)
        self.last_action = f"{player_name} drew 1 card and passed."
        return f"You drew {drawn.short()}. Turn passed."

    def draw_until_playable(self, player_id: int) -> Tuple[bool, str]:
        if player_id != self.current_player_id:
            raise ValueError("It is not your turn.")

        if self.pending_draw_amount > 0:
            amount = self.pending_draw_amount
            self.draw_cards(player_id, amount)
            self.pending_draw_amount = 0
            self.pending_draw_type = None
            self.current_index = self.next_index_from(self.current_index, 1)
            player_name = self.player_display(player_id)
            self.last_action = f"{player_name} drew {amount} cards from the +2 stack and was skipped."
            return False, f"You drew {amount} cards from the +2 stack. Your turn was skipped."

        drawn_cards: List[UnoCard] = []
        playable_card: Optional[UnoCard] = None

        while playable_card is None:
            drawn = self.draw_cards(player_id, 1)[0]
            drawn_cards.append(drawn)

            if self.is_legal(drawn):
                playable_card = drawn

        chosen_color = None
        if playable_card.color == "W":
            chosen_color = self.choose_default_wild_color(player_id)

        won, _message = self.play_card(player_id, playable_card, chosen_color)

        if len(drawn_cards) == 1:
            private_msg = f"You drew {playable_card.short()} and automatically played it."
        else:
            drawn_text = ", ".join(card.short() for card in drawn_cards)
            private_msg = (
                f"You drew {len(drawn_cards)} cards until you found a playable card: {drawn_text}\n"
                f"Automatically played {playable_card.short()}."
            )

        return won, private_msg
    
    def hand_text(self, player_id: int) -> str:
        hand = self.hands.get(player_id, [])

        if not hand:
            return "Your hand is empty."

        groups = {"R": [], "G": [], "B": [], "Y": [], "W": []}

        for card in hand:
            groups[card.color].append(card.short())

        lines = []

        for color in ["R", "G", "B", "Y", "W"]:
            if groups[color]:
                lines.append(f"**{COLOR_NAMES[color]}:** " + ", ".join(groups[color]))

        lines.append("")
        lines.append("Examples: `G1`, `R7`, `B+2`, `YS`, `GREV`, `W:G`, `W4:B`, `G`, `1`, `+2`, `S`, `REV`, `DRAW`.")
        lines.append("Note: `R` means Red. Use `REV` for Reverse.")

        return "\n".join(lines)

    def status_embed(self) -> discord.Embed:
        embed = discord.Embed(title="Uno", color=discord.Color.blurple())

        if not self.started:
            names = "\n".join(self.player_display(pid) for pid in self.players)
            embed.description = self.last_action
            embed.add_field(name="Players", value=names or "None", inline=False)
            return embed

        direction = "clockwise" if self.direction == 1 else "counter-clockwise"
        current_color = COLOR_NAMES.get(self.current_color or "", "Unknown")

        embed.description = self.last_action
        embed.add_field(
            name="Top Card",
            value=f"{self.top_card.short()} | Current color: **{current_color}**",
            inline=False,
        )
        embed.add_field(name="Turn", value=self.player_display(self.current_player_id), inline=True)
        embed.add_field(name="Direction", value=direction, inline=True)

        if self.pending_draw_amount > 0:
            embed.add_field(
                name="Draw Stack",
                value=f"+{self.pending_draw_amount} — play a +2 or draw.",
                inline=False,
            )

        player_lines = []

        for idx, pid in enumerate(self.players):
            marker = "➡️ " if idx == self.current_index else ""
            count = len(self.hands.get(pid, []))
            plural = "card" if count == 1 else "cards"
            player_lines.append(f"{marker}{self.player_display(pid)} — {count} {plural}")

        embed.add_field(name="Players", value="\n".join(player_lines), inline=False)
        return embed


def normalize_notation(raw: str) -> str:
    text = raw.upper().strip()
    text = text.replace(" ", "")
    text = text.replace("-", "")
    text = text.replace("_", "")
    text = text.replace("WILDDRAWFOUR", "W4")
    text = text.replace("WILDDRAW4", "W4")
    text = text.replace("DRAWFOUR", "W4")
    text = text.replace("DRAW4", "W4")
    text = text.replace("WILD4", "W4")
    text = text.replace("+FOUR", "+4")
    return text


def parse_color_token(token: str) -> Optional[str]:
    if token in {"R", "G", "B", "Y"}:
        return token
    return COLOR_WORDS.get(token)


def parse_value_token(token: str) -> Optional[str]:
    if token.isdigit() and token in {str(i) for i in range(10)}:
        return token
    return ACTION_ALIASES.get(token)


def parse_move(raw: str) -> ParsedMove:
    text = normalize_notation(raw)

    if text in {"DRAW", "D", "PASS"}:
        return ParsedMove()

    colon_match = re.fullmatch(r"(W|WC|WILD|W4|\+4):?([RGBY]|RED|GREEN|BLUE|YELLOW)", text)
    if colon_match:
        wild_part, color_part = colon_match.groups()
        chosen = parse_color_token(color_part)
        wild_value = "WILD4" if wild_part in {"W4", "+4"} else "WILD"
        return ParsedMove(wild_value=wild_value, chosen_color=chosen)

    word_wild_match = re.fullmatch(r"(WILD|WC|W)(RED|GREEN|BLUE|YELLOW)", text)
    if word_wild_match:
        chosen = parse_color_token(word_wild_match.group(2))
        return ParsedMove(wild_value="WILD", chosen_color=chosen)

    compact_wild_match = re.fullmatch(r"(W4|\+4|WILD4)([RGBY])", text)
    if compact_wild_match:
        chosen = parse_color_token(compact_wild_match.group(2))
        return ParsedMove(wild_value="WILD4", chosen_color=chosen)

    if text in {"W", "WC", "WILD"}:
        return ParsedMove(wild_value="WILD")

    if text in {"W4", "+4"}:
        return ParsedMove(wild_value="WILD4")

    color = parse_color_token(text)
    if color:
        return ParsedMove(broad_color=color)

    value = parse_value_token(text)
    if value:
        return ParsedMove(broad_value=value)

    for color_word, color_letter in sorted(COLOR_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if text.startswith(color_word):
            value_part = text[len(color_word):]
            value = parse_value_token(value_part)

            if value:
                return ParsedMove(exact_color=color_letter, exact_value=value)

    if text and text[0] in {"R", "G", "B", "Y"}:
        color_letter = text[0]
        value_part = text[1:]
        value = parse_value_token(value_part)

        if value:
            return ParsedMove(exact_color=color_letter, exact_value=value)

    return ParsedMove()

class UnoPlayModal(discord.ui.Modal):
    def __init__(self, cog, channel_id: int):
        super().__init__(title="Play Uno Card")
        self.cog = cog
        self.channel_id = channel_id
        self.notation_input = discord.ui.TextInput(
            label="Card notation",
            placeholder="G1, B+2, YS, GREV, W:G, W4:B, G, 1, +2",
            max_length=20,
            required=True,
        )
        self.add_item(self.notation_input)

    async def on_submit(self, interaction: discord.Interaction):
        game = self.cog.uno_games.get(self.channel_id)

        if not game:
            await interaction.response.send_message("That Uno game no longer exists.", ephemeral=True)
            return

        if not game.started:
            await interaction.response.send_message("The game has not started yet.", ephemeral=True)
            return

        if interaction.user.id not in game.players:
            await interaction.response.send_message("You are not in this Uno game.", ephemeral=True)
            return

        if interaction.user.id != game.current_player_id:
            await interaction.response.send_message("It is not your turn.", ephemeral=True)
            return

        notation = str(self.notation_input.value)
        parsed = parse_move(notation)
        card, error = game.find_card(interaction.user.id, parsed)

        if error:
            await interaction.response.send_message(error, ephemeral=True)
            return

        chosen_color = parsed.chosen_color

        if card.color == "W" and chosen_color is None:
            chosen_color = game.choose_default_wild_color(interaction.user.id)

        won, _message = game.play_card(interaction.user.id, card, chosen_color)

        if won:
            await interaction.response.send_message(f"You played {card.short()} and won!", ephemeral=True)
            await self.cog._close_uno_table(game)
            self.cog.uno_games.pop(self.channel_id, None)
            return

        await interaction.response.send_message(
            f"Played {card.short()}.\n\nUpdated hand:\n{game.hand_text(interaction.user.id)}",
            ephemeral=True,
        )
        await self.cog._refresh_uno_table(game)
        await self.cog._process_cpu_turns(game)


class UnoLobbyView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    def _game(self, interaction: discord.Interaction) -> Optional[UnoGame]:
        channel_id = interaction.channel.id if interaction.channel else None
        if channel_id is None:
            return None
        return self.cog.uno_games.get(channel_id)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno lobby no longer exists.", ephemeral=True)
            return

        try:
            game.add_player(interaction.user.id)
            game.last_action = f"{interaction.user.mention} joined the game."
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog._refresh_uno_table(game)

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.secondary)
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno lobby no longer exists.", ephemeral=True)
            return

        try:
            game.remove_player(interaction.user.id)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        if not game.players:
            self.cog.uno_games.pop(game.channel_id, None)
            await interaction.response.edit_message(content="Uno lobby closed.", embed=None, view=None)
            return

        game.last_action = f"{interaction.user.mention} left the lobby."
        await interaction.response.defer()
        await self.cog._refresh_uno_table(game)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno lobby no longer exists.", ephemeral=True)
            return

        if not self.cog._is_uno_host_or_mod_user(interaction.user, game):
            await interaction.response.send_message("Only the host or a server manager can start this game.", ephemeral=True)
            return

        try:
            game.start()
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog._refresh_uno_table(game)
        await self.cog._process_cpu_turns(game)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno lobby no longer exists.", ephemeral=True)
            return

        if not self.cog._is_uno_host_or_mod_user(interaction.user, game):
            await interaction.response.send_message("Only the host or a server manager can cancel this game.", ephemeral=True)
            return

        self.cog.uno_games.pop(game.channel_id, None)
        await interaction.response.edit_message(content="Uno lobby cancelled.", embed=None, view=None)

    @discord.ui.button(label="Add CPU", style=discord.ButtonStyle.secondary, row=1)
    async def add_cpu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno lobby no longer exists.", ephemeral=True)
            return

        if not self.cog._is_uno_host_or_mod_user(interaction.user, game):
            await interaction.response.send_message("Only the host or a server manager can add CPUs.", ephemeral=True)
            return

        try:
            game.add_cpu()
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog._refresh_uno_table(game)

    @discord.ui.button(label="Remove CPU", style=discord.ButtonStyle.secondary, row=1)
    async def remove_cpu_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno lobby no longer exists.", ephemeral=True)
            return

        if not self.cog._is_uno_host_or_mod_user(interaction.user, game):
            await interaction.response.send_message("Only the host or a server manager can remove CPUs.", ephemeral=True)
            return

        try:
            game.remove_cpu()
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.defer()
        await self.cog._refresh_uno_table(game)

class UnoGameView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    def _game(self, interaction: discord.Interaction) -> Optional[UnoGame]:
        channel_id = interaction.channel.id if interaction.channel else None
        if channel_id is None:
            return None
        return self.cog.uno_games.get(channel_id)

    @discord.ui.button(label="View Hand", style=discord.ButtonStyle.secondary)
    async def view_hand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno game no longer exists.", ephemeral=True)
            return

        if interaction.user.id not in game.players:
            await interaction.response.send_message("You are not in this Uno game.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Your Uno hand:\n" + game.hand_text(interaction.user.id),
            ephemeral=True,
        )

    @discord.ui.button(label="Play Card", style=discord.ButtonStyle.primary)
    async def play_card_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno game no longer exists.", ephemeral=True)
            return

        if interaction.user.id not in game.players:
            await interaction.response.send_message("You are not in this Uno game.", ephemeral=True)
            return

        if interaction.user.id != game.current_player_id:
            await interaction.response.send_message("It is not your turn.", ephemeral=True)
            return

        await interaction.response.send_modal(UnoPlayModal(self.cog, game.channel_id))

    @discord.ui.button(label="Draw", style=discord.ButtonStyle.success)
    async def draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno game no longer exists.", ephemeral=True)
            return

        if interaction.user.id not in game.players:
            await interaction.response.send_message("You are not in this Uno game.", ephemeral=True)
            return

        if interaction.user.id != game.current_player_id:
            await interaction.response.send_message("It is not your turn.", ephemeral=True)
            return

        try:
            won, private_msg = game.draw_until_playable(interaction.user.id)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        if won:
            await interaction.response.send_message(private_msg, ephemeral=True)
            await self.cog._close_uno_table(game)
            self.cog.uno_games.pop(game.channel_id, None)
            return

        await interaction.response.send_message(
            private_msg + "\n\nUpdated hand:\n" + game.hand_text(interaction.user.id),
            ephemeral=True,
        )
        await self.cog._refresh_uno_table(game)
        await self.cog._process_cpu_turns(game)

    @discord.ui.button(label="End", style=discord.ButtonStyle.danger)
    async def end_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self._game(interaction)

        if not game:
            await interaction.response.send_message("That Uno game no longer exists.", ephemeral=True)
            return

        if not self.cog._is_uno_host_or_mod_user(interaction.user, game):
            await interaction.response.send_message("Only the host or a server manager can end this game.", ephemeral=True)
            return

        self.cog.uno_games.pop(game.channel_id, None)
        await interaction.response.edit_message(content="Uno game ended.", embed=None, view=None)

class SpideyGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.uno_games = {}
        self.config = Config.get_conf(self, identifier=13904817238971)
        self.config.register_member(
            difficulty="medium",
            novice_wins= 0, 
            easy_wins=0,
            medium_wins=0,
            hard_wins=0,
            expert_wins=0,
            impossible_wins=0,
            phrase_toggle = False
        )
        self.config.register_guild(difficulty="medium")
    
    @commands.group(name="spideygameset", aliases=["sgs"])
    async def spideygameset(self, ctx: commands.Context):
        """Command to change the game settings."""
        await ctx.send("Currently this command has no settings.")
    
    @commands.group(name="anagram", invoke_without_command=True)
    async def anagram(self, ctx: commands.Context):
        """Anagram game command group."""
        subcommands = ["start", "hint", "leaderboard", "settings", "stop"]
        command_list = "\n".join([f"- **[p]anagram {cmd}**" for cmd in subcommands])

        await ctx.send(f"**Anagram Commands:**\n{command_list}\n\nUse `[p]anagram start` to begin a game!")

    @anagram.command(name="start", aliases=["s"])
    async def anagram_start(self, ctx: commands.Context):
        """Decode a random english word."""
        if ctx.channel.id in self.active_games:
            await ctx.send("A game is already running in this channel. Please wait for the game to end before starting a new one.")
            return
        
        phrase_setting = await self.config.member(ctx.author).phrase_toggle()
        if phrase_setting:
            player_difficulty = "medium"
            phrase_list = get_idioms()
            base = random.choice(phrase_list)
            scrambled = await self.scramble_phrase(base)
        else:
            player_difficulty = await self.config.member(ctx.author).difficulty()
            word_list = get_filtered_words(player_difficulty)
            base = random.choice(word_list)
            scrambled = await self.scrambler(base)

        self.active_games[ctx.channel.id] = {"word": base, "hint_level": 0}
        

        await ctx.send("The game is about to begin . . .")
        await asyncio.sleep(1)
        timeout_duration = get_timeout(base)
        game_message = await ctx.send(f"🔠 **Unscramble this {'phrase' if phrase_setting else 'word'}:** `{scrambled}`\n⏳ **Time remaining: {timeout_duration} seconds**\n{'💡 Type `[p]anagram hint` for a clue!' if not phrase_setting else ''}")

        async def countdown_timer(time_amount: int):
            """Updates the message every 10 seconds."""
            remaining_times = list(range(time_amount - 10, 0, -10))
            for remaining in remaining_times:
                await asyncio.sleep(10)
                if ctx.channel.id not in self.active_games:
                    return
                await game_message.edit(content=f"🔠 **Unscramble this {'phrase' if phrase_setting else 'word'}:** `{scrambled}`\n⏳ **Time remaining: {remaining} seconds**\n{'💡 Type `[p]anagram hint` for a clue!' if not phrase_setting else ''}")

        self.bot.loop.create_task(countdown_timer(timeout_duration))
        def check(message): 
            normalized_guess = message.content.lower().replace("’", "'")
            normalized_answer = base.lower().replace("’", "'")
            return message.channel == ctx.channel and normalized_guess == normalized_answer
        try:
            while ctx.channel.id in self.active_games:
                message = await self.bot.wait_for('message', timeout=timeout_duration, check=check)
                if ctx.channel.id not in self.active_games:
                    return
                if message.content.lower() == base:
                    difficulty_field = f"{player_difficulty}_wins"
                    current_wins = await self.config.member(message.author).get_raw(difficulty_field)
                    await self.config.member(message.author).set_raw(difficulty_field, value=current_wins + 1)
                    await ctx.send(f"🎉 {message.author.mention} won! The {'phrase' if phrase_setting else 'word'} was `{base}`!")
                    break
        except asyncio.TimeoutError:
            if ctx.channel.id in self.active_games:
                await ctx.send(f"⏳ Time's up! Nobody guessed the word. The correct {'phrase' if phrase_setting else 'word'} was `{base}`! Try again!")
        
        if ctx.channel.id not in self.active_games:
            return
        else:
            del self.active_games[ctx.channel.id]

    async def scrambler(self, word: str):
        """Scrambles words."""
        stripped_word = list(word.strip())
        while True:
            shuffled_word = stripped_word[:]
            random.shuffle(shuffled_word)
            anagram = "".join(shuffled_word)
            if anagram != word:
                    return anagram
    
    async def scramble_phrase(self, phrase: str):
        """Scrambles each word in a phrase while keeping spaces in tact."""
        phrase_words = phrase.split(" ")
        scrambled_words = ["".join(random.sample(word, len(word))) for word in phrase_words]
        return " ".join(scrambled_words)
    
    @anagram.command(name="hint")
    async def anagram_hint(self, ctx: commands.Context):
        """Gives the first letter as a hint."""
        if ctx.channel.id not in self.active_games:
            await ctx.send("❌ No active game in this channel!")
            return
        
        game = self.active_games[ctx.channel.id]
        word = game["word"]
        if " " in word:
            await ctx.send("Hints are currently not setup for phrases. Sorry.")
            return
        
        hint_level = game["hint_level"]
        if hint_level == 0:
            hint = f"💡First hint: The word starts with `{word[0].upper()}`"
        elif hint_level == 1:
            half_revealed = list(word[: len(word) // 2])
            random.shuffle(half_revealed)
            hint = f"💡 Second hint: Here is the first half of the word (shuffled): `{''.join(half_revealed)}`"
        elif hint_level == 2:
            revealed = [letter if i % 2 == 0 else "_" for i, letter in enumerate(word)]
            hint = f"💡 Final hint: `{''.join(revealed)}`"
        else:
            await ctx.send("❌ No more hints available!")
            return
        
        game["hint_level"] += 1
        await ctx.send(hint)
    
    @anagram.command(name="stop", aliases=["st"])
    async def anagram_stop(self, ctx:commands.Context, game_channel: discord.TextChannel = None):
        """Stops an existing game."""
        game_channel = game_channel or ctx.channel
        channel_id = game_channel.id
        if channel_id not in self.active_games:
            await ctx.send(f"❌ No active game found in {game_channel.mention}.")
            return
        answer = self.active_games[channel_id]["word"]
        del self.active_games[channel_id]
        
        channel_message = f" in {game_channel.mention}" if game_channel != ctx.channel else ""
        await ctx.send(f"Game successfully stopped{channel_message}! The answer was {answer}!")

    
    @anagram.command(name="leaderboard", aliases=["lb"])
    async def anagram_leaderboard(self, ctx: commands.Context):
        """Shows the multi-column leaderboard for all difficulties."""
        
        all_members = await self.config.all_members(ctx.guild)

        if not all_members:
            await ctx.send("No one has won an anagram game yet!")
            return

        # Sort players by total wins (sum of all difficulty wins)
        sorted_members = sorted(
            all_members.items(),
            key=lambda x: sum(v for v in x[1].values() if isinstance(v, int)),  # Sum of all difficulty wins
            reverse=True
        )

        # Generate leaderboard output
        leaderboard_lines = [
            f"🏆 **Anagram Leaderboard** 🏆\n\n"
            f"```"
            f"{'Player':<15} {'Nov':<4} {'Ez':<4} {'Med':<4} {'Hard':<4} {'Exp':<4} {'Imp':<4} {'Total':<5}\n"
            f"{'-'*50}"
        ]

        for user_id, data in sorted_members[:10]:  # Top 10 players
            total_wins = sum(v for v in data.values() if isinstance(v, int))  # Sum of all difficulty wins
            leaderboard_lines.append(
                f"{ctx.guild.get_member(user_id).display_name:<15} "
                f"{data.get('novice_wins', 0):<4} "
                f"{data.get('easy_wins', 0):<4} "
                f"{data.get('medium_wins', 0):<4} "
                f"{data.get('hard_wins', 0):<4} "
                f"{data.get('expert_wins', 0):<4} "
                f"{data.get('impossible_wins', 0):<4} "
                f"{total_wins:<5}"
            )

        leaderboard_lines.append("```")  # Close code block for formatting
        await ctx.send("\n".join(leaderboard_lines))

    
    @anagram.group(name="settings", invoke_without_command=True)
    async def anagram_setting(self, ctx:commands.Context):
        """Manage your personal anagram game settings."""
        await ctx.send("Use `[p]anagram setting difficulty <novice/easy/medium/hard/expert/impossible>` to change your difficulty.")
    
    @anagram_setting.command(name="difficulty")
    async def anagram_setting_difficulty(self, ctx:commands.Context, difficulty: str):
        """Set your personal anagram difficulty."""
        valid_difficulties = ["novice", "easy", "medium", "hard", "expert", "impossible"]

        if difficulty.lower() not in valid_difficulties:
            await ctx.send(f"❌ Invalid difficulty! Choose from: {', '.join(valid_difficulties)}.")
            return
        
        await self.config.member(ctx.author).difficulty.set(difficulty.lower())
        await ctx.send(f"✅ {ctx.author.mention}, your anagram difficulty has been set to **{difficulty}**!")
    
    @anagram_setting.command(name="phrases")
    async def anagram_setting_phrases(self, ctx:commands.Context):
        """If you run this command, the presumption is you are toggling phrases to the opposite of whatever you have it."""
        toggle_setting = await self.config.member(ctx.author).phrase_toggle()

        if toggle_setting == True:
            toggle_setting = False
        else:
            toggle_setting = True
        
        await self.config.member(ctx.author).phrase_toggle.set(toggle_setting)

        await ctx.send(f"You have successfully toggled phrases `{'on' if toggle_setting else 'off'}`.")

    async def _send_uno_hand(self, ctx: commands.Context, content: str):
        """Fallback for prefix commands. Button users get ephemeral hand messages instead."""
        try:
            await ctx.author.send(content)
            await ctx.tick()
        except discord.Forbidden:
            await ctx.send(
                f"{ctx.author.mention}, I couldn't DM your hand. Use the **View Hand** button on the Uno table instead."
            )

    def _get_uno_game(self, channel_id: int) -> UnoGame:
        game = self.uno_games.get(channel_id)

        if not game:
            raise ValueError("There is no Uno game in this channel. Start one with `[p]uno create`.")

        return game

    def _is_uno_host_or_mod_user(self, user: discord.Member, game: UnoGame) -> bool:
        perms = getattr(user, "guild_permissions", None)
        return user.id == game.host_id or bool(perms and perms.manage_guild)

    def _is_uno_host_or_mod(self, ctx: commands.Context, game: UnoGame) -> bool:
        return self._is_uno_host_or_mod_user(ctx.author, game)

    def _uno_view_for(self, game: UnoGame) -> discord.ui.View:
        return UnoGameView(self) if game.started else UnoLobbyView(self)

    async def _refresh_uno_table(self, game: UnoGame):
        """Edits the original Uno table message instead of spamming a new embed."""
        channel = self.bot.get_channel(game.channel_id)

        if channel is None or game.table_message_id is None:
            return False

        try:
            message = await channel.fetch_message(game.table_message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return False

        await message.edit(embed=game.status_embed(), view=self._uno_view_for(game))
        return True
    
    async def _process_cpu_turns(self, game: UnoGame):
        """Runs CPU turns until a human player is up, someone wins, or a safety cap is hit."""
        turns_processed = 0

        while game.channel_id in self.uno_games and game.started and game.is_cpu(game.current_player_id):
            if turns_processed >= 30:
                game.last_action = "CPU safety stop triggered. Something got weird, so I stopped auto-playing."
                await self._refresh_uno_table(game)
                return False

            try:
                won, _message = game.play_cpu_turn()
            except ValueError as e:
                game.last_action = f"CPU error: {e}"
                await self._refresh_uno_table(game)
                return False

            turns_processed += 1

            if won:
                await self._close_uno_table(game)
                self.uno_games.pop(game.channel_id, None)
                return True

            await self._refresh_uno_table(game)
            await asyncio.sleep(0.8)

        return False

    async def _close_uno_table(self, game: UnoGame):
        """Leaves the final game state visible but removes the buttons."""
        channel = self.bot.get_channel(game.channel_id)

        if channel is None or game.table_message_id is None:
            return False

        try:
            message = await channel.fetch_message(game.table_message_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return False

        await message.edit(embed=game.status_embed(), view=None)
        return True

    @commands.group(name="uno", invoke_without_command=True)
    async def uno(self, ctx: commands.Context):
        """Play Uno."""
        game = self.uno_games.get(ctx.channel.id)

        if not game:
            await ctx.send("No Uno game is running here. Use `[p]uno create` to start a lobby.")
            return

        refreshed = await self._refresh_uno_table(game)

        if refreshed:
            await ctx.send("Uno table refreshed.", delete_after=5)
        else:
            message = await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))
            game.table_message_id = message.id

    @uno.command(name="create", aliases=["c"])
    async def uno_create(self, ctx: commands.Context):
        """Create an Uno lobby in this channel."""
        if ctx.channel.id in self.uno_games:
            await ctx.send("There is already an Uno game in this channel.")
            return

        game = UnoGame(ctx.channel.id, ctx.author.id)
        self.uno_games[ctx.channel.id] = game
        message = await ctx.send(embed=game.status_embed(), view=UnoLobbyView(self))
        game.table_message_id = message.id

    @uno.command(name="join", aliases=["j"])
    async def uno_join(self, ctx: commands.Context):
        """Join the Uno lobby. The Join button is preferred."""
        try:
            game = self._get_uno_game(ctx.channel.id)
            game.add_player(ctx.author.id)
            game.last_action = f"{ctx.author.mention} joined the game."

            if not await self._refresh_uno_table(game):
                await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))

        except ValueError as e:
            await ctx.send(str(e))

    @uno.command(name="leave", aliases=["l"])
    async def uno_leave(self, ctx: commands.Context):
        """Leave an unstarted Uno lobby. The Leave button is preferred."""
        try:
            game = self._get_uno_game(ctx.channel.id)
            game.remove_player(ctx.author.id)

            if not game.players:
                await self._close_uno_table(game)
                del self.uno_games[ctx.channel.id]
                await ctx.send("Uno lobby closed.")
                return

            game.last_action = f"{ctx.author.mention} left the lobby."

            if not await self._refresh_uno_table(game):
                await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))

        except ValueError as e:
            await ctx.send(str(e))

    @uno.command(name="start", aliases=["s"])
    async def uno_start(self, ctx: commands.Context):
        """Start the Uno game. The Start button is preferred."""
        try:
            game = self._get_uno_game(ctx.channel.id)

            if not self._is_uno_host_or_mod(ctx, game):
                await ctx.send("Only the host or a server manager can start this game.")
                return

            game.start()

            if not await self._refresh_uno_table(game):
                message = await ctx.send(embed=game.status_embed(), view=UnoGameView(self))
                game.table_message_id = message.id

            await self._process_cpu_turns(game)

        except ValueError as e:
            await ctx.send(str(e))

    @uno.command(name="hand", aliases=["h"])
    async def uno_hand(self, ctx: commands.Context):
        """Privately show your hand. The View Hand button is preferred."""
        try:
            game = self._get_uno_game(ctx.channel.id)

            if not game.started:
                await ctx.send("The game has not started yet.")
                return

            if ctx.author.id not in game.players:
                await ctx.send("You are not in this Uno game.")
                return

            await self._send_uno_hand(ctx, "Your Uno hand:\n" + game.hand_text(ctx.author.id))

        except ValueError as e:
            await ctx.send(str(e))

    @uno.command(name="play", aliases=["p"])
    async def uno_play(self, ctx: commands.Context, *, notation: str):
        """
        Play a card by notation.

        Examples:
        G1, R7, B+2, YS, GREV, W:G, W4:B, G, 1, +2
        """
        try:
            game = self._get_uno_game(ctx.channel.id)

            if not game.started:
                await ctx.send("The game has not started yet.")
                return

            if ctx.author.id not in game.players:
                await ctx.send("You are not in this Uno game.")
                return

            if ctx.author.id != game.current_player_id:
                await ctx.send("It is not your turn.")
                return

            if normalize_notation(notation) in {"DRAW", "D", "PASS"}:
                won, private_msg = game.draw_until_playable(ctx.author.id)
                await self._send_uno_hand(
                    ctx,
                    private_msg + "\n\n" + game.hand_text(ctx.author.id),
                )

                if won:
                    await self._close_uno_table(game)
                    del self.uno_games[ctx.channel.id]
                    return

                if not await self._refresh_uno_table(game):
                    await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))
                await self._process_cpu_turns(game)
                return

            parsed = parse_move(notation)
            card, error = game.find_card(ctx.author.id, parsed)

            if error:
                await ctx.send(error)
                return

            chosen_color = parsed.chosen_color

            if card.color == "W" and chosen_color is None:
                chosen_color = game.choose_default_wild_color(ctx.author.id)

            won, _message = game.play_card(ctx.author.id, card, chosen_color)

            if won:
                await self._close_uno_table(game)
                del self.uno_games[ctx.channel.id]
                return

            await self._send_uno_hand(
                ctx,
                "Updated Uno hand:\n" + game.hand_text(ctx.author.id),
            )

            if not await self._refresh_uno_table(game):
                await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))
            await self._process_cpu_turns(game)
        except ValueError as e:
            await ctx.send(str(e))


    @uno.command(name="draw", aliases=["d", "pass"])
    async def uno_draw(self, ctx: commands.Context):
        """Draw until playable. If a +2 stack is pending, draw the full stack and lose your turn."""
        try:
            game = self._get_uno_game(ctx.channel.id)

            if not game.started:
                await ctx.send("The game has not started yet.")
                return

            if ctx.author.id not in game.players:
                await ctx.send("You are not in this Uno game.")
                return

            if ctx.author.id != game.current_player_id:
                await ctx.send("It is not your turn.")
                return

            won, private_msg = game.draw_until_playable(ctx.author.id)

            await self._send_uno_hand(
                ctx,
                private_msg + "\n\n" + game.hand_text(ctx.author.id),
            )

            if won:
                await self._close_uno_table(game)
                del self.uno_games[ctx.channel.id]
                return

            if not await self._refresh_uno_table(game):
                await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))

            await self._process_cpu_turns(game)

        except ValueError as e:
            await ctx.send(str(e))
        

    
    @uno.command(name="status", aliases=["table"])
    async def uno_status(self, ctx: commands.Context):
        """Show or refresh the current Uno table."""
        try:
            game = self._get_uno_game(ctx.channel.id)

            if await self._refresh_uno_table(game):
                await ctx.send("Uno table refreshed.", delete_after=5)
            else:
                message = await ctx.send(embed=game.status_embed(), view=self._uno_view_for(game))
                game.table_message_id = message.id

        except ValueError as e:
            await ctx.send(str(e))

    @uno.command(name="notation", aliases=["helpnotation"])
    async def uno_notation(self, ctx: commands.Context):
        """Show Uno notation help."""
        text = (
            "**Uno notation**\n"
            "Exact cards: `G1`, `R7`, `B+2`, `YS`, `GREV`\n"
            "Broad picks: `G` plays any legal Green, `1` plays any legal 1, `+2` plays any legal +2.\n"
            "Wilds: `W:G` plays Wild and chooses Green. `W4:B` plays Wild +4 and chooses Blue.\n"
            "Utility: use the **Draw Until Playable** button, `[p]uno draw`, or `[p]uno play DRAW`.\n"
            "Important: `R` means Red. Use `REV` for Reverse.\n"
            "House rules: +2s stack. +4s do not stack. +2 and +4 do not mix."
        )

        await ctx.send(text)

    @uno.command(name="end", aliases=["stop"])
    async def uno_end(self, ctx: commands.Context):
        """End the Uno game in this channel."""
        try:
            game = self._get_uno_game(ctx.channel.id)

            if not self._is_uno_host_or_mod(ctx, game):
                await ctx.send("Only the host or a server manager can end this game.")
                return

            await self._close_uno_table(game)
            del self.uno_games[ctx.channel.id]
            await ctx.send("Uno game ended.")

        except ValueError as e:
            await ctx.send(str(e))