# concrete mix design calculations - BS/DOE (British / Department of Environment) method

# standard deviation by grade bracket - same style as IS, for target mean strength margin
def get_std_deviation(fck):
    if fck <= 15:
        return 3.5
    elif fck <= 25:
        return 4.0
    elif fck <= 35:
        return 5.0
    elif fck <= 45:
        return 5.0
    return 6.0


# free water content (kg/m3) - uncrushed aggregate baseline, by slump category + max agg size
# crushed aggregate needs extra water (approx +25 kg/m3) added separately below
water_table = {
    "low":    {10: 150, 20: 135, 40: 115},   # slump 25-50mm
    "medium": {10: 180, 20: 170, 40: 155},   # slump 75-100mm
    "high":   {10: 205, 20: 190, 40: 175},   # slump 150-175mm
}

CRUSHED_WATER_EXTRA = 25   # kg/m3 extra water needed for crushed (angular) aggregate

# free water/cement ratio vs target mean strength - approximate DOE strength curve (OPC, 28 day)
strength_wc_table = [
    (15, 0.85), (20, 0.74), (25, 0.65), (30, 0.58),
    (35, 0.52), (40, 0.47), (45, 0.43), (50, 0.38),
]

# durability limits by exposure - same structure as IS 456 based tables
exposure_wc_limit = {
    "mild": 0.55,
    "moderate": 0.50,
    "severe": 0.45,
    "very_severe": 0.45,
    "extreme": 0.40,
}

exposure_min_cement = {
    "mild": 300,
    "moderate": 300,
    "severe": 320,
    "very_severe": 340,
    "extreme": 360,
}

exposure_air = {
    "mild": 1.0,
    "moderate": 1.5,
    "severe": 1.5,
    "very_severe": 2.0,
    "extreme": 2.0,
}

# fine aggregate as % of total aggregate (by mass) - by max size and sand zone
# reuses the same Zone I-IV concept as IS 10262 for consistency
fine_percentage_table = {
    10: {"I": 0.53, "II": 0.47, "III": 0.42, "IV": 0.38},
    20: {"I": 0.42, "II": 0.37, "III": 0.33, "IV": 0.30},
    40: {"I": 0.33, "II": 0.30, "III": 0.27, "IV": 0.24},
}

# assumed wet concrete density (kg/m3) - simplification of DOE's density chart,
# which normally varies with combined aggregate relative density
ASSUMED_WET_DENSITY = 2350

cement_sg = 3.15
fine_sg = 2.65
coarse_sg = 2.65


def get_slump_category(slump):
    if slump <= 50:
        return "low"
    elif slump <= 100:
        return "medium"
    return "high"


def get_water_content(slump, max_agg_size, aggregate_type):
    category = get_slump_category(slump)
    water = water_table[category][max_agg_size]
    if aggregate_type == "crushed":
        water += CRUSHED_WATER_EXTRA
    return water


def get_wc_from_strength(target_strength):
    # linear interpolation on the strength -> free w/c curve
    table = sorted(strength_wc_table, key=lambda x: x[0])
    if target_strength >= table[-1][0]:
        return table[-1][1]
    if target_strength <= table[0][0]:
        return table[0][1]
    for i in range(len(table) - 1):
        s1, r1 = table[i]
        s2, r2 = table[i + 1]
        if s1 <= target_strength <= s2:
            return round(r1 + (r2 - r1) * (target_strength - s1) / (s2 - s1), 3)


def calculate_mix(fck, slump, max_agg_size, exposure, zone, aggregate_type,
                   fine_moisture=0.0, fine_absorption=0.0,
                   coarse_moisture=0.0, coarse_absorption=0.0):

    std_dev = get_std_deviation(fck)
    target_mean_strength = fck + 1.64 * std_dev

    # free water content, adjusted for aggregate shape
    water = get_water_content(slump, max_agg_size, aggregate_type)

    # free w/c ratio - stricter (lower) of strength-based curve and durability limit
    wc_strength = get_wc_from_strength(target_mean_strength)
    wc_limit = exposure_wc_limit[exposure]
    wc_final = min(wc_strength, wc_limit)

    air_percent = exposure_air[exposure]

    # cement content - higher of (water/wc) or minimum required for exposure
    cement_from_wc = water / wc_final
    min_cement = exposure_min_cement[exposure]
    cement = max(cement_from_wc, min_cement)

    # total aggregate from assumed wet density (mass-basis, not absolute volume)
    total_aggregate = ASSUMED_WET_DENSITY - cement - water
    if total_aggregate < 0:
        total_aggregate = 0   # safety guard against unrealistic inputs

    fine_fraction = fine_percentage_table[max_agg_size][zone]
    fine_weight = total_aggregate * fine_fraction
    coarse_weight = total_aggregate - fine_weight

    # moisture correction - same style as ACI/IS modules
    fine_free_moisture = fine_moisture - fine_absorption
    coarse_free_moisture = coarse_moisture - coarse_absorption

    fine_field_weight = fine_weight * (1 + fine_moisture / 100)
    coarse_field_weight = coarse_weight * (1 + coarse_moisture / 100)

    water_from_fine = fine_weight * (fine_free_moisture / 100)
    water_from_coarse = coarse_weight * (coarse_free_moisture / 100)

    field_water = water - water_from_fine - water_from_coarse

    return {
        "method": "BS/DOE",
        "target_mean_strength": round(target_mean_strength, 1),
        "std_deviation": std_dev,
        "slump_category": get_slump_category(slump),
        "wc_strength": round(wc_strength, 3),
        "wc_limit": wc_limit,
        "wc_final": round(wc_final, 3),
        "min_cement_required": min_cement,
        "air_percent": air_percent,
        "coarse_fraction": round(1 - fine_fraction, 3),

        "water_batch": round(water, 1),
        "cement_batch": round(cement, 1),
        "coarse_batch": round(coarse_weight, 1),
        "fine_batch": round(fine_weight, 1),

        "cement_field": round(cement, 1),
        "fine_field": round(fine_field_weight, 1),
        "coarse_field": round(coarse_field_weight, 1),
        "water_field": round(field_water, 1),
    }
