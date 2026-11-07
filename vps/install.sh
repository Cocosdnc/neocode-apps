#!/usr/bin/env bash
# Installe (ou met à jour) la collecte de métriques sur le VPS partagé, depuis Git Bash :
#   vps/install.sh [hôte ssh, défaut : vps]
# Copie collect.py dans /srv/monitor, ajoute la ligne cron (toutes les 5 min) et le site Caddy.
# sudo demande le mot de passe d'ubuntu (une seule fois, pour Caddy).
set -euo pipefail

HOST="${1:-vps}"
cd "$(dirname "$0")"

ssh "$HOST" "mkdir -p /srv/monitor/public"
scp -q collect.py monitor.caddy "$HOST:/srv/monitor/"
ssh "$HOST" 'chmod +x /srv/monitor/collect.py \
  && (crontab -l 2>/dev/null | grep -v /srv/monitor/collect.py; \
      echo "*/5 * * * * /usr/bin/python3 /srv/monitor/collect.py >> /srv/monitor/collect.log 2>&1") | crontab - \
  && /usr/bin/python3 /srv/monitor/collect.py'
ssh -t "$HOST" 'sudo cp /srv/monitor/monitor.caddy /etc/caddy/sites/ && sudo caddy validate --config /etc/caddy/Caddyfile >/dev/null && sudo systemctl reload caddy'
echo "✅ https://monitor.146-59-230-206.sslip.io/metrics.json"
