def get_initial_facing(start: tuple[int, int], width: int, height: int) -> int:
    sx, sy = start
    if sy == 0:
        return 2  # Top wall -> face South
    if sx == width - 1:
        return 3  # Right wall -> face West
    if sy == height - 1:
        return 0  # Bottom wall -> face North
    return 1      # Left wall -> face East