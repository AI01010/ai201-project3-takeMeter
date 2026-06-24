# web/model/ — drop your fine-tuned model here

This folder is **empty by default**. The Test page works without it (it falls back
to the Groq zero-shot backend, or a transparent keyword heuristic).

To serve **your own fine-tuned DistilBERT** on the Test page:

1. In the Colab notebook, run **Section 7** — it produces `takemeter_model_export.zip`.
2. Download and unzip it so this folder contains the model files directly:
   ```
   web/model/
     ├── config.json
     ├── model.safetensors
     ├── tokenizer.json
     ├── vocab.txt
     └── takemeter_meta.json
   ```
3. Install the inference deps:  `pip install transformers torch`
4. Restart the app — the Test page badge will switch to **backend: model**.

> The model files are gitignored (they're large). Commit them only if your repo
> hosting allows it; otherwise keep the link to the Colab export in your README.
