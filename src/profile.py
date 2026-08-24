import json
import os

PROFILE_PATH = "profile.json"


class PlayerProfile:
    def __init__(self):
        self.top_speed_mod = 1.0
        self.accel_mod = 1.0
        self.handling_mod = 1.0
        self.color = (255, 0, 0)  # Default Red
        self.load()

    def load(self):
        if os.path.exists(PROFILE_PATH):
            try:
                with open(PROFILE_PATH, "r") as f:
                    data = json.load(f)
                self.top_speed_mod = data.get("top_speed_mod", 1.0)
                self.accel_mod = data.get("accel_mod", 1.0)
                self.handling_mod = data.get("handling_mod", 1.0)
                self.color = tuple(data.get("color", (255, 0, 0)))
            except Exception:  # noqa: BLE001, S110
                pass

    def save(self):
        data = {
            "top_speed_mod": self.top_speed_mod,
            "accel_mod": self.accel_mod,
            "handling_mod": self.handling_mod,
            "color": self.color,
        }
        try:
            with open(PROFILE_PATH, "w") as f:
                json.dump(data, f, indent=4)
        except Exception:  # noqa: BLE001, S110
            pass
