# Beat-the-Box-Card-Game
Beat the Box or Beat the Deck is a card game. The file allows you to play with an app aid to make the best moves, play the game in the app, optimize strategies, and simulate games

Beat the Box - Game Rules and Documentation

Overview:
Beat the Box is a probability-based card game where players try to get through a deck of cards by making correct predictions about card values. This app allows for 4 different apps to be used to best learn to play the game, and improve your gameplay.

1. Custom Game Mode
   - Select specific cards for initial setup
   - Choose cards to play from remaining deck
   - Full control over game progression
   - Ideal for practice and strategy testing
  
2. Game Player (Standard Mode)
   - Play the game with standard rules
   - Automatic card shuffling and dealing
   - Built-in probability calculations
   - Keyboard shortcuts for quick gameplay

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

The suite uses a consistent rule set across all components and maintains game state accurately throughout play.

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
   - Validate strategies with simulator
  
Notes:
The counter for each Card Counting Methods has an issue for the first undo. It will not undo the change on the count, but only for the first time you hit undo. All subsequent undo clicks will change and update the count.
This was also an issue faced when trying to undo the Higher/Equal or Lower/Equal count, which was fixed, but I could not figure out how to fix it with the Card Counting Method without changing the code for the gameplay and game statistics.

Suggestions:
For further updates I may work on, or if other want to, here are some of my thoughts.
1. Fix the counter for the Card Counting Methods
2. Improve graphics for Game Player and Game Aid
   a. Larger and more vibrant cards
   b. add a drag and drop for playing the cards
   c. Highlightes on card for which are the best to play
   d. Adding text and graphics for winning or losing
3. Add graphs for advanced statistics in the Simulator and Optimizer files
