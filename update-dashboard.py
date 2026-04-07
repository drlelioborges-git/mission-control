#!/usr/bin/env python3
"""Push dashboard data to GitHub Pages repo."""
import json, subprocess, os, time
from datetime import datetime
from pathlib import Path

REPO_DIR = Path("/tmp/mission-control")
DATA_FILE = REPO_DIR / "data" / "dashboard-data.json"

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()

def collect_data():
    # Cron status
    crons_raw = run("openclaw cron list 2>/dev/null")
    crons = []
    for line in crons_raw.split('\n'):
        if line.strip() and not line.startswith('name') and not line.startswith('---'):
            parts = line.split()
            if len(parts) >= 3:
                name = parts[0]
                status = parts[-1] if parts[-1] in ('ok','error','running','skipped') else 'unknown'
                crons.append({'name': name, 'status': status})
    
    # Gateway status
    gw_raw = run("openclaw gateway status 2>/dev/null")
    gateway_ok = 'RPC probe: ok' in gw_raw
    
    # Disk
    disk = run("df -h / | tail -1").split()
    disk_usage = disk[4] if len(disk) > 4 else "?"
    
    # Memory
    mem = run("free -h | grep Mem").split()
    mem_usage = f"{mem[2]}/{mem[1]}" if len(mem) > 3 else "?"
    
    # Uptime
    uptime = run("uptime -p").replace("up ", "")
    
    data = {
        "lastUpdated": datetime.now().strftime("%Y-%m-%d %H:%M:%S BRT"),
        "gateway": {"status": "ok" if gateway_ok else "error", "version": "2026.4.1"},
        "system": {
            "disk": disk_usage,
            "memory": mem_usage,
            "uptime": uptime,
        },
        "crons": {
            "total": len(crons),
            "ok": sum(1 for c in crons if c['status'] == 'ok'),
            "error": sum(1 for c in crons if c['status'] == 'error'),
            "running": sum(1 for c in crons if c['status'] == 'running'),
        },
        "models": {
            "main": "openai-codex/gpt-5.4",
            "fallbacks": ["zai/glm-5.1", "openrouter/deepseek/deepseek-v3.2"],
            "cron_worker": "zai/glm-5.1",
            "marketing": "zai/glm-5.1",
        },
        "agents": {
            "main": "active",
            "cron_worker": "active",
            "marketing": "active",
            "pro": "standby",
        },
        "integrations": {
            "telegram": "ok",
            "google_calendar": "ok",
            "gmail": "ok",
            "buffer_instagram": "ok",
            "github": "ok",
        },
        "recentActivity": [],
        "actionItems": [],
    }
    return data

def push(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    
    os.chdir(REPO_DIR)
    run("git add -A")
    run(f'git commit -m "dashboard update {datetime.now().strftime("%Y-%m-%d %H:%M")}" 2>/dev/null || true')
    run("git push 2>/dev/null")

if __name__ == '__main__':
    data = collect_data()
    push(data)
    print(f"Dashboard updated: gateway={'ok' if data['gateway']['status']=='ok' else 'error'} crons={data['crons']['ok']}/{data['crons']['total']}")
