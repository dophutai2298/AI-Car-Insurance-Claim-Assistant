import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
AI_DIR = PROJECT_DIR / "AI"

DEFAULT_IMAGE_PATH = BACKEND_DIR / "package" / "sample_data" / "xe_ngang.png"
PART_MODEL_PATH = AI_DIR / "models" / "car_part.pt"
DAMAGE_MODEL_PATH = AI_DIR / "models" / "car_damage.pt"
OUTPUT_DIR = BACKEND_DIR / "outputs" / "car_damage_detector"


def existing_file(path: str) -> Path:
    resolved_path = Path(path).expanduser().resolve()
    if not resolved_path.is_file():
        raise argparse.ArgumentTypeError(f"File does not exist: {resolved_path}")
    return resolved_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local CarDamageDetector.")
    parser.add_argument(
        "--image",
        type=existing_file,
        default=DEFAULT_IMAGE_PATH,
        help=f"Input image path (default: {DEFAULT_IMAGE_PATH})",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help='Inference device, for example "cpu" or "0" for the first GPU.',
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} was not found: {path}")


def main() -> None:
    args = parse_args()
    image_path = Path(args.image).resolve()

    require_file(image_path, "Sample image")
    require_file(PART_MODEL_PATH, "Car-part model")
    require_file(DAMAGE_MODEL_PATH, "Car-damage model")

    sys.path.insert(0, str(AI_DIR))
    from car_damage_detector import CarDamageDetector

    detector = CarDamageDetector(
        part_model_path=str(PART_MODEL_PATH),
        damage_model_path=str(DAMAGE_MODEL_PATH),
        output_dir=str(OUTPUT_DIR),
        part_conf=0.25,
        damage_conf=0.15,
        min_damage_percent=3.0,
        imgsz=640,
        device=args.device,
    )

    annotated_image, result = detector.predict(str(image_path))
    annotated_path = OUTPUT_DIR / f"{image_path.stem}_result.jpg"

    print("\nStructured damage result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nAnnotated image shape: {annotated_image.shape}")
    print(f"Annotated image: {annotated_path}")


if __name__ == "__main__":
    main()
