"""Prepara e verifica o runtime TensorFlow da DA sem alterar a instalação da suíte."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


APP = Path(__file__).resolve().parent
LOCK = APP / "data" / "requirements-rocards.txt"
RECIBO = ".rocards-requisitos.sha256"
PROVA = """
from importlib import metadata
from pathlib import Path
import sys
alvo = Path(sys.argv[1]).resolve()
sys.path.insert(0, sys.argv[3])
from radai_rocards_worker import carregar_runtime
tf = carregar_runtime(alvo)
reais = {d.metadata['Name'].lower().replace('_', '-'): d.version
         for d in metadata.distributions(path=[str(alvo)])}
for linha in Path(sys.argv[2]).read_text(encoding='utf-8').splitlines():
    if linha.strip() and not linha.startswith('#'):
        nome, versao = linha.split('==')
        if reais.get(nome) != versao:
            raise RuntimeError('Runtime ROCardS incompleto: ' + linha)
import SimpleITK
from scipy import ndimage, signal
print('ROCardS runtime OK (' + ('GPU' if tf.config.list_physical_devices('GPU') else 'CPU') + ')')
"""


def verificar(python, runtime):
    assinatura = hashlib.sha256(LOCK.read_bytes()).hexdigest()
    if (runtime / RECIBO).read_text(encoding="ascii").strip() != assinatura:
        raise ValueError("O recibo do runtime ROCardS não corresponde ao instalador.")
    app = APP
    prova = subprocess.run([str(python), "-B", "-c", PROVA, str(runtime), str(LOCK), str(app)],
                           timeout=600, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    cpu_validada = prova.returncode == 0 and "ROCardS runtime OK (CPU)" in prova.stdout
    for linha in prova.stdout.splitlines():
        if cpu_validada and ("Could not load dynamic library 'cudart64_110.dll'" in linha
                             or "Could not load dynamic library 'nvcuda.dll'" in linha
                             or "Ignore above cudart dlerror" in linha
                             or "stream_executor/cuda/cuda_driver.cc" in linha
                             or "stream_executor/cuda/cuda_diagnostics.cc" in linha):
            continue
        print(linha, flush=True)
    prova.check_returncode()


def preparar_runtime(python, modelo):
    modelo = Path(modelo)
    modelo.mkdir(parents=True, exist_ok=True)
    runtime = modelo / "runtime"
    try:
        verificar(python, runtime)
        return
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    with tempfile.TemporaryDirectory(dir=modelo, prefix=".preparo-") as temp:
        alvo = Path(temp) / "runtime"
        subprocess.run([str(python), "-m", "pip", "--isolated", "install", "--index-url", "https://pypi.org/simple", "--no-input",
                        "--disable-pip-version-check", "--no-compile", "--only-binary=:all:",
                        "--ignore-installed", "--no-deps", "--target", str(alvo),
                        "-r", str(LOCK)], check=True)
        (alvo / RECIBO).write_text(hashlib.sha256(LOCK.read_bytes()).hexdigest(), encoding="ascii")
        verificar(python, alvo)
        anterior = Path(temp) / "anterior"
        if runtime.exists():
            runtime.rename(anterior)
        try:
            alvo.rename(runtime)
        except OSError:
            if anterior.exists():
                anterior.rename(runtime)
            raise


def preparar():
    """Obtém o plugin para esta estação após a escolha explícita do operador."""
    import radai_models
    from radai_archive import _travar_indice
    pasta = radai_models.pasta_do_modelo("rocards_lad", criar=True)
    with _travar_indice(pasta / "preparo"):
        from radai_rocards_offline import recuperar
        recuperar(pasta)
        radai_models.baixar("rocards_lad", pesquisa_rocards=True)
        preparar_runtime(sys.executable, pasta)


if __name__ == "__main__":
    sys.path.insert(0, str(APP))
    preparar()
