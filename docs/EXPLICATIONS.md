# Comment fonctionne l'application (version 0.4.0)

Ce document sert à ce que toute l'équipe puisse expliquer le code à l'oral.

## 1. Vue d'ensemble

L'application répond à deux objectifs :

- **O1** : recevoir des conseils pour prendre soin d'une plante donnée ;
- **O2** : recevoir des suggestions de plantes adaptées à un environnement donné.

Chaque objectif peut être traité par deux méthodes de recommandation :
**heuristique** et **vectorielle**. Il y a une page d'accueil par méthode
(`index.html` et `vectorielle.html`), chacune avec deux barres de recherche
(O1 et O2). Le tableau de bord compare les deux méthodes.

```
Navigateur                         Serveur
┌───────────────────┐   HTTP    ┌────────────────────────────────────────────┐
│ frontend (8080)   │  + JSON   │ backend Flask (5000)                       │
│ HTML / CSS / JS   │ ────────► │ blueprints ─► services ─► DAO ─► modèles ─►│ base de données
│ Chart.js          │ ◄──────── │ (routes)      (logique)   (requêtes) (ORM) │ SQLite ou PostgreSQL
└───────────────────┘           └────────────────────────────────────────────┘
```

- **Découplage** : le frontend et le backend sont deux programmes séparés,
  servis sur deux adresses différentes. Le seul lien est l'adresse de l'API
  dans `frontend/js/config.js`. On peut remplacer l'un sans toucher l'autre.
- **CORS** : comme les deux adresses diffèrent, le navigateur n'autorise les
  appels que si l'API le permet explicitement. C'est le rôle de
  `_register_cors` dans `backend/app/__init__.py`.

## 2. Architecture du backend (celle du TD03)

| Élément du TD | Dans notre projet |
|---|---|
| `main.py` | `main.py` : crée l'application et la lance |
| `prepa_db.py` | `prepa_db.py` : crée les tables et importe les données via l'ORM |
| `app/__init__.py` avec `create_app()` | idem : configuration puis `register_blueprint(...)` |
| `app/blueprints/<nom>/routes.py` | `health`, `plants`, `recommendations`, `metrics` |
| `app/models/base.py` (`Base`, `BaseModelMixin`) | idem, plus `TimestampMixin` |
| un modèle par fichier (`Superhero.py`) | `Category.py`, `Plant.py`, `RecommendationRun.py` |
| `SuperheroDAOInterface.py`, `SuperheroDAO.py` | `PlantDAOInterface.py`, `PlantDAO.py` (classe `PlantORM`) |
| `UserDAO.py` | `RecommendationRunDAO.py` (classe `RecommendationRunORM`) |
| `app/services/SuperheroService.py` | `PlantService.py`, `RecommendationService.py`, `MetricsService.py` |

Rôle de chaque couche :

- **Blueprint** (`routes.py`) : lit la requête HTTP, appelle un service,
  renvoie du JSON. Aucune logique métier. Les quatre blueprints sont
  enregistrés avec le préfixe `/api`.
- **Service** : la logique métier. Il crée son DAO dans `__init__`.
- **DAO** : toutes les requêtes à la base. Chaque méthode ouvre une session,
  fait sa requête et ferme la session (`try` / `finally`).
- **Modèle ORM** : une classe = une table. SQLAlchemy écrit le SQL ; le même
  code fonctionne avec SQLite et PostgreSQL.
- **Mixins** (`models/base.py`) : `BaseModelMixin` ajoute `to_dict()` (pour
  le JSON) et l'accès `plant['name']` ; `TimestampMixin` ajoute les colonnes
  `created_at` et `updated_at`. Exemple :
  `class Plant(Base, BaseModelMixin, TimestampMixin)`.

