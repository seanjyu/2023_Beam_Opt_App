
"""
Steel frame optimizer

Webapp run using streamlit to find an optimal beam, joist, girder gravity
system.

Inputs

Outputs
"""

import streamlit as st
from optimizer_functions import *

xl_file = pd.read_csv(r'wsec.csv')


def main():
    # streamlit UI
    st.title("Steel Beam Optimizer")
    st.markdown(
        'This app finds the optimum number of beams given dead and '
        'live loads and certain requirements. Note that all connections '
        'are assumed to be simply supported. Please input the required '
        'information in the sidebar and after pressing submit a result or '
        'an error message should appear.')
    st.markdown(
        'A short write up on this app and how it came up with this '
        'solution can be found here: https://sjy2129.github.io/personal_'
        'website/Beam_opt_app.html')

    # sidebar
    st.sidebar.title("Inputs")
    st.sidebar.subheader("Dimensions")
    height_input = st.sidebar.number_input("Height (ft)", min_value=0.0,
                                           format='%f', step=1.0)
    width_input = st.sidebar.number_input("Width (ft)", min_value=0.0,
                                          format='%f', step=1.0)
    st.sidebar.subheader("Depth Limits")
    st.sidebar.markdown(
        "If there are no specific limits please leave the inputs as 0")
    depth_limit_b = st.sidebar.number_input("Depth Limit on Beams (in)",
                                            min_value=0.0, format='%f',
                                            step=0.01)
    depth_limit_g = st.sidebar.number_input("Depth Limit on Girders(in)",
                                            min_value=0.0, format='%f',
                                            step=0.01)
    st.sidebar.subheader("Steel Yield Strength (Fy)")
    fy_input = st.sidebar.number_input("Fy (ksi)", min_value=0.0,
                                       format='%f', step=0.01)
    st.sidebar.subheader("Loads")
    DL_input = st.sidebar.number_input("Dead Load (psf)")
    LL_input = st.sidebar.number_input("Live Load (psf)")

    # Following options commented out for future use
    # SL_input=st.sidebar.number_input("Snow Load (psf)")
    # RL_input=st.sidebar.number_input("Roof Load (psf)")

    # When submit button is pressed check for illegal inputs and if there
    # are errors output error message. If no errors put sidebar values
    # into functions then plot optimal design.
    if st.sidebar.button("Submit"):
        if height_input <= 0:
            st.error("Please input a Height larger than 0")
        elif width_input <= 0:
            st.error("Please input a width larger than 0")
        elif fy_input <= 0:
            st.error("Please input a yield strength larger than 0")
        else:
            sol = frame_optimizer(xl_file, height_input, width_input,
                                  DL_input, LL_input, depth_limit_b,
                                  depth_limit_g, fy_input)
            if len(sol) == 5:
                fig = visualizer_plotly(height_input, width_input, sol[0],
                                        labels=[
                                            sol[1]['EDI_Std_Nomenclature'],
                                            sol[2]['EDI_Std_Nomenclature'],
                                            sol[3][
                                                'EDI_Std_Nomenclature']])
                st.plotly_chart(fig)
                result_str = 'The total weight of this system was ' + str(
                    sol[4] / 100) + ' kips.'
                st.text(result_str)
            else:
                st.error(sol[0])


if __name__ == '__main__':
    main()