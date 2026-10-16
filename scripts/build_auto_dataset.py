#!/usr/bin/env python3
"""Construye un dataset LIMPIADO AUTOMÁTICAMENTE a partir de los videos locales (paso 4B).

Reutiliza el motor del notebook 3.2 (se ejecutan sus celdas, sin widgets) y aplica reglas de limpieza
estrictas. NINGUNA muestra queda verificada por una persona: cada registro lleva
`human_verified: false` y el notebook sigue siendo el camino para la revisión humana.
No sube nada a R2.

Uso (Windows):  uv run scripts/build_auto_dataset.py [video_id ...]
"""
import contextlib, io, json, os, sys, time, hashlib
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import cv2, numpy as np, pandas as pd

REPO = Path(__file__).resolve().parent.parent
NB = REPO / 'to-verify' / '3.2-action-extraction-royaleapi.ipynb'
OUT = REPO / 'dataset'
DEFAULT_VIDEOS = ['4Tt7nuuy-Bg', 'KcLv14GDAns', 'QnFw3kiwOqo']   # videos ya disponibles localmente
WAIT_RATIO = .22        # ~18 % del total (waits / (plays + waits)) según la especificación
WAIT_SPACING = 6.
TEMPLATES_PLAY = ['Juega {card} {zone}.', 'Coloca {card} {zone}.', 'Despliega {card} {zone}.']
TEMPLATES_SPELL = ['Lanza {card} {zone}.', 'Juega {card} {zone}.']

# Cuidado de la máquina: prioridad baja y un hilo.
try:
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception:
    pass
cv2.setNumThreads(1)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')


def log(*args):
    print(*args, flush=True)


nb = json.load(open(NB, encoding='utf-8'))
cell = lambda i: ''.join(nb['cells'][i]['source'])
for i, marker in [(3, '_load_dotenv'), (5, 'def load_manifest'), (6, 'VIDEO_ID'), (8, 'def validate_video'),
                  (12, 'class ActionPipeline'), (15, 'PARAMS = Parameters'), (17, 'APPROVE_LAYOUT'),
                  (19, 'pipe.scan'), (22, 'def build_royale_catalog'), (23, 'install_royaleapi_bank')]:
    assert marker in cell(i), f'El notebook cambió: la celda {i} ya no contiene {marker!r}.'

os.chdir(NB.parent)
ns = {'__name__': '__main__', 'display': lambda *a, **k: None}


def run(*indices):
    for i in indices:
        buf = io.StringIO()
        src = ''.join(l for l in cell(i).splitlines(True) if not l.lstrip().startswith(('%', '!')))
        with contextlib.redirect_stdout(buf):
            exec(compile(src, f'<celda {i}>', 'exec'), ns)
        import matplotlib.pyplot as plt
        plt.close('all')


def lower_first(text):
    return text[:1].lower() + text[1:]


def target_text(card, zone, kind, seed):
    pool = TEMPLATES_SPELL if kind == 'spell' else TEMPLATES_PLAY
    pick = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(pool)
    return pool[pick].format(card=card, zone=lower_first(zone))


def save_frames(pipe, frames, sample_id, root):
    paths, transforms = [], []
    for back, image in zip([6, 4, 2, 0], frames):
        canonical, transform = ns['letterbox'](image, pipe.p.canonical_size)
        rel = f'samples/{sample_id}_t-{back}s.jpg'
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(str(path), cv2.cvtColor(canonical, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 95]):
            raise OSError(f'No se pudo escribir {path}')
        paths.append(rel)
        transforms.append(transform if isinstance(transform, (list, dict)) else str(transform))
    return paths, transforms


