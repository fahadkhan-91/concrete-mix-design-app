# f'ck value se standard grade naming nikalna, method ke hisab se

def get_grade_name(method, fck):
    fck_rounded = round(fck)

    if "IS" in method:
        return f"M{fck_rounded}"

    if "BS" in method:
        # BS/DOE mein grade cylinder/cube dono strength se likha jata hai (e.g. C25/30)
        # cylinder strength ≈ 0.8 * cube strength (approx conversion)
        cylinder = round(fck_rounded * 0.8)
        return f"C{cylinder}/{fck_rounded}"

    # ACI mein formal letter-grade system nahi hota, standard specified strength classes hote hain
    standard_classes = [15, 20, 25, 30, 35, 40, 45, 50]
    nearest = min(standard_classes, key=lambda x: abs(x - fck_rounded))
    return f"f'c {fck_rounded} MPa (nearest standard class: {nearest} MPa)"
