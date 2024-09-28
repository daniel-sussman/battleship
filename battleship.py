from pynput import keyboard
import os, string, copy, random

class Game():
    def __init__(self, handler):
        self.handler = handler
        self.view = View(self)
        self.gridsize = 10
        self.target_grid = Grid(self, '~')
        self.own_grid = Grid(self, ' ')
        self.selector_index = 0
        self.menu_options = []
        self.ephemeral = ""
        self.setup()
    
    def setup(self):
        self.generate_ships()
        self.place_ships()

    def move_cursor(self, dir):
        self.active_grid.move_cursor(dir)
        self.view.display()

    def move_selector(self, incr):
        if any(self.menu_options):
            self.selector_index = (self.selector_index + incr) % len(self.menu_options)
            self.active_grid.option_selected(self.menu_options[self.selector_index])
            self.view.display()
            return True
        else:
            return False

    def rotate_cursor(self):
        self.active_grid.rotate_cursor()
        self.view.display()

    def place_ship(self):
        self.active_grid.place_ship(self.menu_options[self.selector_index])
        self.view.display()

    def player_shoots(self):
        self.ephemeral = self.target_grid.take_a_shot('You')
        if not any(self.target_grid.ships_afloat()):
            self.you_win()
        self.view.display()
        self.handler.pause_handler(self.opponent_turn)

    def generate_ships(self):
        self.own_grid.generate_ships()
        self.target_grid.generate_ships(random=True)

    def next_ship(self):
        if not self.move_selector(0):
            self.do_battle()

    def place_ships(self):
        self.own_grid.activate('placement')
        self.message = 'Place your ships!'
        self.menu_options = list(self.active_grid.ships.keys())
        self.view.display()

    def do_battle(self):
        self.own_grid.deactivate()
        self.target_grid.activate('battle')
        self.enemy = Enemy(self.own_grid.grid)
        self.message = 'Battle!'
        self.view.display()

    def opponent_turn(self):
        self.ephemeral = self.own_grid.take_a_shot('The enemy', self.enemy.calculate())
        self.view.display()
    
    def you_win(self):
        self.message = 'You are victorious!'
        self.view.display()
        raise(keyboard.Listener.StopException)


class Enemy():
    def __init__(self, target_grid):
        self.target_grid = target_grid
        self.target = None

    def calculate(self):
        if not self.target:
            return self._fire_randomly()
    
    def _fire_randomly(self):
        coordinates_valid = False
        while not coordinates_valid:
            x = random.randint(0, len(self.target_grid) - 1)
            y = random.randint(0, len(self.target_grid) - 1)
            if not self.target_grid[y][x] in ['X', '•']:
                coordinates_valid = True
        return (x, y)

