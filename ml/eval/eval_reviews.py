import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure classforge-backend is in sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "classforge-backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.modules.project_reviews.domain.models import VerdictType
from app.modules.project_reviews.pdf_extractor import (
    ExtractedDocument,
    PageContent,
    SECTION_PATTERNS,
    sanitize_text,
    MIN_WORDS_SUFFICIENT_TEXT,
)
from app.modules.project_reviews.evaluator import ProjectEvaluator

DATASET_FILE = Path(__file__).resolve().parent.parent / "data" / "reviews_dataset.jsonl"
OUTPUT_METRICS_FILE = Path(__file__).resolve().parent / "benchmark_results.json"


def parse_sample_to_extracted_doc(sample: Dict[str, Any]) -> ExtractedDocument:
    raw_text = sample.get("document_text", "")
    page_count = sample.get("page_count", 1)

    # Split by [Página X]
    page_blocks = re.split(r"\[Página\s+(\d+)\]", raw_text)
    pages: List[PageContent] = []
    section_pages: Dict[str, List[int]] = {sec: [] for sec in SECTION_PATTERNS}
    total_words = 0

    if len(page_blocks) > 1:
        # Alternating: preamble, page_num, text, page_num, text...
        for i in range(1, len(page_blocks), 2):
            p_num = int(page_blocks[i])
            p_text = sanitize_text(page_blocks[i + 1] if i + 1 < len(page_blocks) else "")
            wc = len(p_text.split())
            total_words += wc
            pages.append(PageContent(page_number=p_num, text=p_text, word_count=wc))

            for sec, pats in SECTION_PATTERNS.items():
                for pat in pats:
                    if pat.search(p_text):
                        if p_num not in section_pages[sec]:
                            section_pages[sec].append(p_num)
                        break
    else:
        cleaned = sanitize_text(raw_text)
        wc = len(cleaned.split())
        total_words = wc
        pages.append(PageContent(page_number=1, text=cleaned, word_count=wc))
        for sec, pats in SECTION_PATTERNS.items():
            for pat in pats:
                if pat.search(cleaned):
                    section_pages[sec].append(1)
                    break

    has_sufficient_text = total_words >= MIN_WORDS_SUFFICIENT_TEXT
    detected_sections = [sec for sec, pgs in section_pages.items() if len(pgs) > 0]
    full_text = "\n\n".join(f"[Página {p.page_number}]\n{p.text}" for p in pages)

    return ExtractedDocument(
        page_count=max(page_count, len(pages)),
        total_word_count=total_words,
        has_sufficient_text=has_sufficient_text,
        pages=pages,
        detected_sections=detected_sections,
        section_pages=section_pages,
        full_text=full_text,
    )


