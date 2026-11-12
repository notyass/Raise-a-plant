FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-prod.txt

COPY . .

EXPOSE 5000

# Au démarrage : import des données si la base est vide, puis serveur gunicorn.
# Un seul processus : les index de recommandation sont gardés en mémoire dans ce processus.
CMD ["sh", "-c", "python prepa_db.py --if-empty && gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 main:app"]
