import csv
import time
import json

from app.database import SessionLocal
from app.rag import answer_question
from app.models import UserDB


def load_dataset(path="eval/dataset.csv"):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def score_retrieval(results):
    answerable = [r for r in results if r["is_answerable"]]
    correct = 0

    for r in answerable:
        actual_filenames = [s["filename"] for s in r["actual_sources"]]
        if r["expected_document"] in actual_filenames:
            correct += 1
        else:
            print("\n[RETRIEVAL FAILED]")
            print(f"Question: {r['question']}")
            print(f"Expected document: {r['expected_document']}")
            print(f"Retrieved documents: {actual_filenames}")

    accuracy = correct / len(answerable) * 100
    print(f"\nRetrieval accuracy: {correct}/{len(answerable)} = {accuracy:.1f}%")
    return accuracy

def score_answer_relevance(results):
    answerable = [r for r in results if r["is_answerable"]]

    correct = 0

    for r in answerable:
        answer = r["actual_answer"].lower()

        expected_phrases = [
            phrase.lower()
            for phrase in r["expected_keyphrases"]
        ]

        if all(phrase in answer for phrase in expected_phrases):
            correct += 1

    score = correct / len(answerable) * 100

    print(
        f"Answer relevance: "
        f"{correct}/{len(answerable)} = {score:.1f}%"
    )

    return score

def score_hallucination_refusal(results):
    unanswerable = [r for r in results if not r["is_answerable"]]

    correct = 0

    for r in unanswerable:
        answer = r["actual_answer"].lower()

        if "i don't have enough information" in answer:
            correct += 1

    score = correct / len(unanswerable) * 100

    print(
        f"Hallucination/refusal rate: "
        f"{correct}/{len(unanswerable)} = {score:.1f}%"
    )

    return score

def calculate_average_latency(results):
    average = sum(r["latency"] for r in results) / len(results)

    print(f"Average latency: {average:.2f} seconds")

    return average

def calculate_average_tokens(results):
    total_tokens = sum(
        r["prompt_tokens"] + r["completion_tokens"]
        for r in results
    )

    average = total_tokens / len(results)

    print(f"Average tokens/question: {average:.0f}")

    return average

def build_summary(results):
    retrieval = score_retrieval(results)
    relevance = score_answer_relevance(results)
    refusal = score_hallucination_refusal(results)
    latency = calculate_average_latency(results)
    tokens = calculate_average_tokens(results)

    return {
        "retrieval_accuracy": retrieval,
        "answer_relevance": relevance,
        "hallucination_refusal_rate": refusal,
        "average_latency_seconds": latency,
        "average_tokens_per_question": tokens,
    }
    
def run():
    dataset = load_dataset()
    db = SessionLocal()
    results = []
    
    user = db.query(UserDB).filter(
        UserDB.email == "test@example.com"
    ).first()

    if user is None:
        user = UserDB(
            email="test@example.com",
            hashed_password="fake"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    user_id = user.id

    for row in dataset:
        start = time.perf_counter()
        result = answer_question(row["question"], db, user_id)
        elapsed = time.perf_counter() - start

        results.append({
            "question": row["question"],
            "is_answerable": row["is_answerable"] == "True",
            "expected_document": row["expected_document"],
            "expected_keyphrases": (
                row["expected_keyphrases"].split("|")
                if row["expected_keyphrases"]
                else []
            ),
            "actual_answer": result["answer"],
            "actual_sources": result["sources"],
            "retrieved_chunks": result["retrieved_chunks"],
            "latency": elapsed,
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
        })

        print(f"[{'OK' if result else 'FAIL'}] {row['question'][:60]}")

    db.close()

    summary = build_summary(results)

    output = {
        "summary": summary,
        "results": results
    }

    with open("eval/results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return results

if __name__ == "__main__":
    results = run()
    print(f"\nRan {len(results)} questions.")