"""
Steel frame optimizer

Webapp run using streamlit to find an optimal beam gravity system.
This file contains the functions for the optimization procedure.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import math

def beam_load(DL, LL, length):
    '''
    Function - beam_load
    Function to determine moment and shear loading given line loads
    :param DL: Dead loads (psf)
    :param LL: Live loads (psf)
    :param length: length of element (ft)
    :return: list containing maximum moment, maximum shear
             and the specific load combination.
    '''

    # calculate load cases and put them in a list.
    lc1 = 1.4 * DL
    lc2 = 1.2 * DL + 1.6 * LL
    all_lc = [lc1, lc2]

    # calculate maximum moment and shear for each load case.
    max_mom = max(all_lc) * (length * 12) ** 2 / (8 * 1000)
    max_shear = max(all_lc) * length * 6 / 1000

    # find index of maximum load case, since only distributed load
    # maximum load case for moment and shear will be the same.
    lc_ind = all_lc.index(max(all_lc))
    return[max_mom, max_shear, lc_ind]

def girder_load(load, beam_no, length):
    '''
    Function - girder_load
    Calculate girder load given load in kips and length of in feet,
    outputs moment in kip-in and shear in kips
    :param load: vertical loads (kips)
    :param beam_no: number of beams on girder
    :param length: length of girder
    :return: list of moment and shear
    '''

    # calculate shear
    shear = load * beam_no / 2

    # calculate between each beam
    length_b = length * 12 / (beam_no + 1)

    # to calculate moment sum area of shear diagram
    moment = 0
    shear_total = shear
    for i in range(beam_no):
        # base case when shear diagram becomes negative
        if shear_total - load <= 0:
            moment = moment + length_b * shear_total
            break
        moment = moment + length_b * shear_total
        shear_count = shear_total - load
    return [moment, shear]

def design(df, length, lc, demand, depth, fy=50):
    '''
    Function - Design
    Outputs optimum design, note demand should be in the units of kip-in
    :param df: Dataframe containing steel section data
    :param length: Length of element (ft)
    :param lc: Load combination
    :param demand: Moment load (kip-in)
    :param depth: Element depth maximum (in)
    :param fy: Element yield stress (ksi)
    :return: Row of dataframe containing an optimum design
    '''

    # First filter based on desired depth
    if depth != 0:
        df = df[df.d.astype(float) <= depth]

    # Filter into different failure modes, note units are in kip-in
    # Note dataframe has columns for Lp, Lr and geometry for each
    # section
    plastic = df[df.Lp.astype(float) >= length]

    inelasticltb = df[(df.Lp.astype(float) < length) &
                      (df.Lr.astype(float) >= length)]

    inelasticltb['MILtb_nc'] = 1.3 * (inelasticltb.plastic.astype(float)
                                    - (inelasticltb.plastic.astype(float)
                                    - 0.7 * fy *
                                    inelasticltb.Sx.astype(float))
                                    * ((length - inelasticltb.Lp.astype(float))
                                    / (inelasticltb.Lr.astype(float)
                                    - inelasticltb.Lp.astype(float))))

    inelasticltb['MILtb'] = np.where(inelasticltb['MILtb_nc'] <=
                                     inelasticltb['plastic'],
                                     inelasticltb['MILtb_nc'],
                                     inelasticltb['plastic'])

    elasticltb = df[df.Lr.astype(float) < length]

    elasticltb['MELtb_nc'] = 1.3 * fy * math.pi ** 2 * 29000 * \
                             (1 + 0.078 * elasticltb.J.astype(float)
                              * (length * 12 /
                                 elasticltb.rts.astype(float)) ** 2
                              / (elasticltb.Sx.astype(float) *
                                 elasticltb.ho.astype(float))) ** 0.5 \
                             / ((length * 12 /
                                 elasticltb.rts.astype(float)) ** 2)

    elasticltb['MELtb'] = np.where(elasticltb['MELtb_nc'] <=
                                   elasticltb['plastic'],
                                   elasticltb['MELtb_nc'],
                                   elasticltb['plastic'])

    # Filter based on capacity
    plasticcap = plastic[plastic['plastic'] > demand[0]]

    inelasticltbcap = inelasticltb[inelasticltb['MILtb'] > demand[0]]

    elasticltbcap = elasticltb[elasticltb['MELtb'] > demand[0]]

    # Sort with respect to weight
    sortedp = plasticcap.sort_values(by = ['W'])
    sortedi = inelasticltbcap.sort_values(by = ['W'])
    sortede = elasticltbcap.sort_values(by = ['W'])
    check = 0

    if len(sortedp)+len(sortedi)+len(sortede)==0:
        fail_m = 'All possible members fail through flexure'
        return fail_m

    # use while loop to keep designing until criteria is met
    while check != 1:
        # compare weights from each failure case
        comparevals = {}
        if len(sortedp) > 0:
            comparevals['p'] = sortedp['W'].iloc[0]
        if len(sortedi) > 0:
            comparevals['i'] = sortedi['W'].iloc[0]
        if len(sortede) > 0:
            comparevals['e'] = sortede['W'].iloc[0]

        # select lowest weight from compare values
        ind1 = min(comparevals)

        if ind1 == 'p':
            #Calculate new demand based on self weight
            newdemand = add_self_weight(sortedp, demand, length, lc)
            if newdemand[0] <= sortedp['plastic'].iloc[0]:
                if shear_design(sortedp,newdemand,fy) == True:
                    check = 1
                    solution = sortedp.iloc[0]
                else:
                    sortedp = sortedp.drop(sortedp.index[0])
            else:
                sortedp = sortedp.drop(sortedp.index[0])
        elif ind1 == 'i':
            newdemand = add_self_weight(sortedi, demand, length, lc)
            if newdemand[0] <= sortedi['MILtb'].iloc[0]:
                if shear_design(sortedi,newdemand,fy) == True:
                    check = 1
                    solution = sortedi.iloc[0]
                else:
                    sortedi = sortedi.drop(sortedi.index[0])
            else:
                sortedi = sortedi.drop(sortedi.index[0])
        else:
            newdemand = add_self_weight(sortede, demand, length, lc)
            if newdemand[0] <= sortede['plastic'].iloc[0]:
                if shear_design(sortede, newdemand, fy) == True:
                    check = 1
                    solution = sortede.iloc[0]
                else:
                    sortede = sortede.drop(sortede.index[0])
            else:
                sortede = sortede.drop(sortede.index[0])
        # Add failure message if all fail by shear (any counter reaches
        # size of dataframe)
        if len(sortedp) == 0 and len(sortedi) == 0 and len(sortede) == 0:
            check = 1
            fail_m = 'All possible members fail through shear'
            return fail_m
    return solution

def shear_design (df, demand, fy=50):
    '''
    Function shear_design
    Check section for shear failure based on AISC formula
    :param df: dataframe row with section data
    :param demand: shear demand (kips)
    :param fy: Yield strength (ksi)
    :return: boolean if shear design pass
    '''
    shearcapacity = 0.6 * fy * df['d'].iloc[0] * df['tw'].iloc[0]
    return True if shearcapacity > demand[1] else False

def add_self_weight(df, demand, length, lc):
    '''
    Function add_self_weight
    Function to add self weight
    :param df: dataframe row with section data
    :param demand: moment and shear load of previous loads
                   in list (kip-in, kip)
    :param length:
    :param lc: governing load combination
    :return: list with new demand (moment, shear)
    '''

    # check which load pattern governs
    if lc == 0:
        factor = 1.4
    else:
        factor = 1.2

    # calculate new moment based on section and return sum of previous
    # loads and new loads.
    addm = df['W'].iloc[0].astype(float) * factor * length **(2) / 8 \
           / 1000 * 12
    addv = df['W'].iloc[0].astype(float) * factor * length / 2 / 1000

    ndemand = [demand[0] + addm, demand[1] + addv]
    return ndemand

def frame_optimizer(df, Height, width, DL, LL, depth_b, depth_g, fy = 50):
    '''
    Function frame_optimizer
    Function to find an optimum number of interior beams based on weight of
    whole system.
    :param df: dataframe with section data
    :param Height: Height of bay (ft)
    :param width: Weight of bay (ft)
    :param DL: Dead load (psf)
    :param LL: Live load (psf)
    :param depth_b: Beam depth maximum (in)
    :param depth_g: Girder depth maximum (in)
    :param fy: Yield strength (ksi)
    :return: if possible solution found return a list of
            [number of interior beams,
             interior beam section data,
             side beam section data,
             girder section data,
             weight of system]
    '''
    # Height and width are the dimensions of the bay, loads are the area
    # dead and live loads. Outputs list containing number of beams:
    # [beam_no, int_beam, side_beam, girder]

    # Find which side is shorter
    if Height / width >= 1:
        long = Height
        short = width
    else:
        long = width
        short = Height

    # Start with 1 interior beam and make weight large (to be replaced
    # with first design)
    beam_no = 1
    weight_0 = 999999999

    # design loop
    while True:
        # Calculate load from loads
        mid_trib = long / (beam_no + 1)
        end_trib = mid_trib / 2
        mid_DL = mid_trib * DL
        mid_LL = mid_trib * LL
        end_DL = end_trib * DL
        end_LL = end_trib * LL
        mid_loads = beam_load(mid_DL, mid_LL, short)
        end_loads = beam_load(end_DL, end_LL, short)

        # design interior beam
        int_beam = design(df, short, mid_loads[2], mid_loads[0:2], depth_b,
                          fy)

        # design side beam
        beam = design(df, short, end_loads[2], end_loads[0:2], depth_b,
                          fy)

        # Obtain Girder load
        if type(int_beam) != str:
            girder_LC = int_beam['W'] * short / 2000 + mid_loads[1]
            girder_loading = girder_load(girder_LC, beam_no, long)
            # design girder
            girder = design(df, long, 0, girder_loading[0:2], depth_g, fy)
            # get total mass
            if isinstance(int_beam, pd.Series) \
                    and isinstance(beam, pd.Series) \
                    and isinstance(girder, pd.Series):
                weight_1 = int_beam['W'] * beam_no*short + beam['W'] \
                           * 2 * short + girder['W'] * 2 * long

                #compare, if larger then break
                if weight_0 < weight_1:
                    break
                else:
                    sol = [beam_no, int_beam, beam, girder,weight_1]
                    weight_0 = weight_1
                    beam_no = beam_no + 1
            else:
                beam_no = beam_no + 1
        else:
            beam_no = beam_no + 1
        if beam_no > 20:
            error_msg = 'Number of in-fill beams required for system' \
                        ' to not fail structurally exceeds 20, please ' \
                        'consider using another floor system or smaller ' \
                        'loads.'
            sol = [error_msg]
            break
    return sol

def visualizer_plotly(Height, width, beam_no, labels):
    '''
    Function visualizer_plotly
    Plot the beam design on a line graph with labels indicated the section
    size.
    :param Height: Height of bay (ft)
    :param width: Width of bay (ft)
    :param beam_no: Number of interior beams
    :param labels: sizes for beams in the order of interior beam,
                   side beam and girder.
    :return: plotly figure
    '''

    # initialize plotly figure and lists
    fig = go.Figure()
    x_interior_beam = []
    y_interior_beam = []

    # depending on bay dimensions add coordinate data to x or y interior
    # beam arrays to plot.
    if Height / width >= 1:
        length_b = Height / (beam_no + 1)
        top_bot_label = labels[1]
        side_label = labels[2]
        x_tickvals = [0, width]
        y_tickvals = [0]
        for i in range(beam_no):
            x_interior_beam.extend([0, width, None])
            y_interior_beam.extend([length_b * (i + 1),
                                  length_b * (i + 1), None])
            y_tickvals.append(round(length_b * (i + 1), 2))
        y_tickvals.append(Height)
    else:
        length_b = width / (beam_no + 1)
        top_bot_label = labels[2]
        side_label = labels[1]
        x_tickvals = [0]
        y_tickvals = [0, Height]
        for i in range(beam_no):
            x_interior_beam.extend([length_b * (i + 1),
                                  length_b * (i + 1), None])
            y_interior_beam.extend([0, Height, None])
            x_tickvals.append(round(length_b * (i + 1), 2))
        x_tickvals.append(width)

    # update plotly axes and add the plots
    fig.update_xaxes(showgrid = True, zeroline = True,
                     visible = True, tickvals = x_tickvals)
    fig.update_yaxes(showgrid = True, zeroline = False,
                     visible = True, tickvals = y_tickvals,
                     scaleanchor = "x", scaleratio = 1)
    fig.add_trace(go.Scatter(x = [0, width, None ,0, width],
                             y = [0, 0, None, Height, Height ],
                             line_shape = 'linear',name = top_bot_label))
    fig.add_trace(go.Scatter(x = [0, 0, None, width, width],
                             y = [0, Height, None, 0, Height],
                             line_shape = 'linear', name = side_label))
    fig.add_trace(go.Scatter(x = x_interior_beam, y = y_interior_beam,
                             line_shape = 'linear', name = labels[0]))
    return fig