class Grid():
    def __init__(self, game, char):
        self.game = game
        self.gridsize = self.game.gridsize
        self.grid = self.generate_grid(self.gridsize, char)
        self.deactivate()

    def generate_grid(self, gridsize, char):
        return [[char for _ in range(gridsize)] for _ in range(gridsize)]
    
    def generate_ships(self, random=False):
        self.ships = {
            'Carrier': [[], [], [], [], []],
            'Battleship': [[], [], [], []],
            'Cruiser': [[], [], []],
            'Submarine': [[], [], []],
            'Destroyer': [[], []]
        }
        if random:
            self._place_all_ships()
    
    def ships_afloat(self):
        return [ship for (ship, arr) in self.ships.items() if any(c for c in arr if c[2] == False)]
    
    def activate(self, mode):
        self.game.active_grid = self
        if mode == 'placement':
            self.cursor = [[0], [0, 1, 2, 3, 4]]
        else:
            self.cursor = [[0], [0]]
    
    def deactivate(self):
        self.cursor = []

    def place_ship(self, ship):
        cells = self._cursor_cells()
        if self._cursor_overlap(cells):
            self.game.ephemeral = 'Ships cannot overlap other ships'
            return False
        for (i, cell) in enumerate(cells):
            self.grid[cell[1]][cell[0]] = ship[0].upper() if ship in ['Carrier', 'Battleship'] else ship[0].lower()
            self.ships[ship][i] = [cell[0], cell[1], False]
        self.game.menu_options.remove(ship)
        self.game.next_ship()

    def _place_all_ships(self):
        for ship in self.ships:
            ship_size = len(self.ships[ship])
            placement_invalid = True
            
            while placement_invalid:
                orientation = random.randint(0, 1)
                pivot = [random.randint(0, self.gridsize - ship_size ** (orientation ^ 1)), random.randint(0, self.gridsize - ship_size ** orientation)]
                ship_cells = self._extend_from_pivot(pivot, ship_size, orientation)
                already_taken = self._get_filled_cells()
                if not any([c for c in ship_cells if c in already_taken]):
                    placement_invalid = False
            
            self.ships[ship] = [[x, y, False] for x, y in ship_cells]

    def _extend_from_pivot(self, pivot, ship_size, orientation):
        x = [pivot[0] + i * (orientation ^ 1) for i in range(ship_size)]
        y = [pivot[1] + j * orientation for j in range(ship_size)]
        return list(zip(x, y))

    def _get_filled_cells(self):
        filled_cells = []
        for arr in self.ships.values():
            filled_cells.extend([(cell[0], cell[1]) for cell in arr if any(cell)])
        return filled_cells
        
    def _cursor_cells(self):
        cursor_size = len(self.cursor[0]) * len(self.cursor[1])
        x_values = self.cursor[0] * len(self.cursor[1])
        y_values = self.cursor[1] * len(self.cursor[0])
        return [(x_values[i], y_values[i]) for i in range(cursor_size)]
    
    def _cursor_overlap(self, cursor_cells):
        return any([c for c in cursor_cells if self.grid[c[1]][c[0]] != ' '])
    
    def is_active_grid(self):
        return any(self.cursor)
    
    def move_cursor(self, dir):
        old_position = [i for i in self.cursor]
        for i, value in enumerate(dir):
            self.cursor[i] = [(j + value) % self.gridsize for j in self.cursor[i]]
        return self._validate_cursor(old_position)
    
    def resize_cursor(self, new_size):
        i = 1 if self.cursor_vertical() else 0
        current_size = len(self.cursor[i])

        if current_size == new_size:
            pass
        elif current_size > new_size:
            self.cursor[i] = self.cursor[i][:new_size]
        else:
            self._safely_increase_cursor_size(i, new_size - current_size)
    
    def rotate_cursor(self, dir='ccw'):
        unchanged = [i for i in self.cursor]
        pivot = (self.cursor[0][0], self.cursor[1][0])
        if self.cursor_vertical():
            if dir == 'ccw':
                self.cursor[0] = [i + pivot[0] for i in range(len(self.cursor[1]))] 
            else:
                self.cursor[0] = [pivot[0] - i for i in range(len(self.cursor[1]))]
            self.cursor[1] = [pivot[1]]
        else: # cursor is horizontal
            if dir == 'ccw':
                self.cursor[1] = [i + pivot[1] for i in range(len(self.cursor[0]))]
            else:
                self.cursor[1] = [pivot[1] - i for i in range(len(self.cursor[0]))]
            self.cursor[0] = [pivot[0]]

        if not self._validate_cursor(unchanged) and dir == 'ccw':
            self.rotate_cursor('cw')
    
    def take_a_shot(self, player, target=None, miss='•'):
        if player == 'You':
            target = (self.cursor[0][0], self.cursor[1][0])
            miss = ' '
            if self.grid[target[1]][target[0]] == 'X' or self.grid[target[1]][target[0]] == ' ':
                return "You've already targeted that cell."

        hit = False
        sunk = None
        for ship in self.ships_afloat():
            for cell in self.ships[ship]:
                if target == (cell[0], cell[1]):
                    cell[2] = True
                    hit = True
                    if not ship in self.ships_afloat():
                        sunk = ship
                    break

        self.grid[target[1]][target[0]] = 'X' if hit else miss
        ephemeral = 'A direct hit!' if hit else f'{player} missed!'
        if sunk:
            ephemeral += f" {player} sank the enemy's {sunk}!" if player == 'You' else f" {player} sank your {sunk}!"
        return ephemeral

    def _safely_increase_cursor_size(self, d, incr):
        old_position = copy.deepcopy(self.cursor)

        self.cursor[d].extend([j + self.cursor[d][-1] + 1 for j in range(incr)])
        if not self._validate_cursor(old_position):
            self.cursor[d] = [j + self.cursor[d][0] - incr for j in range(incr)] + self.cursor[d]

    def cursor_vertical(self):
        return len(self.cursor[0]) == 1
    
    def display_row(self, row_index):
        l = '[' if self.game.own_grid == self else ' '
        r = ']' if self.game.own_grid == self else ' '
        if self.is_active_grid() and row_index in self.cursor[1]:
            return [f":{cell}:" if i in self.cursor[0] else f"{l}{cell}{r}" for (i, cell) in enumerate(self.grid[row_index])]
        else:
            return [f"{l}{cell}{r}" for cell in self.grid[row_index]]
    
    def option_selected(self, option):
        if option in self.ships:
            self.resize_cursor(len(self.ships[option]))
        
    def _cursor_position_invalid(self):
        if any(i for i in self.cursor[0] + self.cursor[1] if i >= self.gridsize): # only checks overflow, not underflow
            return True
        return {self.gridsize - 1, 0}.issubset(set(self.cursor[0])) or {self.gridsize - 1, 0}.issubset(set(self.cursor[1]))
    
    def _validate_cursor(self, unchanged):
        if self._cursor_position_invalid():
            self.cursor = unchanged
            return False
        else:
            return True
        
    def reveal_all_ships(self):
        for ship in self.ships:
            for cell in self.ships[ship]:
                if cell[2]:
                    self.grid[cell[1]][cell[0]] = 'X'
                else:
                    self.grid[cell[1]][cell[0]] = 'O'


