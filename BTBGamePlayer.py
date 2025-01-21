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
from typing import List, Optional, Dict, Tuple
from collections import deque
import random

class Card:
    def __init__(self, value: int, suit: str, is_joker: bool = False):
        self.value = 14 if value == 1 else value
        self.suit = suit
        self.is_joker = is_joker
        
    def __str__(self):
        if self.is_joker:
            return "🃏"
        values = {14: 'A', 11: 'J', 12: 'Q', 13: 'K'}
        return f"{values.get(self.value, str(self.value))}{self.suit}"
    
    def __repr__(self):
        return self.__str__()
    
    def get_playing_value(self) -> int:
        return self.value

class GameMove:
    def __init__(self, drawn_card: Card, position: int, old_card: Optional[Card], 
                 used_inclusive: bool, failed_boxes: Dict[int, Card],
                 inclusive_moves_remaining: int,
                 count1: int = 0, count2: int = 0, count3: int = 0):
        self.drawn_card = drawn_card
        self.position = position
        self.old_card = old_card
        self.used_inclusive = used_inclusive
        # Store a deep copy of failed boxes state
        self.failed_boxes = failed_boxes.copy()
        # Store the number of inclusive moves remaining
        self._inclusive_moves_remaining = inclusive_moves_remaining

        # Store counts
        self.count1 = count1
        self.count2 = count2
        self.count3 = count3

    @property
    def inclusive_moves_remaining(self) -> int:
        return self._inclusive_moves_remaining

class NineBoxGame:
    def __init__(self):
        # print(f"Initializing NineBoxGame at {id(self)}") # Debug
        self.suits = ['♠', '♥', '♦', '♣']
        self.deck = [Card(v, s) for s in self.suits for v in range(1, 14)]
        self.visible_cards: List[Optional[Card]] = []
        self.remaining_deck: List[Card] = []
        self.move_history: deque[GameMove] = deque()
        self.inclusive_choices_remaining = 0
        self.failed_boxes: Dict[int, Card] = {}
        self.num_jokers = 0
        self.show_failed_cards = False  # New attribute for failed card display preference

    def get_inclusive_remaining(self) -> int:
        """Safe getter for inclusive moves remaining"""
        return getattr(self, 'inclusive_choices_remaining', 0)

    def setup_with_jokers(self, joker_count: int):
        """Setup deck with specified number of jokers"""
        self.num_jokers = joker_count
        self.deck = [Card(v, s) for s in self.suits for v in range(1, 14)]
        for _ in range(joker_count):
            self.deck.append(Card(0, '', True))

    def shuffle_and_deal(self):
        """Shuffle the deck and deal initial 9 cards"""
        random.shuffle(self.deck)
        self.visible_cards = self.deck[:9]
        self.remaining_deck = self.deck[9:]
        
    def draw_card(self) -> Optional[Card]:
        """Draw the next card from the remaining deck"""
        if not self.remaining_deck:
            return None
        return self.remaining_deck[0]
    
    def remove_top_card(self):
        """Remove the top card from the remaining deck"""
        if self.remaining_deck:
            self.remaining_deck.pop(0)
    
    def set_inclusive_choices(self, count: int):
        """Set the number of inclusive choices available"""
        # print(f"Setting inclusive choices to: {count} on game {id(self)}")  # Debug line
        self.inclusive_choices_remaining = count
    
    def use_inclusive_choice(self) -> bool:
        """Use one inclusive choice if available"""
        # print(f"Checking inclusive choices: {self.inclusive_choices_remaining}")
        if self.inclusive_choices_remaining > 0:
            self.inclusive_choices_remaining -= 1
            # print(f"Used one, now at: {self.inclusive_choices_remaining}")  # Debug
            return True
        return False
        
    def compare_cards(self, card1: Card, card2: Card) -> str:
        """Compare two cards and return 'higher', 'lower', or 'equal'"""
        if card1.is_joker:
            return 'equal'  # Jokers are considered equal for comparison purposes
            
        val1 = card1.get_playing_value()
        val2 = card2.get_playing_value()
        if val1 == val2:
            return 'equal'
        return 'higher' if val1 > val2 else 'lower'
    
    def undo_last_move(self) -> bool:
        """Undo the last move if possible"""
        if not self.move_history:
            return False
        
        last_move = self.move_history.pop()
        # print(f"Undo - Current inclusive: {self.get_inclusive_remaining()}, Restoring to: {last_move.inclusive_moves_remaining}")  # Debug
        
        # Restore the original card to the position
        self.visible_cards[last_move.position] = last_move.old_card
        
        # Restore the complete failed boxes state
        self.failed_boxes = last_move.failed_boxes.copy()
        
        # Put drawn card back on top of deck if it wasn't a recovery move
        if last_move.drawn_card:
            if last_move.drawn_card.is_joker:
                self.remaining_deck.insert(0, Card(0, '', True))
            else:
                self.remaining_deck.insert(0, last_move.drawn_card)
        
        # Restore inclusive choice if used
        restore_value = last_move.inclusive_moves_remaining
        # print(f"About to restore inclusive moves to: {restore_value}")  # Debug
        self.inclusive_choices_remaining = restore_value
        # print(f"Restored inclusive moves to: {self.inclusive_choices_remaining}")  # Debug
        
        # Verify restoration
        # if self.inclusive_choices_remaining != restore_value:
        #     print(f"WARNING: Restoration failed! Expected {restore_value}, got {self.inclusive_choices_remaining}")

        return True
    
    def calculate_probabilities(self) -> Dict[Tuple[Card, str], float]:
        """Calculate probabilities for each visible card being higher/lower"""
        probabilities = {}
        for i, visible_card in enumerate(self.visible_cards):
            if visible_card is None:
                continue
                
            total = len(self.remaining_deck)
            if total == 0:
                continue
                
            # Count jokers separately
            joker_count = sum(1 for card in self.remaining_deck if card.is_joker)
            regular_cards = [card for card in self.remaining_deck if not card.is_joker]
            
            # Count regular cards by comparing playing values
            higher_count = sum(1 for card in regular_cards 
                            if card.get_playing_value() > visible_card.get_playing_value())
            lower_count = sum(1 for card in regular_cards 
                            if card.get_playing_value() < visible_card.get_playing_value())
            equal_count = sum(1 for card in regular_cards 
                            if card.get_playing_value() == visible_card.get_playing_value())
            
            # Add jokers to all counts since they're always successful
            higher_count += joker_count
            lower_count += joker_count
            equal_count += joker_count
            
            # Calculate standard probabilities
            probabilities[(visible_card, 'higher')] = (higher_count / (total + joker_count)) * 100
            probabilities[(visible_card, 'lower')] = (lower_count / (total + joker_count)) * 100
            
            # Calculate inclusive probabilities if choices remain
            if self.inclusive_choices_remaining > 0:
                higher_equal_count = higher_count + equal_count
                lower_equal_count = lower_count + equal_count
                
                probabilities[(visible_card, 'higher_equal')] = (higher_equal_count / (total + joker_count)) * 100
                probabilities[(visible_card, 'lower_equal')] = (lower_equal_count / (total + joker_count)) * 100
                
        return probabilities
    
