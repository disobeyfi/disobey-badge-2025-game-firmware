from gui.core.colors import BLACK, RECTANGLE, GREEN, D_PINK
from gui.core.ugui import Screen
from gui.widgets.buttons import Button


def change_app(cls_new_screen, args=[], kwargs={}, base_screen=None):
    # Change to cls_new_screen. if cls_new_screen is already open back up to it
    # if cls_new_screen is not open it will be opened on top of base_screen
    # This prevents quick buttons stacking same screen over and over

    if base_screen is None:
        # circular import issues without this :(
        from badge.games.badge_game import GameLobbyScr

        base_screen = GameLobbyScr

    # Check stack for existing screen and change target according
    current = Screen.current_screen
    target_to_back = base_screen
    print(f"change_app: {cls_new_screen=} {target_to_back=}")
    while current and base_screen is not cls_new_screen:
        if isinstance(current, cls_new_screen):
            print(f"change_app: {cls_new_screen} already on stack")
            target_to_back = cls_new_screen
            break
        current = current.parent

    # Navigate back until reaching target_screen, then stack new app on top
    while Screen.current_screen and not isinstance(
        Screen.current_screen, target_to_back
    ):
        Screen.back()

    if cls_new_screen is target_to_back:
        # we reached BaseScreen or cls_new_screen, nothing to add
        return
    # add new screen on top of Base screen
    Screen.change(cls_new_screen, mode=Screen.STACK, args=args, kwargs=kwargs)


def fwdbutton(wri, row, col, cls_screen, text='Next'):
    def fwd(button):
        Screen.change(cls_screen)
    b = Button(wri, row, col,
           callback = fwd, fgcolor = D_PINK, bgcolor = BLACK,
           text = text, shape = RECTANGLE, textcolor=D_PINK)
    return b.mrow