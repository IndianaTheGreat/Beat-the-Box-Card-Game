"""
Beat the Box - Game Rules and Documentation

Overview:
Beat the Box is a probability-based card game where players try to get through a deck of cards by making correct predictions about card values.

Setup:
1. A standard deck of 52 cards is used (optionally with 1-2 jokers)
2. Nine cards are dealt face up in a 3x3 grid (the "box")
3. The remaining cards form the draw pile

Basic Rules:
1. Players select one of the nine visible cards and predict if the next card from the draw pile will be:
   - Higher
   - Lower
   - Higher than or Equal to (using an inclusive choice)
   - Lower than or Equal to (using an inclusive choice)

2. If the prediction is correct:
   - The drawn card replaces the selected card
   - Play continues
   
3. If the prediction is wrong:
   - The selected position becomes "failed"
   - That position cannot be used unless recovered

Special Rules:
1. Inclusive Choices (Higher/Equal or Lower/Equal):
   - Players start with a limited number of these choices
   - When using an inclusive choice and drawing an EXACT match:
     * Player can recover one previously failed box
   
2. Joker Rules:
   - Game can be played with 0, 1, or 2 jokers
   - Jokers are always successful regardless of prediction
   - If a joker is drawn while using an inclusive choice:
     * Player can recover one previously failed box
   - If a card is played on a joker it is always successful
   - If an inclusive choice is played on a joker it is always successful

Victory/Loss Conditions:
- Win: Successfully get through the entire draw pile with at least one usable position
- Loss: All positions become failed, or unable to complete the deck

Strategy Elements:
1. Probability Management:
   - Calculate odds of higher/lower for each card
   - Save inclusive choices for critical moments
   
2. Failed Box Recovery:
   - Strategic use of inclusive choices for recovery opportunities
   - Careful selection of which failed box to recover

Game Variations:
1. Number of Inclusive Choices:
   - With no jokers: 0-43 choices
   - With one joker: 0-44 choices
   - With two jokers: 0-45 choices

2. Failed Box Display:
   - Option to show/hide failed card values when recovering
"""

import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import random
from collections import defaultdict

@dataclass
class SimulationResults:
    """Results from running a simulation of games"""
    total_games: int
    wins: int
    losses: int
    boxes_left_in_wins: List[int]
    cards_left_in_losses: List[int]
    moves_per_game: List[int]
    inclusive_moves_used: List[int]
    jokers_drawn: List[int]

class Card:
    """Represents a playing card with special handling for jokers"""
    def __init__(self, value: int, suit: str, is_joker: bool = False):
        self.value = 14 if value == 1 else value  # Ace = 14
        self.suit = suit
        self.is_joker = is_joker
        
    def __str__(self):
        if self.is_joker:
            return "🃏"
        values = {14: 'A', 11: 'J', 12: 'Q', 13: 'K'}
        return f"{values.get(self.value, str(self.value))}{self.suit}"

def calculate_move_probabilities(visible_card: Card, remaining_deck: List[Card]) -> Dict[str, float]:
    """Calculate success probability for each possible move type"""
    if not remaining_deck:
        return {}
    
    if visible_card.is_joker:
        return {
            'higher': 100.0,
            'lower': 100.0,
            'higher_equal': 100.0,
            'lower_equal': 100.0,
            'exact_match': 100.0
        }

    total_cards = len(remaining_deck)
    joker_count = sum(1 for card in remaining_deck if card.is_joker)
    target_value = visible_card.value

    higher = sum(1 for card in remaining_deck if card.is_joker or 
                (not card.is_joker and card.value > target_value))
    lower = sum(1 for card in remaining_deck if card.is_joker or 
               (not card.is_joker and card.value < target_value))
    equal = sum(1 for card in remaining_deck if not card.is_joker and 
               card.value == target_value)

    return {
        'higher': (higher / total_cards) * 100,
        'lower': (lower / total_cards) * 100,
        'higher_equal': ((higher + equal) / total_cards) * 100,
        'lower_equal': ((lower + equal) / total_cards) * 100,
        'exact_match': ((equal + joker_count) / total_cards) * 100
    }

