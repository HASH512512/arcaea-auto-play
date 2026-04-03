from __future__ import annotations


class TouchEvent:
    def __init__(self, position, action, pointer, alpha=1.0):
        self.position = position
        self.pos = position
        self.action = action
        self.pointer = pointer
        self.alpha = alpha
