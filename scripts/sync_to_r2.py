#!/usr/bin/env python3
"""Sincroniza videos aprobados de cr-dataset.eddux.dev hacia Cloudflare R2.
Ejecutar con: uv run scripts/sync_to_r2.py
"""
import os, sys, time, tempfile
from pathlib import Path
import requests
import boto3
from botocore.config import Config
import yt_dlp

# Cargar automáticamente .env si existe en la raíz
env_file = Path('.env')
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Configuración
R2_ENDPOINT = os.getenv('R2_ENDPOINT')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY')
R2_SECRET_KEY = os.getenv('R2_SECRET_KEY')
R2_BUCKET = os.getenv('R2_BUCKET', 'cr-videos')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')
ANNOTATOR_URL = os.getenv('ANNOTATOR_URL', 'https://cr-dataset.eddux.dev').rstrip('/')
CDN_URL = os.getenv('CDN_URL', 'https://cdn-cr.eddux.dev').rstrip('/')

if not ADMIN_TOKEN and Path('.token').exists():
    ADMIN_TOKEN = Path('.token').read_text().strip()

if not all([R2_ENDPOINT, R2_ACCESS_KEY, R2_SECRET_KEY, ADMIN_TOKEN]):
    print("❌ Error: Faltan credenciales de R2 o ADMIN_TOKEN.")
    print("Crea un archivo .env en la raíz con:")
    print("  R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com")
    print("  R2_ACCESS_KEY=...")
    print("  R2_SECRET_KEY=...")
    print("  R2_BUCKET=cr-videos")
    print("  ADMIN_TOKEN=...")
    sys.exit(1)

# Cliente S3 para Cloudflare R2
s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

def get_r2_existing_videos():
    try:
        resp = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix='videos/')
        items = resp.get('Contents', [])
        return set(Path(it['Key']).stem for it in items)
    except Exception as e:
        print(f"Aviso al listar bucket R2: {e}")
        return set()

def fmt_duration(seconds):
    if not seconds:
        return "duración desconocida"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s:02d}s"

def download_and_upload(video_id: str, duration_s: int = None):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_target = Path(tmpdir) / f"{video_id}.mp4"
        ydl_opts = {
            # Preferir AVC/h264 sobre AV1 para compatibilidad universal con OpenCV/FFmpeg
            'format': 'bestvideo[ext=mp4][vcodec^=avc1][height<=1920]/bestvideo[height<=1920]/best',
            'outtmpl': str(tmp_target),
            'concurrent_fragment_downloads': 8,
            'quiet': True
        }
        print(f"-> Descargando {video_id} ({fmt_duration(duration_s)}) con conexión local...")
        t0 = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtu.be/{video_id}"])

        file_size_mb = tmp_target.stat().st_size / (1024 * 1024)
        print(f"   Descargado ({file_size_mb:.1f} MB en {time.time() - t0:.1f}s). Subiendo a R2...")

        t1 = time.time()
        s3.upload_file(str(tmp_target), R2_BUCKET, f"videos/{video_id}.mp4")
        print(f"✔ Subido a R2 en {time.time() - t1:.1f}s.")
        print(f"   Disponible en: {CDN_URL}/videos/{video_id}.mp4")

def main():
    print(f"Consultando videos aprobados en {ANNOTATOR_URL}...")
    r = requests.get(f"{ANNOTATOR_URL}/api/export", headers={'x-admin-token': ADMIN_TOKEN})
    r.raise_for_status()
    videos = r.json()
    print(f"Total aprobados en Annotator: {len(videos)}")

    existing_r2 = get_r2_existing_videos()
    print(f"Ya presentes en R2: {len(existing_r2)}")

    pending = [v for v in videos if v['id'] not in existing_r2]
    print(f"Pendientes por subir: {len(pending)}")

    for v in pending:
        vid = v['id']
        title = v.get('title', vid)
        print(f"\nProcesando [{vid}] {title}")
        try:
            download_and_upload(vid, v.get("duration_s"))
        except Exception as e:
            print(f"❌ Error con {vid}: {e}")

    print("\n✔ Sincronización finalizada.")

if __name__ == '__main__':
    main()
