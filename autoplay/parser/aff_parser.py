from __future__ import annotations

import re

from easing import Easing

from autoplay.domain.chart import Arc, ArcTap, Chart, Hold, Tap, Timing, TimingGroup
from autoplay.domain.errors import IgnoreDesignantLine, MissingDesignantChoiceError


IDENTIFIER_RE = re.compile(
    r"(?<=[\(, ])(\b(?!true|false|none|\d+\.?\d*|s|b|so|si|soso|sisi|sosi|siso)\w+\b)(?=[,\) ])"
)


def _parse_timinggroup_properties(properties_str: str) -> dict:
    properties: dict = {}
    for item in properties_str.split("_"):
        token = item.strip()
        if not token:
            continue
        if token.startswith("anglex"):
            try:
                properties["anglex"] = int(token[7:] if token.startswith("anglex=") else token[6:])
            except ValueError:
                properties[token] = True
        elif token.startswith("angley"):
            try:
                properties["angley"] = int(token[7:] if token.startswith("angley=") else token[6:])
            except ValueError:
                properties[token] = True
        else:
            properties[token] = True

    for item in properties_str.split(","):
        token = item.strip()
        if not token:
            continue
        if "=" in token:
            key, raw_value = token.split("=", 1)
            key = key.strip()
            value = raw_value.strip()
            lower = value.lower()
            if lower == "true":
                properties[key] = True
            elif lower == "false":
                properties[key] = False
            elif lower == "none":
                properties[key] = None
            elif value.isdigit():
                properties[key] = int(value)
            else:
                try:
                    properties[key] = float(value)
                except ValueError:
                    properties[key] = value
        else:
            properties["type"] = token

    return properties


def parse_aff_chart(content: str, designant_choice: bool | None = None) -> Chart:
    lines = content.splitlines()
    options: dict[str, str] = {}
    notes: list = []

    index = 0
    while index < len(lines):
        line = lines[index]
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        options[key.strip()] = value.strip()
        index += 1

    lcls = {
        "true": True,
        "false": False,
        "none": None,
        "arc": Arc,
        "tap": Tap,
        "arctap": ArcTap,
        "hold": Hold,
        "timing": Timing,
        "timinggroup": TimingGroup,
        "s": Easing.Linear,
        "b": Easing.CubicBezier,
        "so": Easing.So,
        "si": Easing.Si,
        "soso": Easing.SoSo,
        "sisi": Easing.SiSi,
        "sosi": Easing.SoSi,
        "siso": Easing.SiSo,
    }

    stack: list[tuple[list, dict | None]] = []
    current_notes = notes
    current_properties = None

    for raw_line in lines[index:]:
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        if line.lower().startswith("scenecontrol"):
            continue

        if line.startswith("timinggroup"):
            attr_start = line.find("(")
            attr_end = line.rfind(")")
            if attr_start == -1 or attr_end == -1:
                continue
            properties_str = line[attr_start + 1 : attr_end]
            properties = _parse_timinggroup_properties(properties_str)
            stack.append((current_notes, current_properties))
            group = TimingGroup(properties, [])
            current_notes.append(group)
            current_notes = group.notes
            current_properties = properties
            continue

        if line.startswith("};"):
            if stack:
                current_notes, current_properties = stack.pop()
            continue

        if line.endswith(";"):
            line = line[:-1]

        expression = IDENTIFIER_RE.sub(r'"\1"', line)
        try:
            note = eval(expression, {}, lcls)
            if isinstance(note, tuple):
                note = Tap(*note)

            if isinstance(note, Arc) and isinstance(note.trace_arc, str) and note.trace_arc.lower() == "designant":
                if designant_choice is None:
                    raise MissingDesignantChoiceError()
                if not designant_choice:
                    raise IgnoreDesignantLine()
                note.trace_arc = True
            elif isinstance(note, Arc) and isinstance(note.trace_arc, str):
                note.trace_arc = note.trace_arc.lower() == "true"

            current_notes.append(note)
        except IgnoreDesignantLine:
            continue
        except MissingDesignantChoiceError:
            raise
        except Exception as exc:
            print(f"Error parsing line: {line}\\n{exc}")

    return Chart(notes, options)


__all__ = ["MissingDesignantChoiceError", "parse_aff_chart"]
