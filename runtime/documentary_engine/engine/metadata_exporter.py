from .normalizer import FPS


def clock(frame: int):
    minutes, seconds = divmod(frame // FPS, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"


def export(meta: dict, chapters: list, credits: list, destination):
    # YouTube requires at least three chapter starts and ten seconds per chapter.
    manual = ["Chapter markers (reference only)"]
    start_frames = [frame for frame, _ in chapters]
    end = meta["total_frames"]
    valid = len(chapters) >= 3 and all(b - a >= 10 * FPS for a, b in zip(start_frames, start_frames[1:] + [end]))
    marks = [f"{clock(frame)} {title}" for frame, title in chapters]
    sections = [meta["video_title"], meta["video_description"]]
    if valid:
        sections.extend(["Chapters\n" + "\n".join(marks)])
    else:
        sections.extend(["\n".join(manual + marks)])
    sections.append("Tags: " + ", ".join(meta.get("tags", [])))
    sections.append("Visual provenance\n" + "\n".join(
        f"{c['scene_id']}: " + " | ".join(str(c[k]) for k in ("provider", "title", "creator", "license", "license_url", "source_url", "modifications") if c.get(k))
        for c in credits))
    destination.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
