import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def embed(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x ** 2 for x in a) ** 0.5
    magnitude_b = sum(y ** 2 for y in b) ** 0.5
    return dot_product / (magnitude_a * magnitude_b)


vec_diabetes = embed("What are the symptoms of diabetes?")
vec_insulin = embed("How does insulin affect blood sugar?")
vec_guitar = embed("What's a good beginner guitar?")

print("Vector length:", len(vec_diabetes))
print()
print("diabetes vs insulin similarity:", cosine_similarity(vec_diabetes, vec_insulin))
print("diabetes vs guitar similarity:", cosine_similarity(vec_diabetes, vec_guitar))