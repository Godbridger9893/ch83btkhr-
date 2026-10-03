# actions/reminder.py

import platform
import subprocess
import os
import sys
from datetime import datetime


def _reminder_macos_linux(target_dt, safe_message, task_name) -> str:
    """Schedule a reminder on macOS (launchd) or Linux (at/cron). Windows path below is unchanged."""
    import tempfile
    tmp = tempfile.gettempdir()
    notify_script = os.path.join(tmp, f"{task_name}.py")
    _OS = platform.system()
    if _OS == "Darwin":
        script_code = f'''import subprocess
msg = """{safe_message}"""
try:
    subprocess.run(["osascript", "-e", f'display notification "{{msg}}" with title "Brahma Reminder" sound name "Ping"'])
except Exception:
    pass
try:
    subprocess.run(["say", msg])
except Exception:
    pass
try:
    import os
    os.remove(__file__)
except Exception:
    pass
'''
    else:
        script_code = f'''import subprocess, shutil
msg = """{safe_message}"""
try:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "Brahma Reminder", msg])
    elif shutil.which("zenity"):
        subprocess.run(["zenity", "--info", "--text=" + msg])
except Exception:
    pass
print(msg)
try:
    import os
    os.remove(__file__)
except Exception:
    pass
'''
    with open(notify_script, "w", encoding="utf-8") as f:
        f.write(script_code)

    if _OS == "Darwin":
        from pathlib import Path
        label = f"com.celestia.{task_name.lower()}"
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist = plist_dir / f"{label}.plist"
        plist.write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{label}</string>
<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{notify_script}</string></array>
<key>StartCalendarInterval</key><dict><key>Month</key><integer>{target_dt.month}</integer><key>Day</key><integer>{target_dt.day}</integer><key>Hour</key><integer>{target_dt.hour}</integer><key>Minute</key><integer>{target_dt.minute}</integer></dict>
</dict></plist>""",
            encoding="utf-8",
        )
        r = subprocess.run(["launchctl", "load", str(plist)], capture_output=True, text=True)
        if r.returncode != 0:
            return "I couldn't schedule the reminder due to a system error."
        return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."
    # Linux: prefer `at`, fall back to cron
    at_time = target_dt.strftime("%H:%M %Y-%m-%d")
    try:
        r = subprocess.run(["which", "at"], capture_output=True)
        if r.returncode == 0:
            p = subprocess.run(["at", at_time], input=f"{sys.executable} {notify_script}\n",
                               capture_output=True, text=True)
            if p.returncode == 0:
                return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."
    except Exception:
        pass
    try:
        cron_line = f"{target_dt.minute} {target_dt.hour} {target_dt.day} {target_dt.month} * {sys.executable} {notify_script} # {task_name}"
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = r.stdout if r.returncode == 0 else ""
        lines = [l for l in existing.splitlines() if task_name not in l]
        lines.append(cron_line)
        subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n",
                       capture_output=True, text=True)
        return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."
    except Exception:
        try:
            os.remove(notify_script)
        except Exception:
            pass
        return "I couldn't schedule the reminder due to a system error."


def reminder(
    parameters: dict,
    response: str | None = None,
    player=None,
    session_memory=None
) -> str:
    """
    Sets a timed reminder using Windows Task Scheduler.

    parameters:
        - date    (str) YYYY-MM-DD
        - time    (str) HH:MM
        - message (str)

    Returns a result string — Live API voices it automatically.
    No edge_speak needed.
    """

    date_str = parameters.get("date")
    time_str = parameters.get("time")
    message  = parameters.get("message", "Reminder")

    if not date_str or not time_str:
        return "I need both a date and a time to set a reminder."

    try:
        target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if target_dt <= datetime.now():
            return "That time is already in the past."

        task_name    = f"MARKReminder_{target_dt.strftime('%Y%m%d_%H%M')}"
        safe_message = message.replace('"', '').replace("'", "").strip()[:200]

        # Non-Windows: native scheduler, same feature. Windows Task Scheduler path below untouched.
        if os.name != "nt" or platform.system() != "Windows":
            msg = _reminder_macos_linux(target_dt, safe_message, task_name)
            if player:
                player.write_log(f"[reminder] set for {date_str} {time_str}")
            return msg

        python_exe = sys.executable
        if python_exe.lower().endswith("python.exe"):
            pythonw = python_exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                python_exe = pythonw

        temp_dir      = os.environ.get("TEMP", "C:\\Temp")
        notify_script = os.path.join(temp_dir, f"{task_name}.pyw")
        project_root  = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        script_code = f'''import sys, os, time
sys.path.insert(0, r"{project_root}")

try:
    import winsound
    for freq in [800, 1000, 1200]:
        winsound.Beep(freq, 200)
        time.sleep(0.1)
except Exception:
    pass

try:
    from win10toast import ToastNotifier
    ToastNotifier().show_toast(
        "MARK Reminder",
        "{safe_message}",
        duration=15,
        threaded=False
    )
except Exception:
    try:
        import subprocess
        subprocess.run(["msg", "*", "/TIME:30", "{safe_message}"], shell=True)
    except Exception:
        pass

time.sleep(3)
try:
    os.remove(__file__)
except Exception:
    pass
'''
        with open(notify_script, "w", encoding="utf-8") as f:
            f.write(script_code)

        xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>MARK Reminder: {safe_message}</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{target_dt.strftime("%Y-%m-%dT%H:%M:%S")}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{notify_script}"</Arguments>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>'''

        xml_path = os.path.join(temp_dir, f"{task_name}.xml")
        with open(xml_path, "w", encoding="utf-16") as f:
            f.write(xml_content)

        result = subprocess.run(
            f'schtasks /Create /TN "{task_name}" /XML "{xml_path}" /F',
            shell=True, capture_output=True, text=True
        )

        try:
            os.remove(xml_path)
        except Exception:
            pass

        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            print(f"[Reminder] ❌ schtasks failed: {err}")
            try:
                os.remove(notify_script)
            except Exception:
                pass
            return "I couldn't schedule the reminder due to a system error."

        if player:
            player.write_log(f"[reminder] set for {date_str} {time_str}")

        return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."

    except ValueError:
        return "I couldn't understand that date or time format."

    except Exception as e:
        return f"Something went wrong while scheduling the reminder: {str(e)[:80]}"