import tkinter as tk
from tkinter import ttk, messagebox
from BTBSimulator import SimulatedGame, SimulationResults
import numpy as np
import itertools
from collections import defaultdict

class OptimizationResults:
    def __init__(self):
        self.results = {}
        self.parameter_space = {'jokers': set(), 'moves': set(), 'thresholds': set()}
        self.best_params = None
        self.best_win_rate = 0

    def add_result(self, jokers, moves, threshold, result):
        self.results[(jokers, moves, threshold)] = result
        self.parameter_space['jokers'].add(jokers)
        self.parameter_space['moves'].add(moves)
        self.parameter_space['thresholds'].add(threshold)
        
        win_rate = (result.wins / result.total_games) * 100
        if win_rate > self.best_win_rate:
            self.best_win_rate = win_rate
            self.best_params = (jokers, moves, threshold)

    def get_top_results(self, n=10):
        """Get top n results sorted by win rate"""
        sorted_results = sorted(
            [(params, (result.wins / result.total_games) * 100)
             for params, result in self.results.items()],
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_results[:n]

    def get_top_by_parameter(self, parameter, n=5):
        """Get top n results grouped by a specific parameter"""
        param_results = defaultdict(list)
        
        # Group results by parameter
        for (jokers, moves, threshold), result in self.results.items():
            win_rate = (result.wins / result.total_games) * 100
            if parameter == 'jokers':
                param_results[jokers].append((win_rate, moves, threshold))
            elif parameter == 'moves':
                param_results[moves].append((win_rate, jokers, threshold))
            else:  # thresholds
                param_results[threshold].append((win_rate, jokers, moves))

        # Get top results for each parameter value
        top_results = {}
        for param_value, results in param_results.items():
            sorted_results = sorted(results, reverse=True)
            top_results[param_value] = sorted_results[:n]

        return dict(sorted(top_results.items()))

class OptimizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Beat the Box Optimizer")
        self.optimization_results = None
        self.setup_gui()

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Parameters Frame
        param_frame = ttk.LabelFrame(main_frame, text="Optimization Parameters", padding="5")
        param_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        # Simulations count
        ttk.Label(param_frame, text="Simulations per test:").grid(row=0, column=0, padx=5, pady=5)
        self.sim_count = ttk.Entry(param_frame, width=10)
        self.sim_count.grid(row=0, column=1, padx=5, pady=5)
        self.sim_count.insert(0, "1000")

        # Joker range
        ttk.Label(param_frame, text="Joker range:").grid(row=1, column=0, padx=5, pady=5)
        joker_frame = ttk.Frame(param_frame)
        joker_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=5)
        
        self.joker_min = ttk.Entry(joker_frame, width=5)
        self.joker_min.pack(side=tk.LEFT, padx=2)
        self.joker_min.insert(0, "0")
        
        ttk.Label(joker_frame, text="to").pack(side=tk.LEFT, padx=2)
        
        self.joker_max = ttk.Entry(joker_frame, width=5)
        self.joker_max.pack(side=tk.LEFT, padx=2)
        self.joker_max.insert(0, "2")

        # Inclusive moves range
        ttk.Label(param_frame, text="Inclusive moves range:").grid(row=2, column=0, padx=5, pady=5)
        moves_frame = ttk.Frame(param_frame)
        moves_frame.grid(row=2, column=1, columnspan=2, padx=5, pady=5)
        
        self.moves_min = ttk.Entry(moves_frame, width=5)
        self.moves_min.pack(side=tk.LEFT, padx=2)
        self.moves_min.insert(0, "0")
        
        ttk.Label(moves_frame, text="to").pack(side=tk.LEFT, padx=2)
        
        self.moves_max = ttk.Entry(moves_frame, width=5)
        self.moves_max.pack(side=tk.LEFT, padx=2)
        self.moves_max.insert(0, "10")

        # Threshold range
        ttk.Label(param_frame, text="Threshold range (%):").grid(row=3, column=0, padx=5, pady=5)
        threshold_frame = ttk.Frame(param_frame)
        threshold_frame.grid(row=3, column=1, columnspan=2, padx=5, pady=5)
        
        self.threshold_min = ttk.Entry(threshold_frame, width=5)
        self.threshold_min.pack(side=tk.LEFT, padx=2)
        self.threshold_min.insert(0, "0")
        
        ttk.Label(threshold_frame, text="to").pack(side=tk.LEFT, padx=2)
        
        self.threshold_max = ttk.Entry(threshold_frame, width=5)
        self.threshold_max.pack(side=tk.LEFT, padx=2)
        self.threshold_max.insert(0, "10")

        # Step size
        ttk.Label(param_frame, text="Threshold step size:").grid(row=4, column=0, padx=5, pady=5)
        self.step_size = ttk.Entry(param_frame, width=7)
        self.step_size.grid(row=4, column=1, padx=5, pady=5)
        self.step_size.insert(0, "0.5")

        # Progress Frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0.00% Complete")
        self.progress_label.pack(pady=5)

        # Results Text
        self.results_text = tk.Text(main_frame, height=20, width=60)
        self.results_text.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))

        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Run Optimization", 
                  command=self.run_optimization).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Advanced Statistics", 
                  command=self.show_advanced_stats).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Results", 
                  command=self.clear_results).pack(side=tk.LEFT, padx=5)

    def clear_results(self):
        """Clear results display and progress"""
        self.results_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.progress_label.config(text="0.00% Complete")

    def update_progress(self, current, total):
        """Update progress bar and label"""
        percentage = (current / total) * 100
        self.progress_var.set(percentage)
        self.progress_label.config(text=f"{percentage:.2f}% Complete")
        self.root.update_idletasks()

    def validate_inputs(self):
        """Validate all input values"""
        try:
            sim_count = int(self.sim_count.get())
            if sim_count <= 0:
                return False, "Simulation count must be positive"

            joker_min = int(self.joker_min.get())
            joker_max = int(self.joker_max.get())
            if not (0 <= joker_min <= joker_max <= 2):
                return False, "Invalid joker range (0-2)"

            moves_min = int(self.moves_min.get())
            moves_max = int(self.moves_max.get())
            if not (0 <= moves_min <= moves_max <= 45):  # Maximum with 2 jokers
                return False, "Invalid inclusive moves range"

            threshold_min = float(self.threshold_min.get())
            threshold_max = float(self.threshold_max.get())
            if not (0 <= threshold_min <= threshold_max <= 100):
                return False, "Invalid threshold range"

            return True, ""
        except ValueError:
            return False, "Please enter valid numbers"

    def run_optimization(self):
        """Run optimization with current parameters"""
        valid, message = self.validate_inputs()
        if not valid:
            messagebox.showerror("Invalid Input", message)
            return

        # Clear previous results
        self.clear_results()

        # Get parameters
        sim_count = int(self.sim_count.get())
        joker_min = int(self.joker_min.get())
        joker_max = int(self.joker_max.get())
        moves_min = int(self.moves_min.get())
        moves_max = int(self.moves_max.get())
        threshold_min = float(self.threshold_min.get())
        threshold_max = float(self.threshold_max.get())
        step = float(self.step_size.get())

        # Generate parameter combinations
        joker_range = range(joker_min, joker_max + 1)
        moves_range = range(moves_min, moves_max + 1)
        threshold_range = np.arange(threshold_min, threshold_max + step, step)
        total_combinations = len(joker_range) * len(moves_range) * len(threshold_range)

        self.optimization_results = OptimizationResults()
        current_combination = 0

        try:
            for jokers, moves, threshold in itertools.product(joker_range, moves_range, threshold_range):
                # Adjust max moves based on joker count
                max_moves = 43 + jokers
                if moves > max_moves:
                    continue

                wins = 0
                total_jokers_found = 0

                for _ in range(sim_count):
                    game = SimulatedGame(moves, threshold, jokers)
                    won, remaining, stats = game.play_game()
                    if won:
                        wins += 1
                    total_jokers_found += stats['jokers_drawn']

                result = SimulationResults(
                    total_games=sim_count,
                    wins=wins,
                    losses=sim_count - wins,
                    cards_left_in_losses=[],
                    boxes_left_in_wins=[],
                    moves_per_game=[],
                    inclusive_moves_used=[],
                    jokers_drawn=[total_jokers_found]
                )
                
                self.optimization_results.add_result(jokers, moves, threshold, result)
                
                # Update progress
                current_combination += 1
                self.update_progress(current_combination, total_combinations)

            # Display results summary
            self.display_results_summary()
            messagebox.showinfo("Complete", "Optimization completed successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during optimization: {str(e)}")
            self.progress_var.set(0)
            self.progress_label.config(text="0.00% Complete")

    def display_results_summary(self):
        """Display summary of top results"""
        if not self.optimization_results:
            return

        self.results_text.delete(1.0, tk.END)
        
        # Overall top 10 results
        self.results_text.insert(tk.END, "=== Top 10 Overall Configurations ===\n\n")
        for (jokers, moves, threshold), win_rate in self.optimization_results.get_top_results(10):
            self.results_text.insert(tk.END, 
                f"Win Rate: {win_rate:.2f}% - Jokers: {jokers}, "
                f"Moves: {moves}, Threshold: {threshold:.2f}%\n")

        # Top 5 by parameter
        for param, title in [('jokers', 'Joker Count'), 
                           ('moves', 'Inclusive Moves'), 
                           ('thresholds', 'Threshold')]:
            self.results_text.insert(tk.END, f"\n=== Top 5 by {title} ===\n\n")
            top_by_param = self.optimization_results.get_top_by_parameter(param, 5)
            
            for param_value, results in top_by_param.items():
                self.results_text.insert(tk.END, f"{title}: {param_value}\n")
                for win_rate, param1, param2 in results[:5]:
                    if param == 'jokers':
                        self.results_text.insert(tk.END, 
                            f"  {win_rate:.2f}% - Moves: {param1}, Threshold: {param2:.2f}%\n")
                    elif param == 'moves':
                        self.results_text.insert(tk.END, 
                            f"  {win_rate:.2f}% - Jokers: {param1}, Threshold: {param2:.2f}%\n")
                    else:
                        self.results_text.insert(tk.END, 
                            f"  {win_rate:.2f}% - Jokers: {param1}, Moves: {param2}\n")
                self.results_text.insert(tk.END, "\n")

        # Scroll to top
        self.results_text.see("1.0")

    def show_advanced_stats(self):
        """Show detailed statistics in a new window"""
        if not self.optimization_results:
            messagebox.showinfo("No Data", "Please run simulations first")
            return
            
        stats_window = tk.Toplevel(self.root)
        stats_window.title("Advanced Statistics")
        stats_window.geometry("600x800")

        # Create scrollable frame
        frame = ttk.Frame(stats_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create text widget
        stats_text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        scrollbar.config(command=stats_text.yview)

        # Calculate and display statistics
        stats_text.insert(tk.END, "=== Advanced Statistics ===\n\n")

        # Best Configuration
        jokers, moves, threshold = self.optimization_results.best_params
        stats_text.insert(tk.END, "Best Overall Configuration:\n")
        stats_text.insert(tk.END, 
            f"Jokers: {jokers}\n"
            f"Inclusive Moves: {moves}\n"
            f"Threshold: {threshold:.2f}%\n"
            f"Win Rate: {self.optimization_results.best_win_rate:.2f}%\n\n")

        # Statistics by Joker Count
        stats_text.insert(tk.END, "=== Performance by Joker Count ===\n\n")
        for joker_count in sorted(self.optimization_results.parameter_space['jokers']):
            results = [(m, t, r) for (j, m, t), r in self.optimization_results.results.items() 
                      if j == joker_count]
            if results:
                win_rates = [(r.wins/r.total_games*100, m, t) for m, t, r in results]
                best_rate, best_moves, best_threshold = max(win_rates)
                stats_text.insert(tk.END, 
                    f"Jokers: {joker_count}\n"
                    f"Best Win Rate: {best_rate:.2f}%\n"
                    f"Best Moves: {best_moves}\n"
                    f"Best Threshold: {best_threshold:.2f}%\n\n")

        # Statistics by Inclusive Move Range
        stats_text.insert(tk.END, "=== Performance by Inclusive Move Range ===\n\n")
        move_ranges = sorted(self.optimization_results.parameter_space['moves'])
        for moves in move_ranges:
            results = [(j, t, r) for (j, m, t), r in self.optimization_results.results.items() 
                      if m == moves]
            if results:
                win_rates = [(r.wins/r.total_games*100, j, t) for j, t, r in results]
                best_rate, best_jokers, best_threshold = max(win_rates)
                stats_text.insert(tk.END, 
                    f"Moves: {moves}\n"
                    f"Best Win Rate: {best_rate:.2f}%\n"
                    f"Best Jokers: {best_jokers}\n"
                    f"Best Threshold: {best_threshold:.2f}%\n\n")

        # Statistics by Threshold Range
        stats_text.insert(tk.END, "=== Performance by Threshold ===\n\n")
        thresholds = sorted(self.optimization_results.parameter_space['thresholds'])
        for threshold in thresholds:
            results = [(j, m, r) for (j, m, t), r in self.optimization_results.results.items() 
                      if abs(t - threshold) < 0.001]  # Float comparison
            if results:
                win_rates = [(r.wins/r.total_games*100, j, m) for j, m, r in results]
                best_rate, best_jokers, best_moves = max(win_rates)
                stats_text.insert(tk.END, 
                    f"Threshold: {threshold:.2f}%\n"
                    f"Best Win Rate: {best_rate:.2f}%\n"
                    f"Best Jokers: {best_jokers}\n"
                    f"Best Moves: {best_moves}\n\n")

        # Make text read-only
        stats_text.config(state='disabled')
        
        # Add close button
        ttk.Button(stats_window, text="Close", 
                  command=stats_window.destroy).pack(pady=10)

def main():
    root = tk.Tk()
    app = OptimizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()