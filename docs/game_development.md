# Game Development Guide

This document provides comprehensive guidance for developing games on the Disobey 2025 Badge.

## Architecture Overview

Badge games follow a consistent architecture pattern with clear separation of concerns:

- **Screen Classes**: Handle UI, user input, and display logic
- **Game Classes**: Contain game logic and state management
- **Message Classes**: Define inter-badge communication protocols
- **Widget Classes**: Custom UI components specific to games

## Game Architecture Patterns

### 1. Single-File Games (Simple Games)

For simple games like Rock-Paper-Scissors, keep everything in one file:

```python
import hardware_setup as hardware_setup  # ALWAYS IMPORT FIRST
from gui.core.ugui import Screen, ssd
from gui.widgets import Label, Button, RadioButtons
from gui.core.writer import CWriter
from gui.fonts import arial35, font10
from gui.core.colors import *

class RpsScreen(Screen):
    def __init__(self, conn):
        super().__init__()
        self.game = RpsGame()  # Game logic separate class
        # UI setup...

class RpsGame:
    def __init__(self):
        self.scores = {"player": 0, "opponent": 0}
        # Game state...
```

### 2. Multi-File Games (Complex Games)

For complex games like Tic-Tac-Toe or Reaction Game, split into logical components:

```
tictac.py          # Main screen and game logic
tictac_widget.py   # Custom widgets (TTTBox)
tictac_messages.py # Message definitions (or in main file)
```

### 3. Screen Separation Pattern

For games with multiple screens, separate UI logic from game logic:

```python
class GameScreen(Screen):     # Handles UI and input
    def __init__(self, conn):
        self.game_logic = GameLogic()

class GameLogic:              # Pure game state and rules
    def __init__(self):
        self.state = "waiting"
```

## UI Framework Usage

### Essential Imports

```python
# CRITICAL: Always import hardware_setup FIRST
import hardware_setup as hardware_setup
from hardware_setup import BtnConfig, LED_PIN, LED_AMOUNT, LED_ACTIVATE_PIN

# GUI imports
from gui.core.ugui import Screen, ssd, display
from gui.core.writer import CWriter
from gui.widgets import Label, Button, RadioButtons
from gui.core.colors import *

# Async support
import asyncio
from badge.asyncbutton import ButtonEvents, ButAct
```

### Screen Management

```python
# Navigate to new screen
Screen.change(NewScreen, args=(param1,), kwargs={"param": value})

# Stack screen on top (can go back)
Screen.change(NewScreen, mode=Screen.STACK, args=(param1,))

# Go back to previous screen
Screen.back()
```

### Custom Widgets

Create game-specific widgets by extending `Widget`:

```python
class GameButton(Widget):
    def __init__(self, writer, row, col, radius, color, callback):
        super().__init__(writer, row, col, radius*2, radius*2,
                        color, color, False, False)
        self.callback = callback

    def show(self):
        if super().show():
            # Custom drawing code
            display.fillcircle(self.col + self.radius,
                             self.row + self.radius,
                             self.radius, self.fgcolor)
```

## Inter-Badge Communication

### Message Definition Pattern

```python
from badge.msg import AppMsg, BadgeMsg

@AppMsg.register
class GameStart(BadgeMsg):
    def __init__(self, player_id: str, game_mode: int):
        super().__init__()
        self.player_id = player_id
        self.game_mode = game_mode

@AppMsg.register
class GameMove(BadgeMsg):
    def __init__(self, move: int, timestamp: float):
        super().__init__()
        self.move = move
        self.timestamp = timestamp

@AppMsg.register
class GameEnd(BadgeMsg):
    def __init__(self, winner_id: str, final_score: int):
        super().__init__()
        self.winner_id = winner_id
        self.final_score = final_score
```

### Connection Handling

```python
class GameScreen(Screen):
    def __init__(self, conn: Connection):
        super().__init__()
        self.conn = conn

    def read_messages(self):
        """Called when new messages arrive"""
        while self.conn.queue_in.has_data():
            msg = self.conn.queue_in.read()
            if isinstance(msg, GameMove):
                self.handle_opponent_move(msg.move)
            elif isinstance(msg, GameEnd):
                self.handle_game_end(msg.winner_id)

    async def send_move(self, move):
        """Send move to opponent"""
        msg = GameMove(move, time.time())
        await self.conn.queue_out.put(msg)
```

