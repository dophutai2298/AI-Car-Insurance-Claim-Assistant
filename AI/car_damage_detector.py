from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO


class CarDamageDetector:
    """
    Detect car parts + damages and calculate damage percentage.

    Input:
        image_path

    Output:
        annotated_image: numpy.ndarray
        final_result: list[dict]

    Annotated image is automatically saved to output_dir.
    """

    def __init__(
        self,
        part_model_path: str,
        damage_model_path: str,
        output_dir: str = "output",
        part_conf: float = 0.25,
        damage_conf: float = 0.20,
        min_damage_percent: float = 3.0,
        imgsz: int = 640,
        device: str = "cpu",
    ):
        # =====================================================
        # MODELS
        # =====================================================

        self.part_model = YOLO(part_model_path)
        self.damage_model = YOLO(damage_model_path)

        # =====================================================
        # CONFIG
        # =====================================================

        self.part_conf = part_conf
        self.damage_conf = damage_conf
        self.min_damage_percent = min_damage_percent

        self.imgsz = imgsz
        self.device = device

        # =====================================================
        # OUTPUT DIRECTORY
        # =====================================================

        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # =====================================================
        # VISUAL CONFIG
        # =====================================================

        self.part_alpha = 0.35
        self.damage_alpha = 0.50

        # OpenCV = BGR
        self.damage_color = (0, 0, 255)

        self.part_colors = [
            (255, 0, 0),
            (0, 255, 0),
            (0, 255, 255),
            (255, 0, 255),
            (255, 255, 0),
            (0, 128, 255),
            (128, 0, 255),
            (255, 128, 0),
            (128, 255, 0),
            (255, 0, 128),
            (0, 255, 128),
            (128, 128, 255),
            (255, 128, 128),
            (128, 255, 255),
            (255, 255, 128),
            (64, 128, 255),
            (255, 64, 128),
            (128, 64, 255),
            (64, 255, 128),
            (200, 120, 50),
            (50, 200, 120),
        ]

    # =========================================================
    # PUBLIC METHOD
    # =========================================================

    def predict(self, image_path: str):

        image_path = Path(image_path)

        # =====================================================
        # READ IMAGE
        # =====================================================

        image = cv2.imread(
            str(image_path)
        )

        if image is None:
            raise ValueError(
                f"Không đọc được ảnh: {image_path}"
            )

        height, width = image.shape[:2]

        # =====================================================
        # PART PREDICTION
        # =====================================================

        part_result = self.part_model.predict(
            source=str(image_path),
            imgsz=self.imgsz,
            conf=self.part_conf,
            device=self.device,
            verbose=False
        )[0]

        # =====================================================
        # DAMAGE PREDICTION
        # =====================================================

        damage_result = self.damage_model.predict(
            source=str(image_path),
            imgsz=self.imgsz,
            conf=self.damage_conf,
            device=self.device,
            verbose=False
        )[0]

        # =====================================================
        # DAMAGE MASK
        # =====================================================

        damage_instances, damage_mask_total = (
            self._process_damage(
                damage_result,
                width,
                height
            )
        )

        # =====================================================
        # NO PART MASK
        # =====================================================

        if part_result.masks is None:

            output = self._draw_damage_only(
                image,
                damage_mask_total
            )

            output_path = self._save_image(
                output,
                image_path
            )

            print(
                f"Saved: {output_path}"
            )

            return output, []

        # =====================================================
        # ANALYZE PARTS
        # =====================================================

        parts_info = self._analyze_parts(
            part_result=part_result,
            damage_instances=damage_instances,
            damage_mask_total=damage_mask_total,
            width=width,
            height=height
        )

        # =====================================================
        # SORT HIGHEST DAMAGE FIRST
        # =====================================================

        parts_info = sorted(
            parts_info,
            key=lambda item:
                item["damage_percent"],
            reverse=True
        )

        # =====================================================
        # DRAW RESULT
        # =====================================================

        annotated_image = self._draw_result(
            image=image,
            parts_info=parts_info,
            damage_mask_total=damage_mask_total
        )

        # =====================================================
        # FINAL RESULT
        # =====================================================

        final_result = self._build_final_result(
            parts_info
        )

        # =====================================================
        # SAVE
        # =====================================================

        output_path = self._save_image(
            annotated_image,
            image_path
        )

        print()
        print("====================================")
        print("CAR DAMAGE RESULT")
        print("====================================")

        for item in final_result:
            print(item)

        print()
        print(
            f"Annotated image saved: {output_path}"
        )

        return annotated_image, final_result

    # =========================================================
    # PROCESS DAMAGE
    # =========================================================

    def _process_damage(
        self,
        damage_result,
        width,
        height
    ):

        damage_mask_total = np.zeros(
            (height, width),
            dtype=np.uint8
        )

        damage_instances = []

        # Không detect damage
        if damage_result.masks is None:

            return (
                damage_instances,
                damage_mask_total
            )

        damage_masks = (
            damage_result
            .masks
            .data
            .cpu()
            .numpy()
        )

        for i, damage_mask in enumerate(
            damage_masks
        ):

            # ================================================
            # CLASS
            # ================================================

            cls_id = int(
                damage_result.boxes.cls[i]
            )

            damage_name = (
                self.damage_model.names[
                    cls_id
                ]
            )

            # ================================================
            # RESIZE MASK
            # ================================================

            damage_mask = cv2.resize(
                damage_mask,
                (width, height),
                interpolation=cv2.INTER_NEAREST
            )

            damage_mask = (
                damage_mask > 0.5
            ).astype(np.uint8)

            # ================================================
            # STORE
            # ================================================

            damage_instances.append({
                "name": damage_name,
                "mask": damage_mask
            })

            # ================================================
            # MERGE DAMAGE
            # ================================================

            damage_mask_total = np.maximum(
                damage_mask_total,
                damage_mask
            )

        return (
            damage_instances,
            damage_mask_total
        )

    # =========================================================
    # ANALYZE PARTS
    # =========================================================

    def _analyze_parts(
        self,
        part_result,
        damage_instances,
        damage_mask_total,
        width,
        height
    ):

        parts_info = []

        part_masks = (
            part_result
            .masks
            .data
            .cpu()
            .numpy()
        )

        for i, part_mask in enumerate(
            part_masks
        ):

            # ================================================
            # PART CLASS
            # ================================================

            cls_id = int(
                part_result.boxes.cls[i]
            )

            part_name = (
                self.part_model.names[
                    cls_id
                ]
            )

            # ================================================
            # RESIZE MASK
            # ================================================

            part_mask = cv2.resize(
                part_mask,
                (width, height),
                interpolation=cv2.INTER_NEAREST
            )

            part_mask = (
                part_mask > 0.5
            ).astype(np.uint8)

            # ================================================
            # PART AREA
            # ================================================

            part_pixels = np.count_nonzero(
                part_mask
            )

            if part_pixels == 0:
                continue

            # ================================================
            # TOTAL DAMAGE ON PART
            #
            # PART ∩ ALL DAMAGE
            # ================================================

            damaged_area = np.logical_and(
                part_mask > 0,
                damage_mask_total > 0
            )

            damage_pixels = np.count_nonzero(
                damaged_area
            )

            damage_percent = (
                damage_pixels
                / part_pixels
                * 100
            )

            # ================================================
            # IGNORE VERY SMALL DAMAGE
            # ================================================

            if (
                damage_percent
                < self.min_damage_percent
            ):
                continue

            # ================================================
            # DAMAGE TYPES
            # ================================================

            damage_types = {}

            for damage in damage_instances:

                intersection = np.logical_and(
                    part_mask > 0,
                    damage["mask"] > 0
                )

                intersection_pixels = (
                    np.count_nonzero(
                        intersection
                    )
                )

                if intersection_pixels == 0:
                    continue

                damage_name = (
                    damage["name"]
                )

                if damage_name not in damage_types:

                    damage_types[
                        damage_name
                    ] = {
                        "pixels": 0
                    }

                damage_types[
                    damage_name
                ]["pixels"] += (
                    intersection_pixels
                )

            # ================================================
            # DAMAGE % PER TYPE
            # ================================================

            for damage_name in damage_types:

                type_pixels = (
                    damage_types[
                        damage_name
                    ]["pixels"]
                )

                damage_types[
                    damage_name
                ]["percent"] = (
                    type_pixels
                    / part_pixels
                    * 100
                )

            # ================================================
            # MAIN DAMAGE
            # ================================================

            if damage_types:

                main_damage = max(
                    damage_types.items(),
                    key=lambda item:
                        item[1]["pixels"]
                )[0]

            else:

                main_damage = "Unknown"

            # ================================================
            # CENTER FOR LABEL LINE
            # ================================================

            ys, xs = np.where(
                part_mask > 0
            )

            if len(xs) == 0:
                continue

            center = (
                int(np.mean(xs)),
                int(np.mean(ys))
            )

            # ================================================
            # SAVE INTERNAL INFORMATION
            # ================================================

            parts_info.append({
                "cls_id":
                    cls_id,

                "part_name":
                    part_name,

                "part_mask":
                    part_mask,

                "damage_percent":
                    float(damage_percent),

                "damage_types":
                    damage_types,

                "main_damage":
                    main_damage,

                "center":
                    center
            })

        return parts_info

    # =========================================================
    # DRAW RESULT
    # =========================================================

    def _draw_result(
        self,
        image,
        parts_info,
        damage_mask_total
    ):

        output = image.copy()

        # =====================================================
        # PART MASK OVERLAY
        # =====================================================

        for item in parts_info:

            mask = (
                item["part_mask"] > 0
            )

            cls_id = item["cls_id"]

            color = self.part_colors[
                cls_id
                % len(self.part_colors)
            ]

            overlay = np.zeros_like(
                output
            )

            overlay[:] = color

            output[mask] = cv2.addWeighted(
                output[mask],
                1 - self.part_alpha,
                overlay[mask],
                self.part_alpha,
                0
            )

        # =====================================================
        # DAMAGE OVERLAY
        # =====================================================

        damage_mask = (
            damage_mask_total > 0
        )

        if np.any(damage_mask):

            damage_overlay = np.zeros_like(
                output
            )

            damage_overlay[:] = (
                self.damage_color
            )

            output[
                damage_mask
            ] = cv2.addWeighted(
                output[damage_mask],
                1 - self.damage_alpha,
                damage_overlay[
                    damage_mask
                ],
                self.damage_alpha,
                0
            )

        # =====================================================
        # DAMAGE CONTOUR
        # =====================================================

        contours, _ = cv2.findContours(
            damage_mask_total,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        cv2.drawContours(
            output,
            contours,
            -1,
            self.damage_color,
            1
        )

        # =====================================================
        # LABELS
        #
        # Không bbox
        # =====================================================

        self._draw_labels(
            output,
            parts_info
        )

        return output

    # =========================================================
    # DRAW LABELS
    # =========================================================

    def _draw_labels(
        self,
        image,
        parts_info
    ):

        height, width = image.shape[:2]

        # =====================================================
        # AUTO FONT SIZE
        # =====================================================

        if width < 400:

            font_scale = 0.30
            thickness = 1
            padding_x = 4
            padding_y = 3
            gap = 3

        elif width < 800:

            font_scale = 0.40
            thickness = 1
            padding_x = 5
            padding_y = 4
            gap = 4

        else:

            font_scale = 0.55
            thickness = 1
            padding_x = 7
            padding_y = 5
            gap = 5

        font = cv2.FONT_HERSHEY_SIMPLEX

        current_y = 5

        # =====================================================
        # EACH PART
        # =====================================================

        for item in parts_info:

            cls_id = item["cls_id"]

            color = self.part_colors[
                cls_id
                % len(self.part_colors)
            ]

            label = (
                f'{item["part_name"]}: '
                f'{item["damage_percent"]:.1f}% '
                f'[{item["main_damage"]}]'
            )

            (
                (text_width, text_height),
                baseline
            ) = cv2.getTextSize(
                label,
                font,
                font_scale,
                thickness
            )

            box_width = (
                text_width
                + padding_x * 2
            )

            box_height = (
                text_height
                + baseline
                + padding_y * 2
            )

            # Không đủ chỗ
            if (
                current_y + box_height
                >= height
            ):
                break

            # ================================================
            # LABEL BACKGROUND
            # ================================================

            x = 5
            y = current_y

            box_width = min(
                box_width,
                width - x - 2
            )

            cv2.rectangle(
                image,
                (x, y),
                (
                    x + box_width,
                    y + box_height
                ),
                color,
                -1
            )

            # ================================================
            # TEXT
            # ================================================

            cv2.putText(
                image,
                label,
                (
                    x + padding_x,
                    y
                    + padding_y
                    + text_height
                ),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA
            )

            # ================================================
            # LINE TO PART
            # ================================================

            center_x, center_y = (
                item["center"]
            )

            cv2.line(
                image,
                (
                    x + box_width,
                    y + box_height // 2
                ),
                (
                    center_x,
                    center_y
                ),
                color,
                1,
                cv2.LINE_AA
            )

            # ================================================
            # CENTER DOT
            # ================================================

            cv2.circle(
                image,
                (
                    center_x,
                    center_y
                ),
                3,
                color,
                -1
            )

            current_y += (
                box_height + gap
            )

    # =========================================================
    # DAMAGE ONLY
    # =========================================================

    def _draw_damage_only(
        self,
        image,
        damage_mask_total
    ):

        output = image.copy()

        damage_mask = (
            damage_mask_total > 0
        )

        if not np.any(damage_mask):
            return output

        overlay = np.zeros_like(
            output
        )

        overlay[:] = self.damage_color

        output[
            damage_mask
        ] = cv2.addWeighted(
            output[damage_mask],
            1 - self.damage_alpha,
            overlay[damage_mask],
            self.damage_alpha,
            0
        )

        return output

    # =========================================================
    # BUILD FINAL RESULT
    #
    # Không:
    # - confidence
    # - pixels
    # - bbox
    # =========================================================

    def _build_final_result(
        self,
        parts_info
    ):

        final_result = []

        for item in parts_info:

            damage_types = []

            # ================================================
            # DAMAGE TYPES
            # ================================================

            sorted_damage = sorted(
                item[
                    "damage_types"
                ].items(),
                key=lambda x:
                    x[1]["percent"],
                reverse=True
            )

            for (
                damage_name,
                damage_info
            ) in sorted_damage:

                damage_types.append({
                    "type":
                        damage_name,

                    "percent":
                        round(
                            damage_info[
                                "percent"
                            ],
                            2
                        )
                })

            # ================================================
            # RESULT
            # ================================================

            final_result.append({
                "part":
                    item["part_name"],

                "main_damage":
                    item["main_damage"],

                "damage_percent":
                    round(
                        item[
                            "damage_percent"
                        ],
                        2
                    ),

                "damage_types":
                    damage_types
            })

        return final_result

    # =========================================================
    # SAVE IMAGE
    # =========================================================

    def _save_image(
        self,
        image,
        original_path
    ):

        output_path = (
            self.output_dir
            / (
                original_path.stem
                + "_result.jpg"
            )
        )

        success = cv2.imwrite(
            str(output_path),
            image
        )

        if not success:

            raise RuntimeError(
                f"Không lưu được ảnh: "
                f"{output_path}"
            )

        return output_path