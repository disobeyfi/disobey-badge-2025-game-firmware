from neopixel import NeoPixel

L_PINK = (0xFF, 0, 0xF0)


def dimm_gamma(current_colors, fraction, gamma=2.2) -> list[tuple[int, int, int]]:
    """
    Apply gamma-corrected dimming to each (R, G, B) color in the list.

    Parameters
    ----------
    current_colors : list of tuples
        Each tuple is (R, G, B), 0..255.
    fraction : float
        Dimming level [0..1]. 1 means full intensity, 0 means off.
    gamma : float
        Gamma value for human-perceived brightness correction.

    Returns
    -------
    list of tuples
        Gamma-corrected (R, G, B) values scaled by the given fraction.
    """

    def gamma_correct(channel):
        # Convert 0..255 to 0..1, raise to gamma (linear light),
        # scale by fraction, invert gamma, and convert back to 0..255.
        linear = (channel / 255.0) ** gamma  # channel in linear space
        dimmed_linear = linear * fraction  # apply dimming fraction
        corrected = dimmed_linear ** (1.0 / gamma)
        return int(round(corrected * 255))

    return [tuple(gamma_correct(c) for c in color) for color in current_colors]


def clear_leds(np: NeoPixel):
    for i in range(np.n):
        np[i] = (0, 0, 0)
    np.write()