Différences voulues avec le TD : pas de templates Jinja (les routes renvoient
du JSON, l'affichage est dans le frontend) ; pas de connexion utilisateur ;
`get_engine()` garde un seul moteur par base au lieu d'en créer un à chaque
requête.

Les autres fichiers de `services/` sont des fonctions d'aide, sans base de
données ni Flask, donc faciles à tester :

| Fichier | Rôle |
|---|---|
| `normalizer.py` | texte anglais du jeu de données → codes (`full_sun`, `low`…) |
| `query_builder.py` | critères du formulaire O2, poids, libellés français |
| `document_builder.py` | prépare une plante pour les méthodes (noms, caractéristiques) |
| `care_guide.py` | codes → conseils d'entretien en français (page O1) |
| `images.py` | nom latin → titre de page à chercher pour la photo |
| `text_utils.py` | minuscules, sans accents (`simplify`) |
| `recommenders/` | les deux méthodes : `base.py`, `heuristic.py`, `vector.py` |

## 3. Données : import, normalisation, traduction, photos

Le jeu de données est en anglais et décrit le soleil, l'eau, la terre, la
saison et la difficulté en texte libre, avec des centaines de formulations
(« Full sun (6+ hours) », « 1 inch per week, drought tolerant once
established »...).

À l'import, `prepa_db.py` appelle `services/normalizer.py`, qui ramène
chaque texte à une liste de codes grâce à des règles de mots-clés
(expressions régulières) :

| Critère | Codes possibles | Fiches reconnues (sur 1 972) |
|---|---|---|
| soleil | `shade`, `partial_shade`, `full_sun` | 100 % |
| eau | `low`, `medium`, `high` | 94 % |
| terre | `loam`, `sandy`, `clay`, `rich`, `well_drained` | 91 % |
| saison | `warm`, `cool`, `year_round`, `perennial` | 99 % |
| difficulté | `easy`, `moderate`, `difficult` | 100 % |

Une plante peut avoir plusieurs codes : « Full sun to partial shade » donne
`full_sun,partial_shade`. Les codes sont stockés dans les colonnes
`sun_codes`, `water_codes`... de la table `plants`. Ils servent à tout :

- la méthode heuristique les compare aux critères (règles SI... ALORS) ;
- la méthode vectorielle les transforme en nombres (coordonnées) ;
- l'interface affiche leur libellé français (« Mi-ombre ou plein soleil ») ;
- la page d'une plante en tire ses conseils d'entretien (`care_guide.py`).

Les 30 types de plantes ont un nom français (`CATEGORY_NAMES_FR`). Les textes
longs (descriptions, semis, goût, maladies) restent en anglais.

**Photos.** `prepa_images.py` cherche, pour chaque nom latin, la photo
principale de la page Wikipédia de l'espèce, puis son auteur et sa licence
sur Wikimedia Commons (API MediaWiki). Seules les images libres sont gardées,
avec leur crédit. Le résultat est écrit dans `data/images.json` et recopié
dans les colonnes `image_*` de la table `plants`. La photo montre l'espèce,
pas forcément la variété exacte.

## 4. Parcours d'une recherche

**O1, prendre soin d'une plante** (barre de gauche) :

1. `frontend/js/home.js` envoie `POST /api/searches` avec le texte tapé et la
   méthode de la page.
2. `blueprints/recommendations/routes.py` vérifie la requête et appelle
   `RecommendationService.search(...)`.
3. La méthode choisie cherche les fiches dont le nom, le nom latin ou le type
   correspond (`search`).
4. Le frontend ouvre la page de la meilleure fiche (`plante.html?id=...`) ;
   les autres résultats y sont proposés.
5. `frontend/js/plant.js` appelle `GET /api/plants/<id>`, qui renvoie la fiche
   et ses conseils d'entretien générés à partir de la base.

**O2, des plantes pour un environnement** (barre de droite) :

1. `home.js` envoie `POST /api/recommendations` avec les critères : deux
   curseurs de 0 à 100 (lumière, eau) et des choix facultatifs (difficulté,
   saison, terre, type, pot).
2. `query_builder.py` vérifie les critères et découpe la demande. Chaque
   critère porte un **code** (pour l'heuristique : un curseur à 80 % donne
   `full_sun`) et une **valeur entre 0 et 1** (pour la méthode vectorielle :
   0,8). Les deux méthodes reçoivent donc exactement la même demande.
3. La méthode choisie calcule un score par fiche (`recommend`).
4. Le frontend affiche une liste de fiches cliquables, le temps de la
   recherche et un graphique des scores.

Dans les deux cas, le service chronomètre le calcul et l'enregistre dans la
table `recommendation_runs` avec la méthode et l'objectif. Au premier appel
d'une méthode, il lit toutes les plantes et lui fait construire son index
(`fit`), gardé ensuite en mémoire.

Les deux méthodes héritent de `BaseRecommender` (`recommenders/base.py`) et
codent les mêmes méthodes `fit`, `search`, `recommend` et `index_stats`.

## 5. Méthode 1 : heuristique (règles SI... ALORS)

Une heuristique est une règle simple, écrite à la main (`recommenders/heuristic.py`).

**O2 : des filtres stricts.** Chaque critère choisi est une règle :
*SI la fiche ne respecte pas le critère ALORS elle est éliminée*. Une plante
de plein soleil n'est jamais proposée pour un coin d'ombre. Les fiches
restantes sont classées par précision :

- chaque critère a un **poids** (`WEIGHTS` dans `query_builder.py`) : type 3,
  lumière 3, eau 3, difficulté 2, saison 2, terre 2, pot 2 ;
- un critère respecté rapporte 1 point si la fiche ne mentionne que la
  valeur demandée, 0,75 si elle l'accepte parmi d'autres (« mi-ombre ou plein
  soleil » pour une demande « plein soleil ») ;
- score = somme des `poids × points` / somme des poids.

Exemple : demande « plein soleil » et « peu d'eau ». Le romarin (plein soleil,
peu d'eau) obtient 1. La tomate (plein soleil, beaucoup d'eau) est éliminée.

