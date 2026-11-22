"""Compatibilidade da ferramenta de preparo com a implementação do plugin."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from radai_rocards_dependencies import LOCK, RECIBO, preparar_runtime as preparar, verificar


if __name__ == "__main__":
    preparar(sys.executable, Path(sys.argv[1]))