class GameState:
    """Tracks the current state of a Beat the Box game"""
    def __init__(self, visible_cards: List[Optional[Card]], remaining_deck: List[Card],
                 inclusive_moves: int, inclusive_threshold: float):
        self.visible_cards = visible_cards
        self.remaining_deck = remaining_deck
        self.failed_boxes: Dict[int, Card] = {}
        self.inclusive_moves_remaining = inclusive_moves
        self.inclusive_threshold = inclusive_threshold
        self.moves_used = 0
        self.inclusive_moves_used = 0
        self.jokers_drawn = 0

    @classmethod
    def new_game(cls, num_jokers: int = 0, inclusive_moves: int = 5,
                 inclusive_threshold: float = 5.0) -> 'GameState':
        """Create a new game state with a fresh deck"""
        suits = ['♠', '♥', '♦', '♣']
        deck = [Card(v, s) for s in suits for v in range(1, 14)]
        if num_jokers > 0:
            deck.extend([Card(0, '', True) for _ in range(num_jokers)])
        random.shuffle(deck)
        return cls(
            visible_cards=deck[:9],
            remaining_deck=deck[9:],
            inclusive_moves=inclusive_moves,
            inclusive_threshold=inclusive_threshold
        )

    def execute_move(self, position: int, move_type: str,
                    recovery_position: Optional[int] = None) -> bool:
        """Execute a move and update game state"""
        if not self.remaining_deck or position >= len(self.visible_cards):
            return False

        target_card = self.visible_cards[position]
        if target_card is None:  # Can't play on a failed position
            return False

        drawn_card = self.remaining_deck.pop(0)
        if drawn_card.is_joker:
            self.jokers_drawn += 1

        self.moves_used += 1
        is_inclusive = 'equal' in move_type
        if is_inclusive:
            self.inclusive_moves_used += 1
            self.inclusive_moves_remaining -= 1

        success = self.check_move_success(move_type, drawn_card, target_card)
        
        if success:
            self.visible_cards[position] = drawn_card
            # Check for recovery opportunity
            if is_inclusive and recovery_position is not None:
                if self.is_exact_match(drawn_card, target_card) or drawn_card.is_joker:
                    self.recover_position(recovery_position)
        else:
            self.failed_boxes[position] = target_card
            self.visible_cards[position] = None

        return success
    
    def check_move_success(self, move_type: str, drawn_card: Card,
                          target_card: Card) -> bool:
        """Check if a move is successful"""
        if drawn_card.is_joker or target_card.is_joker:
            return True

        if move_type == 'higher':
            return drawn_card.value > target_card.value
        elif move_type == 'lower':
            return drawn_card.value < target_card.value
        elif move_type == 'higher_equal':
            return drawn_card.value >= target_card.value
        elif move_type == 'lower_equal':
            return drawn_card.value <= target_card.value
        return False

    def is_exact_match(self, card1: Card, card2: Card) -> bool:
        """Check if two cards match exactly (for recovery)"""
        if card1.is_joker or card2.is_joker:
            return True
        return card1.value == card2.value

    def recover_position(self, position: int) -> bool:
        """Recover a failed position"""
        if position in self.failed_boxes:
            self.visible_cards[position] = self.failed_boxes[position]
            del self.failed_boxes[position]
            return True
        return False

    def get_game_stats(self) -> Dict[str, int]:
        """Get current game statistics"""
        return {
            'total_moves': self.moves_used,
            'inclusive_moves_used': self.inclusive_moves_used,
            'jokers_drawn': self.jokers_drawn,
            'failed_positions': len(self.failed_boxes),
            'cards_remaining': len(self.remaining_deck),
            'active_positions': sum(1 for card in self.visible_cards if card is not None)
        }

    def is_game_over(self) -> bool:
        """Check if the game is over"""
        return (all(card is None for card in self.visible_cards) or
                not self.remaining_deck)

    def has_won(self) -> bool:
        """Check if the game has been won"""
        # 1. Deck is empty AND we have at least one active position
        return (not self.remaining_deck and 
                any(card is not None for card in self.visible_cards))