**O1 : des règles sur le nom**, de la plus exigeante à la plus souple
(`_search_rule`). La première règle vraie donne le score :

| Règle | Score |
|---|---|
| le nom est exactement la recherche | 1,0 |
| le nom commence par la recherche | 0,9 |
| un mot du nom commence par la recherche | 0,8 |
| le nom contient la recherche | 0,7 |
| le type de plante correspond (« tomate » → Tomates) | 0,6 |
| le nom latin contient la recherche | 0,5 |

Les ex æquo sont départagés par facilité de culture, puis par identifiant.

Forces : rapide, sûre, chaque résultat s'explique par une règle. Faiblesses :
rigide. Un critère de trop ou une faute de frappe, et il n'y a aucun résultat.

## 6. Méthode 2 : vectorielle (distance dans un espace vectoriel)

On représente chaque fiche par une liste de nombres (un vecteur), la demande
aussi, et on mesure leur proximité (`recommenders/vector.py`).

**O2 : une distance entre deux points.** Chaque fiche a 13 coordonnées entre
0 et 1 :

- lumière, eau, difficulté : la position moyenne de ses codes (ombre = 0,
  mi-ombre = 0,5, plein soleil = 1 ; une fiche « mi-ombre ou plein soleil »
  vaut 0,75) ;
- 4 coordonnées « oui / non » pour les saisons, 5 pour les terres, 1 pour le pot.

La demande donne la valeur visée pour chaque critère choisi : un curseur à
80 % vise 0,8. Pour chaque critère, l'**écart** est la différence entre la
valeur de la fiche et la valeur visée. Le score est :

```
distance = racine( somme(poids × écart²) / somme(poids) )      (entre 0 et 1)
score    = 1 - distance
```

C'est une distance euclidienne pondérée. Exemple : demande lumière 100 %, eau
50 %. La tomate (lumière 1, eau 1) a des écarts de 0 et 0,5 :
distance = racine((3 × 0² + 3 × 0,5²) / 6) = 0,35, score = 0,65.

Aucune fiche n'est éliminée : la méthode renvoie toujours les plus proches.
Une fiche qui ne dit rien sur un critère reçoit l'écart maximal (1).

**O1 : des paires de lettres.** Un texte devient le vecteur de ses paires de
lettres voisines : « tomate » donne `_t`, `to`, `om`, `ma`, `at`, `te`, `e_`
(« _ » marque le début ou la fin d'un mot). Deux textes qui partagent
beaucoup de paires ont des vecteurs de même direction. On mesure cela par le
**cosinus** de l'angle entre les deux vecteurs (1 = mêmes paires, 0 = aucune
en commun) ; comme les vecteurs sont ramenés à une longueur de 1, le cosinus
est un simple produit scalaire. La recherche est comparée au nom, au nom
latin et au type de chaque fiche, et on garde la meilleure ressemblance.
En dessous de 0,4, la fiche est ignorée.

Intérêt : « rosemarry » retrouve « Rosemary » et « lavande » retrouve
« Lavender », ce que les règles de l'heuristique ne font pas.

