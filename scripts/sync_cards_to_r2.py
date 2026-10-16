#!/usr/bin/env python3
"""Descarga el catálogo completo de cartas de Clash Royale (normales, evoluciones y nuevas)
desde RoyaleAPI y lo sincroniza hacia Cloudflare R2:
  - Imágenes PNG (150x180 RGBA): assets/cards/<key>.png
  - Manifiesto maestro JSON:     metadata/cards_catalog.json

Ejecutar con: uv run scripts/sync_cards_to_r2.py
"""
import os
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests
import boto3
from botocore.config import Config

# Cargar automáticamente .env si existe en la raíz
env_file = Path('.env')
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

R2_ENDPOINT = os.getenv('R2_ENDPOINT')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY')
R2_SECRET_KEY = os.getenv('R2_SECRET_KEY')
R2_BUCKET = os.getenv('R2_BUCKET', 'cr-videos')
CDN_URL = os.getenv('CDN_URL', 'https://cdn-cr.eddux.dev').rstrip('/')

if not all([R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY]):
    print("❌ Error: Faltan credenciales de R2 en .env (R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY).")
    sys.exit(1)

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4', max_pool_connections=32)
)

CARDS_I18N_URL = "https://royaleapi.github.io/cr-api-data/json/cards_i18n.json"
GITHUB_TREE_URL = "https://api.github.com/repos/RoyaleAPI/cr-api-assets/git/trees/master?recursive=1"
RAW_ASSET_BASE = "https://raw.githubusercontent.com/RoyaleAPI/cr-api-assets/master/cards-150"

# Cartas de eventos temporales presentes en cards_i18n.json que NO son cartas de mazo estándar
EVENT_KEYS_IN_I18N = {
    "super-witch", "super-lava-hound", "super-magic-archer", "santa-hog-rider",
    "super-ice-golem", "super-archers", "terry", "super-mini-pekka",
    "raging-prince", "party-hut", "party-rocket"
}