class View():
    def __init__(self, game):
        self.game = game
    
    def display(self):
        os.system('clear')
        print('   ', *[f" {c} " for c in string.ascii_uppercase[:10]], '\n')
        for i in range(self.game.target_grid.gridsize):
            print(f"{i + 1: >2} ", *self.game.target_grid.display_row(i))
        print()
        for i in range(self.game.own_grid.gridsize):
            print(f"{i + 1: >2} ", *self.game.own_grid.display_row(i))
        print()
        self.display_status_bar()

    def display_status_bar(self):
        message = self.game.message
        if self.game.ephemeral:
            message += f" ** ({self.game.ephemeral})"
            self.game.ephemeral = ""
        print(message)
        if any(self.game.menu_options):
            print()
            print(*[self.parse_option(option, i) for (i, option) in enumerate(self.game.menu_options)])
        if self.game.message == 'Battle!':
            print('\nScorecard:', 'Your ships:', len(self.game.own_grid.ships_afloat()), "  The enemy's ships:", len(self.game.target_grid.ships_afloat()))

    def parse_option(self, option, i):
        return " -> " + option if self.game.selector_index == i else "    " + option


class KeyboardHandler():
    def __init__(self):
        self.game = Game(self)
        self.pause = False
        self.paused_function = None

    def pause_handler(self, function):
        self.paused_function = function
        self.pause = True
        print('\nPress space or enter to continue.')

    def handle_space(self):
        if self.pause:
            self.pause = False
            return self.paused_function()
        
        if self.game.active_grid == self.game.own_grid:
            self.game.place_ship()
        else:
            self.game.player_shoots()

    def handle_tab(self):
        if self.pause:
            return
        if self.game.active_grid == self.game.own_grid:
            self.game.rotate_cursor()

    def move_cursor(self, dir):
        if self.pause:
            return
        self.game.move_cursor(dir)

    def move_selector(self, incr):
        if self.pause:
            return
        if any(self.game.menu_options):
            self.game.move_selector(incr)


def on_press(key, handler):
    if key == keyboard.Key.space:
        handler.handle_space()
    elif key == keyboard.Key.enter:
        handler.handle_space()
    elif key == keyboard.Key.tab:
        handler.handle_tab()
    elif key == keyboard.Key.left:
        handler.move_cursor((-1, 0))
    elif key == keyboard.Key.right:
        handler.move_cursor((1, 0))
    elif key == keyboard.Key.up:
        handler.move_cursor((0, -1))
    elif key == keyboard.Key.down:
        handler.move_cursor((0, 1))
    elif key == keyboard.KeyCode.from_char('z'):
        handler.move_selector(-1)
    elif key == keyboard.KeyCode.from_char('x'):
        handler.move_selector(1)

def on_release(key):
    if key == keyboard.Key.esc:
        os.system('clear')
        return False

handler = KeyboardHandler()

with keyboard.Listener(
    on_press=lambda key: on_press(key, handler),
    on_release=on_release,
    suppress=True
) as listener:
    listener.join()

