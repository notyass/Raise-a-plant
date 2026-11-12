# Comment fonctionne l'application (version 0.2.0)

Ce document sert à ce que toute l'équipe puisse expliquer le code à l'oral.

## 1. Vue d'ensemble

```
Navigateur                         Serveur
┌───────────────────┐   HTTP    ┌───────────────────────────────────────┐
│ frontend (8080)   │  + JSON   │ backend Flask (5000)                  │
│ HTML / CSS / JS   │ ────────► │ contrôleurs ─► services ─► modèles ─► │ base de données
│ Chart.js          │ ◄──────── │ (routes)       (logique)   (ORM)      │ SQLite ou PostgreSQL
└───────────────────┘           └───────────────────────────────────────┘
```

- **Découplage** : le frontend et le backend sont deux programmes séparés,
  servis sur deux adresses différentes. Le seul lien est l'adresse de l'API
  dans `frontend/js/config.js`. On peut remplacer l'un sans toucher l'autre.
- **CORS** : comme les deux adresses diffèrent, le navigateur n'autorise les
  appels que si l'API le permet explicitement. C'est le rôle de
  `_register_cors` dans `backend/app/__init__.py`.
- **MVC** : les modèles sont dans `models/`, les contrôleurs dans
  `controllers/`, et la vue est le frontend. Les `services/` contiennent la
  logique pour que les contrôleurs restent courts.
- **ORM et mixins** : `models/mixins.py` définit `TimestampMixin` (colonnes
  `created_at` et `updated_at`) et `SerializerMixin` (méthode `to_dict()`),
  réutilisés par plusieurs modèles. L'ORM écrit le SQL : le même code
  fonctionne avec SQLite (développement) et PostgreSQL (Docker).

## 2. Parcours d'une recommandation

1. L'utilisateur remplit le formulaire. `frontend/js/recommend.js` envoie
   `POST /api/recommendations` avec les critères.
2. `controllers/recommendations_controller.py` vérifie le format de la
   requête et appelle `recommendation_service.recommend(...)`.
3. `services/query_builder.py` vérifie les critères et les transforme en
   texte anglais. Exemple : plein soleil + débutant + pot devient
   `full sun, easy, container friendly`. Les deux approches reçoivent
   exactement ce même texte : on compare les algorithmes, pas la formulation.
4. Au premier appel, `recommendation_service` lit toutes les plantes,
   construit un texte par plante (`document_builder.py`) et demande à
   l'approche de construire son index (`fit`). L'index reste en mémoire.
5. L'approche choisie (`recommenders/tfidf.py` ou
   `recommenders/embeddings.py`) calcule un score par plante et renvoie les
   meilleures, avec ce qui explique le score.
6. Le service chronomètre le calcul, enregistre la mesure dans la table
   `recommendation_runs` et renvoie le JSON.
7. Le frontend affiche les résultats, le temps de cette requête et un
   graphique des scores. L'onglet « Tableau de bord » lit `GET /api/metrics`.

## 3. TF-IDF et similarité cosinus

On veut mesurer à quel point la fiche d'une plante ressemble à la demande.

- **TF** (fréquence du terme) : plus un terme apparaît dans une fiche, plus
  il compte pour elle. On utilise `1 + ln(tf)` pour qu'un mot répété dix
  fois ne compte pas dix fois plus (`sublinear_tf=True`).
- **IDF** (fréquence inverse) : un terme présent dans presque toutes les
  fiches (« soil ») distingue mal les plantes ; un terme rare (« drought »)
  distingue bien. Formule de scikit-learn : `idf(t) = ln((1 + N) / (1 + df(t))) + 1`,
  où `N` est le nombre de fiches et `df(t)` le nombre de fiches contenant `t`.
- **Poids** d'un terme dans une fiche : `TF × IDF`. Chaque fiche devient un
  vecteur de poids (une coordonnée par terme du vocabulaire), ramené à une
  longueur de 1.
- **Termes** : les mots seuls et les paires de mots voisins, pour distinguer
  « full sun » de « full shade ». La fonction `analyze` de `tfidf.py` fait ce
  découpage : elle ignore les mots vides anglais (« the », « and ») et ne
  forme pas de paire à cheval sur une ponctuation (« Full sun. Easy » ne
  donne pas « sun easy »).
- **Similarité cosinus** : la demande est transformée en vecteur de la même
  façon. Le score est le cosinus de l'angle entre les deux vecteurs : 1 s'ils
  ont la même direction, 0 s'ils n'ont aucun terme en commun. Comme les
  vecteurs ont une longueur de 1, le cosinus est un simple produit scalaire.
- La matrice des fiches est **creuse** : chaque fiche n'utilise qu'une petite
  partie du vocabulaire, on ne stocke donc que les valeurs non nulles.

**Pourquoi cette recommandation ?** Le score est la somme, sur les termes
communs, de `poids dans la demande × poids dans la fiche`. On affiche les
termes qui pèsent le plus (`_explain` dans `tfidf.py`).

## 4. Embeddings et similarité cosinus

TF-IDF ne voit que les mots exacts. Un **embedding** représente le sens.

- Un **modèle de langage** (par défaut `all-MiniLM-L6-v2`, un petit réseau
  de neurones de type Transformer) lit un texte et produit un vecteur de 384
  nombres. Il a été entraîné pour que deux textes de sens proche donnent des
  vecteurs proches, même sans mot en commun.
- Chaque fiche est encodée **une fois**. C'est l'étape lente : les vecteurs
  sont donc enregistrés dans `backend/instance/embeddings_….npy` et relus
  aux démarrages suivants. Le nom du fichier dépend du modèle et des textes :
  si l'un des deux change, les vecteurs sont recalculés.
