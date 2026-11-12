# Données

## Jeu de données utilisé

**Plant Variety Database** de Wind River Greens : 1 972 variétés de plantes
(légumes, aromatiques, fruits, fleurs...) avec description, ensoleillement,
arrosage, type de sol, saison, difficulté, etc. Les textes sont en anglais.

- Dépôt : https://github.com/bripatch/plant-variety-database
- Même jeu de données sur Hugging Face (c'est de là que `prepa_db.py` le
  télécharge) : https://huggingface.co/datasets/WindRiverGreens/plant-variety-database
- Licence : **CC BY 4.0**. Il faut créditer Wind River Greens avec un lien
  vers https://plants.windrivergreens.com (fait dans la page « À propos »).
- Fichiers utilisés : `varieties.csv` (32 colonnes) et `categories.csv`.

La commande `python prepa_db.py` télécharge ces deux fichiers dans ce
dossier puis les importe dans la base. Ils ne sont pas versionnés dans git
(voir `.gitignore`) : chacun les retélécharge avec la commande.

Si le téléchargement est bloqué (réseau de l'IUT par exemple), télécharge
les deux fichiers à la main depuis l'onglet « Files » de la page ci-dessus,
place-les dans ce dossier, puis relance la commande.

## Traduction et normalisation

À l'import, `prepa_db.py` ajoute à chaque fiche une version normalisée de
cinq caractéristiques (soleil, eau, terre, saison, difficulté), calculée par
les règles de `app/services/normalizer.py`. L'interface affiche leur libellé
français (« Plein soleil ou mi-ombre »), ainsi que le nom français des 30
types de plantes. Le texte d'origine est conservé à côté. Les autres champs
(descriptions, semis, goût, maladies...) restent en anglais.

## Photos

`python prepa_images.py` cherche une photo pour chaque espèce : la photo
principale de la page Wikipédia du nom latin, puis son auteur et sa licence
sur Wikimedia Commons (API MediaWiki, gratuite et sans clé). Seules les
images sous licence libre sont gardées. Le résultat est écrit dans
`images.json` (une entrée par espèce : adresse de la vignette, auteur,
licence, page du fichier) et recopié dans la base. L'interface affiche le
crédit de chaque photo sur la page de la plante.

La photo montre l'espèce, pas forcément la variété exacte : toutes les
tomates ont la même photo.

## Dossier `sample/`

19 fiches **d'exemple, écrites à la main** au même format que le vrai jeu
de données. Elles ne viennent pas du jeu de données : elles servent
uniquement aux tests automatiques et à lancer l'application sans réseau
(`python prepa_db.py --sample`). Ne pas les utiliser pour les mesures
de performance du rapport.
