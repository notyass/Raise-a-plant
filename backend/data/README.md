# Données

## Jeu de données utilisé

**Plant Variety Database** de Wind River Greens : 1 972 variétés de plantes
(légumes, aromatiques, fruits, fleurs...) avec description, ensoleillement,
arrosage, type de sol, saison, difficulté, etc. Les textes sont en anglais.

- Page : https://huggingface.co/datasets/WindRiverGreens/plant-variety-database
- Licence : **CC BY 4.0**. Il faut créditer Wind River Greens avec un lien
  vers https://plants.windrivergreens.com (fait dans la page « À propos »).
- Fichiers utilisés : `varieties.csv` (32 colonnes) et `categories.csv`.

La commande `flask --app run seed` télécharge ces deux fichiers dans ce
dossier puis les importe dans la base. Ils ne sont pas versionnés dans git
(voir `.gitignore`) : chacun les retélécharge avec la commande.

Si le téléchargement est bloqué (réseau de l'IUT par exemple), télécharge
les deux fichiers à la main depuis l'onglet « Files » de la page ci-dessus,
place-les dans ce dossier, puis relance la commande.

## Dossier `sample/`

19 fiches **d'exemple, écrites à la main** au même format que le vrai jeu
de données. Elles ne viennent pas du jeu de données : elles servent
uniquement aux tests automatiques et à lancer l'application sans réseau
(`flask --app run seed --sample`). Ne pas les utiliser pour les mesures
de performance du rapport.
