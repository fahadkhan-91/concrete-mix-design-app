# concrete mix design calculations - IS 10262:2019 method

# max water content (kg/m3) at 50mm slump - IS 10262 Table 4
water_table_base = {10: 208, 20: 186, 40: 165}

# max w/c ratio by exposure - IS 456 Table 5
exposure_wc_limit = {
    "mild": 0.55,
    "moderate": 0.50,
    "severe": 0.45,
    "very_severe": 0.45,
    "extreme": 0.40,
}

# minimum cement content (kg/m3) by exposure - IS 456 Table 5
exposure_min_cement = {
    "mild": 300,
    "moderate": 300,
    "severe": 320,
    "very_severe": 340,
    "extreme": 360,
}

# air content (%) - approx, same idea as ACI but IS doesn't mandate air entrainment
# as strictly for normal (non-freeze-thaw) climates, so keep modest values
exposure_air = {
    "mild": 1.0,
    "moderate": 1.5,
    "severe": 1.5,
    "very_severe": 2.0,
    "extreme": 2.0,
}

# coarse aggregate volume fraction (of total aggregate volume) - IS 10262 Table 3
# base values at w/c = 0.5, by zone of sand and max aggregate size
coarse_agg_table = {
    10: {"I": 0.44, "II": 0.46, "III": 0.48, "IV": 0.50},
    20: {"I": 0.60, "II": 0.62, "III": 0.64, "IV": 0.66},
    40: {"I": 0.69, "II": 0.71, "III": 0.73, "IV": 0.75},
}

# assumed material properties
cement_sg = 3.15
fine_sg = 2.65
coarse_sg = 2.65

# standard deviation by grade bracket (IS 10262 Table 1) - used for target mean strength
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


def get_water_content(slump, max_agg_size):
    # base table is for 50mm slump - adjust +3% water per 25mm increase above 50mm
    base = water_table_base[max_agg_size]
    if slump > 50:
        increments = (slump - 50) / 25
        base = base * (1 + 0.03 * increments)
    return base


def get_coarse_fraction(max_agg_size, zone, wc_ratio):
    base_fraction = coarse_agg_table[max_agg_size][zone]
    # correction: +0.01 for every 0.05 decrease in w/c below 0.5, -0.01 for every 0.05 increase
    diff = 0.5 - wc_ratio
    correction = (diff / 0.05) * 0.01
    corrected = base_fraction + correction
    # keep within sane bounds
    return max(0.3, min(0.85, corrected))


def calculate_mix(fck, slump, max_agg_size, exposure, zone,
                   fine_moisture=0.0, fine_absorption=0.0,
                   coarse_moisture=0.0, coarse_absorption=0.0):

    # target mean strength - informational, IS 10262 durability governs w/c here
    # since strength-vs-wc curve needs actual material test data
    std_dev = get_std_deviation(fck)
    target_mean_strength = fck + 1.65 * std_dev

    # water content from table + slump correction
    water = get_water_content(slump, max_agg_size)

    # w/c ratio - durability limit governs (no lab strength-wc curve available here)
    wc_final = exposure_wc_limit[exposure]

    air_percent = exposure_air[exposure]

    # cement content - higher of (water/wc) or minimum required for exposure
    cement_from_wc = water / wc_final
    min_cement = exposure_min_cement[exposure]
    cement = max(cement_from_wc, min_cement)

    # if minimum cement content governed, recompute effective w/c (will be lower/better)
    effective_wc = water / cement

    # coarse aggregate volume (of total aggregate) with w/c correction
    coarse_fraction_of_agg = get_coarse_fraction(max_agg_size, zone, wc_final)

    # volumes, per 1 m3 = 1000 liters
    vol_cement = cement / (cement_sg * 1000) * 1000
    vol_water = water / 1000 * 1000
    vol_air = (air_percent / 100) * 1000

    vol_total_aggregate = 1000 - (vol_cement + vol_water + vol_air)
    vol_coarse = vol_total_aggregate * coarse_fraction_of_agg
    vol_fine = vol_total_aggregate - vol_coarse

    coarse_weight = (vol_coarse / 1000) * coarse_sg * 1000
    fine_weight = (vol_fine / 1000) * fine_sg * 1000

    # moisture correction - same logic as ACI module
    fine_free_moisture = fine_moisture - fine_absorption
    coarse_free_moisture = coarse_moisture - coarse_absorption

    fine_field_weight = fine_weight * (1 + fine_moisture / 100)
    coarse_field_weight = coarse_weight * (1 + coarse_moisture / 100)

    water_from_fine = fine_weight * (fine_free_moisture / 100)
    water_from_coarse = coarse_weight * (coarse_free_moisture / 100)

    field_water = water - water_from_fine - water_from_coarse

    return {
        "method": "IS 10262:2019",
        "target_mean_strength": round(target_mean_strength, 1),
        "std_deviation": std_dev,
        "slump_category": f"{slump} mm (adjusted from 50mm base)",
        "wc_strength": round(effective_wc, 3),   # effective, for display parity with ACI tab
        "wc_limit": wc_final,
        "wc_final": round(effective_wc, 3),
        "min_cement_required": min_cement,
        "air_percent": air_percent,
        "coarse_fraction": round(coarse_fraction_of_agg, 3),

        "water_batch": round(water, 1),
        "cement_batch": round(cement, 1),
        "coarse_batch": round(coarse_weight, 1),
        "fine_batch": round(fine_weight, 1),

        "cement_field": round(cement, 1),
        "fine_field": round(fine_field_weight, 1),
        "coarse_field": round(coarse_field_weight, 1),
        "water_field": round(field_water, 1),
    }
