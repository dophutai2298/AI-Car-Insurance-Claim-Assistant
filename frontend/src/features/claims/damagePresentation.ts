import type { TFunction } from "i18next";

type BilingualLabel = { en: string; vi: string };

export const vehiclePartLabels: Readonly<Record<string, BilingualLabel>> = {
  windshield: { en: "Windshield", vi: "Kính chắn gió" },
  front_windshield: { en: "Front Windshield", vi: "Kính chắn gió trước" },
  rear_windshield: { en: "Rear Windshield", vi: "Kính chắn gió sau" },
  window: { en: "Window", vi: "Kính cửa xe" },
  front_window: { en: "Front Window", vi: "Kính cửa trước" },
  rear_window: { en: "Rear Window", vi: "Kính cửa sau" },
  hood: { en: "Hood", vi: "Nắp ca-pô" },
  trunk: { en: "Trunk", vi: "Nắp cốp" },
  roof: { en: "Roof", vi: "Nóc xe" },
  bumper: { en: "Bumper", vi: "Cản xe" },
  front_bumper: { en: "Front Bumper", vi: "Cản trước" },
  rear_bumper: { en: "Rear Bumper", vi: "Cản sau" },
  fender: { en: "Fender", vi: "Vè chắn bùn / Tai xe" },
  front_fender: { en: "Front Fender", vi: "Vè chắn bùn trước" },
  rear_fender: { en: "Rear Fender", vi: "Vè chắn bùn sau" },
  front_left_fender: {
    en: "Front Left Fender",
    vi: "Vè chắn bùn trước bên trái",
  },
  front_right_fender: {
    en: "Front Right Fender",
    vi: "Vè chắn bùn trước bên phải",
  },
  rear_left_fender: { en: "Rear Left Fender", vi: "Vè chắn bùn sau bên trái" },
  rear_right_fender: {
    en: "Rear Right Fender",
    vi: "Vè chắn bùn sau bên phải",
  },
  door: { en: "Door", vi: "Cửa xe" },
  front_door: { en: "Front Door", vi: "Cửa trước" },
  rear_door: { en: "Rear Door", vi: "Cửa sau" },
  front_left_door: { en: "Front Left Door", vi: "Cửa trước bên trái" },
  front_right_door: { en: "Front Right Door", vi: "Cửa trước bên phải" },
  rear_left_door: { en: "Rear Left Door", vi: "Cửa sau bên trái" },
  rear_right_door: { en: "Rear Right Door", vi: "Cửa sau bên phải" },
  headlight: { en: "Headlight", vi: "Đèn pha" },
  left_headlight: { en: "Left Headlight", vi: "Đèn pha bên trái" },
  right_headlight: { en: "Right Headlight", vi: "Đèn pha bên phải" },
  taillight: { en: "Taillight", vi: "Đèn hậu" },
  left_taillight: { en: "Left Taillight", vi: "Đèn hậu bên trái" },
  right_taillight: { en: "Right Taillight", vi: "Đèn hậu bên phải" },
  mirror: { en: "Mirror", vi: "Gương chiếu hậu" },
  side_mirror: { en: "Side Mirror", vi: "Gương chiếu hậu bên ngoài" },
  left_mirror: { en: "Left Mirror", vi: "Gương chiếu hậu bên trái" },
  right_mirror: { en: "Right Mirror", vi: "Gương chiếu hậu bên phải" },
  grille: { en: "Grille", vi: "Lưới tản nhiệt" },
  wheel: { en: "Wheel", vi: "Bánh xe" },
  tire: { en: "Tire", vi: "Lốp xe" },
  rocker_panel: { en: "Rocker Panel", vi: "Ốp sườn xe" },
  quarter_panel: { en: "Quarter Panel", vi: "Tấm hông sau" },
};

const partAliases: Readonly<Record<string, string>> = {
  windscreen: "windshield",
  front_windscreen: "front_windshield",
  rear_windscreen: "rear_windshield",
  back_windshield: "rear_windshield",
  back_bumper: "rear_bumper",
  bonnet: "hood",
  boot: "trunk",
  trunk_lid: "trunk",
  boot_lid: "trunk",
  headlamp: "headlight",
  tail_light: "taillight",
  tail_lamp: "taillight",
  wing_mirror: "side_mirror",
  wing: "fender",
  tyre: "tire",
};

function normalizeModelLabel(value: string) {
  return value
    .trim()
    .replace(/([a-z])([A-Z])/g, "$1_$2")
    .toLowerCase()
    .replace(/[\s_-]+/g, "_");
}

export function normalizeVehiclePart(value: string) {
  const key = normalizeModelLabel(value);
  return Object.hasOwn(partAliases, key) ? partAliases[key] : key;
}

export function vehiclePartLabel(value: string | null, language: string) {
  if (!value?.trim()) return "";
  const key = normalizeVehiclePart(value);
  const label = Object.hasOwn(vehiclePartLabels, key)
    ? vehiclePartLabels[key]
    : undefined;
  if (label) return label[language.startsWith("vi") ? "vi" : "en"];
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export const damageTypeLabels: Readonly<Record<string, BilingualLabel>> = {
  corrosion: { en: "Corrosion", vi: "Ăn mòn / Rỉ sét" },
  crack: { en: "Crack", vi: "Nứt vỡ" },
  dent: { en: "Dent", vi: "Móp / Lõm" },
  glass_shatter: { en: "Glass Shatter", vi: "Vỡ kính" },
  lamp_broken: { en: "Lamp Broken", vi: "Bể / Vỡ đèn" },
  scratch: { en: "Scratch", vi: "Trầy xước" },
  tire_flat: { en: "Tire Flat", vi: "Xẹp lốp / Thủng lốp" },
};

export function normalizeDamageType(value: string | null) {
  return normalizeModelLabel(value ?? "");
}

export function damageTypeLabel(value: string | null, language: string) {
  const key = normalizeDamageType(value);
  const label = Object.hasOwn(damageTypeLabels, key)
    ? damageTypeLabels[key]
    : undefined;
  if (label) return label[language.startsWith("vi") ? "vi" : "en"];
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

const reviewCodeLabels: Readonly<Record<string, string>> = {
  NO_DAMAGE: "analysis.assessment.NO_DAMAGE",
  REPAIR_LIKELY: "analysis.assessment.REPAIR_LIKELY",
  REPLACEMENT_LIKELY: "analysis.assessment.REPLACEMENT_LIKELY",
  MANUAL_INSPECTION_REQUIRED: "analysis.assessment.MANUAL_INSPECTION_REQUIRED",
  MANUAL_ADJUSTER_REVIEW: "aiReview.humanReviewRequired",
  REVIEW_REQUIRED: "claim.status.REVIEW_REQUIRED",
  SUPPORTS_REPAIR: "pricing.recommendation.SUPPORTS_REPAIR",
  SUPPORTS_REPLACEMENT: "pricing.recommendation.SUPPORTS_REPLACEMENT",
  MANUAL_REVIEW: "pricing.recommendation.MANUAL_REVIEW",
};
const reviewCodePattern = new RegExp(
  `\\b(${Object.keys(reviewCodeLabels).join("|")})\\b`,
  "g",
);

// Presentation only: keep persisted AI text and business identifiers unchanged.
export function localizeReviewText(value: string, t: TFunction) {
  return value.replace(reviewCodePattern, (code) => t(reviewCodeLabels[code]));
}
