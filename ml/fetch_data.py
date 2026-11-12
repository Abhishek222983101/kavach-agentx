"""Downloads the two public datasets used by the guard (both Apache-2.0) into ml/data/raw (not committed)."""
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent / "data" / "raw"
FILES = {
    "deepset_train.parquet": "https://huggingface.co/datasets/deepset/prompt-injections/resolve/main/data/train-00000-of-00001-9564e8b05b4757ab.parquet",
    "deepset_test.parquet": "https://huggingface.co/datasets/deepset/prompt-injections/resolve/main/data/test-00000-of-00001-701d16158af87368.parquet",
    "jailbreak_test.csv": "https://huggingface.co/datasets/jackhhao/jailbreak-classification/resolve/main/balanced/jailbreak_dataset_test_balanced.csv",
}
if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        urllib.request.urlretrieve(url, RAW / name)  # noqa: S310 - fixed https URLs to Hugging Face
        print("ok", name)