def clean_plays(pipe, video_id, match_index, root):
    """Aplica las reglas de limpieza a cada candidato de jugada. Devuelve (muestras, descartes)."""
    kept, audit = [], []
    plays = [e for e in pipe.events if e['event_type'] == 'play_candidate']
    for event in plays:
        row = {'video_id': video_id, 'candidate_id': event['candidate_id'], 'timestamp_sec': round(event['timestamp_sec'], 3),
               'drop_estimate': round(event['drop_estimate'], 2), 'signal': event['signal'], 'decision': 'descartado', 'reason': ''}
        try:
            if event.get('occluded'):
                row['reason'] = 'oclusion_chat'; raise StopIteration
            ident = pipe.identify(event)
            row['state'] = ident['state']; row['card'] = ident.get('name_es'); row['score'] = ident.get('score')
            if ident['state'] != 'propuesta':
                row['reason'] = f"carta_{ident['state']}"; raise StopIteration
            if ident.get('cost_consistent') is not True:
                row['reason'] = 'coste_inconsistente_con_caida_de_elixir'; raise StopIteration
            t = float(event['timestamp_sec'])
            loc = pipe.locate(t, ident.get('kind', 'unknown'))
            props = loc.get('proposals', [])
            if not props:
                row['reason'] = 'sin_localizacion'; raise StopIteration
            top = props[0]
            if top['zone'] is None:
                row['reason'] = 'zona_fuera_de_campo_propio'; raise StopIteration
            if len(props) > 1 and props[1]['zone'] != top['zone'] and top['score'] - props[1]['score'] < .05:
                row['reason'] = 'localizacion_ambigua'; raise StopIteration
            slot = int(event['slot_candidate'])
            payload = pipe._payload(event['candidate_id'], t, slot, ident['name_es'], int(ident['cost']), 'normal',
                                    ident['kind'], top['coord'])
            try:
                frames, times = pipe._input_frames(payload)
            except (ValueError, RuntimeError) as error:
                row['reason'] = 'frames_no_validos: ' + str(error)[:70]; raise StopIteration
            sid = f"{video_id}_m{match_index + 1}_play_{len(kept) + 1:03d}"
            paths, transforms = save_frames(pipe, frames, sid, root)
            kept.append({
                'sample_id': sid, 'video_id': video_id, 'match_index': match_index,
                'timestamp_sec': round(t, 3), 'frames': paths, 'frame_times': [round(x, 3) for x in times],
                'action_type': 'play', 'card_name': payload['card_name'], 'elixir_cost': payload['elixir_cost'],
                'hand_slot': payload['hand_slot'], 'placement_coord': [round(c, 4) for c in payload['placement_coord']],
                'placement_zone': payload['placement_zone'], 'kind': payload['kind'],
                'target_text': target_text(payload['card_name'], payload['placement_zone'], payload['kind'], sid),
                'human_verified': False, 'source': 'auto_cleaned',
                'auto_scores': {'card_score': round(float(ident['score']), 3), 'card_margin': round(float(ident['margin']), 3),
                                'drop_estimate': round(float(event['drop_estimate']), 2),
                                'location_score': round(float(top['score']), 3)},
                'canvas_transforms': transforms,
            })
            row['decision'] = 'aceptado_auto'; row['reason'] = ''
        except StopIteration:
            pass
        audit.append(row)
    return kept, audit


def make_waits(pipe, video_id, match_index, n_plays, root):
    """Esperas automáticas en tramos tranquilos. Menos fiables que las jugadas: requieren auditoría humana."""
    target = max(1, round(n_plays * WAIT_RATIO / (1 - WAIT_RATIO))) if n_plays else 0
    if not target:
        return []
    s = pipe.signals
    t_arr, e_arr = s.timestamp_sec.to_numpy(), s.elixir.to_numpy()
    start, end = pipe.video.start, pipe.video.end
    all_times = np.array([ev['timestamp_sec'] for ev in pipe.events])
    candidates = []
    for t in np.arange(start + 6.5, end - 1.5, .5):
        if np.any((all_times >= t - 3) & (all_times <= t + 1.5)):
            continue
        w = (t_arr >= t - 1.5) & (t_arr <= t + 1.5)
        if w.sum() < 5 or np.min(np.diff(e_arr[w])) < -.35:
            continue
        if pipe._chat_between(t - 6, t + .5):
            continue
        candidates.append(float(t))
    chosen, last = [], -1e9
    for t in candidates:
        if t - last >= WAIT_SPACING:
            chosen.append(t); last = t
    if len(chosen) > target:
        idx = np.linspace(0, len(chosen) - 1, target).round().astype(int)
        chosen = [chosen[i] for i in sorted(set(idx))]
    kept = []
    for n, t in enumerate(chosen, 1):
        try:
            frames, times = [], []
            for back in [6., 4., 2., 0.]:
                image, actual = pipe.video.frame(t - back)
                frames.append(image); times.append(float(actual))
            sid = f"{video_id}_m{match_index + 1}_wait_{n:03d}"
            paths, transforms = save_frames(pipe, frames, sid, root)
        except Exception as error:
            log('   espera omitida:', error); continue
        kept.append({
            'sample_id': sid, 'video_id': video_id, 'match_index': match_index, 'timestamp_sec': round(t, 3),
            'frames': paths, 'frame_times': [round(x, 3) for x in times], 'action_type': 'wait',
            'card_name': None, 'elixir_cost': None, 'hand_slot': None, 'placement_coord': None,
            'placement_zone': None, 'kind': None, 'target_text': 'esperar',
            'human_verified': False, 'source': 'auto_cleaned_wait', 'canvas_transforms': transforms,
        })
    return kept


