import azure.functions as func
import requests
import logging
import json
import fitz
import sys
import io
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.ai.textanalytics import TextAnalyticsClient
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
    entities = get_pii_entities([form['content']])
    redactions = get_chatgpt_response(entities, form['content'])
    filename = f'{myblob.name.replace(".pdf", "").replace("inbound/", "")}-redacted.pdf'
    output = redact_pdf(data, form, redactions)

    stream = io.BytesIO()
    output.save(stream)
    output.close()
    
    blob_client = BlobServiceClient.from_connection_string(os.environ["STORAGE_CONNECTION_STRING"]).get_blob_client(container='outbound', blob=filename)
    blob_client.upload_blob(stream.getvalue(), overwrite=True)

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

def get_chatgpt_response(entities, content):
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
                "content": [
                    {
                    "type": "text",
                    "text": '''
                    You are an AI assistant. Your objective is to identify personally identifiable information. Identify all PII in the provided documents besides the information belonging to the deceased/victim.
                    Titles or job positions are not considered PII.
                    Results should be a JSON array of PII values.
                    JSON response should be plain JSON.
                    {content}
                    '''.format(content=content)
                    },
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "response_format": {"type": "json_object"},
                        "type": "text",
                        "text": '''
                        Give me a JSON array containing valid PII entities for the following scenario. 
                        I am trying to redact PII from medical records. 
                        I have a list of PII from the medical record. 
                        The PII I want to redact belongs to all individuals who are not the victim or the deceased mentioned in the medical record.
                        Titles or job positions are not considered PII and should not be included in the result.

                        The below JSON array are the identified PII entities:
                        {entities}

                        The PII entities were derived from the below text:
                        {content} 
                        '''
                    },
                ],
            }
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
    logging.info(content)
    return json.loads(content)

def get_pii_entities(blob):
    endpoint = os.environ["LANGUAGE_ENDPOINT"]
    key = os.environ["LANGUAGE_KEY"]

    text_analytics_client = TextAnalyticsClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    result = text_analytics_client.recognize_pii_entities(blob)
    entities = [{'text': entity.text, 'category': entity.category} for entity in result[0].entities]
    logging.info(entities)

def redact_pdf(blob, form, redactions):
    # Open the PDF
    try:
        doc = fitz.open('pdf', blob)
    except:
        raise SystemExit(f'Failed to open the PDF file')

    # Split redactions
    redactions = set(word for name in redactions for word in name.split())

    # Get the page
    for page in doc.pages():
        logging.info(f'Starting on page {page.number}')
        page = doc.load_page(page.number)
        scale_x = page.rect[2] / form['pages'][page.number]['width']
        scale_y = page.rect[3] / form['pages'][page.number]['height']

        # Create retractions from extracted values
        for key, value in form['documents'][0]['fields'].items():
            try:
                polygon = value['bounding_regions'][0]['polygon']
            except:
                continue
            logging.info(f'Redacting: Key {key} with content {value["content"]} on page {page.number}')
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

        # Create retractions from content
        for word in form['pages'][page.number]['words']:
            if word['content'] in redactions:
                try:
                    polygon = word['polygon']
                except:
                    continue
                logging.info(f'Redacting: {word["content"]} on page {page.number}')

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