"""Check project role definitions and the shot, asset and dialogue CSV handoff."""

import argparse
import csv
import re
import sys
import tomllib
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def validate_roles_and_skills():
    role_paths = sorted((ROOT / ".codex" / "agents").glob("*.toml"))
    skill_paths = sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md"))
    if not role_paths or not skill_paths:
        raise ValueError("The project must contain role and skill files")

    roles = set()
    for path in role_paths:
        with path.open("rb") as file:
            role = tomllib.load(file)
        for field in ("name", "description", "developer_instructions"):
            if not isinstance(role.get(field), str) or not role[field].strip():
                raise ValueError(f"{path.name}: missing or invalid {field}")
        name = role["name"]
        expected = path.stem.replace("-", "_")
        if name != expected or name in roles:
            raise ValueError(f"{path.name}: expected unique role name {expected}")
        roles.add(name)

    skills = set()
    for path in skill_paths:
        content = path.read_text(encoding="utf-8")
        # The starter uses one-line, plain name and description fields.
        match = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: (\S[^\n]*)\n---\n", content)
        if not match or match[1] != path.parent.name or match[1] in skills:
            raise ValueError(f"{path.parent.name}: invalid or duplicate skill frontmatter")
        skills.add(match[1])
    return len(roles), len(skills)


def read_csv(path, required_fields):
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(required_fields) <= set(fields):
            raise ValueError(f"{path.name}: expected unique columns including {', '.join(required_fields)}")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path.name}:{reader.line_num}: incorrect number of columns")
            rows.append({key: value.strip() for key, value in row.items()})
    return rows


def index_rows(rows, column, file_name):
    index = {}
    for row in rows:
        value = row[column]
        if not value or value in index:
            raise ValueError(f"{file_name}: duplicate or blank {column}: {value!r}")
        index[value] = row
    return index


def validate_package(package):
    shot_fields = ("shot_id", "scene_id", "seconds", "method", "description", "camera",
                   "asset_ids", "dialogue_ids", "vertical_note")
    asset_fields = ("asset_id", "kind", "source", "rights_status", "evidence")
    dialogue_fields = ("dialogue_id", "scene_id", "speaker", "language", "line", "performance_note")
    shots = index_rows(read_csv(package / "shot-list.csv", shot_fields), "shot_id", "shot-list.csv")
    assets = index_rows(read_csv(package / "assets.csv", asset_fields), "asset_id", "assets.csv")
    dialogue = index_rows(read_csv(package / "dialogue.csv", dialogue_fields), "dialogue_id", "dialogue.csv")
    if not shots:
        raise ValueError("shot-list.csv: at least one planned shot is required")

    duration = Decimal(0)
    for shot_id, shot in shots.items():
        if any(not shot[key] for key in ("scene_id", "method", "description", "camera")):
            raise ValueError(f"{shot_id}: incomplete shot directions")
        try:
            seconds = Decimal(shot["seconds"])
        except InvalidOperation as error:
            raise ValueError(f"{shot_id}: invalid shot duration") from error
        if not seconds.is_finite() or seconds <= 0:
            raise ValueError(f"{shot_id}: shot duration must be positive and finite")
        duration += seconds

        for asset_id in filter(None, map(str.strip, shot["asset_ids"].split(";"))):
            if asset_id not in assets:
                raise ValueError(f"{shot_id}: unknown asset {asset_id}")
        for cue_id in filter(None, map(str.strip, shot["dialogue_ids"].split(";"))):
            if cue_id not in dialogue:
                raise ValueError(f"{shot_id}: unknown dialogue cue {cue_id}")
            if dialogue[cue_id]["scene_id"] != shot["scene_id"]:
                raise ValueError(f"{shot_id}: dialogue cue {cue_id} belongs to another scene")
    return len(shots), len(assets), len(dialogue), duration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ROOT / "examples" / "meter-room")
    args = parser.parse_args()
    try:
        roles, skills = validate_roles_and_skills()
        shots, assets, cues, duration = validate_package(args.package)
    except (OSError, ValueError, csv.Error) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    print(f"Validated {roles} role definitions and {skills} skill headers")
    print(f"Validated {shots} shots, {assets} assets and {cues} dialogue cues ({duration} planned seconds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
