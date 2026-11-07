#!/usr/bin/env python3
"""Collecte les métriques du VPS partagé et publie /srv/monitor/public/metrics.json.

Lancé toutes les 5 minutes par la crontab de l'utilisateur ubuntu (voir vps/install.sh).
Aucune dépendance : lit /proc, les cgroups des conteneurs, `docker` et /etc/caddy/sites.

- CPU : moyenne sur l'intervalle depuis le dernier passage (pas un instantané).
- Historique : un point par passage sur 48 h, puis moyennes horaires (avec max) sur 90 jours.
- Projets : un projet = un projet docker compose. Son adresse publique est retrouvée
  en reliant le reverse_proxy de Caddy au port publié par ses conteneurs.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(os.environ.get("MONITOR_DIR", "/srv/monitor"))
STATE = ROOT / "state.json"
OUT = ROOT / "public" / "metrics.json"
RAW_KEEP = 48 * 3600
HOURLY_KEEP = 90 * 24 * 3600
MB = 1024 * 1024


def read(path):
    with open(path) as f:
        return f.read()


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False))
    os.replace(tmp, path)


def cpu_times():
    fields = [int(x) for x in read("/proc/stat").splitlines()[0].split()[1:]]
    idle = fields[3] + fields[4]  # idle + iowait
    return sum(fields[:8]), idle  # sans guest (déjà compté dans user)


def meminfo():
    info = {}
    for line in read("/proc/meminfo").splitlines():
        key, value = line.split(":", 1)
        info[key] = int(value.split()[0]) * 1024
    return info


def docker(*args):
    out = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=60)
    return out.stdout if out.returncode == 0 else ""


def dir_size(path):
    out = subprocess.run(["du", "-sb", path], capture_output=True, text=True, timeout=60)
    try:
        return int(out.stdout.split()[0])
    except (IndexError, ValueError):
        return 0


def labels_of(text):
    return dict(kv.split("=", 1) for kv in (text or "").split(",") if "=" in kv)


def containers():
    ids = docker("ps", "-aq").split()
    if not ids:
        return []
    return json.loads(docker("inspect", *ids) or "[]")


def cgroup_usage(cid):
    base = Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope")
    try:
        usec = int(re.search(r"usage_usec (\d+)", read(base / "cpu.stat")).group(1))
        mem = int(read(base / "memory.current"))
        inactive = re.search(r"^inactive_file (\d+)", read(base / "memory.stat"), re.M)
        mem -= int(inactive.group(1)) if inactive else 0  # comme `docker stats`
        return usec, max(mem, 0)
    except (OSError, AttributeError, ValueError):
        return None


def caddy_sites():
    """{port local: [https://domaine, ...]} d'après /etc/caddy/sites/*.caddy."""
    sites = {}
    for file in sorted(Path("/etc/caddy/sites").glob("*.caddy")):
        host = None
        for raw in read(file).splitlines():
            line = raw.split("#", 1)[0].rstrip()
            if not line.strip():
                continue
            if not raw[0].isspace() and line.endswith("{"):
                host = line[:-1].strip().split(",")[0].strip()
            m = re.search(r"reverse_proxy\s+(?:127\.0\.0\.1|localhost):(\d+)", line)
            if m and host:
                url = host if host.startswith("http") else f"https://{host}"
                sites.setdefault(int(m.group(1)), [])
                if url not in sites[int(m.group(1))]:
                    sites[int(m.group(1))].append(url)
    return sites


def disk_by_project():
    """Taille des volumes docker par projet compose, en octets."""
    try:
        df = json.loads(docker("system", "df", "-v", "--format", "json") or "{}")
    except json.JSONDecodeError:
        return {}
    sizes = {}
    units = {"B": 1, "kB": 1e3, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}
    for vol in df.get("Volumes") or []:
        project = labels_of(vol.get("Labels")).get("com.docker.compose.project")
        m = re.match(r"([\d.]+)\s*([kKMGT]?B)", vol.get("Size", ""))
        if project and m:
            sizes[project] = sizes.get(project, 0) + float(m.group(1)) * units[m.group(2)]
    return sizes


def service_state(name):
    out = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def os_name():
    for line in read("/etc/os-release").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip('"')
    return ""


def average(rows, key):
    values = [r[key] for r in rows if r.get(key) is not None]
    return round(sum(values) / len(values), 1) if values else None


def aggregate_hour(start, rows):
    point = {"t": start}
    for key in ("c", "m", "s", "d", "l"):
        point[key] = average(rows, key)
    point["cx"] = max(r["c"] for r in rows)
    point["mx"] = max(r["m"] for r in rows)
    projects = {}
    for name in {p for r in rows for p in r.get("p", {})}:
        vals = [r["p"][name] for r in rows if name in r.get("p", {})]
        projects[name] = [round(sum(v[i] for v in vals) / len(vals), 1) for i in range(3)]
    point["p"] = projects
    return point


def main():
    now = time.time()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}

    total, idle = cpu_times()
    if "cpu" not in state:  # premier passage : mesure sur 2 s
        state["cpu"] = list(cpu_times())
        state["t"] = now
        time.sleep(2)
        total, idle = cpu_times()
        now = time.time()
    d_total = total - state["cpu"][0]
    cpu = 100 * (1 - (idle - state["cpu"][1]) / d_total) if d_total > 0 else 0
    wall_usec = max((now - state.get("t", now - 300)) * 1e6, 1)
    ncpu = os.cpu_count() or 1

    mem = meminfo()
    st = os.statvfs("/")
    disk_total = st.f_blocks * st.f_frsize
    disk_used = (st.f_blocks - st.f_bfree) * st.f_frsize
    load = [round(float(x), 2) for x in read("/proc/loadavg").split()[:3]]

    # Conteneurs regroupés par projet compose
    sites = caddy_sites()
    vol_sizes = disk_by_project() if now - state.get("diskT", 0) > 3500 else None
    dir_sizes = state.get("dirSizes", {})
    prev_usage = state.get("containers", {})
    usage = {}
    projects = {}
    for c in containers():
        labels = c["Config"].get("Labels") or {}
        name = labels.get("com.docker.compose.project") or c["Name"].lstrip("/")
        proj = projects.setdefault(name, {
            "id": name, "dir": labels.get("com.docker.compose.project.working_dir", ""),
            "urls": [], "containers": [], "cpu": 0.0, "memMB": 0.0,
        })
        status = c["State"]
        proj["containers"].append({
            "name": c["Name"].lstrip("/"),
            "service": labels.get("com.docker.compose.service", ""),
            "state": status.get("Status"),
            "health": (status.get("Health") or {}).get("Status"),
            "startedAt": status.get("StartedAt"),
            "restarts": c.get("RestartCount", 0),
        })
        for bindings in (c["NetworkSettings"].get("Ports") or {}).values():
            for b in bindings or []:
                for url in sites.get(int(b.get("HostPort") or 0), []):
                    if url not in proj["urls"]:
                        proj["urls"].append(url)
        cg = cgroup_usage(c["Id"]) if status.get("Running") else None
        if cg:
            usec, mem_bytes = cg
            usage[c["Id"]] = usec
            prev = prev_usage.get(c["Id"])
            if prev is not None and usec >= prev:
                proj["cpu"] += 100 * (usec - prev) / (wall_usec * ncpu)
            proj["memMB"] += mem_bytes / MB

    if vol_sizes is not None:
        for name, proj in projects.items():
            size = vol_sizes.get(name, 0)
            if proj["dir"]:
                size += dir_size(proj["dir"])
            dir_sizes[name] = round(size / MB, 1)
        state["diskT"] = now
        state["dirSizes"] = dir_sizes

    for proj in projects.values():
        proj["cpu"] = round(proj["cpu"], 2)
        proj["memMB"] = round(proj["memMB"], 1)
        proj["diskMB"] = dir_sizes.get(proj["id"])
        running = sum(1 for c in proj["containers"] if c["state"] == "running")
        proj["running"] = running
        proj["total"] = len(proj["containers"])

    sample = {
        "t": int(now),
        "c": round(cpu, 1),
        "m": round((mem["MemTotal"] - mem["MemAvailable"]) / MB),
        "s": round((mem["SwapTotal"] - mem["SwapFree"]) / MB),
        "d": round(disk_used / MB),
        "l": load[0],
        "p": {n: [p["cpu"], p["memMB"], p["diskMB"] or 0] for n, p in projects.items()},
    }

    raw = state.get("raw", []) + [sample]
    hourly = state.get("hourly", [])
    last_hour = hourly[-1]["t"] if hourly else 0
    current_hour = int(now) // 3600 * 3600
    for hour in sorted({r["t"] // 3600 * 3600 for r in raw}):
        if last_hour < hour < current_hour:
            hourly.append(aggregate_hour(hour, [r for r in raw if hour <= r["t"] < hour + 3600]))
    raw = [r for r in raw if r["t"] > now - RAW_KEEP]
    hourly = [h for h in hourly if h["t"] > now - HOURLY_KEEP]

    state.update({"cpu": [total, idle], "t": now, "containers": usage, "raw": raw, "hourly": hourly})
    atomic_write(STATE, state)

    uptime = float(read("/proc/uptime").split()[0])
    atomic_write(OUT, {
        "v": 1,
        "generatedAt": int(now),
        "interval": 300,
        "host": {
            "name": os.uname().nodename,
            "os": os_name(),
            "kernel": os.uname().release,
            "cpus": ncpu,
            "memTotalMB": round(mem["MemTotal"] / MB),
            "swapTotalMB": round(mem["SwapTotal"] / MB),
            "diskTotalMB": round(disk_total / MB),
            "bootedAt": int(now - uptime),
            "load": load,
        },
        "services": {s: service_state(s) for s in ("caddy", "docker", "fail2ban")},
        "projects": sorted(projects.values(), key=lambda p: p["id"]),
        "recent": raw,
        "hourly": hourly,
    })


if __name__ == "__main__":
    main()
