from car_damage_detector import CarDamageDetector


detector = CarDamageDetector(
    part_model_path="models/car_part.pt",
    damage_model_path="models/car_damage.pt",

    output_dir="outputs",

    part_conf=0.25,
    damage_conf=0.15,

    min_damage_percent=3.0,

    device="cpu"
)


annotated_image, final_result = detector.predict(
    "images/5608f21b-acc2-4c14-abbb-26da04176d17.jpg"
)


print("\nFINAL RESULT:")

for item in final_result:
    print(item) 