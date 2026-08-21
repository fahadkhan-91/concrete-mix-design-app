# concrete mix design calculations - ACI 211.1 method

# water content table (kg/m3) - non air entrained
water_table = {
    "low":    {10: 199, 20: 190, 25: 179, 40: 166},   # slump 25-50
    "medium": {10: 216, 20: 205, 25: 193, 40: 181},   # slump 75-100
    "high":   {10: 228, 20: 216, 25: 202, 40: 190},   # slump 150-175
}

# same but air entrained (jab exposure severe/moderate ho)
water_table_air = {
    "low":    {10: 181, 20: 168, 25: 160, 40: 150},
    "medium": {10: 202, 20: 184, 25: 175, 40: 165},
    "high":   {10: 216, 20: 197, 25: 184, 40: 174},
}

# strength vs w/c ratio, ACI table 6.3.4(a)
wc_table = [
    (40, 0.42),
    (35, 0.47),
    (30, 0.54),
    (25, 0.61),
    (20, 0.69),
    (15, 0.79),
]

# coarse agg volume fraction vs max size + fineness modulus
coarse_agg_table = {
    10: {2.40: 0.50, 2.60: 0.48, 2.80: 0.46, 3.00: 0.44},
    20: {2.40: 0.66, 2.60: 0.64, 2.80: 0.62, 3.00: 0.60},
    25: {2.40: 0.71, 2.60: 0.69, 2.80: 0.67, 3.00: 0.65},
    40: {2.40: 0.75, 2.60: 0.73, 2.80: 0.71, 3.00: 0.69},
}

# exposure ke hisab se air content aur max wc limit
exposure_air = {"mild": 2.0, "moderate": 4.5, "severe": 6.0}
exposure_wc_limit = {"mild": 0.60, "moderate": 0.50, "severe": 0.45}

# assumed values, in kg/m3 or specific gravity
cement_sg = 3.15
fine_sg = 2.65
coarse_sg = 2.65
coarse_dry_density = 1600


def slump_category(slump):
    if slump <= 50:
        return "low"
    elif slump <= 100:
        return "medium"
    return "high"


def get_wc_ratio(fck):
    # simple linear interpolation between table points
    table = sorted(wc_table, key=lambda x: x[0])
    if fck >= table[-1][0]:
        return table[-1][1]
    if fck <= table[0][0]:
        return table[0][1]
    for i in range(len(table) - 1):
        s1, r1 = table[i]
        s2, r2 = table[i + 1]
        if s1 <= fck <= s2:
            return round(r1 + (r2 - r1) * (fck - s1) / (s2 - s1), 3)


def get_coarse_fraction(max_size, fm):
    values = sorted(coarse_agg_table[max_size].keys())
    table = coarse_agg_table[max_size]
    if fm <= values[0]:
        return table[values[0]]
    if fm >= values[-1]:
        return table[values[-1]]
    for i in range(len(values) - 1):
        f1, f2 = values[i], values[i + 1]
        if f1 <= fm <= f2:
            v1, v2 = table[f1], table[f2]
            return round(v1 + (v2 - v1) * (fm - f1) / (f2 - f1), 3)


def calculate_mix(fck, slump, max_agg_size, exposure, fm_sand):
    category = slump_category(slump)

    # air entrained water table use karo agar exposure severe ya moderate ho
    if exposure in ("moderate", "severe"):
        water = water_table_air[category][max_agg_size]
    else:
        water = water_table[category][max_agg_size]

    wc_strength = get_wc_ratio(fck)
    wc_limit = exposure_wc_limit[exposure]
    wc_final = min(wc_strength, wc_limit)   # jo bhi zyada strict ho wo lena hai

    air_percent = exposure_air[exposure]
    cement = water / wc_final

    coarse_fraction = get_coarse_fraction(max_agg_size, fm_sand)
    coarse_weight = coarse_fraction * coarse_dry_density

    # ab volumes nikalna hai, 1m3 = 1000 litre
    vol_cement = cement / (cement_sg * 1000) * 1000
    vol_water = water / 1000 * 1000
    vol_coarse = coarse_weight / (coarse_sg * 1000) * 1000
    vol_air = (air_percent / 100) * 1000

    vol_fine = 1000 - (vol_cement + vol_water + vol_coarse + vol_air)
    fine_weight = (vol_fine / 1000) * fine_sg * 1000

    return {
        "slump_category": category,
        "water": round(water, 1),
        "wc_strength": wc_strength,
        "wc_limit": wc_limit,
        "wc_final": wc_final,
        "cement": round(cement, 1),
        "coarse_fraction": coarse_fraction,
        "coarse": round(coarse_weight, 1),
        "fine": round(fine_weight, 1),
        "air_percent": air_percent,
    }
