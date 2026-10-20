import io
import os
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

_FN = urllib.parse.quote("Brazilian Unified Rainfall Dataset (1885 - 2025).zip", safe="")
URL = f"https://zenodo.org/api/records/18883358/files/{_FN}/content"

OUT_DIR = Path(__file__).resolve().parents[1] / "raw" / "uniplu_br"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UFS = ["MG", "SP", "RJ", "ES"]
YEARS = range(2008, 2024)

class HTTPRangeFile(io.RawIOBase):
    """Arquivo seekable sobre HTTP Range."""

    def __init__(self, url: str):
        self.url = url
        req = urllib.request.Request(url, method="HEAD")
        r = urllib.request.urlopen(req, timeout=60)
        self.size = int(r.headers["Content-Length"])
        self.pos = 0
        self.nbytes = 0

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (
            self.pos + offset if whence == 1 else self.size + offset)
        return self.pos

    def tell(self):
        return self.pos

    def readable(self):
        return True

    def seekable(self):
        return True

    def read(self, n=-1):
        if n == -1 or self.pos + n > self.size:
            n = self.size - self.pos
        if n <= 0:
            return b""
        end = self.pos + n - 1
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        r = urllib.request.urlopen(req, timeout=300)
        if getattr(r, "status", r.getcode()) != 206:
            raise RuntimeError(f"Servidor ignorou Range (status {r.getcode()})")
        data = r.read()
        self.pos += len(data)
        self.nbytes += len(data)
        return data

def main():
    print("=" * 70)
    print("DOWNLOAD SELETIVO DE DADOS UNIPLU-BR PARA O SUDESTE (MG, SP, RJ, ES)")
    print("Período: 2008 a 2023 | Repositório Zenodo (rec 18883358)")
    print("=" * 70)
    
    t0 = time.time()
    print("Conectando ao Zenodo e indexando o diretório central...")
    f = HTTPRangeFile(URL)
    zf = zipfile.ZipFile(f)
    namelist = set(zf.namelist())
    
    targets = []
    for uf in UFS:
        for y in YEARS:
            m = f"{uf}_{y}.zip"
            if m in namelist:
                targets.append((m, zf.getinfo(m).file_size))
            else:
                print(f"[ALERTA] Membro não encontrado: {m}")
                
    total_mb = sum(size for _, size in targets) / (1024 * 1024)
    print(f"Total de arquivos a baixar: {len(targets)} ({total_mb:.2f} MB)")
    print(f"Diretório de destino: {OUT_DIR}\n")
    
    baixados = 0
    pulados = 0
    bytes_baixados = 0
    
    for idx, (member, size_bytes) in enumerate(targets, start=1):
        dest_file = OUT_DIR / member
        size_mb = size_bytes / (1024 * 1024)
        
        # Pula se o arquivo já existir com tamanho consistente (> 0)
        if dest_file.exists() and dest_file.stat().st_size > 0:
            print(f"[{idx:02d}/{len(targets)}] {member} ({size_mb:.2f} MB) -> Já existe no disco [PULADO]")
            pulados += 1
            continue
            
        print(f"[{idx:02d}/{len(targets)}] Baixando {member} ({size_mb:.2f} MB)...", end=" ", flush=True)
        try:
            raw_bytes = zf.read(member)
            dest_file.write_bytes(raw_bytes)
            baixados += 1
            bytes_baixados += len(raw_bytes)
            print("[OK]")
        except Exception as e:
            print(f"[ERRO: {e}]")
            # Tenta reconectar se a conexão cair
            f = HTTPRangeFile(URL)
            zf = zipfile.ZipFile(f)
            
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print(f"DOWNLOAD CONCLUÍDO EM {elapsed:.1f}s!")
    print(f"Baixados: {baixados} | Já existentes: {pulados} | Total: {len(targets)}")
    print(f"Volume baixado nesta execução: {bytes_baixados / (1024*1024):.2f} MB")
    print("=" * 70)

if __name__ == "__main__":
    main()