class GameSetupDialog:
    """Separate class to handle game setup dialog"""
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Game Setup")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Initialize result variables
        self.result = None
        self.joker_count = None
        self.inclusive_choices = None
        self.show_failed = None
        
        # Create and layout the dialog components
        self._create_widgets()
        
    def _create_widgets(self):
        """Create all widgets for the setup dialog"""
        # Joker selection
        joker_frame = ttk.LabelFrame(self.dialog, text="Game Configuration", padding=10)
        joker_frame.pack(padx=10, pady=5, fill='x')
        
        ttk.Label(joker_frame, text="Number of Jokers:").pack(anchor='w')
        self.joker_var = tk.StringVar(value="0")
        self.joker_combo = ttk.Combobox(joker_frame, textvariable=self.joker_var,
                                       values=[0, 1, 2], state='readonly')
        self.joker_combo.pack(pady=(0, 10), fill='x')
        
        # Inclusive choices selection
        ttk.Label(joker_frame, text="Number of inclusive choices:").pack(anchor='w')
        self.choices_var = tk.StringVar(value="5")
        self.choices_combo = ttk.Combobox(joker_frame, textvariable=self.choices_var)
        self.choices_combo.pack(pady=(0, 10), fill='x')
        
        # Show Failed Cards option
        ttk.Label(joker_frame, text="Show Failed Cards in Recovery:").pack(anchor='w')
        self.show_failed_var = tk.StringVar(value="Yes")
        self.show_failed_combo = ttk.Combobox(joker_frame, 
                                             textvariable=self.show_failed_var,
                                             values=["Yes", "No"], 
                                             state='readonly')
        self.show_failed_combo.pack(pady=(0, 10), fill='x')
        
        # Help text for max choices
        self.help_label = ttk.Label(joker_frame, text="")
        self.help_label.pack(pady=(0, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10, padx=10)
        
        ttk.Button(button_frame, text="Start Game", 
                  command=self._on_confirm).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", 
                  command=self._on_cancel).pack(side='left', padx=5)
        
        # Setup event handlers
        self.joker_var.trace_add('write', self._update_choices_range)
        self._update_choices_range()
        
    def _update_choices_range(self, *args):
        """Update the range of available inclusive choices based on joker count"""
        try:
            jokers = int(self.joker_var.get())
            max_choices = 43 + jokers
            self.choices_combo['values'] = list(range(max_choices + 1))
            
            # Update help text
            self.help_label.config(
                text=f"Maximum choices with {jokers} joker(s): {max_choices}")
            
            # Validate current choice
            current = int(self.choices_var.get()) if self.choices_var.get() else 0
            if current > max_choices:
                self.choices_var.set(str(max_choices))
        except ValueError:
            pass
    
    def _validate_inputs(self):
        """Validate all input values"""
        try:
            jokers = int(self.joker_var.get())
            choices = int(self.choices_var.get())
            max_choices = 43 + jokers
            
            if choices < 0:
                messagebox.showwarning(
                    "Invalid Input", 
                    "Number of choices cannot be negative")
                return False
                
            if choices > max_choices:
                messagebox.showwarning(
                    "Invalid Input",
                    f"Maximum allowed choices with {jokers} joker(s) is {max_choices}")
                return False
                
            return True
        except ValueError:
            messagebox.showwarning(
                "Invalid Input", 
                "Please enter valid numbers")
            return False
    
    def _on_confirm(self):
        """Handle confirm button click"""
        if self._validate_inputs():
            self.joker_count = int(self.joker_var.get())
            self.inclusive_choices = int(self.choices_var.get())
            self.show_failed = self.show_failed_var.get() == "Yes"
            self.result = True
            self.dialog.destroy()
    
    def _on_cancel(self):
        """Handle cancel button click"""
        self.result = False
        self.dialog.destroy()
    
class NineBoxGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Beat the Box Game Player")
        # print(f"Creating initial game instance")  # Debug
        self.game = None
        self.status_var = tk.StringVar()
        self.status_var.set("Welcome to Beat the Box Game! Press New Game to start.")
        self.selected_position = None
        self.cards_window = None  # Add this line to track the remaining cards window
        self.cards_text = None    # Add this to track the text widget

        # Add counting method variables
        self.count1_var = tk.StringVar(value="Count Method 1: 0")
        self.count2_var = tk.StringVar(value="Count Method 2: 0")
        self.count3_var = tk.StringVar(value="Count Method 3: 0")
        self.count1 = 0
        self.count2 = 0
        self.count3 = 0

        self.setup_gui()
        self.setup_keyboard_shortcuts()
    def update_status(self, message: str):
        """Update the status bar with a new message
        
        This method updates the game's status display to provide feedback to the player.
        The status bar shows important information like:
        - Game state changes
        - Action results
        - Error messages
        - Player prompts
        
        The message is displayed in the status bar at the bottom of the window
        using the StringVar we created during initialization.
        
        Args:
            message (str): The new status message to display
        """
        """Update the status bar with a new message, including joker warnings if needed"""
        # Check if there's a joker on the board
        has_joker = any(card and card.is_joker for card in self.game.visible_cards if card is not None)
        
        # If there's a joker, append the warning to the status message
        if has_joker:
            message = f"{message} (Remember: be sure to play Higher/Equal on jokers)"

        self.status_var.set(message)

    def select_card(self, position: int):
        """Handle the selection of a card position in the game grid
        
        This is a higher-level method that manages card selection and highlights
        the currently selected card position. It helps players understand which
        card they're currently interacting with.
        
        Args:
            position (int): The position in the grid (0-8) that was selected
        """
        # Reset any previous selection styling
        for button in self.card_buttons:
            button.configure(style='')
        
        # If the position is valid and contains a card
        if (0 <= position < 9 and 
            self.game.visible_cards and 
            self.game.visible_cards[position] is not None):
            
            # Highlight the selected position
            self.card_buttons[position].configure(style='Selected.TButton')
            self.selected_position = position
            
            # Enable appropriate choice buttons
            self.update_button_states(True, position)
            
            # Update status to show selected card
            card = self.game.visible_cards[position]
            self.update_status(f"Selected {card}. Choose Higher, Lower, or use an inclusive choice.")
        else:
            self.selected_position = None
            self.update_button_states(False)

    def card_button_click(self, position: int):
        """Handle clicks on card positions in the game grid
        
        This is the primary event handler for card clicks. It checks game state
        and manages the response to player interaction with the card grid.
        
        Args:
            position (int): The position in the grid (0-8) that was clicked
        """
        # Check if game is active and has cards
        if not self.game.visible_cards or not self.game.remaining_deck:
            self.update_status("No active game. Please start a new game.")
            return
        
        # Check if clicked position is failed
        if self.game.visible_cards[position] is None:
            self.update_status("That position is failed! Choose another position.")
            return
        
        # Handle valid card selection
        self.select_card(position)

    def init_styles(self):
        """Initialize custom styles for the game interface
        
        This method sets up custom styles for various interface elements,
        particularly for highlighting selected cards.
        """
        style = ttk.Style()
        
        # Create a style for selected buttons
        style.configure('Selected.TButton', 
                    background='lightblue',
                    relief='sunken')

    def check_play_success(self, drawn_card, target_card, player_choice, actual_result):
        """Check if the play was successful"""
        # Jokers are always successful
        if drawn_card.is_joker:
            return True
            
        # For non-joker cards
        if player_choice == 'higher':
            return drawn_card.get_playing_value() > target_card.get_playing_value()
        elif player_choice == 'lower':
            return drawn_card.get_playing_value() < target_card.get_playing_value()
        elif player_choice == 'higher_equal':
            return drawn_card.get_playing_value() >= target_card.get_playing_value()
        elif player_choice == 'lower_equal':
            return drawn_card.get_playing_value() <= target_card.get_playing_value()
        return False

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions"""
        self.root.bind('<Control-z>', lambda e: self.undo_move())  # Ctrl+Z for undo
        self.root.bind('<Control-n>', lambda e: self.new_game())   # Ctrl+N for new game

        self.root.bind('<Control-p>', lambda e: self.show_probabilities())  # Ctrl+P for probabilities
        self.root.bind('<Control-c>', lambda e: self.show_remaining_cards())  # Add new shortcut for remaining cards

        self.root.bind('<Control-r>', lambda e: self.show_rules())  # Ctrl+R for rules
        self.root.bind('<Control-y>', lambda e: self.show_strategy())  # Ctrl+Y for strategy
        self.root.bind('<Control-h>', lambda e: self.show_keyboard_help())  # Ctrl+h for Help

        # Choice shortcuts
        self.root.bind('<KeyPress-w>', lambda e: self.handle_choice_shortcut("higher"))
        self.root.bind('<KeyPress-s>', lambda e: self.handle_choice_shortcut("lower"))
        self.root.bind('<KeyPress-d>', lambda e: self.handle_choice_shortcut("higher_equal"))
        self.root.bind('<KeyPress-a>', lambda e: self.handle_choice_shortcut("lower_equal"))

        # Position selection - Regular number keys
        number_mappings = {
            '7': 0, '8': 1, '9': 2,  # Top row
            '4': 3, '5': 4, '6': 5,  # Middle row
            '1': 6, '2': 7, '3': 8   # Bottom row
        }

        # Position selection - Numpad
        numpad_mappings = {
            'KP_7': 0, 'KP_8': 1, 'KP_9': 2,
            'KP_4': 3, 'KP_5': 4, 'KP_6': 5,
            'KP_1': 6, 'KP_2': 7, 'KP_3': 8
        }
    
        # Bind regular numbers
        for key, position in number_mappings.items():
            self.root.bind(key, lambda e, pos=position: self.handle_position_selection(pos))
        
        # Bind numpad numbers
        for key, position in numpad_mappings.items():
            self.root.bind(f'<{key}>', lambda e, pos=position: self.handle_position_selection(pos))

        # For Help Shortcut
        self.root.bind('<Control-h>', lambda e: self.show_keyboard_help())

    def handle_choice_shortcut(self, choice):
        """Handle keyboard shortcuts for choices"""
        # First check if a position is selected
        if self.selected_position is None:
            self.update_status("Select a card position first!")
            return

        # Check if the position is valid and has a card
        if (self.selected_position >= len(self.game.visible_cards) or 
            self.game.visible_cards[self.selected_position] is None):
            self.update_status("Invalid position or failed box!")
            return

        # Map choices to their respective commands
        choice_map = {
            "higher": lambda: self.make_choice("higher"),
            "lower": lambda: self.make_choice("lower"),
            "higher_equal": lambda: self.make_choice("higher_equal"),
            "lower_equal": lambda: self.make_choice("lower_equal")
        }

        # Check if this is an inclusive choice
        is_inclusive = "equal" in choice
        if is_inclusive and self.game.inclusive_choices_remaining <= 0:
            self.update_status("No inclusive choices remaining!")
            return

        # Execute the choice
        if choice in choice_map:
            choice_map[choice]()

    def handle_position_selection(self, position):
        """Handle position selection from keyboard"""
        self.card_button_click(position)

    def show_keyboard_help(self):
        """Show keyboard shortcuts help window"""
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("Keyboard Shortcuts")
        help_dialog.geometry("300x300")
        
        help_text = """
        Position Selection:
        7 8 9 (Top row)
        4 5 6 (Middle row)
        1 2 3 (Bottom row)
        
        Choice Selection:
        W - Higher
        S - Lower
        D - Higher or Equal
        A - Lower or Equal
        
        Other Shortcuts:
        Ctrl+Z - Undo
        Ctrl+N - New Game
        Ctrl+P - Show Probabilities
        Ctrl+H - Show this help
        """
        
        ttk.Label(help_dialog, text=help_text, justify=tk.LEFT).pack(padx=10, pady=10)
        ttk.Button(help_dialog, text="Close", command=help_dialog.destroy).pack(pady=5)

    def setup_gui(self):
        """Setup the GUI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Game board frame
        board_frame = ttk.LabelFrame(main_frame, text="Game Board", padding="5")
        board_frame.grid(row=0, column=0, columnspan=2, pady=5)
        
        # Create card buttons grid
        self.card_buttons: List[ttk.Button] = []
        self.create_card_grid(board_frame)

        # Add choice buttons frame
        choice_frame = ttk.LabelFrame(main_frame, text="Action Choices", padding="5")
        choice_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        # Create and store button references for enabling/disabling
        self.higher_button = ttk.Button(choice_frame, text="Higher (W)", 
                                    command=lambda: self.make_choice("higher"),
                                    state='disabled')
        self.lower_button = ttk.Button(choice_frame, text="Lower (S)", 
                                    command=lambda: self.make_choice("lower"),
                                    state='disabled')
        self.higher_equal_button = ttk.Button(choice_frame, text="Higher or Equal (D)", 
                                            command=lambda: self.make_choice("higher_equal"),
                                            state='disabled')
        self.lower_equal_button = ttk.Button(choice_frame, text="Lower or Equal (A)", 
                                            command=lambda: self.make_choice("lower_equal"),
                                            state='disabled')
        
        self.higher_button.grid(row=0, column=0, padx=5, pady=5)
        self.lower_button.grid(row=0, column=1, padx=5, pady=5)
        self.higher_equal_button.grid(row=0, column=2, padx=5, pady=5)
        self.lower_equal_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Add inclusive choices display frame
        choices_frame = ttk.LabelFrame(main_frame, text="Game Statistics", padding="5")
        choices_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Add inclusive choice counters
        self.cards_remaining_var = tk.StringVar(value="Cards Remaining: 43")
        self.inclusive_var = tk.StringVar(value="Higher/Equal or Lower/Equal: 0")
        
        ttk.Label(choices_frame, textvariable=self.cards_remaining_var).grid(
            row=0, column=0, padx=10, pady=5)
        ttk.Label(choices_frame, textvariable=self.inclusive_var).grid(
            row=0, column=1, padx=10, pady=5)

        # Add counting methods display frame
        counting_frame = ttk.LabelFrame(main_frame, text="Card Counting Methods", padding="5")
        counting_frame.grid(row=3, column=0, columnspan=2, pady=5)

        # Method 1 display
        ttk.Label(counting_frame, textvariable=self.count1_var).grid(
            row=0, column=0, padx=10, pady=5)

        # Method 2 display
        ttk.Label(counting_frame, textvariable=self.count2_var).grid(
            row=0, column=1, padx=10, pady=5)

        # Method 3 display
        ttk.Label(counting_frame, textvariable=self.count3_var).grid(
            row=0, column=2, padx=10, pady=5)


        # Update the control_frame grid position to row=4
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=4, column=0, columnspan=2, pady=5)

        # Configure the grid columns to create centering effect
        # control_frame.grid_columnconfigure(0, weight=10)  # Left margin expands
        # control_frame.grid_columnconfigure(3, weight=10)  # Right margin expands
    
        # Control buttons
        ttk.Button(control_frame, text="New Game (Ctrl+N)", 
                  command=self.new_game).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="Undo (Ctrl+Z)",
                  command=self.undo_move).grid(row=0, column=2, padx=5, pady=5)

        ttk.Button(control_frame, text="Show Probabilities (Ctrl+P)", 
                  command=self.show_probabilities).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="Show Remaining Cards (Ctrl+C)",
                  command=self.show_remaining_cards).grid(row=1, column=2, padx=5, pady=5)

        
        ttk.Button(control_frame, text="How to Play (Ctrl+R)",
                command=self.show_rules).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(control_frame, text="Strategy (Ctrl+Y)",
                command=self.show_strategy).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(control_frame, text="Keyboard Help (Ctrl+H)", 
                command=self.show_keyboard_help).grid(row=2, column=2, padx=5, pady=5)
        
        # Status bar
        status_frame = ttk.Frame(main_frame, relief=tk.SUNKEN)
        status_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, padx=5, pady=2)

    def update_counts(self, card):
        """Update all counting methods based on the card played"""
        if not card or card.is_joker:
            return
            
        value = card.get_playing_value()
        
        # Method 1: +1 over 8, -1 under 8, 0 for 8
        if value > 8:
            self.count1 += 1
        elif value < 8:
            self.count1 -= 1
            
        # Method 2
        if value in [12, 13, 14]:  # Q, K, A
            self.count2 += 2
        elif value in [9, 10, 11]:  # 9, 10, J
            self.count2 += 1
        elif value in [5, 6, 7]:  # 7, 6, 5
            self.count2 -= 1
        elif value in [2, 3, 4]:  # 4, 3, 2
            self.count2 -= 2
            
        # Method 3
        if value in [13, 14]:  # K, A
            self.count3 += 3
        elif value in [11, 12]:  # Q, J
            self.count3 += 2
        elif value in [9, 10]:  # 9, 10
            self.count3 += 1
        elif value in [6, 7]:  # 7, 6
            self.count3 -= 1
        elif value in [4, 5]:  # 5, 4
            self.count3 -= 2
        elif value in [2, 3]:  # 3, 2
            self.count3 -= 3
            
        self.update_count_display()

    def update_count_display(self):
        """Update the display of all counting methods"""
        self.count1_var.set(f"Count Method 1: {self.count1}")
        self.count2_var.set(f"Count Method 2: {self.count2}")
        self.count3_var.set(f"Count Method 3: {self.count3}")

    def reset_counts(self):
        """Reset all counting methods to zero"""
        self.count1 = 0
        self.count2 = 0
        self.count3 = 0
        self.update_count_display()    

    def create_card_grid(self, parent):
        """Create the grid of card buttons"""
        for i in range(9):
            btn = ttk.Button(parent, text="Empty", width=10,
                           command=lambda pos=i: self.card_button_click(pos))
            btn.grid(row=i//3, column=i%3, padx=2, pady=2)
            self.card_buttons.append(btn)

    def new_game(self):
        """Start a new game with setup options"""
        # Create and show the setup dialog
        setup_dialog = GameSetupDialog(self.root)
        self.root.wait_window(setup_dialog.dialog)
        
        # Check if user confirmed the setup
        if not setup_dialog.result:
            return
            
        # Initialize new game with selected options
        # print(f"Creating new game instance")  # Debug line
        self.game = NineBoxGame()
        self.game.setup_with_jokers(setup_dialog.joker_count)
        self.game.set_inclusive_choices(setup_dialog.inclusive_choices)
        self.game.show_failed_cards = setup_dialog.show_failed

        # Reset counts
        self.reset_counts()
        
        # Setup game state
        self.game.shuffle_and_deal()

        # Update counts for initial dealt cards
        for card in self.game.visible_cards:
            self.update_counts(card)

        self.update_display()
        self.update_inclusive_display()
        self.update_cards_remaining()
        self.update_status("Game started! Select a card and make your prediction.")
        self.update_button_states(False)
        self.selected_position = None

    def card_button_click(self, position):
        """Handle card button clicks in the game grid
        
        This method is called when a player clicks on one of the nine card positions.
        It manages the game state by:
        1. Checking if the position is valid (not failed)
        2. Updating the selected position
        3. Enabling/disabling appropriate choice buttons
        4. Updating the game status
        
        Args:
            position (int): The grid position that was clicked (0-8)
        """
        # If no game is in progress or no cards remaining, do nothing
        if not self.game.visible_cards or not self.game.remaining_deck:
            return
            
        # If position is failed (None in visible_cards), do nothing
        if self.game.visible_cards[position] is None:
            self.update_status("That position is failed! Choose another position.")
            self.update_button_states(False)
            return
            
        # Update selected position and enable choice buttons
        self.update_button_states(True, position)
        
        # Update status to show selected card
        selected_card = self.game.visible_cards[position]
        self.update_status(f"Selected {selected_card}. Choose Higher, Lower, or use an inclusive choice.")

    def process_play(self, position, player_choice):
        # print(f"Processing play on game {id(self.game)}") # Debug
        # print(f"Start of process_play - Inclusive remaining: {self.game.inclusive_choices_remaining}") # Debug

        # Save inclusive moves count BEFORE any changes or checks
        inclusive_at_start = self.game.inclusive_choices_remaining
        # print(f"Saved current inclusive remaining: {inclusive_at_start}")  # Debug

        # Check for inclusive choice AFTER saving the count
        used_inclusive = player_choice in ['higher_equal', 'lower_equal']
        if used_inclusive:
            if not self.game.use_inclusive_choice():
                messagebox.showwarning("No Inclusive Choices", 
                                    "No inclusive choices remaining!")
                return

        """Process the play after choice is made"""
        drawn_card = self.game.draw_card()
        target_card = self.game.visible_cards[position]
        
        if not drawn_card:
            self.update_status("No more cards in the deck!")
            return

        # Update counts for the new card
        self.update_counts(drawn_card)
                
        # Save move with complete game state
        old_card = self.game.visible_cards[position]
        # print(f"Storing move with inclusive count: {inclusive_at_start}")  # Debug
        self.game.move_history.append(GameMove(
            drawn_card=drawn_card,
            position=position,
            old_card=old_card,
            used_inclusive=used_inclusive,
            failed_boxes=self.game.failed_boxes.copy(),  # Store current failed boxes state
            inclusive_moves_remaining=inclusive_at_start,
            count1=self.count1,  # Store current counts
            count2=self.count2,
            count3=self.count3
        ))
        
        # Special joker handling
        if drawn_card.is_joker or target_card.is_joker:  # Check both drawn card and target card
            self.game.visible_cards[position] = drawn_card
            self.card_buttons[position].configure(text=str(drawn_card))
            message = f"Drew a Joker! Automatic success!"
            
            # If using inclusive choice with joker (either drawn or target), offer recovery
            if used_inclusive and self.game.failed_boxes:
                message = f"Drew a Joker! You can recover a failed box."
                self.update_status(message)
                self.offer_failed_box_recovery()
                
            self.game.remove_top_card()
            self.update_cards_remaining()
            self.update_status(message)
            self.update_inclusive_display()
            self.update_button_states(False)
            return
        
        # Regular card handling
        actual_result = self.game.compare_cards(drawn_card, target_card)
        is_correct = self.check_play_success(drawn_card, target_card, player_choice, actual_result)
        
        if is_correct:
            self.game.visible_cards[position] = drawn_card
            self.card_buttons[position].configure(text=str(drawn_card))
            message = f"Drew {drawn_card}. Correct!"
            
            # Check for exact match with inclusive move
            if used_inclusive and actual_result == 'equal':
                self.offer_failed_box_recovery()
        else:
            self.game.failed_boxes[position] = target_card
            self.game.visible_cards[position] = None
            self.card_buttons[position].configure(text="Failed")
            message = f"Drew {drawn_card}. Wrong!"
        
        self.game.remove_top_card()
        self.update_cards_remaining()
        self.update_status(message)
        self.update_inclusive_display()
        
        if hasattr(self, 'prob_window') and self.prob_window.winfo_exists():
            self.update_probabilities()
            
        self.update_button_states(False)

    def offer_failed_box_recovery(self):
        """Offer to recover a failed box if any exist using a 3x3 grid layout"""
        failed_positions = list(self.game.failed_boxes.keys())
        if not failed_positions:
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Recover Failed Box")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Select a failed box to recover:").pack(pady=5)
        
        # Create 3x3 grid frame
        grid_frame = ttk.Frame(dialog)
        grid_frame.pack(pady=5)
        
        # Create buttons for all positions, enable only failed ones
        for i in range(9):
            if i in failed_positions:
                button_text = f"Position {i+1}"
                if self.game.show_failed_cards:
                    button_text += f"\n{self.game.failed_boxes[i]}"
                btn = ttk.Button(grid_frame, text=button_text,
                               command=lambda pos=i: self.recover_failed_box(pos, dialog))
            else:
                btn = ttk.Button(grid_frame, text="", state='disabled')
            
            btn.grid(row=i//3, column=i%3, padx=2, pady=2)
        
        # Skip button below the grid
        ttk.Button(dialog, text="Skip Recovery", 
                  command=dialog.destroy).pack(pady=5)

    def recover_failed_box(self, position: int, dialog: tk.Toplevel):
        """Recover a failed box"""
        # Before recovering, append a new GameMove to track this recovery
        recovered_card = self.game.failed_boxes[position]
        self.game.move_history.append(GameMove(
            drawn_card=None,  # No card drawn for recovery
            position=position,
            old_card=None,    # Position was failed
            used_inclusive=False,
            failed_boxes=self.game.failed_boxes.copy(),  # Store current state before recovery
            inclusive_moves_remaining=self.game.get_inclusive_remaining(),
            count1=self.count1,  # Store current counts
            count2=self.count2,
            count3=self.count3
        ))
        
        # Now perform the recovery
        self.game.visible_cards[position] = recovered_card
        self.card_buttons[position].configure(text=str(recovered_card))

        # Update counts for the recovered card
        self.update_counts(recovered_card)
    
        del self.game.failed_boxes[position]
        dialog.destroy()
        self.update_status(f"Recovered position {position+1}")
    
    def update_button_states(self, enable=False, position=None):
        # print(f"Update buttons - Inclusive remaining: {self.game.inclusive_choices_remaining}") # Debug

        """Update the state of choice buttons"""
        self.selected_position = position if enable else None
    
        state = 'normal' if enable else 'disabled'
    
        buttons = {
            'higher': self.higher_button,
            'lower': self.lower_button,
            'higher_equal': self.higher_equal_button,
            'lower_equal': self.lower_equal_button
        }
        
        for name, button in buttons.items():
            if name in ['higher_equal', 'lower_equal']:
                button_state = state if (enable and self.game.inclusive_choices_remaining > 0) else 'disabled'
            else:
                button_state = state
            button.configure(state=button_state)

    def make_choice(self, choice):
        """Handle choice button clicks"""
        # print(f"Making choice {choice} on game {id(self.game)}")  # Print game object ID
        if self.selected_position is None:
            return
            
        # if choice in ['higher_equal', 'lower_equal']:
        #     if not self.game.use_inclusive_choice():
        #         messagebox.showwarning("No Inclusive Choices", 
        #                             "No inclusive choices remaining!")
        #         return
        
        self.process_play(self.selected_position, choice)
        self.update_button_states(False)

    def update_display(self):
        """Update all display elements"""
        for i, card in enumerate(self.game.visible_cards):
            self.card_buttons[i].configure(text=str(card) if card else "Failed")
        
        remaining_cards = len(self.game.remaining_deck)
        cleared_positions = sum(1 for card in self.game.visible_cards if card is None)
        inclusive_remaining = self.game.inclusive_choices_remaining
        self.update_status(
            f"Cards in deck: {remaining_cards} | "
            f"Cleared positions: {cleared_positions}/9 | "
            f"Inclusive choices: {inclusive_remaining}"
        )
    
    def update_inclusive_display(self):
        """Update the inclusive choices display"""
        remaining = self.game.inclusive_choices_remaining
        self.inclusive_var.set(f"Higher/Equal or Lower/Equal: {remaining}")

    def update_cards_remaining(self):
        """Update the cards remaining display"""
        remaining = len(self.game.remaining_deck)
        self.cards_remaining_var.set(f"Cards Remaining: {remaining}")
    
    def undo_move(self):
        """Undo the last move"""
        if self.game.move_history:  # If there are moves to undo
            # Get the last move's counts before we undo
            last_move = self.game.move_history[-1]
            last_counts = (last_move.count1, last_move.count2, last_move.count3)
            
            if self.game.undo_last_move():
                # Restore the counts to previous state
                self.count1, self.count2, self.count3 = last_counts
                self.update_count_display()
                
                # Rest of the existing undo logic remains the same...
                for i, card in enumerate(self.game.visible_cards):
                    if card is None:
                        if i in self.game.failed_boxes:
                            self.card_buttons[i].configure(text="Failed")
                        else:
                            self.card_buttons[i].configure(text="Empty")
                    else:
                        self.card_buttons[i].configure(text=str(card))

                if self.selected_position is not None:
                    self.update_button_states(True, self.selected_position)
                else:
                    self.update_button_states(False)
                
                self.update_display()
                self.update_inclusive_display()
                self.update_cards_remaining()
                self.update_status("Last move undone!")
                
                if hasattr(self, 'prob_window') and self.prob_window.winfo_exists():
                    self.update_probabilities()
        else:
            self.update_status("No moves to undo!")
            messagebox.showwarning("Warning", "No moves to undo!")
    
    def show_probabilities(self):
        """Show probability window"""
        self.prob_window = tk.Toplevel(self.root)
        self.prob_window.title("Probabilities")
        self.update_probabilities()
        
        # Auto-refresh every 1000ms (1 second)
        self.prob_window.after(1000, self.refresh_probabilities)

    def refresh_probabilities(self):
        """Refresh probabilities if window is still open"""
        if hasattr(self, 'prob_window') and self.prob_window.winfo_exists():
            self.update_probabilities()
            self.prob_window.after(1000, self.refresh_probabilities)

    def update_probabilities(self):
        """Update the probabilities display"""
        # Clear existing labels
        for widget in self.prob_window.winfo_children():
            widget.destroy()
            
        probabilities = self.game.calculate_probabilities()
        sorted_probs = sorted(probabilities.items(), 
                            key=lambda x: x[1], 
                            reverse=True)
        
        for i, ((card, direction), prob) in enumerate(sorted_probs):
            ttk.Label(self.prob_window, 
                    text=f"{card} ({direction}): {prob:.1f}%").grid(row=i, column=0, padx=5, pady=2)

    def show_rules(self):
        """Show game rules window"""
        rules_dialog = tk.Toplevel(self.root)
        rules_dialog.title("How to Play")
        rules_dialog.geometry("600x800")
        
        # Create a frame with scrollbar
        frame = ttk.Frame(rules_dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=text.yview)
        
        # Rules text
        rules_text = """Beat the Box - Game Rules

        Setup:
        - A standard deck of 52 cards is used (with optional 1-2 jokers)
        - Nine cards are dealt face up in a 3x3 grid (the "box")
        - The remaining cards form the draw pile

        Basic Rules:
        1. Players select one of the nine visible cards and predict if the next card from the draw pile will be:
        • Higher
        • Lower
        • Higher than or Equal to (using an inclusive choice)
        • Lower than or Equal to (using an inclusive choice)

        2. If the prediction is correct:
        • The drawn card replaces the selected card
        • Play continues

        3. If the prediction is wrong:
        • The selected position becomes "failed"
        • That position cannot be used unless recovered

        Special Rules:
        1. Inclusive Choices (Higher/Equal or Lower/Equal):
        • Players start with a limited number of these choices
        • When using an inclusive choice and drawing an EXACT match:
            - Player can recover one previously failed box

        2. Joker Rules:
        • Game can be played with 0, 1, or 2 jokers
        • Jokers are always successful regardless of prediction
        • If a joker is drawn while using an inclusive choice:
            - Player can recover one previously failed box
        • If a card is played on a joker it is always successful
        • If an inclusive choice is played on a joker it is always successful

        Victory/Loss Conditions:
        - Win: Successfully get through the entire draw pile with at least one usable position
        - Loss: All positions become failed, or unable to complete the deck"""

        # Insert rules text
        text.insert('1.0', rules_text)
        text.config(state='disabled')  # Make text read-only
        
        # Close button
        ttk.Button(rules_dialog, text="Close", 
                command=rules_dialog.destroy).pack(pady=10)

    def show_strategy(self):
        """Show strategy window"""
        strategy_dialog = tk.Toplevel(self.root)
        strategy_dialog.title("Strategy Guide")
        strategy_dialog.geometry("600x800")
        
        # Create a frame with scrollbar
        frame = ttk.Frame(strategy_dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=text.yview)
        
        # Strategy text
        strategy_text = """Beat the Box - Strategy Guide

        Card Counting Strategies:

        1. Basic Counting (Method 1):
        This method provides a simple way to track the overall "high/low" balance of cards:
        • +1 for cards over 8
        • -1 for cards under 8
        • 0 for 8 and jokers
        
        Use this count to quickly gauge whether more high or low cards remain.

        2. Intermediate Counting (Method 2):
        This method provides more detail by weighting face cards more heavily:
        • +2 for Q, K, A
        • +1 for 9, 10, J
        • -1 for 7, 6, 5
        • -2 for 4, 3, 2
        • 0 for 8 and jokers
        
        This gives a better indication of extreme high/low cards remaining.

        3. Advanced Counting (Method 3):
        This method provides the most detailed tracking:
        • +3 for K, A
        • +2 for Q, J
        • +1 for 9, 10
        • -1 for 7, 6
        • -2 for 5, 4
        • -3 for 3, 2
        • 0 for 8 and jokers
        
        Use this for the most precise probability calculations.

        General Strategy Tips:

        1. Inclusive Choice Management:
        • Save inclusive choices for critical situations
        • Use them on cards close to the middle (7-9) for better odds
        • Consider using them when the count suggests high risk

        2. Position Management:
        • Try to keep multiple positions viable
        • When recovering a failed position, choose ones that give you
            more flexibility in future plays

        3. Using the Count:
        • A positive count indicates more high cards remaining
        • A negative count indicates more low cards remaining
        • The higher the absolute value, the stronger the trend

        4. Joker Strategy:
        • Always use inclusive choices on jokers for free recoveries
        • When drawn on an inclusive choice, carefully consider which
            failed position to recover

        5. Probability Awareness:
        • Use the probability display (Ctrl+P) to verify your count-based
            intuitions
        • Pay attention to how each card played affects future probabilities

        Advanced Tips:
        • Track multiple counting methods simultaneously for better accuracy
        • Consider both the count and the visible grid when making decisions
        • Use inclusive choices more aggressively when the count gives you
            high confidence
        • Save recoveries for positions that complement your remaining cards"""
        
        # Insert strategy text
        text.insert('1.0', strategy_text)
        text.config(state='disabled')  # Make text read-only
        
        # Close button
        ttk.Button(strategy_dialog, text="Close", 
                command=strategy_dialog.destroy).pack(pady=10)

    def update_remaining_cards(self):
        """Update the display of remaining cards"""
        if not hasattr(self, 'cards_window') or not self.cards_window or not self.cards_window.winfo_exists():
            return
            
        if not self.game or not self.game.remaining_deck:
            self.cards_window.destroy()
            return
            
        # Count remaining cards
        remaining_cards = {
            'Joker': 0,
            'Ace': 0,
            'King': 0,
            'Queen': 0,
            'Jack': 0,
            '10': 0,
            '9': 0,
            '8': 0,
            '7': 0,
            '6': 0,
            '5': 0,
            '4': 0,
            '3': 0,
            '2': 0
        }
        
        # Count each card
        for card in self.game.remaining_deck:
            if card.is_joker:
                remaining_cards['Joker'] += 1
            else:
                value = card.get_playing_value()
                if value == 14:
                    remaining_cards['Ace'] += 1
                elif value == 13:
                    remaining_cards['King'] += 1
                elif value == 12:
                    remaining_cards['Queen'] += 1
                elif value == 11:
                    remaining_cards['Jack'] += 1
                else:
                    remaining_cards[str(value)] += 1
        
        # Create the display text
        display_text = "Remaining Cards in Deck:\n\n"
        total_cards = 0
        
        for card_name, count in remaining_cards.items():
            if count > 0:  # Only show cards that are still in the deck
                display_text += f"{card_name}: {count}\n"
                total_cards += count
        
        display_text += f"\nTotal Cards Remaining: {total_cards}"
        
        # Update the text widget
        self.cards_text.config(state='normal')
        self.cards_text.delete('1.0', tk.END)
        self.cards_text.insert('1.0', display_text)
        self.cards_text.config(state='disabled')
        
        # Schedule the next update
        self.cards_window.after(1000, self.update_remaining_cards)

    def show_remaining_cards(self):
        """Show a window with all remaining cards and their counts"""
        if not self.game or not self.game.remaining_deck:
            messagebox.showwarning("No Game", "No active game or deck is empty!")
            return
            
        # If window exists, bring to front instead of creating new one
        if hasattr(self, 'cards_window') and self.cards_window and self.cards_window.winfo_exists():
            self.cards_window.lift()
            return
            
        # Create a new window
        self.cards_window = tk.Toplevel(self.root)
        self.cards_window.title("Remaining Cards")
        self.cards_window.geometry("300x500")
        
        # Create scrollable frame
        frame = ttk.Frame(self.cards_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        self.cards_text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        self.cards_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=self.cards_text.yview)
        
        # Initial update
        self.update_remaining_cards()
        
        # Close button
        ttk.Button(self.cards_window, text="Close", 
                  command=self.cards_window.destroy).pack(pady=10)

    
def main():
    root = tk.Tk()
    app = NineBoxGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()