## Performance Guidelines

### Memory Management

```python
# Use const() for game constants
from micropython import const
MAX_PLAYERS = const(2)
ROUND_TIME_MS = const(5000)

# Use __slots__ for game objects
class Player:
    __slots__ = ('name', 'score', 'moves')

# Monitor memory usage
import gc
print(f"Free memory: {gc.mem_free()} bytes")
gc.collect()  # Force cleanup between rounds
```

### Timing and Frame Rate

```python
# Target 10-15 FPS for smooth gameplay
FRAME_TIME_MS = const(67)  # ~15 FPS

async def game_loop(self):
    while self.running:
        start_time = time.ticks_ms()

        self.update_game_state()
        self.render_frame()

        # Maintain consistent frame rate
        elapsed = time.ticks_diff(time.ticks_ms(), start_time)
        sleep_time = max(0, FRAME_TIME_MS - elapsed)
        await asyncio.sleep_ms(sleep_time)
```

### Async Patterns

```python
# Use asyncio for non-blocking operations
async def highlight_button(self, duration_ms):
    self.button.set_highlight(True)
    await asyncio.sleep_ms(duration_ms)
    self.button.set_highlight(False)

# Handle multiple async tasks
async def game_timer(self, timeout_seconds):
    try:
        await asyncio.sleep(timeout_seconds)
        self.handle_timeout()
    except asyncio.CancelledError:
        pass  # Timer was cancelled

# Cancel tasks properly
self.timer_task = asyncio.create_task(self.game_timer(30))
# Later: self.timer_task.cancel()
```

## Navigation Patterns

### Screen Stack Management

The badge uses a sophisticated screen stack system to manage navigation between games and menus.

```python
from badge.games import change_app

# Navigate to a game, preventing duplicate stacking
def open_my_game():
    change_app(MyGameScreen, args=[param1], kwargs={"param": value})

# Standard screen changes
Screen.change(NewScreen, args=(param1,))          # Replace current screen
Screen.change(NewScreen, mode=Screen.STACK)       # Stack on top (can go back)
Screen.change(NewScreen, mode=Screen.REPLACE)     # Replace without history
Screen.back()                                     # Return to previous screen
```

### Smart Navigation Utility

Use `change_app()` for game navigation to prevent screen stacking issues:

```python
from badge.games import change_app

class GameMenuScreen(Screen):
    def __init__(self):
        super().__init__()
        Button(wri, 50, 50, text="Play RPS",
               callback=lambda btn: change_app(RpsScreen))
        Button(wri, 80, 50, text="Play Tic-Tac-Toe",
               callback=lambda btn: change_app(TicTacScreen))
```

### Navigation Buttons

Create navigation buttons using the helper function:

```python
from badge.games import fwdbutton

class GameScreen(Screen):
    def __init__(self):
        super().__init__()
        wri = CWriter(ssd, font10, WHITE, BLACK)

        # Create forward navigation button
        row = fwdbutton(wri, 140, 50, NextScreen, text="Continue")

        # Multiple navigation options
        fwdbutton(wri, row, 50, GameModeScreen, text="Competitive")
        fwdbutton(wri, row, 200, CasualScreen, text="Casual")
```

## Widget Patterns

### Essential Widget Imports

```python
from gui.widgets import Label, Button, RadioButtons, LED
from gui.widgets.buttons import Button
from gui.widgets.region import Region
from bdg.widgets.hidden_active_widget import HiddenActiveWidget
from bdg.widgets.meter import Meter
```

### Custom Game Widgets

Extend the base `Widget` class for game-specific components:

