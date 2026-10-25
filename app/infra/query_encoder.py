import numpy as np

MAX_LEN = 256  # 질의 한 문장을 모델에 넣을 때 최대 토큰 수


class QueryEncoder:
    """영어 문장 -> 길이 1인 벡터(768개). multilingual-e5-base 규칙대로 질의 앞에 'query: '를 붙인다.

    torch/transformers는 이 클래스를 만들 때만 불러온다 (앱 import 때는 불리지 않는다).
    """

    def __init__(self, model_name: str):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self._torch = torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).to(self._device).eval()
        self._model = model.half() if self._device == "cuda" else model  # 게임 임베딩을 만들 때와 같은 정밀도

    def encode(self, text: str) -> np.ndarray:
        torch = self._torch
        with torch.no_grad():
            batch = self._tokenizer(
                ["query: " + text], max_length=MAX_LEN, padding=True, truncation=True, return_tensors="pt"
            ).to(self._device)
            hidden = self._model(**batch).last_hidden_state  # (1, 토큰 수, 768)
            mask = batch["attention_mask"].unsqueeze(-1)  # 진짜 토큰만 1, 패딩은 0
            vec = (hidden * mask).sum(1) / mask.sum(1)  # 패딩을 뺀 평균
            vec = torch.nn.functional.normalize(vec.float(), dim=-1)
        return vec[0].cpu().numpy()