# Metadatos de las cartas lanzadas entre 2023 y 2026 + tropas de torre y eventos en cr-api-assets
EXTRA_CARDS_METADATA = {
    # Nuevas cartas jugables estándar (2023-2026)
    "little-prince":     {"name_en": "Little Prince",     "name_es": "Principito",            "elixir": 3, "type": "Troop", "rarity": "Champion",  "standard": True},
    "goblin-curse":      {"name_en": "Goblin Curse",      "name_es": "Maldición duende",      "elixir": 2, "type": "Spell", "rarity": "Epic",      "standard": True},
    "goblin-demolisher": {"name_en": "Goblin Demolisher", "name_es": "Duende demoledor",      "elixir": 4, "type": "Troop", "rarity": "Rare",      "standard": True},
    "goblin-machine":    {"name_en": "Goblin Machine",    "name_es": "Máquina duende",        "elixir": 5, "type": "Troop", "rarity": "Legendary", "standard": True},
    "suspicious-bush":   {"name_en": "Suspicious Bush",   "name_es": "Arbusto sospechoso",    "elixir": 2, "type": "Troop", "rarity": "Rare",      "standard": True},
    "void":              {"name_en": "Void",              "name_es": "Vacío",                 "elixir": 3, "type": "Spell", "rarity": "Epic",      "standard": True},
    "goblinstein":       {"name_en": "Goblinstein",       "name_es": "Goblinstein",           "elixir": 5, "type": "Troop", "rarity": "Champion",  "standard": True},
    "berserker":         {"name_en": "Berserker",         "name_es": "Berserker",             "elixir": 2, "type": "Troop", "rarity": "Common",    "standard": True},
    "boss-bandit":       {"name_en": "Boss Bandit",       "name_es": "Bandida líder",         "elixir": 6, "type": "Troop", "rarity": "Champion",  "standard": True},
    "rune-giant":        {"name_en": "Rune Giant",        "name_es": "Gigante rúnica",        "elixir": 4, "type": "Troop", "rarity": "Epic",      "standard": True},
    "spirit-empress":    {"name_en": "Spirit Empress",    "name_es": "Emperatriz espiritual", "elixir": 6, "type": "Troop", "rarity": "Champion",  "standard": True},
    "vines":             {"name_en": "Vines",             "name_es": "Enredaderas",           "elixir": 3, "type": "Spell", "rarity": "Epic",      "standard": True},

    # Tropas de torre (no aparecen en los 4 slots de la mano)
    "tower-princess":    {"name_en": "Tower Princess",    "name_es": "Princesa de torre",     "elixir": 0, "type": "Tower", "rarity": "Common",    "standard": False},
    "cannoneer":         {"name_en": "Cannoneer",         "name_es": "Cañonero",              "elixir": 0, "type": "Tower", "rarity": "Epic",      "standard": False},
    "dagger-duchess":    {"name_en": "Dagger Duchess",    "name_es": "Duquesa de dagas",      "elixir": 0, "type": "Tower", "rarity": "Legendary", "standard": False},
    "royal-chef":        {"name_en": "Royal Chef",        "name_es": "Chef real",             "elixir": 0, "type": "Tower", "rarity": "Legendary", "standard": False},
    "baby-goblins":      {"name_en": "Baby Goblins",      "name_es": "Bebés duendes",         "elixir": 0, "type": "Tower", "rarity": "Common",    "standard": False},

    # Cartas retiradas o de eventos especiales
    "heal":              {"name_en": "Heal",              "name_es": "Curación",              "elixir": 1, "type": "Spell", "rarity": "Rare",      "standard": False},
    "fire-spirits":      {"name_en": "Fire Spirits",      "name_es": "Espíritus de fuego",    "elixir": 2, "type": "Troop", "rarity": "Common",    "standard": False},
    "barbarian-launcher":{"name_en": "Barbarian Launcher","name_es": "Lanzabárbaros",         "elixir": 5, "type": "Building", "rarity": "Rare",   "standard": False},
    "super-hog-rider":   {"name_en": "Super Hog Rider",   "name_es": "Supermontapuercos",     "elixir": 5, "type": "Troop", "rarity": "Legendary", "standard": False},
    "super-knight":      {"name_en": "Super Knight",      "name_es": "Supercaballero",        "elixir": 4, "type": "Troop", "rarity": "Legendary", "standard": False},
    "warmth":            {"name_en": "Warmth",            "name_es": "Calor",                 "elixir": 2, "type": "Spell", "rarity": "Epic",      "standard": False},
    "wizard-trio":       {"name_en": "Wizard Trio",       "name_es": "Trío de magos",         "elixir": 7, "type": "Troop", "rarity": "Legendary", "standard": False},
    "rocket-silo":       {"name_en": "Rocket Silo",       "name_es": "Silo de cohetes",       "elixir": 5, "type": "Building", "rarity": "Epic",   "standard": False},
}


def resolve_base_and_variant(card_key: str) -> tuple[str, str]:
    if card_key.endswith("-hero-ev1"):
        return card_key[:-9], "hero_evolution"
    if card_key.endswith("-ev1"):
        return card_key[:-4], "evolution"
    if card_key.endswith("-hero"):
        return card_key[:-5], "hero"
    return card_key, "base"


def get_existing_r2_cards() -> set[str]:
    existing = set()
    continuation = None
    while True:
        kwargs = {"Bucket": R2_BUCKET, "Prefix": "assets/cards/"}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            existing.add(Path(obj["Key"]).stem)
        if not resp.get("IsTruncated"):
            break
        continuation = resp.get("NextContinuationToken")
    return existing


