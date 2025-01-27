"""
Custom Beat The Box Game
This version extends BTBGamePlayer with custom card selection functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Dict, Tuple
from collections import deque
import random

# Import the original game classes
from BTBGamePlayer import NineBoxGame, GameSetupDialog, NineBoxGUI, Card, GameMove

class CustomNineBoxGame(NineBoxGame):
    """
    Extended version of NineBoxGame that allows custom card selection
    """
    def shuffle_and_deal(self):
        """Override the shuffle_and_deal method to not do anything initially"""
        pass  # We'll handle this after custom card selection

class CustomGameGUI(NineBoxGUI):
    """
    Modified version of NineBoxGUI that allows custom card selection
    Both for initial setup and during gameplay
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Custom Beat the Box Game Simulator")
        self.game = None  # Will be initialized in new_game
        self.status_var = tk.StringVar()
        self.status_var.set("Welcome to Beat the Box Game! Press New Game to start.")
        self.selected_position = None
        self.cards_window = None
        self.cards_text = None
        self.selected_card_var = tk.StringVar()  # For selecting next card to play

        # Initialize counting variables
        self.count1_var = tk.StringVar(value="Count Method 1: 0")
        self.count2_var = tk.StringVar(value="Count Method 2: 0")
        self.count3_var = tk.StringVar(value="Count Method 3: 0")
        self.count1 = 0
        self.count2 = 0
        self.count3 = 0

        self.setup_gui()
        self.setup_keyboard_shortcuts()

    def setup_gui(self):
        """Modified setup_gui to include card selection combobox"""
        super().setup_gui()  # Call original setup_gui first

        # Add card selection frame below the original GUI elements
        selection_frame = ttk.LabelFrame(self.root, text="Select Next Card", padding="5")
        selection_frame.grid(row=6, column=0, columnspan=2, pady=5)  # Put it at the bottom

        # Add label and combobox for selecting the next card to play
        ttk.Label(selection_frame, text="Select the card you want to play:").pack(padx=5, pady=2)
        self.drawn_card_combo = ttk.Combobox(selection_frame, 
                                            textvariable=self.selected_card_var,
                                            state='readonly',
                                            width=30)  # Made wider for better visibility
        self.drawn_card_combo.pack(padx=5, pady=5)
        
        # Initialize with empty list
        self.drawn_card_combo['values'] = []

    def get_remaining_cards(self) -> List[str]:
        """Get list of remaining cards as strings"""
        return [str(card) for card in self.game.remaining_deck]

    def card_button_click(self, position):
        """Handle card button clicks"""
        if not self.selected_card_var.get():
            self.update_status("Please select a card to play first!")
            messagebox.showwarning("Warning", "Please select a card to play first!")
            return
            
        try:
            drawn_card = self.parse_card(self.selected_card_var.get())
            target_card = self.game.visible_cards[position]
            
            if target_card is None:
                self.update_status("This position is already cleared!")
                messagebox.showwarning("Warning", "This position is already cleared!")
                return
            
            # Create a choice dialog for higher/lower
            choice_dialog = tk.Toplevel(self.root)
            choice_dialog.title("Choose Comparison")
            choice_dialog.geometry("250x250")
            choice_dialog.transient(self.root)
            choice_dialog.grab_set()
            
            choice_var = tk.StringVar()
            
            def make_choice(choice):
                if choice in ['higher_equal', 'lower_equal']:
                    if not self.game.use_inclusive_choice():
                        messagebox.showwarning("No Inclusive Choices", 
                                            "No inclusive choices remaining!")
                        return
                choice_var.set(choice)
                choice_dialog.destroy()
            
            ttk.Label(choice_dialog, text="Select your choice:").pack(pady=10)
            ttk.Button(choice_dialog, text="Higher", 
                    command=lambda: make_choice("higher")).pack(pady=5)
            ttk.Button(choice_dialog, text="Lower", 
                    command=lambda: make_choice("lower")).pack(pady=5)
            
            if self.game.inclusive_choices_remaining > 0:
                ttk.Label(choice_dialog, 
                        text=f"Inclusive choices remaining: {self.game.inclusive_choices_remaining}"
                        ).pack(pady=5)
                ttk.Button(choice_dialog, text="Higher or Equal", 
                        command=lambda: make_choice("higher_equal")).pack(pady=5)
                ttk.Button(choice_dialog, text="Lower or Equal", 
                        command=lambda: make_choice("lower_equal")).pack(pady=5)
            
            # Wait for dialog
            self.root.wait_window(choice_dialog)
            
            # Get actual result and player's choice
            actual_result = self.game.compare_cards(drawn_card, target_card)
            player_choice = choice_var.get()
            
            if not player_choice:  # If no choice was made (dialog was closed)
                return

            # Process the play
            self.process_play(position, player_choice, drawn_card, target_card, actual_result)
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

    def process_play(self, position, player_choice, drawn_card, target_card, actual_result):
        """Process the play after choice is made"""
        is_correct = False
        used_inclusive = player_choice in ['higher_equal', 'lower_equal']
        
        if used_inclusive:
            is_correct = (player_choice == 'higher_equal' and 
                        (actual_result == 'higher' or actual_result == 'equal')) or \
                    (player_choice == 'lower_equal' and 
                        (actual_result == 'lower' or actual_result == 'equal'))
        else:
            is_correct = actual_result == player_choice
        
        # Save move for undo with complete game state
        old_card = self.game.visible_cards[position]
        self.game.move_history.append(GameMove(
            drawn_card=drawn_card,
            position=position,
            old_card=old_card,
            used_inclusive=used_inclusive,
            failed_boxes=self.game.failed_boxes.copy(),
            inclusive_moves_remaining=self.game.inclusive_choices_remaining,
            count1=self.count1,
            count2=self.count2,
            count3=self.count3
        ))
        
        # Update counts for the new card
        self.update_counts(drawn_card)
        
        if is_correct:
            self.game.visible_cards[position] = drawn_card
            self.card_buttons[position].configure(text=str(drawn_card))
            choice_text = "higher/equal" if player_choice == "higher_equal" else \
                        "lower/equal" if player_choice == "lower_equal" else \
                        actual_result
            self.update_status(f"Correct! {drawn_card} is {choice_text} to {target_card}")
            
            # Check for recovery opportunity with inclusive choices
            if used_inclusive and actual_result == 'equal':
                self.offer_failed_box_recovery()
        else:
            self.game.failed_boxes[position] = target_card
            self.game.visible_cards[position] = None
            self.card_buttons[position].configure(text="Failed")
            self.update_status(f"Wrong! {drawn_card} was {actual_result} than {target_card}")
        
        # Update remaining cards
        self.game.remaining_deck = [card for card in self.game.remaining_deck 
                                if str(card) != str(drawn_card)]
        self.drawn_card_combo['values'] = self.get_remaining_cards()
        self.selected_card_var.set('')
        
        # Refresh probabilities if window is open
        if hasattr(self, 'prob_window') and self.prob_window.winfo_exists():
            self.update_probabilities()

    @staticmethod
    def parse_card(card_str: str) -> Card:
        """Convert a card string to a Card object
        
        Args:
            card_str (str): String representation of a card (e.g., "A♠", "10♣", "🃏")
            
        Returns:
            Card: A Card object representing the card
            
        Examples:
            "A♠" -> Card(14, "♠")  # Ace is represented as 14
            "10♣" -> Card(10, "♣")
            "🃏" -> Card(0, "", True)  # Joker
        """
        if card_str == "🃏":
            return Card(0, '', True)
            
        value_map = {'A': 14, 'J': 11, 'Q': 12, 'K': 13}
        suit = card_str[-1]  # Last character is always the suit
        value = card_str[:-1]  # Everything before the suit is the value
        
        try:
            value = int(value)  # Try to convert to integer (for numbers 2-10)
        except ValueError:
            value = value_map[value]  # Convert face cards using our mapping
            
        return Card(value, suit)
        
    def setup_initial_cards(self):
        """Custom card selection interface for initial game setup"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Initial Cards")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create list of all possible cards
        cards = []
        for suit in ['♠', '♥', '♦', '♣']:
            for value in range(1, 14):
                card = Card(value, suit)
                cards.append(str(card))

        # Add jokers if game has them
        for _ in range(self.game.num_jokers):
            cards.append("🃏")
        
        selected_cards = []
        card_buttons = []
        
        def add_card(card_str):
            if len(selected_cards) < 9:
                selected_cards.append(card_str)
                # Update button states
                for btn in card_buttons:
                    if btn['text'] == card_str:
                        btn.configure(state='disabled')
                update_display()
                self.update_status(f"Selected card: {card_str}")
                if len(selected_cards) == 9:
                    # Convert selected cards to Card objects and set up the game
                    self.game.visible_cards = [
                        Card(0, '', True) if c == "🃏" else self.parse_card(c) 
                        for c in selected_cards
                    ]
                    
                    # Update remaining deck
                    self.game.remaining_deck = [
                        card for card in self.game.deck 
                        if not any(str(card) == str(visible_card) 
                                 for visible_card in self.game.visible_cards)
                    ]
                    
                    # Update interface
                    self.update_display()
                    self.update_inclusive_display()
                    self.update_cards_remaining()
                    
                    # Update the card selection combobox with remaining cards
                    self.drawn_card_combo['values'] = [str(card) for card in self.game.remaining_deck]
                    self.update_status("Initial cards set! Ready to play.")
                    
                    # Update counts for initial dealt cards
                    for card in self.game.visible_cards:
                        self.update_counts(card)
                        
                    dialog.destroy()
        
        def update_display():
            for i, card in enumerate(selected_cards):
                self.card_buttons[i].configure(text=card if i < len(selected_cards) else "Empty")
        
        # Create grid of card buttons
        for i, card in enumerate(cards):
            btn = ttk.Button(dialog, text=card, width=5,
                           command=lambda c=card: add_card(c))
            btn.grid(row=i//13, column=i%13, padx=1, pady=1)
            card_buttons.append(btn)

    def new_game(self):
        """Override new_game to use custom game class and setup"""
        setup_dialog = GameSetupDialog(self.root)
        self.root.wait_window(setup_dialog.dialog)
        
        if not setup_dialog.result:
            return
            
        # Initialize new custom game instance
        self.game = CustomNineBoxGame()
        self.game.setup_with_jokers(setup_dialog.joker_count)
        self.game.set_inclusive_choices(setup_dialog.inclusive_choices)
        self.game.show_failed_cards = setup_dialog.show_failed

        # Reset counts
        self.reset_counts()
        
        # Instead of shuffling, show card selection dialog
        self.setup_initial_cards()
        
        # Update the card selection combobox with remaining cards
        self.drawn_card_combo['values'] = self.get_remaining_cards()

    # Keep the rest of the methods from BTBGameAid...

def main():
    root = tk.Tk()
    app = CustomGameGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()