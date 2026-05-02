# app_webp

App desktop Python (PySide6) per convertire immagini JPG/PNG in WebP usando il comando di sistema `cwebp`.

## Requisiti esterni (non Python)

Questa app dipende da un tool di sistema esterno:

- `cwebp`: eseguibile CLI usato per convertire realmente le immagini.

Su macOS, `cwebp` si installa tramite Homebrew con il pacchetto `webp`.

### 1) Installa Homebrew (se non presente)

```bash
brew --version
```

Se il comando non esiste, installa Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2) Installa il pacchetto `webp` (include `cwebp`)

```bash
brew install webp
```

Verifica finale:

```bash
cwebp -version
```

## Requisiti Python

- Python 3.10+
- `uv` (consigliato per ambiente virtuale e installazione dipendenze)

Verifica:

```bash
python3 --version
uv --version
```

Se `uv` manca:

```bash
brew install uv
```

## Installazione progetto con uv

### 1) Crea ambiente virtuale

```bash
uv venv .venv
```

### 2) Installa dipendenze Python

```bash
uv pip install -r requirements.txt
```

## Avvio app (con uv)

```bash
uv run python app_webp.py
```

## Troubleshooting rapido

- Errore `cwebp non trovato`:
  - `cwebp` non e nel `PATH` oppure non e installato.
  - riesegui `brew install webp` e poi `cwebp -version`.
- Errore su `uv`:
  - verifica installazione con `uv --version`.
  - in caso assente: `brew install uv`.

## Funzioni principali (V1.1)

- Drag and drop multiplo di file JPG/JPEG/PNG
- Pulsante per selezione file input
- Slider qualita 0-100 (default 80)
- Campi opzionali prefisso/suffisso
- Cartella output selezionabile (default: cartella file sorgente)
- Selezione cartella output: il dialog parte dalla cartella del primo file in coda (se presente)
- Naming SEO: `prefisso-nome-pulito-suffisso.webp`
- Popup di conferma in caso di file output gia esistente:
  - Yes / No / Yes to All / No to All / Cancel
- Conversione in worker thread con progress bar
- Console log in basso (sfondo nero, testo verde)
- Salvataggio impostazioni (qualita, prefisso, suffisso, output)

## Note naming SEO

- Il nome originale viene convertito in kebab-case:
  - lowercase
  - simboli e spazi convertiti in trattini
  - trattini multipli collassati in uno
- `prefisso` e `suffisso` vengono sanitizzati allo stesso modo.

Esempio:
- Input: `My Summer Photo 2026!!.JPG`
- Prefisso: `Promo`
- Suffisso: `Hero`
- Output: `promo-my-summer-photo-2026-hero.webp`
