from pathlib import Path
from transformers import AutoTokenizer, AutoConfig, AutoModelForTokenClassification
import torch
from typing import List, Union

class LocalCkipWordSegmenter:
    def __init__(self, model_path: Union[str, Path] = "models/ckip-models/bert-base"):
        if isinstance(model_path, Path):
            model_path = str(model_path)
        self.model_path = model_path.replace("\\", "/")  # 💡 避免 Windows 把 / 轉成 \ 導致 repo id 失效

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.config = AutoConfig.from_pretrained(self.model_path)
        self.model = AutoModelForTokenClassification.from_pretrained(self.model_path)
        self.model.eval()

        # Load label mapping if exists
        self.id2label = self.config.id2label if hasattr(self.config, "id2label") else {0: "O", 1: "B", 2: "I"}

    def __call__(self, texts: List[str]) -> List[List[str]]:
        results = []
        for text in texts:
            encoding = self.tokenizer(
                text,
                return_tensors="pt",
                return_offsets_mapping=True,
                truncation=True,
                max_length=512
            )
            with torch.no_grad():
                outputs = self.model(
                    input_ids=encoding["input_ids"],
                    attention_mask=encoding["attention_mask"]
                )
            logits = outputs.logits[0]
            preds = torch.argmax(logits, dim=-1).tolist()
            tokens = self.tokenizer.convert_ids_to_tokens(encoding["input_ids"][0])
            offsets = encoding["offset_mapping"][0].tolist()

            words = []
            current_word = ""
            for token, pred_id, offset in zip(tokens, preds, offsets):
                label = self.id2label.get(pred_id, "O")
                start, end = offset
                if start == end or token in ["[CLS]", "[SEP]"]:
                    continue

                if label == "B":
                    if current_word:
                        words.append(current_word)
                    current_word = text[start:end]
                elif label == "I" and current_word:
                    current_word += text[start:end]
                else:  # label == "O" or unexpected
                    if current_word:
                        words.append(current_word)
                        current_word = ""
            if current_word:
                words.append(current_word)
            results.append(words)
        return results
