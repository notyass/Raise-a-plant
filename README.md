# Raise a Plant

> « Pourquoi acheter un 10, quand tu peux en faire pousser dix ? »

Application web **découplée** qui aide les débutants à réussir leurs
plantations. Elle répond à deux objectifs :

- **O1** : recevoir des conseils pour prendre soin d'une plante donnée ;
- **O2** : recevoir des suggestions de plantes adaptées à un environnement donné.

Chaque recherche peut se faire avec deux méthodes de recommandation
différentes, et un tableau de bord compare leurs temps de réponse et leur
complexité.

SAÉ BUT3 Informatique 5.Real.01, 2026-2027.
Équipe : Yacine Raboudi, Solène Bourg, Faizan Ishaq, Antoine Badedji,
Christophe Félix Lin Huang.

**Version actuelle : 0.4.0.**

## Les deux méthodes

| | Méthode 1 : heuristique | Méthode 2 : vectorielle |
|---|---|---|
| Principe | des règles « SI... ALORS... » écrites à la main | des distances dans un espace vectoriel |
| O1 (retrouver une plante) | règles sur le nom : exact, début, mot, type, nom latin | ressemblance des paires de lettres, tolère les fautes de frappe |
| O2 (plantes pour un environnement) | filtres stricts : un critère non respecté élimine la fiche | distance entre la demande et chaque fiche : répond toujours |
| Fichier | `app/services/recommenders/heuristic.py` | `app/services/recommenders/vector.py` |

## Pages de l'interface

| Page | Rôle |
|---|---|
| `index.html` | accueil avec la méthode heuristique : objectifs du projet, barres de recherche O1 et O2 |
| `vectorielle.html` | la même page d'accueil avec la méthode vectorielle |
| `plante.html?id=…` | page d'une plante générée à partir de la base : photo, fiche, conseils d'entretien |
| `tableau-de-bord.html` | comparaison des deux méthodes pour chaque objectif |
| `equipe.html` | présentation de l'équipe et du projet |

## Architecture

Le backend suit la structure vue en TD (Flask + Blueprints + ORM + Services),
sans les templates Jinja puisque l'affichage est dans le frontend.

```
plante-ton-gramme/                (le dossier garde son ancien nom)
├── backend/                      API JSON (Python, Flask, SQLAlchemy)
│   ├── main.py                   point d'entrée : python main.py
│   ├── prepa_db.py               crée la base et importe les données
│   ├── prepa_images.py           récupère les photos (Wikimedia Commons)
│   ├── app/
│   │   ├── __init__.py           create_app() : configuration, blueprints, CORS
│   │   ├── config.py             configuration (base de données, origines autorisées)
│   │   ├── errors.py             erreurs renvoyées en JSON
│   │   ├── blueprints/           un dossier par Blueprint, avec son routes.py
│   │   │   ├── health/           GET /api/health
│   │   │   ├── plants/           GET /api/plants, /api/plants/<id>, /api/categories
│   │   │   ├── recommendations/  POST /api/searches, /api/recommendations, GET /api/options, /api/approaches
│   │   │   └── metrics/          GET /api/metrics
│   │   ├── models/               ORM : une classe par fichier
│   │   │   ├── base.py           Base, BaseModelMixin, TimestampMixin, get_engine()
│   │   │   ├── Category.py, Plant.py, RecommendationRun.py
│   │   │   ├── PlantDAOInterface.py, PlantDAO.py
│   │   │   └── RecommendationRunDAO.py
│   │   └── services/             logique métier
│   │       ├── PlantService.py, RecommendationService.py, MetricsService.py
│   │       ├── normalizer.py     texte anglais -> codes (soleil, eau, terre...)
│   │       ├── query_builder.py  critères du formulaire O2, poids, libellés français
│   │       ├── care_guide.py     conseils d'entretien de la page d'une plante (O1)
│   │       ├── document_builder.py, images.py, text_utils.py
│   │       └── recommenders/     les méthodes : base.py, heuristic.py, vector.py
│   ├── data/                     jeu de données (téléchargé) et échantillon
│   └── tests/                    tests automatiques (pytest)
├── frontend/                     interface (HTML, CSS, JavaScript, Chart.js)
├── serve_frontend.py             sert le frontend en développement
├── docs/EXPLICATIONS.md          explication détaillée du fonctionnement
└── docker-compose.yml            PostgreSQL + backend + frontend
```

