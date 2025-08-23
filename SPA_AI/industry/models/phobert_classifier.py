import torch
import torch.nn as nn
import logging
from transformers import AutoModel, AutoTokenizer
import os

class IndustryClassifier(nn.Module):
    def __init__(self, n_classes=5):
        super(IndustryClassifier, self).__init__()
        self.bert = AutoModel.from_pretrained("vinai/phobert-base")
        self.drop = nn.Dropout(p=0.3)
        self.fc = nn.Linear(self.bert.config.hidden_size, n_classes)
        nn.init.normal_(self.fc.weight, std=0.02)
        nn.init.normal_(self.fc.bias, 0)

    def forward(self, input_ids, attention_mask):
        _, pooled_output = self.bert(input_ids=input_ids, attention_mask=attention_mask, return_dict=False)
        output = self.drop(pooled_output)
        return self.fc(output)

class PhoBERTClassifier:
    def __init__(self, model_path, labels):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.labels = labels
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("vinai/phobert-base")
            self.model = IndustryClassifier(n_classes=len(labels))
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found at: {model_path}")
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.to(self.device)
            self.model.eval()
            logging.info(f"Model loaded successfully from {model_path}")
        except Exception as e:
            logging.error(f"Error initializing classifier: {str(e)}")
            raise

    def predict(self, text):
        try:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self.model(input_ids=inputs["input_ids"], attention_mask=inputs["attention_mask"])
                probs = torch.softmax(outputs, dim=1)
                pred_idx = torch.argmax(probs, dim=1).item()
            return self.labels[pred_idx], probs[0].cpu().numpy()
        except Exception as e:
            logging.error(f"Prediction error: {str(e)}")
            return "Unknown", [0]*len(self.labels)
