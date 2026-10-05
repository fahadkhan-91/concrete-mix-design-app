# unit conversion helpers - metric (SI) se imperial mein convert karne ke liye

KG_TO_LB = 2.20462
M3_TO_YD3 = 1.30795
KGM3_TO_LBYD3 = 1.68556   # kg/m3 -> lb/yd3, combined density conversion


def kgm3_to_lbyd3(value):
    return value * KGM3_TO_LBYD3


def kg_to_lb(value):
    return value * KG_TO_LB


def m3_to_yd3(value):
    return value * M3_TO_YD3
