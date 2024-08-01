# Overview
Sample project to redact information from PDF files using Azure Document Intelligence and Azure OpenAI.

This project will extract labeled values using the specified `FORM_RECOGNIZER_MODEL_ID`.

`STORAGE_CONNECTION_STRING` is the connection string to your Azure Storage Account, i.e. `DefaultEndpointsProtocol=https;AccountName=<account-name>;AccountKey=<account-key>;EndpointSuffix=core.windows.net`.  

`OPENAI_ENDPOINT` is the URL for your Azure OpenAI model deployment, i.e. `https://<service-name>.openai.azure.com/openai/deployments/<model>/chat/completions?api-version=2024-02-15-preview`.  

`OPENAI_KEY` is the API key for your Azure OpenAI service.  

`FORM_RECOGNIZER_ENDPOINT` is the URL for your Azure Form Recognizer service, i.e. `https://<service-name>.cognitiveservices.azure.com`.  

`FORM_RECOGNIZER_KEY` is the API key for your Azure Form Recognizer service.  

`FORM_RECOGNIZER_MODEL_ID` is the name of the trained model for your custom extraction.  

# Limitations
- Only works for one custom extraction model
- Redactions black out the entire line and not just the identified values, need to fix
- Prompt is hardcoded and not passed in environment, need to fix
