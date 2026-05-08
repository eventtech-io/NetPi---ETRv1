
"""Built-in fixture profiles for common DMX fixtures."""

FIXTURE_PROFILES = {
    "generic_dimmer": {
        "id": "generic_dimmer",
        "name": "Generic Dimmer",
        "manufacturer": "Generic",
        "model": "Dimmer",
        "modes": {
            "1ch": {
                "name": "1 Channel",
                "channel_count": 1,
                "channels": [
                    {"name": "Dimmer", "offset": 0, "type": "dimmer"},
                ],
            },
        },
    },
    "generic_rgb": {
        "id": "generic_rgb",
        "name": "Generic RGB",
        "manufacturer": "Generic",
        "model": "RGB Par",
        "modes": {
            "3ch": {
                "name": "3 Channel",
                "channel_count": 3,
                "channels": [
                    {"name": "Red", "offset": 0, "type": "color"},
                    {"name": "Green", "offset": 1, "type": "color"},
                    {"name": "Blue", "offset": 2, "type": "color"},
                ],
            },
            "4ch": {
                "name": "4 Channel (RGB + Dimmer)",
                "channel_count": 4,
                "channels": [
                    {"name": "Red", "offset": 0, "type": "color"},
                    {"name": "Green", "offset": 1, "type": "color"},
                    {"name": "Blue", "offset": 2, "type": "color"},
                    {"name": "Dimmer", "offset": 3, "type": "dimmer"},
                ],
            },
            "7ch": {
                "name": "7 Channel",
                "channel_count": 7,
                "channels": [
                    {"name": "Dimmer", "offset": 0, "type": "dimmer"},
                    {"name": "Red", "offset": 1, "type": "color"},
                    {"name": "Green", "offset": 2, "type": "color"},
                    {"name": "Blue", "offset": 3, "type": "color"},
                    {"name": "Strobe", "offset": 4, "type": "effect"},
                    {"name": "Macro", "offset": 5, "type": "effect"},
                    {"name": "Speed", "offset": 6, "type": "speed"},
                ],
            },
        },
    },
    "generic_rgba": {
        "id": "generic_rgba",
        "name": "Generic RGBA",
        "manufacturer": "Generic",
        "model": "RGBA Par",
        "modes": {
            "4ch": {
                "name": "4 Channel",
                "channel_count": 4,
                "channels": [
                    {"name": "Red", "offset": 0, "type": "color"},
                    {"name": "Green", "offset": 1, "type": "color"},
                    {"name": "Blue", "offset": 2, "type": "color"},
                    {"name": "Amber", "offset": 3, "type": "color"},
                ],
            },
            "5ch": {
                "name": "5 Channel (RGBA + Dimmer)",
                "channel_count": 5,
                "channels": [
                    {"name": "Red", "offset": 0, "type": "color"},
                    {"name": "Green", "offset": 1, "type": "color"},
                    {"name": "Blue", "offset": 2, "type": "color"},
                    {"name": "Amber", "offset": 3, "type": "color"},
                    {"name": "Dimmer", "offset": 4, "type": "dimmer"},
                ],
            },
        },
    },
    "generic_rgbw": {
        "id": "generic_rgbw",
        "name": "Generic RGBW",
        "manufacturer": "Generic",
        "model": "RGBW Par",
        "modes": {
            "4ch": {
                "name": "4 Channel",
                "channel_count": 4,
                "channels": [
                    {"name": "Red", "offset": 0, "type": "color"},
                    {"name": "Green", "offset": 1, "type": "color"},
                    {"name": "Blue", "offset": 2, "type": "color"},
                    {"name": "White", "offset": 3, "type": "color"},
                ],
            },
            "5ch": {
                "name": "5 Channel (RGBW + Dimmer)",
                "channel_count": 5,
                "channels": [
                    {"name": "Red", "offset": 0, "type": "color"},
                    {"name": "Green", "offset": 1, "type": "color"},
                    {"name": "Blue", "offset": 2, "type": "color"},
                    {"name": "White", "offset": 3, "type": "color"},
                    {"name": "Dimmer", "offset": 4, "type": "dimmer"},
                ],
            },
        },
    },
    "moving_head_16ch": {
        "id": "moving_head_16ch",
        "name": "Moving Head (16ch)",
        "manufacturer": "Generic",
        "model": "Moving Head",
        "modes": {
            "16ch": {
                "name": "16 Channel",
                "channel_count": 16,
                "channels": [
                    {"name": "Pan", "offset": 0, "type": "pan"},
                    {"name": "Pan Fine", "offset": 1, "type": "pan"},
                    {"name": "Tilt", "offset": 2, "type": "tilt"},
                    {"name": "Tilt Fine", "offset": 3, "type": "tilt"},
                    {"name": "Speed", "offset": 4, "type": "speed"},
                    {"name": "Dimmer", "offset": 5, "type": "dimmer"},
                    {"name": "Strobe", "offset": 6, "type": "effect"},
                    {"name": "Red", "offset": 7, "type": "color"},
                    {"name": "Green", "offset": 8, "type": "color"},
                    {"name": "Blue", "offset": 9, "type": "color"},
                    {"name": "White", "offset": 10, "type": "color"},
                    {"name": "Color Macro", "offset": 11, "type": "effect"},
                    {"name": "Gobo", "offset": 12, "type": "gobo"},
                    {"name": "Prism", "offset": 13, "type": "effect"},
                    {"name": "Focus", "offset": 14, "type": "focus"},
                    {"name": "Reset", "offset": 15, "type": "control"},
                ],
            },
        },
    },
}


def get_profile(profile_id: str) -> dict | None:
    return FIXTURE_PROFILES.get(profile_id)


def list_profiles() -> list[dict]:
    return list(FIXTURE_PROFILES.values())


def get_profile_modes(profile_id: str) -> dict:
    profile = FIXTURE_PROFILES.get(profile_id)
    if not profile:
        return {}
    return profile.get("modes", {})
