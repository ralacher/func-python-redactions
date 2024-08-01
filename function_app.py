import azure.functions as func
import requests
import logging
import json
import fitz
import io
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="inbound",
                               connection="STORAGE_CONNECTION_STRING")
def FileUpload(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")
    data = myblob.read()
    form = get_form_recognizer(data)
    redactions = get_chatgpt_response(form['content'])
    filename = f'{myblob.name.replace(".pdf", "").replace("inbound/", "")}-redacted.pdf'
    output = redact_pdf(data, form, redactions)

    stream = io.BytesIO()
    output.save(stream)
    output.close()
    
    blob_client = BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"]).get_blob_client(container='outbound', blob=filename)
    blob_client.upload_blob(stream.getvalue())

def get_form_recognizer(blob):
    endpoint = os.environ["FORM_RECOGNIZER_ENDPOINT"]
    key = os.environ["FORM_RECOGNIZER_KEY"]
    model_id = os.environ["FORM_RECOGNIZER_MODEL_ID"]

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    # Make sure your document's type is included in the list of document types the custom model can analyze
    #with open(blob.read(), 'rb') as f:
    poller = document_analysis_client.begin_analyze_document(model_id, blob)
    result = poller.result()
    return result.to_dict()

def get_chatgpt_response(content):
    GPT4V_KEY = os.environ["OPENAI_KEY"]
    GPT4V_ENDPOINT = os.environ["OPENAI_ENDPOINT"]

    headers = {
        "Content-Type": "application/json",
        "api-key": GPT4V_KEY,
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "response_format": {"type": "json_object"},
                "content": [
                    {
                    "type": "text",
                    "text": '''
                    You are an AI assistant. 
                    Your objective is to identify personally identifiable information.
                    Identify all names in the document besides the name of the deceased.
                    Results should be a JSON array of PII values.
                    JSON response should be plain JSON.
                    {content}
                    '''.format(content=content)
                    },
                ],
            },
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    # Send request
    try:
        response = requests.post(GPT4V_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")

    # Handle the response as needed (e.g., print or process)
    content = response.json()['choices'][0]['message']['content'].replace('```', '').replace('json', '')
    print(content)
    return json.loads(content)

def redact_pdf(blob, form, redactions):
    # Open the PDF
    try:
        img = fitz.Document(stream=blob)
        pdfbytes = img.convert_to_pdf()
        doc = fitz.open('pdf', pdfbytes)
    except:
        raise SystemExit(f'Failed to open the PDF file')
    
    # Get the page
    for page in doc.pages():
        page = doc.load_page(page.number)
        scale_x = page.rect[2] / form['pages'][0]['width']
        scale_y = page.rect[3] / form['pages'][0]['height']

        for line in form['pages'][0]['lines']:
            for redaction in redactions:
                if redaction in line['content']:
                    try:
                        polygon = line['polygon']
                    except:
                        continue

                    scaled_polygon = []
                    for i in range(0, len(polygon), 2):
                        x = polygon[i]['x'] * scale_x
                        y = polygon[i]['y'] * scale_y
                        scaled_polygon.extend([x, y])

                    min_x = min(scaled_polygon[0::2])
                    max_x = max(scaled_polygon[0::2])
                    min_y = min(scaled_polygon[1::2])
                    max_y = max(scaled_polygon[1::2])

                    rect = fitz.Rect(min_x, min_y, max_x, max_y)

                    page.add_redact_annot(rect)
                    page.apply_redactions()
                    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
                    page.draw_rect(rect, color=(0,0,0), fill=(0,0,0))
    return doc
    '''
    for k,v in form['documents'][0]['fields'].items():

        try:
            polygon = v['bounding_regions'][0]['polygon']
            print(f'Redacting: {v["content"]} ')
        except:
            continue

        scaled_polygon = []
        for i in range(0, len(polygon), 2):
            x = polygon[i]['x'] * scale_x
            y = polygon[i]['y'] * scale_y
            scaled_polygon.extend([x, y])

        min_x = min(scaled_polygon[0::2])
        max_x = max(scaled_polygon[0::2])
        min_y = min(scaled_polygon[1::2])
        max_y = max(scaled_polygon[1::2])

        rect = fitz.Rect(min_x, min_y, max_x, max_y)

        page.add_redact_annot(rect)
        page.apply_redactions()
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)
        page.draw_rect(rect, color=(0,0,0), fill=(0,0,0))
        # then save the doc to a new PDF:
    '''