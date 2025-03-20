

class SimpleMessages:
    def __init__(self):
        self.history = []

    def add(self, role, content):
        self.history.append((role, content))
        return self  # 允许链式调用