class SimulatedGame:
    """Simulates a game of Beat the Box following the official rules"""
    def __init__(self, inclusive_limit: int, inclusive_threshold: float, jokers: int = 0):
        self.inclusive_limit = inclusive_limit
        self.inclusive_threshold = inclusive_threshold
        self.num_jokers = jokers
        self.game_state: Optional[GameState] = None

    def setup_game(self):
        """Initialize a new game"""
        self.game_state = GameState.new_game(
            num_jokers=self.num_jokers,
            inclusive_moves=self.inclusive_limit,
            inclusive_threshold=self.inclusive_threshold
        )

    def find_best_move(self) -> Optional[Tuple[int, str, Optional[int]]]:
        """Find the best move based on current game state"""
        if not self.game_state:
            return None

        best_prob = -1.0
        best_move = None
        
        # Check each position for the best move
        for pos, card in enumerate(self.game_state.visible_cards):
            if card is None:  # Skip failed positions
                continue
                
            probs = calculate_move_probabilities(card, self.game_state.remaining_deck)
            if not probs:
                continue
            
            # Check regular moves
            for move_type in ['higher', 'lower']:
                if probs[move_type] > best_prob:
                    best_prob = probs[move_type]
                    best_move = (pos, move_type, None)
            
            # Then check inclusive moves if available
            if self.game_state.inclusive_moves_remaining > 0:
                for move_type in ['higher_equal', 'lower_equal']:
                    current_prob = probs[move_type]
                    
                    # Use inclusive move if it significantly improves probability
                    # or if we have a good chance of recovery
                    should_use_inclusive = (
                        current_prob > best_prob + self.game_state.inclusive_threshold or
                        (current_prob > best_prob and probs['exact_match'] > 20)
                    )
                    
                    if should_use_inclusive:
                        best_prob = current_prob
                        recovery_pos = None
                        
                        # Consider recovery if we have failed boxes and good recovery chance
                        if self.game_state.failed_boxes and probs['exact_match'] > 20:
                            # Choose the most recently failed box
                            recovery_pos = max(self.game_state.failed_boxes.keys())
                        
                        best_move = (pos, move_type, recovery_pos)
        
        return best_move

    def make_best_move(self) -> bool:
        """Make the best available move"""
        if not self.game_state:
            return False

        # First check if we have any valid moves
        valid_positions = [i for i, card in enumerate(self.game_state.visible_cards) 
                         if card is not None]
        
        if not valid_positions:
            return False

        best_move = self.find_best_move()
        if not best_move:
            # Even if we don't find a "best" move, we should still try any valid move
            # This prevents premature losses
            position = valid_positions[0]
            # Try higher or lower based on card value
            card = self.game_state.visible_cards[position]
            if card.value <= 7:  # For lower cards, guess higher
                move_type = 'higher'
            else:  # For higher cards, guess lower
                move_type = 'lower'
            return self.game_state.execute_move(position, move_type, None)

        position, move_type, recovery_position = best_move
        return self.game_state.execute_move(position, move_type, recovery_position)

    def play_game(self) -> Tuple[bool, int, Dict[str, int]]:
        """Play through an entire game"""
        self.setup_game()
        
        while not self.game_state.is_game_over():
            # Try to make a move
            move_success = self.make_best_move()
            
            # Only return early if we have no valid moves left
            if not move_success and all(card is None for card in self.game_state.visible_cards):
                stats = self.game_state.get_game_stats()
                return False, stats['cards_remaining'], stats

        # Get final stats after game is over
        stats = self.game_state.get_game_stats()
        won = self.game_state.has_won()
        
        # Calculate remaining based on win/loss
        if won:
            remaining = stats['active_positions']
        else:
            remaining = stats['cards_remaining']

        return won, remaining, stats