```python
class GameButton(Widget):
    def __init__(self, writer, row, col, radius, color, hl_color, callback):
        radius -= 2  # Account for borders
        super().__init__(writer, row, col, radius*2, radius*2,
                        color, color, False, False)
        self.radius = radius
        self.active = False
        self.hl = False
        self.hl_color = hl_color
        self.callback = callback

    def show(self):
        if super().show():
            c = self.hl_color if self.hl else self.fgcolor
            display.fillcircle(self.col + self.radius,
                             self.row + self.radius,
                             self.radius, c)
            if self.active:
                self.draw_bd(WHITE)

    def set_highlight(self, value):
        self.hl = value
        self.show()
```

### Widget State Management

```python
class GameWidget(Widget):
    def __init__(self, writer, row, col, **kwargs):
        super().__init__(writer, row, col, **kwargs)
        self.game_state = "idle"

    def set_state(self, new_state):
        """Update widget appearance based on game state"""
        self.game_state = new_state
        if new_state == "active":
            self.fgcolor = GREEN
        elif new_state == "disabled":
            self.fgcolor = GRAY
        self.show()
```

### Hidden Active Widget Pattern

For screens that need immediate continuation logic:

```python
class ConditionalScreen(Screen):
    def __init__(self):
        super().__init__()

        # Check if we should skip this screen
        if self.should_skip():
            # Create minimal UI for after_open continuation
            wri = CWriter(ssd, font10, WHITE, BLACK)
            HiddenActiveWidget(wri)  # Invisible widget to make screen valid
        else:
            self.create_full_ui()

    def after_open(self):
        """Handle continuation after screen is fully initialized"""
        if self.should_skip():
            Screen.change(NextScreen)  # Safe to change screens here
```

## Critical Screen Lifecycle Information

### ⚠️ Screen Initialization Timing

**IMPORTANT**: You cannot change screens during `__init__()`. Screen changes must happen in `after_open()`.

```python
class MyScreen(Screen):
    def __init__(self):
        super().__init__()
        # ❌ WRONG - Will cause white screen
        # if some_condition:
        #     Screen.change(OtherScreen)

        # ✅ CORRECT - Set up for after_open decision
        self.should_continue = some_condition
        if self.should_continue:
            # Create minimal UI
            wri = CWriter(ssd, font10, WHITE, BLACK)
            HiddenActiveWidget(wri)
        else:
            # Create full UI
            self.setup_full_ui()

    def after_open(self):
        """Called after screen is fully initialized"""
        if self.should_continue:
            Screen.change(NextScreen)  # ✅ Safe here
```

### Screen Initialization Best Practices

```python
class ConditionalGameScreen(Screen):
    def __init__(self, game_state=None):
        super().__init__()
        self.game_state = game_state

        # Always create some UI during init
        wri = CWriter(ssd, font10, WHITE, BLACK)

        if self._should_skip_to_results():
            # Minimal UI for immediate continuation
            HiddenActiveWidget(wri)
            self.skip_to_results = True
        else:
            # Full game UI
            self.skip_to_results = False
            self._create_game_ui(wri)

    def _should_skip_to_results(self):
        """Determine if we should skip directly to results"""
        return (self.game_state and
                self.game_state.get("completed", False))

    def after_open(self):
        """Handle post-initialization logic"""
        if self.skip_to_results:
            Screen.change(GameResultsScreen,
                         args=(self.game_state,))
```

## Game Structure Templates

### Casual Single-Player Game

```python
class CasualGameScreen(Screen):
    def __init__(self):
        super().__init__()
        self.score = 0
        self.level = 1
        self.setup_ui()

    def setup_ui(self):
        # Create UI elements
        pass

    def handle_input(self, button_event):
        # Process player input
        pass

    def update_score(self, points):
        self.score += points
        self.score_label.value(f"Score: {self.score}")
```

### Competitive Multi-Player Game

```python
class MultiPlayerGameScreen(Screen):
    def __init__(self, conn: Connection):
        super().__init__()
        self.conn = conn
        self.game_state = "waiting"
        self.player_moves = {}
        self.setup_ui()

    def read_messages(self):
        """Handle incoming messages from opponent"""
        while self.conn.queue_in.has_data():
            msg = self.conn.queue_in.read()
            self.process_message(msg)

    async def send_move(self, move):
        """Send move to opponent"""
        msg = GameMove(move)
        await self.conn.queue_out.put(msg)

    def determine_winner(self):
        """Implement game-specific win conditions"""
        pass
```