Forces : souple, répond toujours, tient compte de la valeur exacte du
curseur. Faiblesses : ne garantit rien (elle peut proposer une plante
d'ombre un peu trop au soleil) et ses résultats s'expliquent moins bien.

## 7. Comparaison des deux méthodes

Notations : `N` fiches, `c` critères choisis (7 au plus), `d` coordonnées par
fiche (13), `P` paires de lettres par fiche en moyenne.

| | Heuristique | Vectorielle |
|---|---|---|
| Principe | règles SI... ALORS | distance entre vecteurs |
| O2 : critère non respecté | fiche éliminée | fiche pénalisée |
| O2 : demande trop stricte | aucun résultat | les fiches les plus proches |
| O2 : valeur exacte du curseur | ignorée (seul le niveau compte) | prise en compte |
| O1 : faute de frappe | aucun résultat | tolérée |
| Construction de l'index | O(N) | O(N × d) + O(N × P) |
| O1 : calcul | O(N) comparaisons de textes | O(N × P), matrice creuse |
| O2 : calcul | O(N × c), boucle Python | O(N × d), calcul numpy |
| Tri | O(N log N) | O(N log N) |
| Mémoire | O(N) | O(N × d) + O(N × P) |
| Explication | la règle ou les points de chaque critère | proximité par critère, paires de lettres |

À retenir :

- les deux méthodes sont linéaires en `N`, avec des temps du même ordre sur
  1 972 fiches (quelques millisecondes) ;
- les **scores ne sont pas comparables** entre méthodes : on compare les
  classements, le nombre de résultats et les temps ;
- le tableau de bord compte les recherches restées **sans résultat** : c'est
  là que les deux méthodes diffèrent le plus.

## 8. Métriques

Deux durées sont enregistrées pour chaque recherche :

- `algo_ms` : le calcul de la méthode seul (scores, tri, explication) ;
- `total_ms` : tout le traitement côté serveur (vérification, lectures en
  base, calcul). La **première** recherche d'une méthode après un démarrage
  inclut la construction de son index : elle tire le maximum vers le haut.

`MetricsService` regroupe les mesures par méthode et par objectif, et
`computeStats` calcule nombre, minimum, maximum, moyenne, médiane et 95e
centile. Le temps réseau entre navigateur et serveur n'est pas compté.

## 9. Limites connues (matière pour le rapport d'optimisation)

Recommandation :
- Heuristique, O2 : beaucoup d'ex æquo, et aucun résultat dès qu'un critère
  est trop strict.
- Vectorielle, O2 : elle peut proposer une fiche qui viole un critère
  important ; on pourrait combiner les deux (filtrer par règles, puis classer
  par distance).
- La normalisation se trompe parfois (une règle de mots-clés ne comprend pas
  la phrase) et 6 à 9 % des fiches n'ont pas de code pour l'eau ou la terre.
- O1 : les noms des variétés sont en anglais. « menthe » ne trouve « Mint »
  qu'avec la méthode vectorielle, et de justesse.
- Le jeu de données ne dit pas si une plante est toxique pour les animaux :
  cette règle ne peut pas être codée.
- La qualité des résultats n'a pas encore été évaluée : il faudrait une liste
  de demandes avec les plantes attendues, et mesurer chaque méthode dessus.

Performance :
- Heuristique : boucle Python sur toutes les fiches. Un filtre SQL (`WHERE`)
  ou des tableaux numpy iraient plus vite.
- Vectorielle : toutes les distances sont calculées. Un index spatial
  (arbre k-d) éviterait de tout parcourir.
- Les deux : tri complet en O(N log N) alors qu'il suffit des k meilleurs
  (`numpy.argpartition` : O(N + k log k)).
- Les index sont reconstruits à chaque démarrage et ne sont pas partagés
  entre plusieurs processus.
- Chaque recherche compte les plantes en base pour vérifier l'index.
- `GET /api/metrics` relit toutes les mesures ; les statistiques pourraient
  être calculées en SQL.
- Les résultats renvoient tous les champs de chaque plante alors que la liste
  n'en affiche que quelques-uns (plus de données sur le réseau, donc plus de
  batterie côté client).
- Les photos sont chargées depuis Wikimedia à chaque affichage.
- La consommation d'énergie n'est pas encore mesurée.

## 10. Suite prévue

1. Comparaison directe : lancer les deux méthodes sur la même demande et
   afficher les deux listes côte à côte.
2. Mesure de la consommation (énergie, mémoire) et rapport de performance.
3. Optimisations de la section 9, avec mesures avant et après.
4. Branding, logo, interface finale.
