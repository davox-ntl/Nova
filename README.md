# NOVA — traduction des langues ivoiriennes

API FastAPI + interface web, avec traduction DeepSeek (index JSON par langue) et voix Edge TTS.

## Développement local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis renseigner DEEPSEEK_API_KEY
python run.py           # http://localhost:8000
```

Vérification : `.venv/bin/ruff check app tests` puis `.venv/bin/python -m unittest discover -s tests -q`.

## Déploiement sur Vercel

Le projet est détecté automatiquement comme application **FastAPI** (Python 3.12, fichier `.python-version`). L'entrypoint est déclaré dans `pyproject.toml` (`app.main:app`) et `vercel.json` fixe une durée maximale de 120 s pour les appels DeepSeek + Edge TTS.

1. Poussez le dossier `nova/` dans Git. **Les fichiers JSON des index sont nécessaires** :
   `data/index_de_langue/{dyu,any,bci,bet}/{vocabulaire,phonetique,prononciation}.json`.
   Les PDF sources ne servent qu'à régénérer les index ; ils sont exclus du bundle de la fonction
   Vercel via `excludeFiles` dans `vercel.json`.
2. Dans Vercel, importez le dépôt. Si le dépôt contient plusieurs dossiers, réglez **Root Directory** sur `nova`.
3. Laissez les champs Build/Install/Output vides (détection FastAPI) et déployez.
4. Ajoutez les variables d'environnement dans **Project Settings → Environment Variables** :

   | Variable | Exemple | Obligatoire |
   |---|---|---|
   | `AI_PROVIDER` | `deepseek` | non (`deepseek` par défaut) |
   | `DEEPSEEK_API_KEY` | `sk-...` | **oui** (ou clé NVIDIA/Gemini) |
   | `DEEPSEEK_MODEL` | `deepseek-flash` | non |
   | `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | non |

   Ne renseignez pas `NOVA_DB_PATH` : sur Vercel la base est automatiquement placée dans `/tmp/nova.db` (seul emplacement accessible en écriture).

5. Vérifiez après déploiement :
   - `GET /api/health` → `"tts_engine": "edge-tts"` et les 4 langues dans `reference_indexes` ;
   - `POST /api/translations` avec `{"source_language":"fr","target_language":"dyu","text":"Bonjour"}` ;
   - `GET /api/tts?text=Bonjour` → `audio/mpeg` avec `x-tts-engine: edge-tts`.

Alternative CLI, depuis `nova/` :

```bash
npx vercel@latest          # lien le projet une fois
npx vercel env add DEEPSEEK_API_KEY production
npx vercel deploy --prod
```

### Limite à connaître

Sur Vercel, le système de fichiers est en lecture seule et `/tmp` est éphémère : l'historique des traductions et les retours (`feedback`) ne survivent pas à un redémarrage du fonction et ne sont pas partagés entre instances. Pour une persistance durable, remplacez SQLite dans `app/database.py` par une base gérée (Vercel Postgres/Neon) via une variable de connexion.
