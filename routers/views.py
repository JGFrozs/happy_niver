import os
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Views do Cliente & Exibição"])
templates = Jinja2Templates(directory="templates")

CHAVE_MESTRA = os.getenv("CHAVE_MESTRA")

def get_gspread_client():
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciais = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", escopo)
    return gspread.authorize(credenciais)

def obter_aba_normalizada(planilha, nome_esperado):
    for w in planilha.worksheets():
        if w.title.strip().lower() == nome_esperado.strip().lower():
            return w
    raise gspread.exceptions.WorksheetNotFound(f"Aba '{nome_esperado}' não foi encontrada.")

def buscar_aniversariante_no_sheets(nome_cliente_url, nome_digitado):
    try:
        cliente_gspread = get_gspread_client()
        planilha = cliente_gspread.open("cadastro happy-niver")
        aba = obter_aba_normalizada(planilha, "Aniversariantes")
        registros = aba.get_all_records()
        
        for linha in registros:
            if str(linha["Cliente"]).strip().lower() == nome_cliente_url.strip().lower() and \
               str(linha["Nome"]).strip().lower() == nome_digitado.strip().lower():
                return {
                    "Nome": linha["Nome"],
                    "Data": linha["Data"],
                    "video": linha["midia"],  
                    "Fundo": linha["Fundo"]
                }
        return None
    except Exception as e:
        print(f"Erro inesperado ao buscar aniversariante: {e}")
        return None

def obter_proximo_aniversario_por_cliente(nome_cliente):
    try:
        cliente_gspread = get_gspread_client()
        planilha = cliente_gspread.open("cadastro happy-niver")
        aba = obter_aba_normalizada(planilha, "Aniversariantes")
        registros = aba.get_all_records()
        
        hoje = datetime.now()
        datas = []
        for linha in registros:
            if str(linha["Cliente"]).strip().lower() == nome_cliente.strip().lower():
                data_partes = linha["Data"].split("-")
                data_obj = datetime(hoje.year, int(data_partes[1]), int(data_partes[2]))
                if data_obj < hoje: data_obj = data_obj.replace(year=hoje.year + 1)
                datas.append(data_obj)
        
        return min(datas).strftime("%Y-%m-%dT00:00:00") if datas else hoje.strftime("%Y-%m-%dT00:00:00")
    except:
        return datetime.now().strftime("%Y-%m-%dT00:00:00")

# --- ROTAS DE VISUALIZAÇÃO ---

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="homepage.html")

@router.get("/cliente/{nome_cliente}/acesso", response_class=HTMLResponse)
async def acesso_cliente(request: Request, nome_cliente: str):
    proximo_niver = obter_proximo_aniversario_por_cliente(nome_cliente)
    contexto = {"proximo_niver": proximo_niver, "cliente": nome_cliente}
    return templates.TemplateResponse(request=request, name="index.html", context=contexto)

@router.post("/cliente/{nome_cliente}/verificar", response_class=HTMLResponse)
async def verificar_cliente(request: Request, nome_cliente: str, usuario_input: str = Form(...)):
    if ":" in usuario_input:
        senha, nome = usuario_input.split(":", 1)
        if senha == CHAVE_MESTRA:
            contexto = {
                "nome": nome.title(), 
                "arquivo_midia": f"parabens_{nome.lower()}.mp4", 
                "arquivo_fundo": f"fundo_{nome.lower()}.png"
            }
            return templates.TemplateResponse(request=request, name="dashboard.html", context=contexto)

    dados = buscar_aniversariante_no_sheets(nome_cliente, usuario_input)
    if dados:
        hoje = datetime.now()
        data_niver = datetime.strptime(dados["Data"], "%Y-%m-%d")
        
        if hoje.month == data_niver.month and hoje.day == data_niver.day:
            contexto = {
                "nome": dados["Nome"], 
                "arquivo_midia": dados["video"], 
                "arquivo_fundo": dados["Fundo"]
            }
            return templates.TemplateResponse(request=request, name="dashboard.html", context=contexto)
        else:
            data_alvo = f"{hoje.year if data_niver.month >= hoje.month else hoje.year+1}-{dados['Data'][5:]}T00:00:00"
            contexto = {"nome": dados["Nome"], "data_alvo": data_alvo}
            return templates.TemplateResponse(request=request, name="countdown.html", context=contexto)
    
    contexto = {"erro": "Nome não encontrado", "cliente": nome_cliente}
    return templates.TemplateResponse(request=request, name="index.html", context=contexto)