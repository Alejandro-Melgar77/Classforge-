import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATASET_FILE = BASE_DIR / "ml" / "data" / "reviews_dataset.jsonl"
BENCHMARK_FILE = BASE_DIR / "ml" / "eval" / "benchmark_results.json"
TRAIN_CONFIG_FILE = BASE_DIR / "ml" / "train" / "training_config.json"


def test_ml_dataset_structure_and_volume():
    """Validates dataset has at least 20 samples with full annotations."""
    assert DATASET_FILE.exists(), f"Dataset file not found at {DATASET_FILE}"

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        samples = [json.loads(line) for line in f if line.strip()]

    assert len(samples) >= 20, f"Expected >= 20 samples, got {len(samples)}"

    valid_verdicts = {"APROBADO", "RECHAZADO", "INFORMACION_INSUFICIENTE"}
    verdict_counts = {v: 0 for v in valid_verdicts}

    for s in samples:
        assert "id" in s and s["id"]
        assert "title" in s
        assert "document_text" in s
        assert "page_count" in s and s["page_count"] >= 1
        assert "ground_truth" in s

        gt = s["ground_truth"]
        assert "verdict" in gt
        assert gt["verdict"] in valid_verdicts
        verdict_counts[gt["verdict"]] += 1
        assert "total_score" in gt
        assert "has_sufficient_text" in gt

    # Ensure all 3 classes are represented
    for v, count in verdict_counts.items():
        assert count >= 4, f"Class {v} underrepresented with only {count} samples"


def test_benchmark_metrics_quality_criteria():
    """Validates benchmark execution results meet production quality thresholds."""
    assert BENCHMARK_FILE.exists(), f"Benchmark results file not found at {BENCHMARK_FILE}"

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["samples_evaluated"] >= 20
    assert metrics["accuracy"] >= 0.85, f"Expected accuracy >= 0.85, got {metrics['accuracy']}"
    assert metrics["macro_f1"] >= 0.85, f"Expected macro F1 >= 0.85, got {metrics['macro_f1']}"
    assert metrics["schema_validity_percent"] == 100.0
    assert metrics["hallucination_rate_percent"] == 0.0
    assert metrics["avg_latency_ms"] < 1000.0, f"Latency too high: {metrics['avg_latency_ms']} ms"


def test_training_config_and_hardware_profile():
    """Validates reproducible LoRA training configuration and honest hardware metadata."""
    assert TRAIN_CONFIG_FILE.exists(), f"Training config not found at {TRAIN_CONFIG_FILE}"

    with open(TRAIN_CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    assert cfg["version"] == "1.0.0"
    assert "lora_parameters" in cfg
    assert cfg["lora_parameters"]["r"] == 16
    assert cfg["lora_parameters"]["lora_alpha"] == 32
    assert "hardware_environment" in cfg
    # On this machine CUDA is False
    assert cfg["hardware_environment"]["cuda_available"] is False
    assert cfg["hardware_environment"]["device"] == "CPU"
