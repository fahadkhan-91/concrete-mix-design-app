# ACI 211.1 Concrete Mix Design Calculation Engine

# Table 6.3.3 - Approximate water content (kg/m3) - Non-air-entrained concrete
# Keys: (slump_range, max_agg_size) -> water content
WATER_CONTENT_TABLE = {
    "low":    {10: 199, 20: 190, 25: 179, 40: 166},   # slump 25-50mm
    "medium": {10: 216, 20: 205, 25: 193, 40: 181},   # slump 75-100mm
    "high":   {10: 228, 20: 216, 25: 202, 40: 190},   # slump 150-175mm
}

# Table 6.3.4(a) - W/C ratio vs target compressive strength (MPa), non-air-entrained
WC_RATIO_TABLE = [
    (40, 0.42),
    (35, 0.47),
    (30, 0.54),
    (25, 0.61),
    (20, 0.69),
    (15, 0.79),
]

# Table 6.3.6 - Coarse aggregate volume fraction (b/bo) vs max agg size & fineness modulus of sand
COARSE_AGG_VOLUME_TABLE = {
    10: {2.40: 0.50, 2.60: 0.48, 2.80: 0.46, 3.00: 0.44},
    20: {2.40: 0.66, 2.60: 0.64, 2.80: 0.62, 3.00: 0.60},
    25: {2.40: 0.71, 2.60: 0.69, 2.80: 0.67, 3.00: 0.65},
    40: {2.40: 0.75, 2.60: 0.73, 2.80: 0.71, 3.00: 0.69},
}

# Assumed material properties (can be made user-editable later)
CEMENT_SG = 3.15          # specific gravity of cement
FINE_AGG_SG = 2.65        # specific gravity of fine aggregate
COARSE_AGG_SG = 2.65      # specific gravity of coarse aggregate
COARSE_AGG_DRY_RODDED_DENSITY = 1600   # kg/m3 (typical assumption)
AIR_CONTENT_PERCENT = 2.0  # non-air-entrained, approx trapped air %


def get_slump_category(slump):
    if slump <= 50:
        return "low"
    elif slump <= 100:
        return "medium"
    else:
        return "high"


def interpolate_wc_ratio(fck):
    """Linearly interpolate w/c ratio for a given target strength."""
    table = sorted(WC_RATIO_TABLE, key=lambda x: x[0])
    if fck >= table[-1][0]:
        return table[-1][1]
    if fck <= table[0][0]:
        return table[0][1]
    for i in range(len(table) - 1):
        s1, r1 = table[i]
        s2, r2 = table[i + 1]
        if s1 <= fck <= s2:
            # linear interpolation
            ratio = r1 + (r2 - r1) * (fck - s1) / (s2 - s1)
            return round(ratio, 3)


def interpolate_coarse_agg_volume(max_agg_size, fm_sand):
    """Interpolate coarse aggregate volume fraction based on fineness modulus."""
    fm_values = sorted(COARSE_AGG_VOLUME_TABLE[max_agg_size].keys())
    table = COARSE_AGG_VOLUME_TABLE[max_agg_size]

    if fm_sand <= fm_values[0]:
        return table[fm_values[0]]
    if fm_sand >= fm_values[-1]:
        return table[fm_values[-1]]

    for i in range(len(fm_values) - 1):
        f1, f2 = fm_values[i], fm_values[i + 1]
        if f1 <= fm_sand <= f2:
            v1, v2 = table[f1], table[f2]
            return round(v1 + (v2 - v1) * (fm_sand - f1) / (f2 - f1), 3)


def calculate_mix(data):
    fck = data['fck']
    slump = data['slump']
    max_agg_size = data['max_agg_size']
    fm_sand = data['fm_sand']

    # Step 1: Water content
    slump_category = get_slump_category(slump)
    water_content = WATER_CONTENT_TABLE[slump_category][max_agg_size]

    # Step 2: W/C ratio
    wc_ratio = interpolate_wc_ratio(fck)

    # Step 3: Cement content
    cement_content = water_content / wc_ratio

    # Step 4: Coarse aggregate volume fraction & weight
    coarse_agg_fraction = interpolate_coarse_agg_volume(max_agg_size, fm_sand)
    coarse_agg_weight = coarse_agg_fraction * COARSE_AGG_DRY_RODDED_DENSITY

    # Step 5: Volumes (per 1 m3 = 1000 liters)
    volume_cement = cement_content / (CEMENT_SG * 1000) * 1000   # liters
    volume_water = water_content / 1000 * 1000                  # liters
    volume_coarse = coarse_agg_weight / (COARSE_AGG_SG * 1000) * 1000  # liters
    volume_air = (AIR_CONTENT_PERCENT / 100) * 1000              # liters

    volume_used = volume_cement + volume_water + volume_coarse + volume_air
    volume_fine = 1000 - volume_used   # remaining liters for fine aggregate

    fine_agg_weight = (volume_fine / 1000) * FINE_AGG_SG * 1000

    return {
        'slump_category': slump_category,
        'water': round(water_content, 1),
        'wc_ratio': wc_ratio,
        'cement': round(cement_content, 1),
        'coarse_agg_fraction': coarse_agg_fraction,
        'coarse_agg': round(coarse_agg_weight, 1),
        'fine_agg': round(fine_agg_weight, 1),
        'air_content_percent': AIR_CONTENT_PERCENT,
    }
