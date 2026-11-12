"""Récupère une photo libre pour chaque espèce : python prepa_images.py

Pour chaque nom latin de la base, le script demande à Wikipédia la photo
principale de la page de l'espèce, puis à Wikimedia Commons son auteur et sa
licence (API MediaWiki, gratuite et sans clé). Seules les images sous
licence libre sont gardées, avec leur crédit.

Le résultat est écrit dans data/images.json, puis recopié dans la base.
prepa_db.py relit ce fichier : pas besoin de relancer ce script après une
réinitialisation de la base. À lancer une fois, après prepa_db.py
(une à deux minutes, connexion internet nécessaire).

Wikimedia exige que chaque programme s'identifie avec une adresse de
contact (adresse web ou e-mail) dans son en-tête User-Agent ; sans elle, les
requêtes sont refusées (erreur 429). Par défaut, le script utilise l'adresse
du dépôt git du projet. Pour en donner une autre :

    python prepa_images.py --contact https://github.com/equipe/projet
"""
import argparse
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.models import Plant, get_engine
from app.services.images import clean_repository_url, lookup_title
from prepa_db import IMAGE_COLUMNS, IMAGES_FILE

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
BATCH_SIZE = 50  # nombre maximal de titres par requête
THUMBNAIL_WIDTH = 480
PAUSE_SECONDS = 1.0  # pause entre deux requêtes, par politesse pour le serveur
MAX_ATTEMPTS = 4  # nombre d'essais d'une requête refusée pour cause de trafic
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# En-tête User-Agent, rempli au démarrage par main() : voir build_user_agent().
USER_AGENT = None


def repository_url():
    """Adresse web du dépôt git du projet (git remote), ou None."""
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=BACKEND_DIR, capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None  # git absent, ou pas de dépôt distant
    return clean_repository_url(result.stdout)


def build_user_agent(contact):
    """User-Agent conforme à la règle de Wikimedia : « Nom/version (contact) »."""
    return f"RaiseAPlant/0.4 ({contact}; projet etudiant, BUT Informatique)"


def call_api(url, params):
    """Appelle une API MediaWiki et renvoie la partie « query » de la réponse JSON.

    Si le serveur répond qu'il reçoit trop de requêtes (429) ou qu'il est
    surchargé (503), on attend le temps qu'il indique puis on réessaie.
    """
    params = dict(params, action="query", format="json", formatversion="2")
    request = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT}
    )
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            time.sleep(PAUSE_SECONDS)
            return data.get("query", {})
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or attempt == MAX_ATTEMPTS:
                # on montre le début de la réponse : Wikimedia y explique le refus
                message = clean_html(error.read().decode("utf-8", errors="replace"))[:300]
                raise SystemExit(f"[!] Requête refusée par Wikimedia (erreur {error.code}). {message}")
            retry_after = error.headers.get("Retry-After", "")
            wait = int(retry_after) if retry_after.isdigit() else 10 * attempt
            print(f"    serveur occupé (erreur {error.code}) : nouvel essai dans {wait} s...")
            time.sleep(wait)


def batches(items, size=BATCH_SIZE):
    for start in range(0, len(items), size):
        yield items[start:start + size]


def resolve(title, query):
    """Suit les renommages de l'API : titre demandé -> titre de la page renvoyée."""
    for step in ("normalized", "redirects"):
        for entry in query.get(step, []):
            if entry.get("from") == title:
                title = entry.get("to")
    return title


def fetch_page_images(titles):
    """{titre demandé: (nom du fichier image, adresse de la vignette)} pour les pages illustrées."""
    found = {}
    for batch in batches(titles):
        query = call_api(WIKIPEDIA_API, {
            "titles": "|".join(batch),
            "redirects": "1",
            "prop": "pageimages",
            "piprop": "thumbnail|name",
            "pithumbsize": str(THUMBNAIL_WIDTH),
            "pilicense": "free",  # uniquement les images sous licence libre
        })
        pages = {page.get("title"): page for page in query.get("pages", [])}
        for title in batch:
            page = pages.get(resolve(title, query))
            if page and page.get("pageimage") and page.get("thumbnail"):
                found[title] = (page["pageimage"], page["thumbnail"]["source"])
        print(f"    {len(found)} images trouvées...", end="\r")
    print()
    return found


def clean_html(text):
    """Enlève les balises HTML d'un crédit (« <a href=...>Nom</a> » -> « Nom »)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def fetch_credits(file_names):
    """{nom de fichier: (auteur, licence, adresse de la page du fichier)} depuis Wikimedia Commons."""
    credits = {}
    for batch in batches(sorted(set(file_names))):
        titles = {f"File:{name}": name for name in batch}
        query = call_api(COMMONS_API, {
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": "extmetadata|url",
            "iiextmetadatafilter": "Artist|LicenseShortName",
        })
        pages = {page.get("title"): page for page in query.get("pages", [])}
        for title, name in titles.items():
            page = pages.get(resolve(title, query))
            if not page or not page.get("imageinfo"):
                continue  # fichier absent de Commons : pas de crédit, on ne garde pas l'image
            info = page["imageinfo"][0]
            metadata = info.get("extmetadata", {})
            author = clean_html(metadata.get("Artist", {}).get("value"))
            license_name = clean_html(metadata.get("LicenseShortName", {}).get("value"))
            if license_name:
                credits[name] = (author or "Auteur inconnu", license_name, info.get("descriptionurl"))
    return credits


def main():
    global USER_AGENT
    parser = argparse.ArgumentParser(description="Récupère une photo libre pour chaque espèce.")
    parser.add_argument("--contact", help="adresse web ou e-mail de contact, envoyée à Wikimedia "
                                          "(par défaut : l'adresse du dépôt git du projet)")
    contact = parser.parse_args().contact or repository_url()
    if not contact:
        raise SystemExit(
            "[!] Wikimedia demande une adresse de contact. Relance avec, par exemple :\n"
            "    python prepa_images.py --contact https://github.com/ton-compte/ton-depot"
        )
    USER_AGENT = build_user_agent(contact)
    print(f"[*] Identification auprès de Wikimedia : {USER_AGENT}")

    engine = get_engine(Config.SQLALCHEMY_DATABASE_URI)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        plants = session.query(Plant).all()
        if not plants:
            print("[!] La base est vide : lance d'abord python prepa_db.py")
            return

        titles = sorted({title for title in (lookup_title(p.scientific_name) for p in plants) if title})
        print(f"[*] Recherche d'une photo pour {len(titles)} espèces sur Wikipédia...")
        page_images = fetch_page_images(titles)
        print(f"[*] Lecture des crédits de {len(page_images)} images sur Wikimedia Commons...")
        credits = fetch_credits([file_name for file_name, _ in page_images.values()])

        images = {}
        for title, (file_name, thumbnail) in page_images.items():
            if file_name in credits:
                author, license_name, page_url = credits[file_name]
                images[title] = {
                    "image_url": thumbnail,
                    "image_author": author,
                    "image_license": license_name,
                    "image_page_url": page_url,
                }

        with open(IMAGES_FILE, "w", encoding="utf-8") as json_file:
            json.dump(images, json_file, ensure_ascii=False, indent=1, sort_keys=True)

        # recopie dans la base
        illustrated = 0
        for plant in plants:
            image = images.get(lookup_title(plant.scientific_name)) or {}
            for column in IMAGE_COLUMNS:
                setattr(plant, column, image.get(column))
            illustrated += 1 if image else 0
        session.commit()
        print(f"[+] {len(images)} photos enregistrées dans data/images.json ; "
              f"{illustrated} plantes sur {len(plants)} ont une photo.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