async def run_benchmark():
    print(f"=== ClassForge 2.0: Evaluador Inteligente Local — Ejecución de Benchmark ===")
    print(f"Leyendo dataset desde: {DATASET_FILE}")

    if not DATASET_FILE.exists():
        print(f"Error: Dataset no encontrado en {DATASET_FILE}")
        sys.exit(1)

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        samples = [json.loads(line) for line in f if line.strip()]

    print(f"Muestras cargadas: {len(samples)}")
    evaluator = ProjectEvaluator()

    results = []
    classes = [VerdictType.APROBADO.value, VerdictType.RECHAZADO.value, VerdictType.INFORMACION_INSUFICIENTE.value]
    confusion_matrix = {c: {c2: 0 for c2 in classes} for c in classes}

    schema_valid_count = 0
    hallucination_count = 0
    total_citations_checked = 0
    score_diffs = []
    latencies_ms = []

    for s in samples:
        doc = parse_sample_to_extracted_doc(s)
        gt = s["ground_truth"]
        gt_verdict = gt["verdict"]

        t0 = time.perf_counter()
        eval_result = await evaluator.evaluate_document(doc)
        dt = (time.perf_counter() - t0) * 1000
        latencies_ms.append(dt)

        pred_verdict = (
            eval_result["verdict"].value
            if hasattr(eval_result["verdict"], "value")
            else str(eval_result["verdict"])
        )
        pred_score = eval_result["total_score"]

        # Validate schema compliance
        if (
            "verdict" in eval_result
            and "total_score" in eval_result
            and "criteria_scores" in eval_result
            and "recommendations" in eval_result
        ):
            schema_valid_count += 1

        # Check citations for hallucination
        for c in eval_result.get("criteria_scores", []):
            citations = c.citations if hasattr(c, "citations") else c.get("citations", [])
            for p in citations:
                total_citations_checked += 1
                if p < 1 or p > doc.page_count:
                    hallucination_count += 1

        if gt_verdict in confusion_matrix and pred_verdict in confusion_matrix[gt_verdict]:
            confusion_matrix[gt_verdict][pred_verdict] += 1

        if gt_verdict != VerdictType.INFORMACION_INSUFICIENTE.value:
            gt_score = gt.get("total_score", 0.0)
            score_diffs.append(abs(pred_score - gt_score))

        match = pred_verdict == gt_verdict
        results.append(
            {
                "id": s["id"],
                "title": s["title"],
                "expected": gt_verdict,
                "predicted": pred_verdict,
                "score_pred": pred_score,
                "match": match,
                "latency_ms": round(dt, 2),
            }
        )

    # Calculate metrics
    total = len(samples)
    correct = sum(1 for r in results if r["match"])
    accuracy = correct / total if total > 0 else 0.0

    # Per-class metrics
    per_class_metrics = {}
    macro_p, macro_r, macro_f1 = 0.0, 0.0, 0.0

    for c in classes:
        tp = confusion_matrix[c][c]
        fp = sum(confusion_matrix[other][c] for other in classes if other != c)
        fn = sum(confusion_matrix[c][other] for other in classes if other != c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_class_metrics[c] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": sum(confusion_matrix[c].values()),
        }
        macro_p += precision
        macro_r += recall
        macro_f1 += f1

    macro_p /= len(classes)
    macro_r /= len(classes)
    macro_f1 /= len(classes)

    mae = sum(score_diffs) / len(score_diffs) if score_diffs else 0.0
    schema_validity = (schema_valid_count / total) * 100
    hallucination_rate = (hallucination_count / total_citations_checked * 100) if total_citations_checked > 0 else 0.0
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

    benchmark_summary = {
        "samples_evaluated": total,
        "correct_predictions": correct,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "mean_absolute_error_score": round(mae, 2),
        "schema_validity_percent": round(schema_validity, 2),
        "hallucination_rate_percent": round(hallucination_rate, 2),
        "avg_latency_ms": round(avg_latency, 2),
        "per_class": per_class_metrics,
        "confusion_matrix": confusion_matrix,
        "individual_results": results,
    }

    OUTPUT_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("           RESULTADOS DE BENCHMARK DE EVALUACIÓN LOCAL           ")
    print("=" * 65)
    print(f" Muestras Totales:               {total}")
    print(f" Exactitud (Accuracy):           {accuracy * 100:.2f}% ({correct}/{total})")
    print(f" Macro F1-Score:                 {macro_f1:.4f}")
    print(f" Macro Precisión:                {macro_p:.4f}")
    print(f" Macro Recall:                   {macro_r:.4f}")
    print(f" Error Medio Absoluto (MAE):     {mae:.2f} pts")
    print(f" Tasa de Validez de Esquema:     {schema_validity:.1f}%")
    print(f" Tasa de Alucinación de Citas:   {hallucination_rate:.2f}%")
    print(f" Latencia Media por Documento:   {avg_latency:.2f} ms")
    print("-" * 65)
    print(" Métricas por Clase:")
    for c, m in per_class_metrics.items():
        print(f"   [{c:25}] P: {m['precision']:.3f} | R: {m['recall']:.3f} | F1: {m['f1_score']:.3f} (N={m['support']})")
    print("=" * 65)
    print(f"Reporte detallado guardado en: {OUTPUT_METRICS_FILE}\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
