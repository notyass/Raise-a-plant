"""Récupère une photo libre pour chaque espèce : python prepa_images.py

Pour chaque nom latin de la base, le script demande à Wikipédia la photo
principale de la page de l'espèce, puis à Wikimedia Commons son auteur et sa
licence (API MediaWiki, gratuite et sans clé). Seules les images sous
licence libre sont gardées, avec leur crédit.

Le résultat est écrit dans data/images.json, puis recopié dans la base.
prepa_db.py relit ce fichier : pas besoin de relancer ce script après une
réinitialisation de la base. À lancer une fois, après prepa_db.py
(une à deux minutes, connexion internet nécessaire).
"""
import json
import re
import time
import urllib.parse
import urllib.request

from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.models import Plant, get_engine
from app.services.images import lookup_title
from prepa_db import IMAGE_COLUMNS, IMAGES_FILE

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia demande un User-Agent qui décrit le programme.
USER_AGENT = "RaiseAPlant/0.4 (projet etudiant BUT Informatique, IUT de Villetaneuse)"
BATCH_SIZE = 50  # nombre maximal de titres par requête
THUMBNAIL_WIDTH = 480
PAUSE_SECONDS = 0.5  # pause entre deux requêtes, par politesse pour le serveur


def call_api(url, params):
    """Appelle une API MediaWiki et renvoie la partie « query » de la réponse JSON."""
    params = dict(params, action="query", format="json", formatversion="2")
    request = urllib.request.Request(
        url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    time.sleep(PAUSE_SECONDS)
    return data.get("query", {})


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
