# concrete mix design calculations - ACI 211.1 method

water_table = {
    "low":    {10: 199, 20: 190, 25: 179, 40: 166},
    "medium": {10: 216, 20: 205, 25: 193, 40: 181},
    "high":   {10: 228, 20: 216, 25: 202, 40: 190},
}

water_table_air = {
    "low":    {10: 181, 20: 168, 25: 160, 40: 150},
    "medium": {10: 202, 20: 184, 25: 175, 40: 165},
    "high":   {10: 216, 20: 197, 25: 184, 40: 174},
}

wc_table = [
    (40, 0.42), (35, 0.47), (30, 0.54),
    (25, 0.61), (20, 0.69), (15, 0.79),
]

coarse_agg_table = {
    10: {2.40: 0.50, 2.60: 0.48, 2.80: 0.46, 3.00: 0.44},
    20: {2.40: 0.66, 2.60: 0.64, 2.80: 0.62, 3.00: 0.60},
    25: {2.40: 0.71, 2.60: 0.69, 2.80: 0.67, 3.00: 0.65},
    40: {2.40: 0.75, 2.60: 0.73, 2.80: 0.71, 3.00: 0.69},
}

exposure_air = {"mild": 2.0, "moderate": 4.5, "severe": 6.0}
exposure_wc_limit = {"mild": 0.60, "moderate": 0.50, "severe": 0.45}

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


def calculate_mix(fck, slump, max_agg_size, exposure, fm_sand,
                   fine_moisture=0.0, fine_absorption=0.0,
                   coarse_moisture=0.0, coarse_absorption=0.0):
    """
    fine_moisture / coarse_moisture = actual moisture content of aggregate on site (%)
    fine_absorption / coarse_absorption = aggregate's absorption capacity (%)
    Agar site pe dry aggregate use ho raha ho to sab 0 rakh do, batch design values hi milengi.
    """
    category = slump_category(slump)

    if exposure in ("moderate", "severe"):
        water = water_table_air[category][max_agg_size]
    else:
        water = water_table[category][max_agg_size]

    wc_strength = get_wc_ratio(fck)
    wc_limit = exposure_wc_limit[exposure]
    wc_final = min(wc_strength, wc_limit)

    air_percent = exposure_air[exposure]
    cement = water / wc_final

    coarse_fraction = get_coarse_fraction(max_agg_size, fm_sand)
    coarse_weight = coarse_fraction * coarse_dry_density

    vol_cement = cement / (cement_sg * 1000) * 1000
    vol_water = water / 1000 * 1000
    vol_coarse = coarse_weight / (coarse_sg * 1000) * 1000
    vol_air = (air_percent / 100) * 1000

    vol_fine = 1000 - (vol_cement + vol_water + vol_coarse + vol_air)
    fine_weight = (vol_fine / 1000) * fine_sg * 1000

    # yahan tak sab "dry / batch design" quantities hain - ab moisture correction lagayenge

    # free moisture = jo moisture aggregate ke andar absorb nahi hui, balke bahar chipki hui hai
    fine_free_moisture = fine_moisture - fine_absorption
    coarse_free_moisture = coarse_moisture - coarse_absorption

    # field weight - aggregate apna moisture bhi carry karega isliye weight badh jayega
    fine_field_weight = fine_weight * (1 + fine_moisture / 100)
    coarse_field_weight = coarse_weight * (1 + coarse_moisture / 100)

    # extra pani jo aggregate se mix mein add ho raha hai, wo batch water se minus karna hai
    water_from_fine = fine_weight * (fine_free_moisture / 100)
    water_from_coarse = coarse_weight * (coarse_free_moisture / 100)

    field_water = water - water_from_fine - water_from_coarse

    return {
        "slump_category": category,
        "wc_strength": wc_strength,
        "wc_limit": wc_limit,
        "wc_final": wc_final,
        "air_percent": air_percent,
        "coarse_fraction": coarse_fraction,

        # dry / batch design quantities (lab basis, no moisture)
        "water_batch": round(water, 1),
        "cement_batch": round(cement, 1),
        "coarse_batch": round(coarse_weight, 1),
        "fine_batch": round(fine_weight, 1),

        # field quantities (actual site pe dalne wali quantity, moisture adjusted)
        "cement_field": round(cement, 1),   # cement moisture se affect nahi hota
        "fine_field": round(fine_field_weight, 1),
        "coarse_field": round(coarse_field_weight, 1),
        "water_field": round(field_water, 1),
    }
def compute_batch_quantities(result, volume_m3=1.0, bag_weight=50):
    """
    result = calculate_mix() ka output
    volume_m3 = kitna total concrete cast karna hai (m3 mein)
    bag_weight = ek cement bag ka weight (kg), Pakistan mein aam tor pe 50kg hota hai
    """
    cement_per_m3 = result["cement_field"]
    water_per_m3 = result["water_field"]
    fine_per_m3 = result["fine_field"]
    coarse_per_m3 = result["coarse_field"]

    # ek bag ke against kitna paani/ret/bajri chahiye
    bags_per_m3 = cement_per_m3 / bag_weight

    water_per_bag = water_per_m3 / bags_per_m3
    fine_per_bag = fine_per_m3 / bags_per_m3
    coarse_per_bag = coarse_per_m3 / bags_per_m3

    # poori job ke liye total quantities
    total_cement = cement_per_m3 * volume_m3
    total_water = water_per_m3 * volume_m3
    total_fine = fine_per_m3 * volume_m3
    total_coarse = coarse_per_m3 * volume_m3
    total_bags = total_cement / bag_weight

    return {
        "bags_per_m3": round(bags_per_m3, 2),
        "water_per_bag": round(water_per_bag, 1),
        "fine_per_bag": round(fine_per_bag, 1),
        "coarse_per_bag": round(coarse_per_bag, 1),

        "volume_m3": volume_m3,
        "total_bags": round(total_bags, 1),
        "total_cement_kg": round(total_cement, 1),
        "total_water_kg": round(total_water, 1),
        "total_fine_kg": round(total_fine, 1),
        "total_coarse_kg": round(total_coarse, 1),
    }
def compute_cost_estimate(batch_info, cement_rate_per_bag, fine_rate_per_kg, coarse_rate_per_kg, water_rate_per_liter=0):
    """
    batch_info = compute_batch_quantities() ka output
    rates = local currency mein (jo bhi currency user use kar raha ho)
    """
    cement_cost = batch_info["total_bags"] * cement_rate_per_bag
    fine_cost = batch_info["total_fine_kg"] * fine_rate_per_kg
    coarse_cost = batch_info["total_coarse_kg"] * coarse_rate_per_kg
    water_cost = batch_info["total_water_kg"] * water_rate_per_liter  # 1 kg water ~ 1 liter

    total_cost = cement_cost + fine_cost + coarse_cost + water_cost
    cost_per_m3 = total_cost / batch_info["volume_m3"] if batch_info["volume_m3"] > 0 else 0

    return {
        "cement_cost": round(cement_cost, 2),
        "fine_cost": round(fine_cost, 2),
        "coarse_cost": round(coarse_cost, 2),
        "water_cost": round(water_cost, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_m3": round(cost_per_m3, 2),
    }
