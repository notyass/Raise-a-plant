# Plante ton gramme

> « Pourquoi acheter un 10, quand tu peux en faire pousser dix ? »

Application web **découplée** de recommandation comparée de plantations.
L'utilisateur décrit ses conditions (soleil, eau, terre, saison, niveau) et
l'application lui recommande des plantes, en affichant pour chaque approche de
recommandation ses résultats, ses temps de réponse et sa complexité.

SAÉ BUT3 Informatique 5.Real.01, 2026-2027.
Équipe : Yacine Raboudi, Solène Bourg, Faizan Ishaq, Antoine Badedji,
Christophe Félix Lin Huang.

**Version actuelle : 0.2.0.**

| | 0.1.0 | 0.2.0 (actuelle) | Version finale (1.0.0) |
|---|---|---|---|
| Approche 1 : TF-IDF + cosinus | faite | faite | à optimiser |
| Approche 2 : embeddings + cosinus | emplacement prévu | faite | à optimiser |
| Tableau de bord | une approche | une carte par approche | comparaison sur une même demande |
| Interface | complète, sobre | complète, sobre | branding, logo |

## Architecture

```
plante-ton-gramme/
├── backend/                  API JSON (Python, Flask)
│   ├── run.py                point d'entrée
│   ├── app/
│   │   ├── __init__.py       fabrique de l'application, CORS
│   │   ├── config.py         configuration (base de données, origines autorisées)
│   │   ├── models/           M : tables (ORM SQLAlchemy) et mixins
│   │   ├── controllers/      C : routes HTTP (un Blueprint par fichier)
│   │   ├── services/         logique métier
│   │   │   ├── recommenders/ les approches de recommandation
│   │   │   └── ...
│   │   ├── cli.py            commande `flask seed`
│   │   └── errors.py         erreurs renvoyées en JSON
│   ├── data/                 jeu de données (téléchargé) et échantillon
│   └── tests/                tests automatiques (pytest)
├── frontend/                 interface (HTML, CSS, JavaScript, Chart.js)
├── docs/EXPLICATIONS.md      explication détaillée du fonctionnement
└── docker-compose.yml        PostgreSQL + backend + frontend
```

Le backend ne renvoie que du JSON et le frontend n'est fait que de fichiers
statiques : les deux communiquent uniquement par HTTP (voir
`frontend/js/config.js`). Dans le modèle MVC, la « vue » est le frontend.

Le détail du fonctionnement (TF-IDF, complexité, métriques, limites) est
dans [docs/EXPLICATIONS.md](docs/EXPLICATIONS.md).

## Lancer en local (sans Docker, base SQLite)

Il faut Python 3.10 ou plus récent. Deux terminaux sont nécessaires.

**Terminal 1 : le backend**

```
cd backend
python -m venv .venv
.venv\Scripts\activate            (Windows ; sous macOS/Linux : source .venv/bin/activate)
pip install -r requirements.txt
flask --app run seed              (télécharge et importe les 1 972 plantes, une seule fois)
flask --app run run --debug       (API sur http://localhost:5000/api)
```

Sans connexion internet : `flask --app run seed --sample` importe 19 fiches
d'exemple à la place.

**Approche embeddings (facultatif mais nécessaire pour comparer)**

```
pip install -r requirements-embeddings.txt     (installe PyTorch : plusieurs centaines de Mo)
flask --app run build-index                    (télécharge le modèle et calcule les vecteurs des fiches)
```

`build-index` est à lancer une fois : les vecteurs sont gardés dans
`backend/instance/`. Sans cette commande, le calcul se fait à la première
recommandation par embeddings, qui est alors lente. Sans ces dépendances,
l'application fonctionne et l'approche est affichée comme indisponible.

Le modèle se choisit avec la variable d'environnement `EMBEDDING_MODEL`
(par défaut `sentence-transformers/all-MiniLM-L6-v2`).

**Terminal 2 : le frontend**

```
python -m http.server 8080 --directory frontend
```

Puis ouvrir http://localhost:8080. Ne pas ouvrir `index.html` par
double-clic : le navigateur bloque alors les appels à l'API.

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
| GET | `/api/options` | critères du formulaire et leurs choix |
| GET | `/api/approaches` | approches disponibles et prévues |
| GET | `/api/categories` | types de plantes avec leur nombre de fiches |
| GET | `/api/plants?category=&q=&page=&per_page=` | catalogue paginé |
| GET | `/api/plants/<id>` | fiche d'une plante |
| POST | `/api/recommendations` | calcule une recommandation |
| GET | `/api/metrics` | temps de réponse et index de chaque approche |

Exemple de recommandation :

```
POST /api/recommendations
{"criteria": {"sun": "full_sun", "difficulty": "easy", "container": true},
 "approach": "tfidf", "top_k": 5}          ("approach" : "tfidf" ou "embeddings")
```

## Données

Plant Variety Database de Wind River Greens (CC BY 4.0), 1 972 variétés.
Détails et crédits dans [backend/data/README.md](backend/data/README.md).

## Organisation git et versions

- Numérotation sémantique `MAJEUR.MINEUR.CORRECTIF` : `0.1.0` pour la
  première approche, `0.2.0` avec la deuxième, `1.0.0` pour la version
  finale. Chaque rendu porte une étiquette git (`v0.2.0`).
- Une branche par fonctionnalité (`feature/embeddings`, `feature/dashboard`),
  fusionnée dans `main` par pull request relue par un autre membre.

## Licence

Code sous licence MIT (fichier `LICENSE`). **Proposition à valider en
équipe**, le sujet demande de justifier ce choix : la licence MIT est courte,
autorise toute réutilisation tant que les auteurs sont cités, et reste
compatible avec les bibliothèques utilisées (Flask et scikit-learn en BSD,
Chart.js en MIT, sentence-transformers en Apache 2.0). Les données gardent leur propre licence (CC BY 4.0).
