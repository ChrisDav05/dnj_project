import io
import os
import pdfplumber
import easyocr
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload

SPREADSHEET_ID = "13v-UlK5EWAErkZ4CBDb1Zmba6JH7e5tFL-qQw3IupMg"
RANGE_NAME = "A:I"  # pega ID (coluna A), Nome (coluna C) e Link (coluna I)

reader = easyocr.Reader(['pt'])

def get_services():
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/spreadsheets.readonly"
        ]
    )
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets

def download_file(drive_service, file_id, filename):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(filename, "wb")
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return filename

def check_file_for_payment(filepath):
    padroes = ["R$45,00", "R$ 45,00"]
    if filepath.lower().endswith(".pdf"):
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and any(p in text for p in padroes):
                    return True
    else:
        results = reader.readtext(filepath)
        texto = " ".join([res[1] for res in results])
        if any(p in texto for p in padroes):
            return True
    return False

class PagamentoCheckView(View):
    def get(self, request, *args, **kwargs):
        user_id_param = request.GET.get("id")
        if not user_id_param:
            return JsonResponse({"status": "erro", "msg": "Informe um ID"}, status=400)

        drive, sheets = get_services()
        sheet = sheets.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()
        values = result.get("values", [])

        if not values:
            return JsonResponse({"status": "erro", "msg": "Planilha vazia"})

        pagamento = None

        # Define pasta para salvar os arquivos
        pasta_comprovantes = os.path.join(settings.BASE_DIR, "static", "img", "comprovantes")
        os.makedirs(pasta_comprovantes, exist_ok=True)

        for i, row in enumerate(values[1:], start=2):
            if len(row) < 9:
                continue

            user_id = row[0]     # Coluna A -> ID
            nome_completo = row[2] if len(row) > 2 else "Não informado"  # Coluna C -> Nome
            link = row[8]        # Coluna I -> Link

            if user_id != user_id_param:
                continue

            if "id=" not in link:
                pagamento = {
                    "linha": i,
                    "id": user_id,
                    "nome": nome_completo,
                    "status": "Link inválido ❌"
                }
                break

            file_id = link.split("id=")[-1]
            filename_base = f"comprovante_{i}"
            filepath = os.path.join(pasta_comprovantes, filename_base)

            try:
                file = drive.files().get(fileId=file_id, fields="name, mimeType").execute()
                name = file["name"]
                mime = file["mimeType"]

                if "pdf" in mime:
                    filepath += ".pdf"
                else:
                    filepath += ".png"

                # baixa o arquivo para a pasta static/img/comprovantes
                download_file(drive, file_id, filepath)

                status = "Pagamento encontrado (R$ 45,00) ✅" if check_file_for_payment(filepath) else "Pagamento não encontrado ❌"
                pagamento = {
                    "linha": i,
                    "id": user_id,
                    "nome": nome_completo,
                    "arquivo": name,
                    "status": status,
                    "caminho_salvo": filepath.replace(str(settings.BASE_DIR), "")
                }
            except Exception as e:
                pagamento = {
                    "linha": i,
                    "id": user_id,
                    "nome": nome_completo,
                    "status": f"⚠️ Erro: {str(e)}"
                }
            break

        if not pagamento:
            return JsonResponse({"status": "erro", "msg": f"ID {user_id_param} não encontrado"}, status=404)

        return JsonResponse({"pagamento": pagamento}, json_dumps_params={'ensure_ascii': False})



# import io
# import os
# import pdfplumber
# import easyocr
# from django.views import View
# from django.http import JsonResponse
# from django.conf import settings
# from googleapiclient.discovery import build
# from google.oauth2.service_account import Credentials
# from googleapiclient.http import MediaIoBaseDownload

# SPREADSHEET_ID = "13v-UlK5EWAErkZ4CBDb1Zmba6JH7e5tFL-qQw3IupMg"
# RANGE_NAME = "A:I"  # pega ID (coluna A) e Link (coluna I)

