# Overview
Sample project to redact information from PDF files using Azure Document Intelligence and Azure OpenAI.

This project will extract labeled values using the specified `FORM_RECOGNIZER_MODEL_ID`.

| Key                          | Description                                                                                                           |
|------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `STORAGE_CONNECTION_STRING`  | The connection string to your Azure Storage Account, i.e. `DefaultEndpointsProtocol=https;AccountName=<account-name>;AccountKey=<account-key>;EndpointSuffix=core.windows.net`. |
| `OPENAI_ENDPOINT`            | The URL for your Azure OpenAI model deployment, i.e. `https://<service-name>.openai.azure.com/openai/deployments/<model>/chat/completions?api-version=2024-02-15-preview`. |
| `OPENAI_KEY`                 | The API key for your Azure OpenAI service.                                                                            |
| `FORM_RECOGNIZER_ENDPOINT`   | The URL for your Azure Form Recognizer service, i.e. `https://<service-name>.cognitiveservices.azure.com`.            |
| `FORM_RECOGNIZER_KEY`        | The API key for your Azure Form Recognizer service.                                                                   |
| `FORM_RECOGNIZER_MODEL_ID`   | The name of the trained model for your custom extraction.                                                             |
| `LANGUAGE_ENDPOINT`          | The URL for your Language Service instance, i.e. `https://<service-name>.cognitiveservices.azure.com/`                |
| `LANGUAGE_KEY`               | The API key for your Azure Language Service.                                                                          |