## Common Patterns and Utilities

### Game State Management

```python
from enum import IntEnum

class GameState(IntEnum):
    WAITING = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3

class Game:
    def __init__(self):
        self.state = GameState.WAITING

    def transition_to(self, new_state):
        print(f"State: {self.state} -> {new_state}")
        self.state = new_state
```

### Error Handling

```python
class GameError(Exception):
    pass

class InvalidMoveError(GameError):
    pass

try:
    self.make_move(move)
except InvalidMoveError as e:
    self.show_error_message(str(e))
except GameError as e:
    print(f"Game error: {e}")
    self.reset_game()
```

### Button Event Handling

```python
from badge.asyncbutton import ButtonEvents, ButAct

class GameScreen(Screen):
    def after_open(self):
        # Set up button handling
        self.button_events = ButtonEvents()
        self.reg_task(self.handle_buttons(), True)

    async def handle_buttons(self):
        async for button, event in self.button_events.get_btn_events():
            if button == "btn_a" and event == ButAct.ACT_PRESS:
                self.handle_action_button()
            elif button == "btn_start" and event == ButAct.ACT_PRESS:
                self.pause_game()
```

## Testing and Debugging

### Development Testing

```python
# Add debug prints for development
DEBUG = True

def debug_print(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}")

# Test game logic separately
def test_game_logic():
    game = MyGame()
    assert game.make_move(1) == "valid"
    assert game.check_winner() == None
```

### Memory Monitoring

```python
import gc

def log_memory(label=""):
    free = gc.mem_free()
    print(f"Memory {label}: {free} bytes free")

# Use at key points
log_memory("before game start")
self.start_game()
log_memory("after game start")
```

## Troubleshooting Common Issues

### White Screen / Blank Display

**Symptom**: Screen appears white or blank when navigating to your game
**Cause**: Attempting to change screens during `__init__()` instead of `after_open()`

```python
# ❌ CAUSES WHITE SCREEN
class BrokenScreen(Screen):
    def __init__(self):
        super().__init__()
        if some_condition:
            Screen.change(OtherScreen)  # Wrong! Too early!

# ✅ CORRECT APPROACH
class WorkingScreen(Screen):
    def __init__(self):
        super().__init__()
        # Always create some UI during init
        wri = CWriter(ssd, font10, WHITE, BLACK)
        if some_condition:
            HiddenActiveWidget(wri)  # Minimal valid UI
            self.should_redirect = True
        else:
            self.create_full_ui(wri)
            self.should_redirect = False

    def after_open(self):
        if self.should_redirect:
            Screen.change(OtherScreen)  # Safe here!
```

### Import Dependency Errors

**Symptom**: `NameError: name 'color_map' isn't defined` in GUI modules
**Cause**: Incorrect import order causing circular dependencies

```python
# ❌ WRONG ORDER
from gui.core.ugui import Screen, ssd
import hardware_setup as hardware_setup  # Too late!

# ✅ CORRECT ORDER
import hardware_setup as hardware_setup  # ALWAYS FIRST
from gui.core.ugui import Screen, ssd
```

### Message Communication Failures

**Symptom**: Messages not received between badges in multiplayer games
**Cause**: Missing message registration or incorrect connection handling

```python
# ✅ ENSURE MESSAGE REGISTRATION
@AppMsg.register  # Don't forget this decorator!
class GameMove(BadgeMsg):
    def __init__(self, move: int):
        super().__init__()
        self.move = move

# ✅ PROPER CONNECTION CHECK
def read_messages(self):
    if not self.conn or not self.conn.queue_in:
        return  # No connection available

    while self.conn.queue_in.has_data():
        msg = self.conn.queue_in.read()
        self.process_message(msg)
```

### Memory Issues in Long Games

**Symptom**: Badge crashes or becomes unresponsive after playing for a while
**Cause**: Memory leaks from unreleased objects or excessive memory usage

