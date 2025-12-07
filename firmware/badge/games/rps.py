import random
import hardware_setup as hardware_setup  # Create a display instance
from gui.core.ugui import Screen, ssd
from bdg.config import Config
from .winner_screen import WinScr  # needed to display the winner screen
from gui.widgets import Label, Button, CloseButton, RadioButtons
from gui.core.writer import CWriter
from gui.fonts import arial35, freesans20, font10 as font10
import gui.fonts.arial10 as arial10
from gui.core.colors import *


class RpsScreen(Screen):
    def __init__(self, conn):
        super().__init__()
        self.wri = CWriter(ssd, font10, GREEN, BLACK, verbose=False)
        self.wribut = CWriter(ssd, arial10, GREEN, BLACK, verbose=False)

        # Labels for rounds and info
        self.round_label = Label(self.wri, 170 // 3 - 30, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN)
        self.round_label.value("There are usually 3 rounds.")

        self.info = Label(self.wri, 170 // 3 - 5, 2, 316, bdcolor=False, justify=1, fgcolor=D_PINK)
        self.info.value("Make your choice, make it wisely.")

        self.player_weapon = None  # Store the player's choice
        self.game = RpsGame()  # Initialize the game

        # RadioButtons for weapon choices
        table = [
            {'text': 'rock', 'args': ['rock']},
            {'text': 'paper', 'args': ['paper']},
            {'text': 'scissors', 'args': ['scissors']},
            {'text': 'lizard', 'args': ['lizard']},
            {'text': 'spock', 'args': ['spock']},
        ]
        col = 1
        rb = RadioButtons(DARKGREEN, self.play_round)
        for t in table:
            rb.add_button(
                self.wribut, 80, col, textcolor=WHITE,
                fgcolor=GREEN, height=40, width=55, **t
            )
            col += 65

        # Label to display scores underneath the radiobuttons
        self.score_label = Label(self.wri, 170 // 3 + 80, 2, 316, bdcolor=False, justify=1, fgcolor=D_GREEN)
        self.update_score()

    def update_score(self):
        """Update the score label."""
        player_score = self.game.scores["player"]
        opponent_score = self.game.scores["opponent"]
        self.score_label.value(f"You: {player_score} / Opponent: {opponent_score}")

    def play_round(self, button, player_weapon):
        """Handle the player weapon selection directly."""
        self.player_weapon = player_weapon
        print(f"Player selected: {self.player_weapon}")

        result, winner = self.game.play_round(self.player_weapon)

        # Display the round result
        if winner == "tie":
            self.info.value(f"{result} Try again!")
            print(f"Tie! Round {self.game.round_count}. Retrying...")
        else:
            self.info.value(result)
            print(f"Round {self.game.round_count} result: {result}")

        # Update the round label
        self.round_label.value(f"Round {self.game.round_count}:")

        # Update the score display
        self.update_score()

        # Check for consecutive wins
        if self.game.consecutive_winner:
            message2 = "two times in a row."
            self.display_final_winner(message2)
        elif self.game.round_count >= 3:
            if self.game.is_tied():
                print("Tie - playing additional rounds")
            else:
                message2 = "the last round."
                self.display_final_winner(message2)

    def display_final_winner(self, message2):
        """Transition to the Winner Screen with the result."""
        winner = self.game.determine_final_winner()
        last_result = self.game.last_result
        message1 = f"{last_result}"

        def return_to_game():
            Screen.change(RpsScreen)

        Screen.change(WinScr, args=(winner, message1, message2))
        self.game = RpsGame()  # Initialize the game


class RpsGame:
    def __init__(self):
        self.win_descriptions = {
            ("rock", "scissors"): "Rock smashes scissors",
            ("rock", "lizard"): "Rock crushes lizard",
            ("scissors", "paper"): "Scissors cut paper",
            ("scissors", "lizard"): "Scissors decapitate lizard",
            ("paper", "rock"): "Paper covers rock",
            ("paper", "spock"): "Paper disproves Spock",
            ("lizard", "spock"): "Lizard poisons Spock",
            ("lizard", "paper"): "Lizard eats paper",
            ("spock", "scissors"): "Spock smashes scissors",
            ("spock", "rock"): "Spock vaporizes rock",
        }
        self.round_count = 0
        self.scores = {"player": 0, "opponent": 0}
        self.last_result = ""
        self.last_winner = None  
        self.consecutive_winner = None  

    def opponent_choice(self):
        random.seed()
        options = ["rock", "paper", "scissors", "lizard", "spock"]
        choice = random.choice(options)
        print(f"Opponent selected: {choice}")
        return choice

    def determine_winner(self, player, opponent):
        if player == opponent:
            return "It was a tie", "tie"
        elif (player, opponent) in self.win_descriptions:
            description = f"{self.win_descriptions[(player, opponent)]}, you won"
            return description, "player"
        elif (opponent, player) in self.win_descriptions:
            description = f"{self.win_descriptions[(opponent, player)]}, you lost"
            return description, "opponent"
        else:
            return "O.o Unexpected outcome!?", None

    def play_round(self, player_weapon):
        """Play a round."""
        self.round_count += 1
        opponent_weapon = self.opponent_choice()
        result, winner = self.determine_winner(player_weapon, opponent_weapon)

        # Update scores
        if winner == "player":
            self.scores["player"] += 1
        elif winner == "opponent":
            self.scores["opponent"] += 1

        # Save the last round's result
        self.last_result = result

        # Track consecutive wins
        if winner == self.last_winner and winner in ["player", "opponent"]:
            self.consecutive_winner = winner  # Track consecutive wins
        else:
            self.consecutive_winner = None  # Reset if no consecutive wins

        self.last_winner = winner  # Update last_winner

        return result, winner

    def is_tied(self):
        """Check if the scores are tied after three rounds."""
        return self.scores["player"] == self.scores["opponent"]

    def determine_final_winner(self):
        """Determine the winner after three rounds."""
        if self.scores["player"] > self.scores["opponent"]:
            nick = Config.config["espnow"]["nick"]

            return nick
        elif self.scores["opponent"] > self.scores["player"]:
            return "opponent"
        else:
            return "tie"
