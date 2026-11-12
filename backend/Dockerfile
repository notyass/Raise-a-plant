FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-prod.txt requirements-embeddings.txt ./
# PyTorch en version « processeur seul » : image bien plus légère que la version GPU.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt -r requirements-prod.txt -r requirements-embeddings.txt

COPY . .

EXPOSE 5000

# Au démarrage : import des données si la base est vide, calcul des index
# (téléchargement du modèle et vecteurs des fiches), puis serveur gunicorn.
# Un seul processus : les index sont gardés en mémoire dans ce processus.
CMD ["sh", "-c", "flask --app run seed && flask --app run build-index && gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 180 run:app"]
