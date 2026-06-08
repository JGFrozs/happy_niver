import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["Autenticação & Cadastro"])
templates = Jinja2Templates(directory="templates")

# Configurações de E-mail carregadas do ambiente global
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")    
EMAIL_SENHA = os.getenv("EMAIL_SENHA")            
SMTP_SERVER = "smtp.gmail.com"                    
SMTP_PORT = 587                                   

def get_gspread_client():
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credenciais = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", escopo)
    return gspread.authorize(credenciais)

def obter_aba_normalizada(planilha, nome_esperado):
    for w in planilha.worksheets():
        if w.title.strip().lower() == nome_esperado.strip().lower():
            return w
    raise gspread.exceptions.WorksheetNotFound(f"Aba '{nome_esperado}' não foi encontrada.")

def obter_linha_cliente_sheets(nome_cliente, email):
    try:
        cliente_gspread = get_gspread_client()
        planilha = cliente_gspread.open("cadastro happy-niver")
        aba = obter_aba_normalizada(planilha, "clientes")
        registros = aba.get_all_records()
        
        nome_busca = nome_cliente.strip().lower()
        email_busca = email.strip().lower()
        
        for indice, linha in enumerate(registros, start=2):
            if str(linha.get("Nome_Cliente", "")).strip().lower() == nome_busca or \
               str(linha.get("E-mail", "")).strip().lower() == email_busca:
                return indice
        return None
    except Exception as e:
        print(f"Erro ao verificar existência do cliente: {e}")
        return None

def atualizar_telefone_sheets(linha_num, novo_telefone):
    try:
        cliente_gspread = get_gspread_client()
        planilha = cliente_gspread.open("cadastro happy-niver")
        aba = obter_aba_normalizada(planilha, "clientes")
        aba.update_cell(linha_num, 3, novo_telefone)
        return True
    except Exception as e:
        print(f"Erro ao atualizar telefone no Sheets: {e}")
        return False

def salvar_cliente_sheets(nome_cliente, email, telefone):
    try:
        cliente_gspread = get_gspread_client()
        planilha = cliente_gspread.open("cadastro happy-niver")
        aba = obter_aba_normalizada(planilha, "clientes")
        aba.append_row([nome_cliente, email, telefone])
        return True
    except Exception as e:
        print(f"Erro ao salvar cliente no Sheets: {e}")
        return False

def enviar_email_boas_vindas(nome_cliente, email_destino):
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("Aviso: Variáveis de e-mail ausentes no arquivo .env")
        return False
    try:
        mensagem = MIMEMultipart()
        mensagem["From"] = EMAIL_REMETENTE
        mensagem["To"] = email_destino
        mensagem["Subject"] = f"Bem-vindo ao Happy Niver, {nome_cliente}! 🎉"

        link_acesso = f"http://127.0.0.1:8000/cliente/{nome_cliente}/acesso"
        corpo_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #4A1525;">Olá, {nome_cliente}!</h2>
                <p>Seu cadastro no <strong>Happy Niver</strong> foi concluído.</p>
                <p>Para visualizar e liberar as surpresas de aniversário configuradas para você, clique no botão abaixo:</p>
                <br>
                <a href="{link_acesso}" style="background-color: #F4B942; color: #0d1b2a; padding: 12px 25px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block;">Acessar Meu Painel</a>
                <br><br>
                <p>Link direto se o botão não funcionar:<br>{link_acesso}</p>
                <hr style="border: 0; border-top: 1px solid #ccc;">
                <p style="font-size: 12px; color: #777;">Equipe Happy Niver - Eternizando Afeto</p>
            </body>
        </html>
        """
        mensagem.attach(MIMEText(corpo_html, "html"))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.sendmail(EMAIL_REMETENTE, email_destino, msg=mensagem.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao despachar e-mail: {e}")
        return False

# --- ROTAS DE CADASTRO ---

@router.get("/cadastro", response_class=HTMLResponse)
async def pagina_cadastro(request: Request):
    return templates.TemplateResponse(request=request, name="cadastro.html")

@router.post("/cadastrar_novo")
async def cadastrar_novo_cliente(
    request: Request,
    nome_cliente: str = Form(...),
    email: str = Form(...),
    telefone: str = Form(...)
):
    linha_existente = obter_linha_cliente_sheets(nome_cliente, email)
    if linha_existente:
        sucesso_atualizacao = atualizar_telefone_sheets(linha_existente, telefone)
        if sucesso_atualizacao:
            enviar_email_boas_vindas(nome_cliente, email)
            return RedirectResponse(url=f"/cadastro_sucesso?email={email}&atualizado=true", status_code=303)
        else:
            return templates.TemplateResponse(request=request, name="cadastro.html", context={"erro": "Erro ao atualizar seus dados na planilha."})

    sucesso_sheets = salvar_cliente_sheets(nome_cliente, email, telefone)
    if sucesso_sheets:
        enviar_email_boas_vindas(nome_cliente, email)
        return RedirectResponse(url=f"/cadastro_sucesso?email={email}", status_code=303)
    
    return templates.TemplateResponse(request=request, name="cadastro.html", context={"erro": "Erro ao salvar os dados na planilha."})

@router.get("/cadastro_sucesso", response_class=HTMLResponse)
async def pagina_sucesso(request: Request, email: str, atualizado: bool = False):
    return templates.TemplateResponse(
        request=request, 
        name="cadastro_sucesso.html", 
        context={"email": email, "atualizado": atualizado}
    )