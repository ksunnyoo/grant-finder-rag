"""kiwipiepy 형태소 + BM25 희소 벡터 (sparse)."""
import json
import math
from collections import Counter
from functools import lru_cache
from pathlib import Path

from kiwipiepy import Kiwi

from grant_finder_rag.contracts.models import SparseVec

KEEP_TAGS = {"NNG", "NNP", "SL", "SN", "VV", "VA", "XR"}


@lru_cache(maxsize=1)
def _kiwi() -> Kiwi:
    return Kiwi()


def tokenize(text: str) -> list[str]:
    """명사·어근·용언·외국어·숫자만 남긴 형태소 목록."""
    tokens = _kiwi().tokenize(text)
    return [t.form.lower() for t in tokens if t.tag.split("-")[0] in KEEP_TAGS]


class Bm25SparseEncoder:
    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.vocab: dict[str, int] = {}
        self.df: dict[str, int] = {}
        self.num_docs = 0
        self.avg_len = 0.0

    def _idf(self, token: str) -> float:
        df = self.df[token]
        return math.log(1 + (self.num_docs - df + 0.5) / (df + 0.5))

    def _doc_vector(self, tokens: list[str]) -> SparseVec:
        counts = Counter(tokens)
        avg_len = self.avg_len or 1.0
        norm = self.k1 * (1 - self.b + self.b * len(tokens) / avg_len)
        pairs = []
        for token, tf in counts.items():
            index = self.vocab.get(token)
            if index is None:
                continue
            weight = self._idf(token) * tf * (self.k1 + 1) / (tf + norm)
            pairs.append((index, weight))
        pairs.sort()
        return SparseVec(indices=[i for i, _ in pairs], values=[w for _, w in pairs])

    def fit_transform(self, texts: list[str]) -> list[SparseVec]:
        """문서 집합으로 단어 사전과 통계를 만들고, 문서별 벡터를 반환한다."""
        token_lists = [tokenize(t) for t in texts]
        df: Counter = Counter()
        for tokens in token_lists:
            df.update(set(tokens))
        self.df = dict(df)
        self.vocab = {token: i for i, token in enumerate(sorted(df))}
        self.num_docs = len(texts)
        self.avg_len = sum(len(t) for t in token_lists) / max(len(token_lists), 1)
        return [self._doc_vector(tokens) for tokens in token_lists]

    def encode_documents(self, texts: list[str]) -> list[SparseVec]:
        return [self._doc_vector(tokenize(t)) for t in texts]

    def encode_query(self, text: str) -> SparseVec:
        indices = sorted({self.vocab[t] for t in tokenize(text) if t in self.vocab})
        return SparseVec(indices=indices, values=[1.0] * len(indices))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "k1": self.k1,
            "b": self.b,
            "num_docs": self.num_docs,
            "avg_len": self.avg_len,
            "vocab": self.vocab,
            "df": self.df,
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Bm25SparseEncoder":
        data = json.loads(path.read_text(encoding="utf-8"))
        encoder = cls(k1=data["k1"], b=data["b"])
        encoder.num_docs = data["num_docs"]
        encoder.avg_len = data["avg_len"]
        encoder.vocab = data["vocab"]
        encoder.df = data["df"]
        return encoder
