from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from src.niver.lista import aniversariantes
from datetime import datetime

app = FastAPI()

# Configuração de templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="src"), name="static")

# Chave Mestra para testes: Use no formato "Gabriel_Dev_2026:Nome"
CHAVE_MESTRA = "Gabriel_Dev_2026"

def obter_proximo_aniversario():
    """Calcula a data do próximo aniversário geral para o timer da home"""
    hoje = datetime.now()
    datas_futuras = []
    
    for nome, data_str in aniversariantes.items():
        partes = data_str.split("-")
        mes, dia = int(partes[1]), int(partes[2])
        
        data_aniv = datetime(hoje.year, mes, dia)
        
        # Se já passou este ano, aponta para o ano que vem
        if data_aniv < hoje:
            data_aniv = data_aniv.replace(year=hoje.year + 1)
            
        datas_futuras.append(data_aniv)

    proxima_data = min(datas_futuras)
    return proxima_data.strftime("%Y-%m-%dT00:00:00")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    proximo_niver = obter_proximo_aniversario()
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"proximo_niver": proximo_niver}
    )

@app.post("/verificar", response_class=HTMLResponse)
async def verificar_nome(request: Request, nome_input: str = Form(...)):
    entrada = nome_input.strip()
    hoje = datetime.now()
    hoje_str = hoje.strftime("%m-%d") # Formato MM-DD
    
    # --- 1. LÓGICA DE ACESSO DESENVOLVEDOR (Senha:Nome) ---
    if ":" in entrada:
        senha, nome_teste = entrada.split(":", 1)
        if senha == CHAVE_MESTRA:
            nome_original = nome_teste.strip().title()
            arquivo_midia = f"parabens_{nome_original.lower()}.mp4"
            arquivo_fundo = f"fundo_{nome_original.lower()}.png"
            
            return templates.TemplateResponse(
                request=request, 
                name="dashboard.html", 
                context={
                    "nome": nome_original, 
                    "arquivo_midia": arquivo_midia, 
                    "arquivo_fundo": arquivo_fundo
                }
            )

    # --- 2. LÓGICA NORMAL DE USUÁRIO ---
    nome_clean = entrada.lower()
    mapeamento = {n.lower(): n for n in aniversariantes.keys()}

    if nome_clean in mapeamento:
        nome_original = mapeamento[nome_clean]
        # Pega MM-DD da string "YYYY-MM-DD"
        data_niver_config = aniversariantes[nome_original].split("-", 1)[1]

        # CASO A: É HOJE! (LIBERADO)
        if hoje_str == data_niver_config:
            arquivo_midia = f"parabens_{nome_original.lower()}.mp4"
            arquivo_fundo = f"fundo_{nome_original.lower()}.png"
            
            return templates.TemplateResponse(
                request=request, 
                name="dashboard.html", 
                context={
                    "nome": nome_original, 
                    "arquivo_midia": arquivo_midia, 
                    "arquivo_fundo": arquivo_fundo
                }
            )

        # CASO B: AINDA NÃO CHEGOU (REDIRECIONA PARA O TIMER)
        else:
            mes_n, dia_n = int(data_niver_config.split("-")[0]), int(data_niver_config.split("-")[1])
            ano_alvo = hoje.year
            data_alvo = datetime(ano_alvo, mes_n, dia_n)
            
            # Correção para datas que já passaram no ano atual
            if data_alvo < hoje:
                ano_alvo += 1
            
            data_alvo_iso = f"{ano_alvo}-{data_niver_config}T00:00:00"
            mensagem = f"Olhei nos meus arquivos e ainda não é hora de ver a surpresa que Gabriel preparou para você, {nome_original}. Mas não se preocupe, garanto que irá superar suas expectativas!"
            
            return templates.TemplateResponse(
                request=request, 
                name="countdown.html", 
                context={
                    "nome": nome_original, 
                    "data_alvo": data_alvo_iso,
                    "mensagem": mensagem
                }
            )

    # --- 3. NÃO ESTÁ NA LISTA ---
    else:
        nome_exibicao = entrada.title()
        erro = f"Desculpe, não temos nada de especial para você hoje, {nome_exibicao}."
        proximo_niver = obter_proximo_aniversario()
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={"erro": erro, "proximo_niver": proximo_niver}
        )