Chemin d'une requête : `routes.py` (Blueprint) → Service → DAO → modèle ORM
→ base de données. Le backend ne renvoie que du JSON et le frontend n'est
fait que de fichiers statiques : les deux communiquent uniquement par HTTP
(voir `frontend/js/config.js`).

Le détail du fonctionnement (méthodes, complexité, métriques, limites) est
dans [docs/EXPLICATIONS.md](docs/EXPLICATIONS.md).

## Lancer en local (sans Docker, base SQLite)

Il faut Python 3.10 ou plus récent. Deux terminaux sont nécessaires.

**Terminal 1 : le backend**

```
cd backend
python -m venv .venv
.venv\Scripts\activate            (Windows ; sous macOS/Linux : source .venv/bin/activate)
pip install -r requirements.txt
python prepa_db.py                (télécharge et importe les 1 972 plantes)
python prepa_images.py            (facultatif : récupère les photos, une à deux minutes)
python main.py                    (API sur http://localhost:5000/api)
```

`python prepa_db.py` réinitialise la base : à relancer après chaque
changement des modèles ou des règles de normalisation. Sans connexion
internet, `python prepa_db.py --sample` importe 19 fiches d'exemple.
`prepa_images.py` écrit `data/images.json`, que `prepa_db.py` relit ensuite :
inutile de le relancer après une réinitialisation.

**Terminal 2 : le frontend** (depuis la racine du projet)

```
python serve_frontend.py
```

Puis ouvrir http://localhost:8080. Ce petit serveur interdit au navigateur de
garder les fichiers en mémoire : après une mise à jour du code, on voit tout
de suite la nouvelle version. Ne pas ouvrir `index.html` par double-clic : le
navigateur bloque alors les appels à l'API.

## Lancer avec Docker (base PostgreSQL)

```
docker compose up --build
```

- Interface : http://localhost:8080
- API : http://localhost:5000/api/health

Les données sont importées au premier démarrage du backend.

## Tests

```
cd backend
python -m pytest
```

## API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/health` | état de l'API, version, nombre de plantes |
| GET | `/api/options` | critères du formulaire O2 et leurs choix |
| GET | `/api/approaches` | les deux méthodes et les deux objectifs |
| GET | `/api/categories` | types de plantes avec leur nombre de fiches |
| GET | `/api/plants?category=&q=&page=&per_page=` | liste paginée des plantes |
| GET | `/api/plants/<id>` | page d'une plante : fiche et conseils d'entretien |
| POST | `/api/searches` | O1 : retrouve une plante par son nom |
| POST | `/api/recommendations` | O2 : propose des plantes pour un environnement |
| GET | `/api/metrics` | temps de réponse de chaque méthode, par objectif |

Exemples (`approach` vaut `heuristic` ou `vector` ; `sun` et `water` sont des
curseurs de 0 à 100) :

```
POST /api/searches
{"query": "tomate", "approach": "heuristic", "top_k": 8}

POST /api/recommendations
{"criteria": {"sun": 80, "water": 30, "difficulty": "easy", "container": true},
 "approach": "vector", "top_k": 12}
```

## Données

Plant Variety Database de Wind River Greens (CC BY 4.0), 1 972 variétés.
Les types de plantes, cinq caractéristiques (soleil, eau, terre, saison,
difficulté) et les conseils d'entretien sont en français ; les descriptions
restent en anglais. Les photos viennent de Wikimedia Commons, avec le nom de
l'auteur et la licence de chacune. Détails et crédits dans
[backend/data/README.md](backend/data/README.md).

## Organisation git et versions

- Numérotation sémantique `MAJEUR.MINEUR.CORRECTIF`. `0.1.0` : première
  approche (TF-IDF). `0.2.0` : essai d'une approche par embeddings. `0.3.0` :
  architecture du TD, approche heuristique, libellés français. `0.4.0` : deux
  objectifs, méthode vectorielle à curseurs, pages de l'interface, photos.
  `1.0.0` : version finale. Chaque rendu porte une étiquette git (`v0.4.0`).
- Une branche par fonctionnalité, fusionnée dans `main` par pull request
  relue par un autre membre.

## Licence

Code sous licence MIT (fichier `LICENSE`). **Proposition à valider en
équipe**, le sujet demande de justifier ce choix : la licence MIT est courte,
autorise toute réutilisation tant que les auteurs sont cités, et reste
compatible avec les bibliothèques utilisées (Flask et scikit-learn en BSD,
SQLAlchemy et Chart.js en MIT). Les données gardent leur propre licence
(CC BY 4.0).
