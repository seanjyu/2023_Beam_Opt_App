# Work in progress
# def vibration_analysis(short, long, conc_unit_weight, floor_modulus,
#                        floor_thickness, beam, beam_no, dead, live):
#     # Calculate the modular ratio, steel modulus assumed to be 29000 ksi,
#     # factor concrete modulus by 1.35 for dynamic modulus of elasticity
#     modular_ratio = 29000 / 1.35 / floor_modulus
#
#     # Find new center of mass
#     Equivalent_conc_area = long * 12 / beam_no / modular_ratio
#     y_bar = (beam['A'] * beam['d']/2 -
#              (Equivalent_conc_area * (floor_thickness ** 2) / 2)) \
#             / (beam['A'] + Equivalent_conc_area * floor_thickness)
#
#
#     # calculate new moment of inertia
#     Ij = beam['Ix'] + beam['A'] * (beam['d'] / 2 + y_bar) ** 2 + \
#          Equivalent_conc_area * floor_thickness ** 3 / 12 + \
#          Equivalent_conc_area * floor_thickness * \
#          (floor_thickness/2 - y_bar) ** 2
#
#     # calculate weight per linear ft for beam
#     w_b = long * / beam_no * (conc_unit_weight * floor_thickness / 12 + dead * + live + beam['W'])