class SimulatorGUI:
    """GUI interface for running Beat the Box simulations"""
    def __init__(self, root):
        self.root = root
        self.root.title("Beat the Box Simulator")
        self.setup_gui()
        self.results = None
    
    def setup_gui(self):
        """Setup the GUI interface"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input fields
        ttk.Label(main_frame, text="Number of Simulations:").grid(row=0, column=0, pady=5)
        self.sim_count = ttk.Entry(main_frame)
        self.sim_count.grid(row=0, column=1, pady=5)
        self.sim_count.insert(0, "1000")
        
        # Jokers Dropdown
        ttk.Label(main_frame, text="Number of Jokers:").grid(row=1, column=0, pady=5)
        self.joker_count = ttk.Combobox(main_frame, values=[0, 1, 2], state='readonly', width=17)
        self.joker_count.grid(row=1, column=1, pady=5)
        self.joker_count.set(0)
        self.joker_count.bind('<<ComboboxSelected>>', self.update_inclusive_range)
        
        # Inclusive Moves
        ttk.Label(main_frame, text="Inclusive Moves:").grid(row=2, column=0, pady=5)
        self.inclusive_count = ttk.Combobox(main_frame, state='readonly', width=17)
        self.inclusive_count.grid(row=2, column=1, pady=5)
        self.update_inclusive_range()
        
        # Inclusive Threshold
        ttk.Label(main_frame, text="Inclusive Threshold (%):").grid(row=3, column=0, pady=5)
        self.threshold = ttk.Entry(main_frame)
        self.threshold.grid(row=3, column=1, pady=5)
        self.threshold.insert(0, "9.5")
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Simulation Progress", padding="5")
        progress_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_label = ttk.Label(progress_frame, text="0.00% Complete")
        self.progress_label.pack(pady=(0, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Run Simulations", 
                  command=self.run_simulations).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Advanced Statistics", 
                  command=self.show_advanced_stats).pack(side=tk.LEFT, padx=5)
        
        # Results display
        self.results_text = tk.Text(main_frame, height=6, width=40)
        self.results_text.grid(row=6, column=0, columnspan=2, pady=5)
    
    def update_inclusive_range(self, event=None):
        """Update the inclusive moves range based on joker count"""
        jokers = int(self.joker_count.get())
        max_inclusive = 43 + jokers  # Base 43 + number of jokers
        values = list(range(max_inclusive + 1))
        self.inclusive_count.config(values=values)
        if not self.inclusive_count.get() or int(self.inclusive_count.get()) > max_inclusive:
            self.inclusive_count.set(0)
    
    def update_progress(self, current, total):
        """Update the progress bar and label"""
        percentage = (current / total) * 100
        self.progress_var.set(percentage)
        self.progress_label.config(text=f"{percentage:.2f}% Complete")
        self.root.update_idletasks()
    
    def validate_inputs(self) -> Tuple[bool, str]:
        """Validate all input values"""
        try:
            sim_count = int(self.sim_count.get())
            if sim_count <= 0:
                return False, "Simulation count must be positive"

            joker_count = int(self.joker_count.get())
            inclusive_count = int(self.inclusive_count.get())
            
            # Validation is simpler now since Combobox restricts input
            max_inclusive = 43 + joker_count
            if not (0 <= inclusive_count <= max_inclusive):
                return False, f"Inclusive moves must be between 0 and {max_inclusive}"

            threshold = float(self.threshold.get())
            if not (0 <= threshold <= 100):
                return False, "Threshold must be between 0 and 100"
                
            return True, ""
        except ValueError:
            return False, "Please enter valid numbers"

    def run_simulations(self):
        """Run the specified number of game simulations"""
        valid, message = self.validate_inputs()
        if not valid:
            messagebox.showerror("Invalid Input", message)
            return

        sim_count = int(self.sim_count.get())
        inclusive_count = int(self.inclusive_count.get())
        threshold = float(self.threshold.get())
        joker_count = int(self.joker_count.get())

        # Reset progress
        self.progress_var.set(0)
        self.progress_label.config(text="0.00% Complete")

        try:
            # Run simulations and update progress
            moves_per_game = []
            inclusive_moves_used = []
            jokers_drawn = []
            wins = 0
            boxes_left_in_wins = []
            cards_left_in_losses = []

            update_frequency = max(1, min(10, sim_count // 100))
            
            for i in range(sim_count):
                game = SimulatedGame(inclusive_count, threshold, joker_count)
                won, remaining, stats = game.play_game()
                
                # Collect statistics
                moves_per_game.append(stats['total_moves'])
                inclusive_moves_used.append(stats['inclusive_moves_used'])
                jokers_drawn.append(stats['jokers_drawn'])
                
                if won:
                    wins += 1
                    boxes_left_in_wins.append(remaining)
                else:
                    cards_left_in_losses.append(remaining)

                # Update progress periodically
                if (i + 1) % update_frequency == 0:
                    self.update_progress(i + 1, sim_count)
            
            # Store results
            self.results = SimulationResults(
                total_games=sim_count,
                wins=wins,
                losses=sim_count - wins,
                boxes_left_in_wins=boxes_left_in_wins,
                cards_left_in_losses=cards_left_in_losses,
                moves_per_game=moves_per_game,
                inclusive_moves_used=inclusive_moves_used,
                jokers_drawn=jokers_drawn
            )
            
            # Update display
            self.update_results_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during simulation: {str(e)}")
            self.progress_var.set(0)
            self.progress_label.config(text="0.00% Complete")

    def update_results_display(self):
        """Update the results text display"""
        if not self.results:
            return
            
        win_rate = (self.results.wins / self.results.total_games) * 100
        avg_moves = sum(self.results.moves_per_game) / len(self.results.moves_per_game)
        avg_inclusive = sum(self.results.inclusive_moves_used) / len(self.results.inclusive_moves_used)
        avg_jokers = sum(self.results.jokers_drawn) / len(self.results.jokers_drawn)
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, 
            f"Total Games: {self.results.total_games}\n"
            f"Wins: {self.results.wins} ({win_rate:.1f}%)\n"
            f"Losses: {self.results.losses} ({100-win_rate:.1f}%)\n"
            f"Avg Moves/Game: {avg_moves:.1f}\n"
            f"Avg Inclusive Used: {avg_inclusive:.1f}\n"
            f"Avg Jokers Drawn: {avg_jokers:.1f}\n"
        )
    
    def show_advanced_stats(self):
        """Show detailed statistics in a new window"""
        if not self.results:
            messagebox.showinfo("No Data", "Please run simulations first")
            return
            
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Advanced Statistics")

        scrollbar = ttk.Scrollbar(stats_window)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        stats_text = tk.Text(stats_window, height=30, width=60, yscrollcommand=scrollbar.set)
        stats_text.pack(padx=10, pady=10)
        scrollbar.config(command=stats_text.yview)
        
        # Calculate detailed statistics
        try:

            # Safe division function
            def safe_div(a, b, default=0.0):
                try:
                    return a / b if b != 0 else default
                except:
                    return default

            win_rate = (self.results.wins / self.results.total_games) * 100 if self.results.total_games > 0 else 0
            
            # Move statistics with error checking
            avg_moves = safe_div(sum(self.results.moves_per_game), 
                           len(self.results.moves_per_game))
            max_moves = max(self.results.moves_per_game) if self.results.moves_per_game else 0
            min_moves = min(self.results.moves_per_game) if self.results.moves_per_game else 0
        
            # Calculate inclusive move statistics
            avg_inclusive = safe_div(sum(self.results.inclusive_moves_used),
                               len(self.results.inclusive_moves_used))
            max_inclusive = max(self.results.inclusive_moves_used) if self.results.inclusive_moves_used else 0

            # Calculate usage rate safely
            inclusive_limit = float(self.inclusive_count.get() or 0)
            usage_rate = safe_div(avg_inclusive, inclusive_limit) * 100 if inclusive_limit > 0 else 0
            
            # Calculate joker statistics
            avg_jokers = safe_div(sum(self.results.jokers_drawn),
                            len(self.results.jokers_drawn))
            max_jokers = max(self.results.jokers_drawn) if self.results.jokers_drawn else 0
            
            # Calculate box statistics
            avg_boxes = safe_div(sum(self.results.boxes_left_in_wins),
                           len(self.results.boxes_left_in_wins))
                
            # Calculate card statistics for losses
            avg_cards = safe_div(sum(self.results.cards_left_in_losses),
                           len(self.results.cards_left_in_losses))
            
            # Create detailed statistics text
            stats = f"""=== Simulation Settings ===
            Total Games: {self.results.total_games}
            Inclusive Moves Allowed: {self.inclusive_count.get()}
            Inclusive Threshold: {self.threshold.get()}%
            Number of Jokers: {self.joker_count.get()}

            === Overall Results ===
            Win Rate: {win_rate:.1f}%
            Total Wins: {self.results.wins}
            Total Losses: {self.results.losses}

            === Move Statistics ===
            Average Moves per Game: {avg_moves:.1f}
            Maximum Moves in a Game: {max_moves}
            Minimum Moves in a Game: {min_moves}

            === Inclusive Move Usage ===
            Average Inclusive Moves Used: {avg_inclusive:.1f}
            Maximum Inclusive Moves Used: {max_inclusive}
            Average Usage Rate: {usage_rate:.1f}%

            === Joker Statistics ===
            Average Jokers Drawn: {avg_jokers:.1f}
            Maximum Jokers Drawn: {max_jokers}

            === Winning Games Statistics ===
            Average Boxes Left: {avg_boxes:.2f}

            Box Distribution:"""
            
            # Add box distribution
            if self.results.wins > 0 and self.results.boxes_left_in_wins:
                box_distribution = defaultdict(int)
                for boxes in self.results.boxes_left_in_wins:
                    box_distribution[boxes] += 1
                
                for boxes in sorted(box_distribution.keys()):
                    count = box_distribution[boxes]
                    percentage = safe_div(count, self.results.wins) * 100
                    stats += f"\n{boxes} boxes: {count} times ({percentage:.1f}%)"
            else:
                stats += "\nNo winning games recorded"
            
            stats += "\n\n=== Losing Games Statistics ==="
            stats += f"\nAverage Cards Left: {avg_cards:.2f}\n\nCard Distribution:"
            
            # Add card distribution
            if self.results.losses > 0 and self.results.cards_left_in_losses:
                card_distribution = defaultdict(int)
                for cards in self.results.cards_left_in_losses:
                    card_distribution[cards] += 1
                
                for cards in sorted(card_distribution.keys()):
                    count = card_distribution[cards]
                    percentage = safe_div(count, self.results.losses) * 100
                    stats += f"\n{cards} cards: {count} times ({percentage:.1f}%)"
            else:
                stats += "\nNo losing games recorded"
        
            # Update the text widget
            stats_text.delete(1.0, tk.END)
            stats_text.insert(tk.END, stats)
            stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error calculating statistics: {str(e)}")
            stats_window.destroy()        
   
def test_game_logic():
    """Test the game logic with various scenarios"""
    # Create a game with known state
    game = SimulatedGame(inclusive_limit=5, inclusive_threshold=5.0, jokers=0)
    game.setup_game()
    
    # Test win condition
    game.game_state.remaining_deck = []  # Empty deck
    game.game_state.visible_cards = [Card(10, '♠'), None, None, None, None, None, None, None, None]
    assert game.game_state.has_won() == True, "Should win with empty deck and one active position"
    
    # Test loss condition
    game.game_state.visible_cards = [None] * 9
    assert game.game_state.has_won() == False, "Should lose with no active positions"
    
    # Test game over condition
    assert game.game_state.is_game_over() == True, "Game should be over with no active positions"

    return "All tests passed"

# Tests to verify the fixes:
def test_early_game_state():
    """Test that games don't end too early"""
    game = SimulatedGame(inclusive_limit=5, inclusive_threshold=5.0, jokers=0)
    game.setup_game()
    
    # Verify initial state
    assert len(game.game_state.visible_cards) == 9, "Should start with 9 cards"
    assert all(card is not None for card in game.game_state.visible_cards), "All positions should be active"
    
    # Make a few moves
    for _ in range(3):
        before_active = sum(1 for card in game.game_state.visible_cards if card is not None)
        game.make_best_move()
        after_active = sum(1 for card in game.game_state.visible_cards if card is not None)
        # Even after failed moves, we shouldn't lose too many positions at once
        assert after_active >= before_active - 1, "Should only fail one position at a time"
    
    # Verify game isn't over too early
    assert not (all(card is None for card in game.game_state.visible_cards)), "Game shouldn't fail all positions this quickly"

def main():
    root = tk.Tk()
    app = SimulatorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()