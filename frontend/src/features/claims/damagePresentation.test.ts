import { describe, expect, it } from "vitest";
import i18n from "../../i18n";
import {
  damageTypeLabel,
  localizeReviewText,
  normalizeVehiclePart,
  normalizeDamageType,
  vehiclePartLabel,
} from "./damagePresentation";

describe("vehicle damage presentation", () => {
  it.each(["Front-Bumper", "front_bumper", " front bumper ", "FrontBumper"])(
    "normalizes %s without changing the business value",
    (part) => {
      expect(normalizeVehiclePart(part)).toBe("front_bumper");
      expect(vehiclePartLabel(part, "vi-VN")).toBe("Cản trước");
      expect(vehiclePartLabel(part, "en-US")).toBe("Front Bumper");
    },
  );

  it.each([
    ["Fender", "Vè chắn bùn / Tai xe"],
    ["Hood", "Nắp ca-pô"],
    ["Windshield", "Kính chắn gió"],
    ["rear_left_door", "Cửa sau bên trái"],
    ["front_left_fender", "Vè chắn bùn trước bên trái"],
    ["rear_bumper", "Cản sau"],
  ])("translates %s", (part, label) => {
    expect(vehiclePartLabel(part, "vi")).toBe(label);
  });

  it.each([
    ["corrosion", "Corrosion", "Ăn mòn / Rỉ sét"],
    ["crack", "Crack", "Nứt"],
    ["dent", "Dent", "Móp / Lõm"],
    ["glass shatter", "Glass Shatter", "Vỡ kính"],
    ["lamp broken", "Lamp Broken", "Vỡ đèn"],
    ["scratch", "Scratch", "Trầy xước"],
    ["tire flat", "Tire Flat", "Xẹp lốp"],
  ])("translates damage type %s in both languages", (value, en, vi) => {
    expect(damageTypeLabel(value, "en-US")).toBe(en);
    expect(damageTypeLabel(value, "vi-VN")).toBe(vi);
  });

  it.each([
    "glass shatter",
    "Glass-Shatter",
    "GLASS_SHATTER",
    " GlassShatter ",
  ])("normalizes damage type %s to a stable filter key", (value) => {
    expect(normalizeDamageType(value)).toBe("glass_shatter");
    expect(damageTypeLabel(value, "vi")).toBe("Vỡ kính");
  });

  it("keeps unknown and missing damage types readable", () => {
    expect(damageTypeLabel("custom_damage", "vi")).toBe("Custom Damage");
    expect(damageTypeLabel("constructor", "vi")).toBe("Constructor");
    expect(damageTypeLabel(null, "vi")).toBe("");
    expect(damageTypeLabel("  ", "en")).toBe("");
  });

  it("supports common aliases and a readable fallback for unmapped parts", () => {
    expect(vehiclePartLabel("bonnet", "vi")).toBe("Nắp ca-pô");
    expect(vehiclePartLabel("custom_panel", "vi")).toBe("Custom Panel");
    expect(vehiclePartLabel("constructor", "vi")).toBe("Constructor");
    expect(vehiclePartLabel(null, "vi")).toBe("");
    expect(vehiclePartLabel("  ", "en")).toBe("");
  });

  it.each(["en", "vi"])(
    "renders assessment codes as meaningful %s labels inside AI prose",
    async (language) => {
      await i18n.changeLanguage(language);
      const text =
        "REPAIR_LIKELY / REPLACEMENT_LIKELY / MANUAL_INSPECTION_REQUIRED / NO_DAMAGE.";
      expect(localizeReviewText(text, i18n.t)).toBe(
        [
          "REPAIR_LIKELY",
          "REPLACEMENT_LIKELY",
          "MANUAL_INSPECTION_REQUIRED",
          "NO_DAMAGE",
        ]
          .map((code) => i18n.t(`analysis.assessment.${code}`))
          .join(" / ") + ".",
      );
      expect(text).toContain("REPAIR_LIKELY");
      expect(
        localizeReviewText("prefix_REPAIR_LIKELY UNKNOWN_STATUS", i18n.t),
      ).toBe("prefix_REPAIR_LIKELY UNKNOWN_STATUS");
    },
  );
});
