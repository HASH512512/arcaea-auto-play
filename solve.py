from autoplay.solver.coordinate import CoordConv
from autoplay.solver.core import solve_4k as solve
from autoplay.solver.events import TouchEvent


def distance_of(pos1, pos2):
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5


if __name__ == "__main__":
    conv = CoordConv((760, 920), (650, 340), (1690, 340), (1580, 920))
    print(conv(0, 0))
    print(conv(0.5, 0))
    print(conv(0.5, 0.5))
    print(conv(1, 1))
    print(conv(-0.5, 0))
    print(conv(1.5, 0))


__all__ = ["CoordConv", "TouchEvent", "distance_of", "solve"]
