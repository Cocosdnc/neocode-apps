#!/usr/bin/env bash
# Installe (ou met à jour) la collecte de métriques sur le VPS partagé, depuis Git Bash :
#   vps/install.sh [hôte ssh, défaut : vps]
# Copie collect.py dans /srv/monitor, ajoute la ligne cron (toutes les 5 min) et le site Caddy.
# Sans sudo (mot de passe d'ubuntu inconnu) : le fichier Caddy est copié par un conteneur jetable
# (ubuntu est dans le groupe docker), puis Caddy est rechargé par son API locale (caddy reload).
set -euo pipefail

HOST="${1:-vps}"
cd "$(dirname "$0")"

ssh "$HOST" "mkdir -p /srv/monitor/public"
scp -q collect.py monitor.caddy "$HOST:/srv/monitor/"
ssh "$HOST" 'chmod +x /srv/monitor/collect.py \
  && (crontab -l 2>/dev/null | grep -v /srv/monitor/collect.py; \
      echo "*/5 * * * * /usr/bin/python3 /srv/monitor/collect.py >> /srv/monitor/collect.log 2>&1") | crontab - \
  && /usr/bin/python3 /srv/monitor/collect.py'
ssh "$HOST" 'docker run --rm -v /etc/caddy/sites:/sites -v /srv/monitor/monitor.caddy:/monitor.caddy:ro node:22-alpine     sh -c "cp /monitor.caddy /sites/ && chown 0:0 /sites/monitor.caddy && chmod 644 /sites/monitor.caddy"   && caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null   && caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile'
echo "✅ https://monitor.146-59-230-206.sslip.io/metrics.json"
