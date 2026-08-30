"""
commands.py
-----------
Every "/word ..." you type gets routed here instead of going to the AI.
This is the extension point: Phase 2 will register /trailer and
/musicvideo here, Phase 3 will register /open and /file, etc.

To add a new command:
1. Write a function `def cmd_foo(args: str) -> str:`
2. Add it to the COMMANDS dict at the bottom
"""

from pathlib import Path

from ai_brain import memory, config, files, computer, voice, ai_client


def cmd_help(args: str) -> str:
    lines = ["Available commands:"]
    for name, fn in COMMANDS.items():
        doc = (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""
        lines.append(f"  /{name:<10} {doc}")
    lines.append("  (anything else) -> sent to the AI as a normal message")
    return "\n".join(lines)


def cmd_clear(args: str) -> str:
    """Clear the current chat memory/history."""
    memory.clear_history()
    return "Chat history cleared."


def cmd_quit(args: str) -> str:
    """Exit the program."""
    raise SystemExit


def cmd_trailer(args: str) -> str:
    """Build a trailer: /trailer <project_name> | <movie idea>"""
    if "|" not in args:
        return ('Usage: /trailer <project_name> | <movie idea>\n'
                f'Put your images (and optionally one music file) in '
                f'{config.PROJECTS_DIR}/<project_name>/media/ first.')

    name_part, idea_part = args.split("|", 1)
    project_name = name_part.strip()
    idea = idea_part.strip()

    if not project_name or not idea:
        return "Both a project name and a movie idea are required."

    # Lazy import: creator/ pulls in ffmpeg-dependent code, no need to
    # pay that cost until /trailer is actually used.
    from ai_brain.creator import trailer_builder

    project_dir = config.PROJECTS_DIR / project_name
    try:
        output_path = trailer_builder.build_trailer(project_dir, idea)
    except FileNotFoundError as e:
        return str(e)
    except RuntimeError as e:
        return f"Video build failed:\n{e}"

    return f"Trailer built: {output_path}"


def cmd_musicvideo(args: str) -> str:
    """Build a music video: /musicvideo <project_name> | <lyrics or theme>"""
    if "|" not in args:
        return ('Usage: /musicvideo <project_name> | <lyrics or theme>\n'
                f'Put your images and exactly one song file in '
                f'{config.PROJECTS_DIR}/<project_name>/media/ first.')

    name_part, theme_part = args.split("|", 1)
    project_name = name_part.strip()
    theme = theme_part.strip()

    if not project_name:
        return "A project name is required."

    from ai_brain.creator import music_video_builder

    project_dir = config.PROJECTS_DIR / project_name
    try:
        output_path = music_video_builder.build_music_video(project_dir, theme)
    except FileNotFoundError as e:
        return str(e)
    except RuntimeError as e:
        return f"Video build failed:\n{e}"

    return f"Music video built: {output_path}"


def cmd_file(args: str) -> str:
    """File assistant: /file list [dir] | new <path> | mkdir <path> | rename <path> <new_name> | mv <path> <new_path> | rm <path>"""
    parts = args.split(maxsplit=2)
    if not parts:
        return cmd_file.__doc__

    action = parts[0].lower()
    try:
        if action == "list":
            target = parts[1] if len(parts) > 1 else ""
            entries = files.list_files(target)
            return "\n".join(entries) if entries else "(empty)"

        elif action == "new":
            if len(parts) < 2:
                return "Usage: /file new <path>"
            p = files.create_file(parts[1])
            return f"Created {p}"

        elif action == "mkdir":
            if len(parts) < 2:
                return "Usage: /file mkdir <path>"
            p = files.make_folder(parts[1])
            return f"Created folder {p}"

        elif action == "rename":
            if len(parts) < 3:
                return "Usage: /file rename <path> <new_name>"
            new_name = parts[2].split()[0]
            p = files.rename(parts[1], new_name)
            return f"Renamed to {p}"

        elif action == "mv":
            if len(parts) < 3:
                return "Usage: /file mv <path> <new_path>"
            p = files.move(parts[1], parts[2])
            return f"Moved to {p}"

        elif action == "rm":
            if len(parts) < 2:
                return "Usage: /file rm <path>  (asks for confirmation)"
            return f"Type '/file rmconfirm {parts[1]}' to permanently delete it."

        elif action == "rmconfirm":
            if len(parts) < 2:
                return "Usage: /file rmconfirm <path>"
            files.delete(parts[1], confirm=True)
            return f"Deleted {parts[1]}"

        else:
            return cmd_file.__doc__

    except (files.UnsafePathError, FileNotFoundError, FileExistsError, PermissionError) as e:
        return f"Error: {e}"


def cmd_open(args: str) -> str:
    """Open an approved app: /open <name>  (list approved with /open list)"""
    name = args.strip()
    if not name or name.lower() == "list":
        approved = ", ".join(computer.list_approved())
        return f"Approved apps: {approved or '(none configured — edit APPROVED_APPS in ai_brain/config.py)'}"
    try:
        return computer.open_app(name)
    except (computer.AppNotApprovedError, FileNotFoundError) as e:
        return f"Error: {e}"


def cmd_voice(args: str) -> str:
    """Have one spoken exchange: listen through the mic, reply out loud."""
    if not voice.is_available():
        return ("Voice isn't set up yet. Run: pip install -r requirements-voice.txt "
                "(Linux also needs: sudo apt install portaudio19-dev espeak)")
    try:
        heard = voice.listen()
    except voice.VoiceNotAvailableError as e:
        return f"Error: {e}"

    if not heard:
        return "Didn't catch that — try again."

    history = memory.load_history()
    history = memory.append_message(history, "user", heard)
    reply = ai_client.get_ai_reply(history)
    memory.append_message(history, "assistant", reply)

    voice.speak(reply)
    return f"You said: \"{heard}\"\n{config.ASSISTANT_NAME}: {reply}"


COMMANDS = {
    "help": cmd_help,
    "clear": cmd_clear,
    "trailer": cmd_trailer,
    "musicvideo": cmd_musicvideo,
    "file": cmd_file,
    "open": cmd_open,
    "voice": cmd_voice,
    "quit": cmd_quit,
    "exit": cmd_quit,
}


def is_command(text: str) -> bool:
    return text.strip().startswith("/")


def run_command(text: str) -> str:
    text = text.strip()[1:]  # drop leading /
    name, _, args = text.partition(" ")
    name = name.lower()
    if name not in COMMANDS:
        return f"Unknown command '/{name}'. Type /help to see what's available."
    return COMMANDS[name](args.strip())
