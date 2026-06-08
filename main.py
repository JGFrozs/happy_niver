import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from routers import auth, views  # Importando nossos novos roteadores

# Garante o carregamento do ambiente antes de qualquer coisa
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

app = FastAPI(title="Happy Niver - Sistema Modular")

# Montagem de arquivos estáticos apontando para a sua pasta 'src'
app.mount("/static", StaticFiles(directory="src"), name="static")

# Incluindo as rotas de cada módulo no aplicativo principal
app.include_router(views.router)  # Home, Index, Dashboard, Countdown
app.include_router(auth.router)   # Cadastro e Sucesso

# Bloco de log para inicialização segura
print("\n" + "="*50)
print("[SISTEMA] Estrutura modular carregada com sucesso!")
print(f"[SISTEMA] Monitorando banco através da planilha Google.")
print("="*50 + "\n")