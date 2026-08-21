def calculate_mix(data):
    """
    ACI 211.1 mix design calculation.
    Currently a skeleton — real table lookups added in next step.
    """
    fck = data['fck']
    slump = data['slump']
    max_agg_size = data['max_agg_size']

    # Placeholder values — will replace with real ACI 211.1 tables next step
    water_content = 185  # kg/m3 (dummy)
    wc_ratio = 0.5        # dummy

    cement_content = water_content / wc_ratio

    return {
        'water': water_content,
        'cement': round(cement_content, 2),
        'wc_ratio': wc_ratio,
        'note': 'Yeh dummy values hain, agla step mein real ACI tables add karenge'
    }
