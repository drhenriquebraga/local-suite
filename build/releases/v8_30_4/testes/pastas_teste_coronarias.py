from pathlib import Path

raiz = Path(__file__).resolve().parents[1]
PROGRAMA = raiz / "programa" if (raiz / "programa/app").is_dir() else raiz
