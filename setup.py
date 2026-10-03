"""Celestia first-time setup. Idempotent — safe to re-run anytime.

Steps: system deps (macOS) → pip install → Playwright browsers → config bootstrap.
Windows-only packages are marked `; sys_platform == 'win32'` in requirements.txt,
so pip skips them on macOS/Linux while keeping full Windows functionality.
"""

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
EXAMPLE_KEYS = CONFIG_DIR / "api_keys.example.json"
API_KEYS = CONFIG_DIR / "api_keys.json"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kwargs)


def _real_os_system() -> str:
    return {"Windows": "Windows", "Darwin": "Darwin", "Linux": "Linux"}.get(
        platform.system(), platform.system()
    )


def check_python() -> None:
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required, you have {sys.version.split()[0]}.")
        print("   macOS: brew install python@3.12")
        raise SystemExit(1)


def install_system_deps() -> None:
    """macOS Homebrew libraries that pip packages build against."""
    if platform.system() != "Darwin":
        return
    brew = shutil.which("brew")
    if brew is None:
        print("⚠️  Homebrew not found — skipping system libraries.")
        print("   Install it from https://brew.sh, then run:")
        print("     brew install portaudio")
        print("   and re-run this setup if microphone input fails.")
        return
    # portaudio: required to build PyAudio (microphone input).
    try:
        r = _run([brew, "list", "portaudio"],
                 capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print("Installing PortAudio (microphone support)...")
            _run([brew, "install", "portaudio"], check=False, timeout=600)
        else:
            print("PortAudio already installed.")
    except Exception as e:
        print(f"⚠️  Could not ensure PortAudio: {e}")
        print("   Try manually: brew install portaudio")


def install_python_deps() -> None:
    print(f"Installing requirements... (platform: {platform.system()} "
          f"{platform.machine()}, python {sys.version.split()[0]})")
    print("NOTE: Windows-only packages (comtypes, pycaw, win10toast, pywinauto)")
    print("      are marked `; sys_platform == 'win32'` in requirements.txt,")
    print("      so pip skips them on macOS/Linux. Nothing was removed —")
    print("      they still install on Windows with full functionality.")
    try:
        _run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
             check=False)
        _run([sys.executable, "-m", "pip", "install", "-r",
              str(BASE_DIR / "requirements.txt")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ pip install failed (exit {e.returncode}).")
        if platform.system() == "Darwin":
            print("\nmacOS hints:")
            print("  • PyAudio needs PortAudio:  brew install portaudio")
            print("    then re-run:  python3 setup.py")
            print("  • Isolate issues with a venv: python3 -m venv .venv && "
                  "source .venv/bin/activate")
            print("  • Inspect one package: pip install --verbose <package-name>")
        raise SystemExit(e.returncode)


def install_playwright() -> None:
    print("Installing Playwright browsers...")
    try:
        _run([sys.executable, "-m", "playwright", "install"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n⚠️ Playwright browser download failed (exit {e.returncode}).")
        print("The Python package installed fine — retry browsers later with:")
        print(f"  {sys.executable} -m playwright install")
        raise SystemExit(e.returncode)


def bootstrap_config() -> None:
    """Creates config/api_keys.json (correct os_system) and the user-data
    copies the app reads at runtime. Never overwrites existing files."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not API_KEYS.exists() and EXAMPLE_KEYS.exists():
        try:
            data = json.loads(EXAMPLE_KEYS.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data["os_system"] = _real_os_system()
        API_KEYS.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"Created {API_KEYS} — paste your Gemini/OpenRouter keys in it")
        print(" (or enter them in the setup screen on first launch).")
    elif API_KEYS.exists():
        # Heal stale os_system values from old templates ("Windows" on a Mac).
        try:
            data = json.loads(API_KEYS.read_text(encoding="utf-8"))
            if data.get("os_system") != _real_os_system():
                data["os_system"] = _real_os_system()
                API_KEYS.write_text(json.dumps(data, indent=2), encoding="utf-8")
                print(f"Corrected os_system in {API_KEYS} → {_real_os_system()}.")
        except Exception:
            pass
    else:
        print(f"⚠️  {EXAMPLE_KEYS} missing — create {API_KEYS} manually.")

    # User-data copies (~/.config/CelestiaAI or ~/CelestiaAI) used by llm_client & friends.
    try:
        from core.user_paths import get_user_data_dir
        user_cfg = get_user_data_dir() / "config"
        user_cfg.mkdir(parents=True, exist_ok=True)
        for name in ("api_keys.json", "app_settings.json"):
            src, dst = CONFIG_DIR / name, user_cfg / name
            if not dst.exists() and src.exists():
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"Seeded {dst}.")
    except Exception as e:
        print(f"⚠️  Could not seed user-data config: {e}")


def print_next_steps() -> None:
    if platform.system() == "Darwin":
        print("\nmacOS notes (features preserved, native backends used):")
        print("  • Volume/brightness use osascript (no pycaw needed).")
        print("  • Notifications use launchd + osascript (no win10toast needed).")
        print("  • Global Push-to-Talk needs pynput (installed) + Accessibility")
        print("    permission for your terminal/IDE.")
        print("  • Grant Screen Recording too, for screenshots/click automation.")
        print("  • Optional display-brightness API: brew install brightness")
    print("\n✅ Setup complete! Launch with:")
    if platform.system() == "Windows":
        print("   start_celestia.bat")
    else:
        print("   ./start_celestia.sh   (or: python3 main.py)")


def main() -> None:
    check_python()
    install_system_deps()
    install_python_deps()
    install_playwright()
    bootstrap_config()
    print_next_steps()


if __name__ == "__main__":
    main()
