# NeoCode apps — registre des applis

Un seul fichier, [`public/apps.json`](public/apps.json), liste toutes les applis du groupe.
Chaque appli le télécharge de temps en temps (une fois par jour au plus) et propose les **autres** applis de la liste.

- Registre publié : **https://cocosdnc.github.io/neocode-apps/apps.json**
- Page vitrine : https://cocosdnc.github.io/neocode-apps/

Publié automatiquement par GitHub Pages à chaque push sur `main` (≈ 1 minute).
Le fichier est vérifié avant publication (`scripts/validate.mjs`) : si une erreur s'y glisse, rien n'est publié
et les téléphones gardent la dernière version valide.

## Ajouter une appli

1. Mettre son icône (PNG carré, 256×256 conseillé) dans `public/icons/<id>.png`.
2. Ajouter un bloc dans `public/apps.json` (copier celui d'une autre appli) :

| Champ | Rôle |
| --- | --- |
| `id` | identifiant unique, minuscules et tirets (`funnyalarm`). **Chaque appli s'en sert pour se retirer elle-même de la liste : ne jamais le changer.** |
| `name` | nom affiché |
| `active` | `false` pour masquer l'appli sans la supprimer |
| `tagline` / `description` | textes par langue (`fr`, `en`, `es`…). `en` est obligatoire : c'est la langue de secours |
| `icon` | URL de l'icône : `https://cocosdnc.github.io/neocode-apps/icons/<id>.png` |
| `color` | couleur de fond de la carte, `#RRGGBB` |
| `website` | site de l'appli, ouvert quand il n'y a pas de lien store |
| `scheme` | lien profond (`monapp://`) pour ouvrir l'appli si elle est déjà installée |
| `android.storeUrl` / `ios.storeUrl` | lien Play Store / App Store. Laisser `""` tant que l'appli n'y est pas |

3. Commit + push (ou modifier directement le fichier sur github.com, bouton ✏️). C'est tout :
les applis déjà installées verront la nouvelle au prochain rafraîchissement, sans mise à jour.

## Vérifier en local

```bash
node scripts/validate.mjs
```

## Brancher une nouvelle appli sur le registre

Donner à Claude, dans le dossier de l'appli, le texte de [`PROMPT_CLAUDE.md`](PROMPT_CLAUDE.md)
en remplaçant `<ID_DE_L_APPLI>` par son `id`.