# reader = easyocr.Reader(['pt'])

# def get_services():
#     creds = Credentials.from_service_account_file(
#         "credentials.json",
#         scopes=[
#             "https://www.googleapis.com/auth/drive.readonly",
#             "https://www.googleapis.com/auth/spreadsheets.readonly"
#         ]
#     )
#     drive = build("drive", "v3", credentials=creds)
#     sheets = build("sheets", "v4", credentials=creds)
#     return drive, sheets

# def download_file(drive_service, file_id, filename):
#     request = drive_service.files().get_media(fileId=file_id)
#     fh = io.FileIO(filename, "wb")
#     downloader = MediaIoBaseDownload(fh, request)
#     done = False
#     while not done:
#         status, done = downloader.next_chunk()
#     return filename

# # Verifica se o arquivo contém o valor do pagamento

# def check_file_for_payment(filepath):
#     padroes = ["R$45,00", "R$ 45,00"]
#     if filepath.lower().endswith(".pdf"):
#         with pdfplumber.open(filepath) as pdf:
#             for page in pdf.pages:
#                 text = page.extract_text()
#                 if text and any(p in text for p in padroes):
#                     return True
#     else:
#         results = reader.readtext(filepath)
#         texto = " ".join([res[1] for res in results])
#         if any(p in texto for p in padroes):
#             return True
#     return False

# class PagamentoCheckView(View):
#     def get(self, request, *args, **kwargs):
#         user_id_param = request.GET.get("id")
#         if not user_id_param:
#             return JsonResponse({"status": "erro", "msg": "Informe um ID"}, status=400)

#         drive, sheets = get_services()
#         sheet = sheets.spreadsheets()
#         result = sheet.values().get(
#             spreadsheetId=SPREADSHEET_ID,
#             range=RANGE_NAME
#         ).execute()
#         values = result.get("values", [])

#         if not values:
#             return JsonResponse({"status": "erro", "msg": "Planilha vazia"})

#         pagamento = None

#         # Define pasta para salvar os arquivos
#         pasta_comprovantes = os.path.join(settings.BASE_DIR, "static", "img", "comprovantes")
#         os.makedirs(pasta_comprovantes, exist_ok=True)

#         for i, row in enumerate(values[1:], start=2):
#             if len(row) < 9:
#                 continue

#             user_id = row[0]
#             link = row[8]  # coluna I
#             if user_id != user_id_param:
#                 continue

#             if "id=" not in link:
#                 pagamento = {"linha": i, "id": user_id, "status": "Link inválido ❌"}
#                 break

#             file_id = link.split("id=")[-1]
#             filename_base = f"comprovante_{i}"
#             filepath = os.path.join(pasta_comprovantes, filename_base)  # caminho completo

#             try:
#                 file = drive.files().get(fileId=file_id, fields="name, mimeType").execute()
#                 name = file["name"]
#                 mime = file["mimeType"]

#                 if "pdf" in mime:
#                     filepath += ".pdf"
#                 else:
#                     filepath += ".png"

#                 # baixa o arquivo para a pasta static/img/comprovantes
#                 download_file(drive, file_id, filepath)

#                 status = "Pagamento encontrado (R$ 45,00) ✅" if check_file_for_payment(filepath) else "Pagamento não encontrado ❌"
#                 pagamento = {
#                     "linha": i,
#                     "id": user_id,
#                     "arquivo": name,
#                     "status": status,
#                     "caminho_salvo": filepath.replace(str(settings.BASE_DIR), "")  # caminho relativo para debug
#                 }
#             except Exception as e:
#                 pagamento = {"linha": i, "id": user_id, "status": f"⚠️ Erro: {str(e)}"}
#             break

#         if not pagamento:
#             return JsonResponse({"status": "erro", "msg": f"ID {user_id_param} não encontrado"}, status=404)

#         return JsonResponse({"pagamento": pagamento}, json_dumps_params={'ensure_ascii': False})
