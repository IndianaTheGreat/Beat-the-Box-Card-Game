import tkinter as tk
from tkinter import ttk, scrolledtext
from BTBGameAid import CustomGameGUI
from BTBGamePlayer import NineBoxGUI
from BTBOptimizer import OptimizerGUI
from BTBSimulator import SimulatorGUI

class MainApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Beat the Box Suite")
        self.setup_gui()

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure main window
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, 
                              text="Beat the Box Game Suite", 
                              font=('Helvetica', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Application buttons
        ttk.Button(main_frame, 
                  text="Game Assistant", 
                  command=self.launch_custom_game,
                  width=30).grid(row=1, column=0, pady=10, padx=10)
        
        ttk.Button(main_frame, 
                  text="Game Player", 
                  command=self.launch_game_player,
                  width=30).grid(row=2, column=0, pady=10, padx=10)
        
        ttk.Button(main_frame, 
                  text="Game Simulator", 
                  command=self.launch_simulator,
                  width=30).grid(row=3, column=0, pady=10, padx=10)
        
        ttk.Button(main_frame, 
                  text="Strategy Optimizer", 
                  command=self.launch_optimizer,
                  width=30).grid(row=4, column=0, pady=10, padx=10)

        # Description labels
        ttk.Label(main_frame, 
                 text="Play with guided assistance, custom card selection, and detailed statistics",
                 wraplength=200).grid(row=1, column=1, pady=10, padx=10, sticky=tk.W)
        
        ttk.Label(main_frame, 
                 text="Play Beat the Box with standard rules and automated shuffling",
                 wraplength=200).grid(row=2, column=1, pady=10, padx=10, sticky=tk.W)
        
        ttk.Label(main_frame, 
                 text="Run game simulations with various settings",
                 wraplength=200).grid(row=3, column=1, pady=10, padx=10, sticky=tk.W)
        
        ttk.Label(main_frame, 
                 text="Optimize game strategy with different parameters",
                 wraplength=200).grid(row=4, column=1, pady=10, padx=10, sticky=tk.W)

        # Additional Information Buttons
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(info_frame, 
                  text="How it Works", 
                  command=self.show_how_it_works,
                  width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(info_frame, 
                  text="Important Points", 
                  command=self.show_important_points,
                  width=20).pack(side=tk.LEFT, padx=5)

        # Exit button
        ttk.Button(main_frame, 
                  text="Exit", 
                  command=self.root.quit,
                  width=20).grid(row=6, column=0, columnspan=2, pady=(20,0))

    def launch_game_player(self):
        game_window = tk.Toplevel(self.root)
        NineBoxGUI(game_window)

    def launch_custom_game(self):
        game_window = tk.Toplevel(self.root)
        CustomGameGUI(game_window)

    def launch_optimizer(self):
        optimizer_window = tk.Toplevel(self.root)
        OptimizerGUI(optimizer_window)

    def launch_simulator(self):
        simulator_window = tk.Toplevel(self.root)
        SimulatorGUI(simulator_window)

    def show_how_it_works(self):
        info_window = tk.Toplevel(self.root)
        info_window.title("How it Works")
        info_window.geometry("600x400")

        text_widget = scrolledtext.ScrolledText(info_window, wrap=tk.WORD, width=70, height=20)
        text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        how_it_works = """Beat the Box Suite - How it Works

1. Game Player (Standard Mode)
   - Play the game with standard rules
   - Automatic card shuffling and dealing
   - Built-in probability calculations
   - Keyboard shortcuts for quick gameplay

2. Custom Game Mode
   - Select specific cards for initial setup
   - Choose cards to play from remaining deck
   - Full control over game progression
   - Ideal for practice and strategy testing

3. Strategy Optimizer
   - Test different game parameters
   - Analyze win rates across configurations
   - Find optimal joker and inclusive move counts
   - Compare different threshold settings

4. Game Simulator
   - Run multiple games automatically
   - Collect detailed statistics
   - Test different strategies
   - Analyze game outcomes

Each component is designed to work together, allowing you to:
- Learn the game mechanics
- Practice with custom scenarios
- Optimize your strategy
- Validate your approach through simulation

The suite uses a consistent rule set across all components and maintains game state accurately throughout play."""

        text_widget.insert(tk.END, how_it_works)
        text_widget.config(state='disabled')

        ttk.Button(info_window, text="Close", 
                  command=info_window.destroy).pack(pady=10)

    def show_important_points(self):
        info_window = tk.Toplevel(self.root)
        info_window.title("Important Points")
        info_window.geometry("600x400")

        text_widget = scrolledtext.ScrolledText(info_window, wrap=tk.WORD, width=70, height=20)
        text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        important_points = """Beat the Box Suite - Important Points

Key Strategy Points:
1. Inclusive Moves
   - Each joker adds one to max inclusive moves
   - Critical for recovering failed positions
   - Most effective with cards near 7-8 value
   - Can recover positions on exact matches

2. Joker Mechanics
   - Always successful regardless of prediction
   - Can be used for guaranteed recoveries
   - Count as success for all prediction types
   - Don't affect card counting statistics

3. Card Counting
   - Three different counting methods available
   - Use counts to guide decision making
   - Counts update automatically during play
   - Helpful for probability estimation

4. Failed Box Recovery
   - Only possible with inclusive moves
   - Requires exact match or joker
   - Choose recovery positions strategically
   - Consider remaining deck composition

Important Technical Notes:
1. Save Resources
   - Close windows you're not using
   - Limit simultaneous simulations
   - Use reasonable simulation counts
   - Clear results periodically

2. Parameter Limits
   - Jokers: 0-2
   - Inclusive moves: 0-43 (+ joker count)
   - Threshold: 0-100%
   - Nine positions maximum

3. Game Progress
   - Track moves and success rates
   - Monitor inclusive moves remaining
   - Watch for recovery opportunities
   - Keep multiple positions viable

4. Best Practices
   - Start with standard mode to learn
   - Use custom mode for specific scenarios
   - Optimize settings incrementally
   - Validate strategies with simulator"""

        text_widget.insert(tk.END, important_points)
        text_widget.config(state='disabled')

        ttk.Button(info_window, text="Close", 
                  command=info_window.destroy).pack(pady=10)

def main():
    root = tk.Tk()
    app = MainApplication(root)
    root.mainloop()

if __name__ == "__main__":
    main()