# Instruction à donner à Claude dans chaque appli

Remplacer `<ID_DE_L_APPLI>` par l'`id` de l'appli dans `public/apps.json` (ex. `scrollsavior`, `funnyalarm`).

---

Ajoute à cette appli une section « Nos autres applis » qui propose les autres applis du groupe NeoCode,
à partir d'un registre en ligne. L'`id` de cette appli dans le registre est **`<ID_DE_L_APPLI>`**.

## Le registre

URL : `https://cocosdnc.github.io/neocode-apps/apps.json` (GET simple, public, pas d'authentification).
Format (voir la source : https://github.com/Cocosdnc/neocode-apps/blob/main/public/apps.json) :

```json
{
  "schemaVersion": 1,
  "apps": [
    {
      "id": "funnyalarm",
      "name": "FunnyAlarm",
      "active": true,
      "tagline": { "fr": "…", "en": "…", "es": "…" },
      "description": { "fr": "…", "en": "…" },
      "icon": "https://cocosdnc.github.io/neocode-apps/icons/funnyalarm.png",
      "color": "#1B1446",
      "website": "https://funnyalarm.com",
      "scheme": "funnyalarm://",
      "android": { "package": "com.neocodeconsulting.funnyalarm", "storeUrl": "" },
      "ios": { "bundleId": "com.funnyalarm.app", "storeUrl": "" }
    }
  ]
}
```

La liste change sans mise à jour de l'appli (ajouts, retraits, textes) : rien ne doit être codé en dur à part l'URL et l'`id` de cette appli.

## Récupération (une fois de temps en temps)

- Au démarrage de l'appli (et au retour au premier plan), **sans bloquer l'interface** : si le dernier téléchargement
  réussi date de moins de 24 h, ne rien faire ; sinon télécharger en tâche de fond avec un délai max de 8 s.
- Garder en cache local la dernière réponse valide + sa date, avec le stockage déjà utilisé par l'appli
  (n'ajoute pas de nouvelle dépendance de stockage).
- En cas d'échec (hors ligne, erreur HTTP, JSON invalide, `schemaVersion` différent de 1) : ignorer
  silencieusement et garder le cache. Sans cache, la section ne s'affiche pas.
- Aucune donnée envoyée, aucun identifiant, aucune analytics : juste le GET.

## Filtrage et textes

- Garder les applis où `active === true` et `id !== "<ID_DE_L_APPLI>"`. Ignorer une entrée incomplète
  (sans `id`, `name`, `icon` ou `website`) au lieu de planter. Ignorer les champs inconnus (le format pourra s'enrichir).
- Langue : celle de l'i18n actuelle de l'appli, sinon `en`, sinon la première disponible.
- Mets cette logique (validation, filtrage, choix de langue, décision « faut-il rafraîchir ») dans une fonction pure,
  séparée de l'UI, et teste-la si l'appli a des tests.

## Affichage

- Dans l'écran Réglages (ou l'endroit le plus naturel de l'appli), une section discrète « Nos autres applis »
  (titre traduit dans toutes les langues de l'appli), une carte par appli : icône, nom, `tagline`.
  Style cohérent avec le reste de l'appli. Rien du tout si la liste filtrée est vide.
- Au toucher : 1) essayer d'ouvrir `scheme` (l'appli est peut-être installée) avec `Linking.openURL`, en attrapant l'échec ;
  2) sinon `android.storeUrl` ou `ios.storeUrl` selon la plateforme s'il n'est pas vide ;
  3) sinon `website`.

## Fin

Respecte les conventions et la version d'Expo du projet (voir AGENTS.md). Lance lint, typecheck et tests avant de dire que c'est fini.