def build_catalog() -> list[dict]:
    print("Consultando metadatos i18n y árbol de assets en RoyaleAPI...")
    i18n_data = requests.get(CARDS_I18N_URL, timeout=15).json()
    i18n_by_key = {c["key"]: c for c in i18n_data}

    tree_data = requests.get(GITHUB_TREE_URL, timeout=15).json()
    asset_keys = sorted([
        p["path"].split("/")[1][:-4]
        for p in tree_data.get("tree", [])
        if p["path"].startswith("cards-150/")
        and p["path"].endswith(".png")
        and not p["path"].split("/")[1].startswith("_")
        and "unknown" not in p["path"]
    ])

    catalog = []
    for key in asset_keys:
        base_key, variant = resolve_base_and_variant(key)
        if base_key in i18n_by_key:
            c = i18n_by_key[base_key]
            name_en = c["name"]
            name_es = c.get("_lang", {}).get("name", {}).get("es", name_en)
            elixir = c.get("elixir", 0)
            c_type = c.get("type", "Troop")
            rarity = c.get("rarity", "Common")
            is_std_base = base_key not in EVENT_KEYS_IN_I18N
        elif base_key in EXTRA_CARDS_METADATA:
            m = EXTRA_CARDS_METADATA[base_key]
            name_en = m["name_en"]
            name_es = m["name_es"]
            elixir = m["elixir"]
            c_type = m["type"]
            rarity = m["rarity"]
            is_std_base = m["standard"]
        else:
            name_en = base_key.replace("-", " ").title()
            name_es = name_en
            elixir = 0
            c_type = "Unknown"
            rarity = "Common"
            is_std_base = False

        is_standard_deck_card = is_std_base and variant in ("base", "evolution")
        r2_key = f"assets/cards/{key}.png"

        catalog.append({
            "key": key,
            "base_key": base_key,
            "name_en": name_en,
            "name_es": name_es,
            "elixir": elixir,
            "type": c_type,
            "rarity": rarity,
            "variant": variant,
            "is_evolution": variant in ("evolution", "hero_evolution"),
            "is_standard_deck_card": is_standard_deck_card,
            "r2_key": r2_key,
            "cdn_url": f"{CDN_URL}/{r2_key}",
            "source_url": f"{RAW_ASSET_BASE}/{key}.png",
        })

    return catalog


def sync_card_image(entry: dict) -> tuple[str, bool, str]:
    key = entry["key"]
    try:
        r = requests.get(entry["source_url"], timeout=15)
        r.raise_for_status()
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=entry["r2_key"],
            Body=r.content,
            ContentType="image/png",
        )
        return key, True, ""
    except Exception as e:
        return key, False, str(e)


def main():
    t0 = time.time()
    catalog = build_catalog()
    std_base = [c for c in catalog if c["is_standard_deck_card"] and c["variant"] == "base"]
    std_evo = [c for c in catalog if c["is_standard_deck_card"] and c["variant"] == "evolution"]
    extra = [c for c in catalog if not c["is_standard_deck_card"]]

    print(f"Total assets de cartas encontrados: {len(catalog)}")
    print(f"  - Cartas de mazo estándar (base):        {len(std_base)}")
    print(f"  - Evoluciones de mazo estándar (-ev1):   {len(std_evo)}")
    print(f"  - Especiales / Héroes / Torres / Evento: {len(extra)}")

    existing = get_existing_r2_cards()
    pending = [c for c in catalog if c["key"] not in existing]
    print(f"Ya presentes en R2: {len(existing)} | Pendientes por subir: {len(pending)}")

    if pending:
        print(f"Subiendo {len(pending)} imágenes PNG (150x180) a R2 en paralelo...")
        ok_count = 0
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(sync_card_image, item) for item in pending]
            for fut in as_completed(futures):
                k, ok, err = fut.result()
                if ok:
                    ok_count += 1
                else:
                    print(f"  ❌ Falló {k}: {err}")
        print(f"✔ Imágenes subidas: {ok_count}/{len(pending)}")

    # Guardar manifiesto maestro en R2 y copia local de referencia
    manifest = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_assets": len(catalog),
        "total_standard_base": len(std_base),
        "total_standard_evolutions": len(std_evo),
        "cards": {c["key"]: c for c in catalog},
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    s3.put_object(
        Bucket=R2_BUCKET,
        Key="metadata/cards_catalog.json",
        Body=manifest_bytes,
        ContentType="application/json",
    )
    print(f"✔ Manifiesto subido a R2: s3://{R2_BUCKET}/metadata/cards_catalog.json")
    print(f"✔ Proceso completado en {time.time() - t0:.1f}s.")


if __name__ == "__main__":
    main()