```python
# ✅ PROPER MEMORY MANAGEMENT
import gc

class LongRunningGame(Screen):
    def cleanup_round(self):
        # Clear large objects
        self.game_history = []
        self.cached_data = None

        # Force garbage collection
        gc.collect()

        # Monitor memory
        free_mem = gc.mem_free()
        if free_mem < 50000:  # Less than 50KB free
            print(f"Warning: Low memory {free_mem} bytes")
```

### Button Events Not Working

**Symptom**: Button presses don't trigger game actions
**Cause**: Button event handler not properly registered or async task not started

```python
# ✅ PROPER BUTTON HANDLING
from badge.asyncbutton import ButtonEvents, ButAct

class GameScreen(Screen):
    def __init__(self):
        super().__init__()
        self.button_events = ButtonEvents()
        # Don't start handler here - wait for after_open

    def after_open(self):
        # Start button handler after screen is ready
        self.reg_task(self.handle_buttons(), True)

    async def handle_buttons(self):
        async for button, event in self.button_events.get_btn_events():
            if button == "btn_a" and event == ButAct.ACT_PRESS:
                self.handle_action()
```

### Game State Synchronization Issues

**Symptom**: Multiplayer game states get out of sync between badges
**Cause**: Race conditions or missing state validation

```python
# ✅ PROPER STATE SYNCHRONIZATION
class MultiplayerGame:
    def __init__(self):
        self.state_lock = asyncio.Lock()
        self.game_state = "waiting"

    async def process_opponent_move(self, move):
        async with self.state_lock:
            if self.game_state != "playing":
                return  # Ignore moves in wrong state

            self.apply_move(move)
            self.validate_game_state()
```

## Best Practices

1. **Always import `hardware_setup` first** to avoid circular dependencies
2. **Never change screens in `__init__()`** - use `after_open()` for screen transitions
3. **Create minimal UI for conditional screens** using `HiddenActiveWidget` when skipping
4. **Use `change_app()` for game navigation** to prevent screen stacking issues
5. **Use async/await** for timing and non-blocking operations
6. **Separate UI from game logic** for maintainability
7. **Handle connection errors gracefully** in multiplayer games
8. **Monitor memory usage** especially in long-running games
9. **Use consistent naming** for messages and game states
10. **Test on actual hardware** - timing can differ from simulation
11. **Implement proper cleanup** when games end or screens change
12. **Register button handlers in `after_open()`** not in `__init__()`

## Example: Complete Simple Game

```python
import hardware_setup as hardware_setup
import asyncio
import random
from gui.core.ugui import Screen, ssd
from gui.widgets import Label, Button
from gui.core.writer import CWriter
from gui.fonts import font10, arial35
from gui.core.colors import *

class SimpleGame(Screen):
    def __init__(self):
        super().__init__()
        self.score = 0
        self.target = 0
        self.setup_ui()
        self.start_round()

    def setup_ui(self):
        wri = CWriter(ssd, font10, GREEN, BLACK)
        wri_big = CWriter(ssd, arial35, WHITE, BLACK)

        self.score_label = Label(wri, 10, 10, 100)
        self.target_label = Label(wri_big, 60, 10, 200)
        self.result_label = Label(wri, 120, 10, 200)

        Button(wri, 140, 50, text="Hit!", callback=self.hit_target)
        Button(wri, 140, 150, text="Miss!", callback=self.miss_target)

    def start_round(self):
        self.target = random.randint(1, 10)
        self.target_label.value(str(self.target))
        self.score_label.value(f"Score: {self.score}")
        self.result_label.value("")

    def hit_target(self, btn):
        if self.target <= 5:  # Hit is correct for low numbers
            self.score += 10
            self.result_label.value("Correct!")
        else:
            self.score -= 5
            self.result_label.value("Wrong!")
        self.schedule_next_round()

    def miss_target(self, btn):
        if self.target > 5:  # Miss is correct for high numbers
            self.score += 10
            self.result_label.value("Correct!")
        else:
            self.score -= 5
            self.result_label.value("Wrong!")
        self.schedule_next_round()

    def schedule_next_round(self):
        self.reg_task(self.next_round_delayed(), True)

    async def next_round_delayed(self):
        await asyncio.sleep(1.5)
        self.start_round()
```

This comprehensive guide should help developers create engaging, well-structured games for the badge!