- À chaque demande, la requête est encodée par le même modèle, puis comparée
  à toutes les fiches par similarité cosinus (produit matrice × vecteur),
  exactement comme pour TF-IDF.
- La matrice est **dense** : N × 384 nombres, tous utiles. Celle de TF-IDF
  est creuse : N × V cases, presque toutes à zéro.
- Toutes les fiches reçoivent un score : il y a toujours `top_k` résultats,
  même si rien ne correspond vraiment. TF-IDF, lui, ne renvoie rien quand
  aucun mot n'est commun.

**Pourquoi cette recommandation ?** Un embedding ne dit pas quel mot a
compté. On encode donc aussi chaque critère séparément (« full sun »,
« easy »…) et on mesure sa proximité avec la fiche : on affiche les critères
que la fiche satisfait le mieux au sens du modèle (`_explain` dans
`embeddings.py`). C'est une indication, pas une décomposition exacte du score.

**Dépendances** : la bibliothèque `sentence-transformers` (qui installe
PyTorch) est dans `requirements-embeddings.txt`. Si elle est absente,
l'approche est signalée comme indisponible et le reste fonctionne.
`recommendation_service._create_recommender` lui passe le nom du modèle et
le dossier de cache.

**Tests** : `tests/fake_encoder.py` remplace le modèle par une fonction
légère qui respecte le même contrat (textes → vecteurs). On teste ainsi la
mécanique (normalisation, tri, filtre, cache) sans télécharger de modèle.

## 5. Complexité des deux approches

Notations : `N` fiches, `L` termes distincts par fiche en moyenne, `V` taille
du vocabulaire, `d` dimension des embeddings, `C` coût d'un passage de texte
dans le modèle de langage (il dépend de la longueur du texte et de la taille
du modèle, pas de `N`).

| Étape | TF-IDF | Embeddings |
|---|---|---|
| Construction de l'index | O(N × L) | O(N × C) la première fois, puis relecture O(N × d) |
| Préparer la requête | proportionnel à sa longueur | O(C) : un passage dans le modèle |
| Similarité avec les N fiches | O(N × L), matrice creuse | O(N × d), matrice dense |
| Tri des scores | O(N log N) | O(N log N) |
| Mémoire | O(N × L) + O(V) | O(N × d) + poids du modèle |

À retenir pour la comparaison : les deux recherches sont linéaires en `N`,
mais les embeddings paient à chaque requête le passage dans le modèle (`C`),
et demandent plus de matériel (mémoire pour le modèle, processeur ou carte
graphique). TF-IDF est léger mais limité aux mots exacts.

Les valeurs mesurées (N, V, L, d, mémoire, temps de construction) sont
affichées dans le tableau de bord.

## 6. Métriques

Deux durées sont enregistrées pour chaque recommandation :

- `algo_ms` : le calcul de l'approche seul (vectorisation ou encodage de la
  requête, similarité, tri, explication) ;
- `total_ms` : tout le traitement côté serveur (vérification, lectures en
  base, calcul). La **première** requête après un démarrage inclut la
  construction de l'index : elle tire le maximum vers le haut.

`metrics_service.compute_stats` calcule nombre, minimum, maximum, moyenne,
médiane et 95e centile. Le temps réseau entre navigateur et serveur n'est pas
compté.

## 7. Limites connues (matière pour le rapport d'optimisation)

Recommandation :
- Tous les champs d'une fiche sont mélangés dans un seul texte : le mot
  « moderate » de l'arrosage se confond avec celui de la difficulté.
- TF-IDF : seuls les mots exacts comptent. Sur le vrai jeu de données, les
  mots-clés « needs little water » font remonter des variétés dont le nom
  contient « Little ». À comparer avec les embeddings sur la même demande.
- Embeddings : le modèle par défaut ne lit que les 256 premiers morceaux de
  mots d'un texte ; la fin des fiches les plus longues est ignorée.
- Embeddings : la requête est une liste de mots-clés, alors que le modèle a
  été entraîné sur des phrases. Une requête rédigée pourrait mieux marcher.
- Les données et les mots-clés sont en anglais. Un modèle multilingue
  (voir `config.py`) accepterait des mots-clés en français, mais il est plus lent.
- La qualité des résultats n'a pas encore été évaluée : il faudrait une liste
  de demandes avec les plantes attendues, et mesurer chaque approche dessus.

Performance :
- TF-IDF : le produit matrice × requête parcourt toutes les fiches. Un index
  inversé ne parcourrait que les fiches contenant un terme de la requête.
- Embeddings : comparaison avec toutes les fiches. Une recherche approximative
  des plus proches voisins (HNSW, FAISS) éviterait de tout parcourir.
- Embeddings : la même requête est réencodée à chaque fois ; on pourrait
  mémoriser les vecteurs des requêtes fréquentes.
- Tri complet en O(N log N) alors qu'il suffit des k meilleurs
  (`numpy.argpartition` : O(N + k log k)).
- L'index TF-IDF est reconstruit à chaque démarrage, et les index ne sont
  pas partagés entre plusieurs processus.
- Chaque recommandation compte les plantes en base pour vérifier l'index.
- `GET /api/metrics` relit toutes les mesures ; les statistiques pourraient
  être calculées en SQL.
- Le catalogue renvoie tous les champs de chaque plante alors que la liste
  n'en affiche que quelques-uns (plus de données sur le réseau, donc plus de
  batterie côté client).
- La consommation d'énergie n'est pas encore mesurée.

## 8. Suite prévue

1. Comparaison directe : lancer les deux approches sur la même demande et
   afficher les deux listes côte à côte (plantes communes, différences de
   rang, temps de chacune).
2. Mesure de la consommation (énergie, mémoire) et rapport de performance.
3. Optimisations de la section 7, avec mesures avant et après.
4. Branding, logo, interface finale.