def main(video_ids):
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    log('Cargando motor del notebook 3.2...')
    run(3, 5)
    ns['MAX_SCAN_SECONDS'] = None
    run(12, 13, 22)
    samples, audit, summary = [], [], []
    for video_id in video_ids:
        log(f'\n== {video_id} ==')
        ns['VIDEO_ID'] = video_id
        try:
            run(6, 8, 15, 16, 17, 19, 23)
        except Exception as error:
            log('   OMITIDO:', type(error).__name__, str(error)[:120])
            summary.append({'video_id': video_id, 'estado': f'omitido: {type(error).__name__}'})
            continue
        pipe = ns['pipe']
        match_index = int(pipe.match.get('match_index', 1)) - 1 if isinstance(pipe.match, dict) else 0
        plays, rows = clean_plays(pipe, video_id, match_index, OUT)
        waits = make_waits(pipe, video_id, match_index, len(plays), OUT)
        n_cand = len(rows)
        samples += plays + waits
        audit += rows
        summary.append({'video_id': video_id, 'estado': 'ok', 'candidatos': n_cand, 'jugadas_aceptadas': len(plays),
                        'esperas': len(waits), 'chat_muestras': int(pipe.signals.chat.sum()),
                        'muestras_destello_corregidas': int((pipe.signals.elixir != pipe.signals.elixir_raw).sum()),
                        'muestras_escaneadas': len(pipe.signals)})
        log(f"   candidatos={n_cand} aceptadas={len(plays)} esperas={len(waits)}")
    with (OUT / 'annotations.jsonl').open('w', encoding='utf-8') as f:
        for rec in samples:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    audit_df = pd.DataFrame(audit)
    audit_df.to_csv(OUT / 'limpieza_candidatos.csv', index=False)
    sum_df = pd.DataFrame(summary)
    sum_df.to_csv(OUT / 'limpieza_resumen.csv', index=False)
    write_report(samples, audit_df, sum_df)
    log(f'\nDataset en {OUT} | {len(samples)} muestras | {time.time() - t0:.0f}s')


def write_report(samples, audit_df, sum_df):
    plays = [s for s in samples if s['action_type'] == 'play']
    waits = [s for s in samples if s['action_type'] == 'wait']
    L = ['# Dataset limpiado automáticamente (sin verificación humana)', '',
         f'- Muestras: **{len(samples)}** ({len(plays)} jugadas + {len(waits)} esperas)',
         f'- Proporción de esperas: {len(waits) / max(1, len(samples)):.0%} (objetivo 15–20 %)',
         '- Cada registro tiene `human_verified: false`. Para uso en entrenamiento debe pasar por la revisión humana del notebook 3.2.',
         '', '## Resumen por video', '']
    if len(sum_df):
        L += ['| ' + ' | '.join(sum_df.columns) + ' |', '|' + '---|' * len(sum_df.columns)]
        L += ['| ' + ' | '.join(str(v) for v in r) + ' |' for r in sum_df.fillna('').values.tolist()]
    L += ['', '## Motivos de descarte de candidatos de jugada', '']
    if len(audit_df):
        disc = audit_df[audit_df.decision == 'descartado'].reason.str.split(':').str[0].value_counts()
        L += ['| motivo | candidatos |', '|---|---|'] + [f'| {k} | {v} |' for k, v in disc.items()]
        L += ['', f'Aceptados automáticamente: {int((audit_df.decision == "aceptado_auto").sum())} de {len(audit_df)}']
    L += ['', '## Reglas de limpieza aplicadas', '',
          '1. Sin oclusión por chat/emote en la ventana de la jugada ni en los 4 frames de entrada.',
          '2. Carta identificada con confianza suficiente (estado `propuesta`) y presente en el catálogo permitido (sin evoluciones, héroes, campeones ni cartas de evento).',
          '3. Coste de la carta coherente con la caída de elixir (±1), con el elixir ya corregido de destellos.',
          '4. Posición localizada dentro del campo propio y sin ambigüedad entre dos zonas.',
          '5. Seis segundos de historia disponibles; frame actual 0.5–0.8 s antes del despliegue (sin filtración).',
          '6. Esperas: tramos de ≥3 s sin eventos ni caídas de elixir, separadas ≥6 s, sin chat.',
          '', '## Limitaciones conocidas', '',
          '- Las esperas no están auditadas: una jugada omitida por el detector podría haberse etiquetado como espera.',
          '- La zona sale de una propuesta automática (cambio de imagen), que puede confundirse con movimiento de tropas.',
          '- Jugadas con hechizos al campo rival, evoluciones o cartas excluidas se descartan: el dataset no las cubre.',
          '- Detector y catálogo no se midieron contra una anotación manual completa.']
    (OUT / 'README.md').write_text('\n'.join(L), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1:] or DEFAULT_VIDEOS)
