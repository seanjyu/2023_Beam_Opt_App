import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import plotly.graph_objects as go
pd.options.mode.chained_assignment = None

#determine loading

#following lines are user inputs
DL=1
LL=1
Height=10
Width=10
xl_file = pd.read_csv(r'wsec.csv') # r'C:\Users\Sean Yu\Desktop\Summer Projects\Steel Framing optimizer\wsec.csv')


def beam_load(DL,LL,leng):
    #Calculate load on beam given psf loads and Height in feet, outputs moment in kip-in
    lc1=1.4*DL
    lc2=1.2*DL+1.6*LL
    #lc3=
    all_lc=[lc1,lc2]
    mmom=max(all_lc)*(leng*12)**(2)/8/1000
    mshear=max(all_lc)*leng*6/1000 #12/2
    lc_ind=all_lc.index(max(all_lc))
    return[mmom,mshear,lc_ind]
def design(df,leng,lc,demand=[200,100], depth=999,fy=50):
    #Outputs
    #Note demand should be in the units of kip-in and kips

    #First filter based on desired depth
    df=df[df.d.astype(float) <= depth]

    #Filter into different failure modes, note units are in kip-in
    plastic=df[df.Lp.astype(float)>=leng]
    inelasticltb=df[(df.Lp.astype(float)<leng) & (df.Lr.astype(float)>=leng)]
    inelasticltb['MILtb_nc']=1.3*(inelasticltb.plastic.astype(float)-(inelasticltb.plastic.astype(float)-0.7*fy*inelasticltb.Sx.astype(float))*((leng-inelasticltb.Lp.astype(float))/(inelasticltb.Lr.astype(float)-inelasticltb.Lp.astype(float))))
    inelasticltb['MILtb']=np.where(inelasticltb['MILtb_nc']<=inelasticltb['plastic'],inelasticltb['MILtb_nc'],inelasticltb['plastic'])
    elasticltb=df[df.Lr.astype(float)<leng]
    elasticltb['MELtb_nc']=1.3*fy*3.14159265359**2*29000*(1+0.078*elasticltb.J.astype(float)*(leng*12/elasticltb.rts.astype(float))**2/(elasticltb.Sx.astype(float)*elasticltb.ho.astype(float)))**0.5/((leng*12/elasticltb.rts.astype(float))**2)
    elasticltb['MELtb']=np.where(elasticltb['MELtb_nc']<=elasticltb['plastic'],elasticltb['MELtb_nc'],elasticltb['plastic'])
    #Filter based on capacity
    plasticcap=plastic[plastic['plastic']>demand[0]]
    inelasticltbcap=inelasticltb[inelasticltb['MILtb']>demand[0]]
    elasticltbcap=elasticltb[elasticltb['MELtb']>demand[0]]
    #Sort with respect to weight
    sortedp=plasticcap.sort_values(by=['W'])
    sortedi=inelasticltbcap.sort_values(by=['W'])
    sortede=elasticltbcap.sort_values(by=['W'])
    check=0

    if len(sortedp)+len(sortedi)+len(sortede)==0:
        fail_m = 'All possible members fail through flexure'
        return fail_m

    while check!=1:
        #compare minimum values
        comparevals={}
        #dfs=[sortedp,sortedi,sortede]
        if len(sortedp)>0:
            comparevals['p']=sortedp['W'].iloc[0]
        if len(sortedi)>0:
            comparevals['i']=sortedi['W'].iloc[0]
        if len(sortede)>0:
            comparevals['e']=sortede['W'].iloc[0]
        #print(comparevals)
        #for df in dfs:
        #    if len(df)>0:
        #        comparevals.append(df['W'].iloc[0])
        #ind1=comparevals.index(min(comparevals))
        ind1=min(comparevals)
        if ind1 == 'p':
            #Calculate new demand based on self weight
            newdemand=addselfweight(sortedp,demand,leng,lc)
            if newdemand[0]<=sortedp['plastic'].iloc[0]:
                if sheardesign(sortedp,newdemand,fy) == True:
                    check=1
                    solution=sortedp.iloc[0]
                else:
                    sortedp=sortedp.drop(sortedp.index[0])
            else:
                sortedp=sortedp.drop(sortedp.index[0])
        elif ind1 == 'i':
            newdemand = addselfweight(sortedi, demand, leng, lc)
            if newdemand[0] <= sortedi['MILtb'].iloc[0]:
                if sheardesign(sortedi,newdemand,fy) == True:
                    check=1
                    solution=sortedi.iloc[0]
                else:
                    sortedi=sortedi.drop(sortedi.index[0])
            else:
                sortedi=sortedi.drop(sortedi.index[0])
        else:
            newdemand = addselfweight(sortede, demand, leng, lc)
            if newdemand[0] <= sortede['plastic'].iloc[0]:
                if sheardesign(sortede, newdemand, fy) == True:
                    check = 1
                    solution = sortede.iloc[0]
                else:
                    sortede=sortede.drop(sortede.index[0])
            else:
                sortede = sortede.drop(sortede.index[0])
        # Add failure message if all fail by shear (any counter reaches size of dataframe)

        if len(sortedp)==0 and len(sortedi)==0 and len(sortede)==0:
            check=1
            fail_m = 'All possible members fail through shear'
            return fail_m
    return solution

def sheardesign (df, demand, fy=50):
    shearcapacity=0.6*fy*df['d'].iloc[0]*df['tw'].iloc[0]
    return True if shearcapacity>demand[1] else False

def fillframe(df, maxlen):
    if len(df)==maxlen:
        return df
    nrow={'W':99999}
    while len(df) != maxlen:
        df=df.append(nrow,ignore_index=True)
    return df
def addselfweight(df,demand,Height,lc):
    if lc==0:
        factor=1.4
    else:
        factor=1.2
    addm=df['W'].iloc[0].astype(float)*factor*Height**(2)/8/1000*12
    addv=df['W'].iloc[0].astype(float)*factor*Height/2/1000

    ndemand=[demand[0]+addm,demand[1]+addv]
    return ndemand

def frame_optimizer(df,Height,width,DL,LL):
    #Height and width are the dimensions of the bay, loads are the area dead and live loads
    #Outputs list containing number of beams, sol=[beam_no,mid_beam,end_beam,girder]

    #Find which side is shorter
    if Height/width>=1:
        long=Height
        short=width
    else:
        long=width
        short=Height
    beam_no=1
    weight_0=999999999
    while True:
        #Calculate load from loads
        mid_trib=long/(beam_no+1)
        end_trib=mid_trib/2
        mid_DL=mid_trib*DL
        mid_LL=mid_trib*LL
        end_DL= end_trib*DL
        end_LL = end_trib*LL
        mid_loads=beam_load(mid_DL,mid_LL,short)
        end_loads = beam_load(end_DL, end_LL, short)
        #design mid beam
        mid_beam=design(df,short,mid_loads[2],mid_loads[0:2])
        #design end beam
        end_beam=design(df,short,end_loads[2],end_loads[0:2])
        #Obtain Girder load
        if type(mid_beam)!=str:
            girder_LC=mid_beam['W']*short/2000+mid_loads[1]
            girder_loading=girder_load(girder_LC,beam_no,long)
            #design girder
            girder=design(df,long,0,girder_loading[0:2])
            #get total mass
            if isinstance(mid_beam,pd.Series) and isinstance(end_beam,pd.Series) and isinstance(girder,pd.Series):
                weight_1=mid_beam['W']*beam_no*short+end_beam['W']*2*short+girder['W']*2*long
                #compare, if larger then break
                if weight_0<weight_1:
                    sol=[beam_no,mid_beam,end_beam,girder]
                    break
                else:
                    weight_0=weight_1
                    beam_no=beam_no+1
            else:
                beam_no = beam_no + 1
        else:
            beam_no = beam_no + 1
        if beam_no > 20:
            print('Number of in-fill beams required for system to not fail structurally exceeds 20, please consider using another floor system')
            sol=[0]
            break
    return sol

def girder_load(load,beam_no,Height):
    #function that calculates girder load given load in kips and Height in feet, outputs moment in kip-in and shear in kips
    shear=load*beam_no/2
    length_b=Height*12/(beam_no+1)
    moment=0
    shear_count=shear
    for i in range(beam_no):
        if shear_count-load<=0:
            moment = moment + length_b * shear_count
            break
        moment = moment + length_b*shear_count
        shear_count=shear_count-load
    return [moment,shear]
def visualizer(Height,width,beam_no,labels=['test1','test2','test3']):
    #Visualize bays using matplotlib
    plt.clf()
    plt.figure(1)
    plt.xlim(-1,1.45*width)
    plt.axis('off')
    mid_beam_label=mpatches.Patch(color='blue',label=labels[0])
    end_beam_label=mpatches.Patch(color='green',label=labels[1])
    girder_label=mpatches.Patch(color='red',label=labels[2])
    plt.legend(handles=[mid_beam_label,end_beam_label,girder_label],loc=7)
    if Height / width >= 1:
        plt.plot([0.025*width, 0.975*width], [0, 0], 'g')
        plt.plot([0.025*width, 0.975*width], [Height, Height], 'g')
        plt.plot([0, 0], [0, Height], 'r')
        plt.plot([width, width], [0, Height], 'r')
        length_b=Height/(beam_no+1)
        for i in range(beam_no):
            plt.plot([0.025*width, 0.975*width],[length_b*(i+1),length_b*(i+1)],'b')
    else:
        length_b = width / (beam_no + 1)
        plt.plot([0, width], [0, 0], 'r')
        plt.plot([0, width], [Height, Height], 'r')
        plt.plot([0, 0], [0.025*Height, 0.975*Height], 'g')
        plt.plot([width, width], [0.025*Height, 0.975*Height], 'g')
        for i in range(beam_no):
            plt.plot([length_b * (i + 1), length_b * (i + 1)],[0.025*Height, 0.975*Height],'b')
def visualizer_plotly(Height,width,beam_no,labels=['mid_beam','end_beam','girder']):
    fig = go.Figure() #layout=go.Layout(xaxis=go.layout.xaxis('showgrid'))
    x_infill_beam = []
    y_infill_beam = []
    if Height / width >=1:
        length_b = Height / (beam_no + 1)
        top_bot_label=labels[1]
        side_label=labels[2]
        x_tickvals=[0,width]
        y_tickvals=[0]
        for i in range(beam_no):
            x_infill_beam.extend([0, width, None])
            y_infill_beam.extend([length_b*(i+1),length_b*(i+1),None])
            y_tickvals.append(round(length_b*(i+1),2))
        y_tickvals.append(Height)
    else:
        length_b = width / (beam_no + 1)
        top_bot_label = labels[2]
        side_label = labels[1]
        x_tickvals = [0]
        y_tickvals = [0, Height]
        for i in range(beam_no):
            x_infill_beam.extend([length_b * (i + 1), length_b * (i + 1), None])
            y_infill_beam.extend([0, Height, None])
            x_tickvals.append(round(length_b*(i+1),2))
        x_tickvals.append(width)
    fig.update_xaxes(showgrid=True, zeroline=True, visible=True,tickvals=x_tickvals)
    fig.update_yaxes(showgrid=True, zeroline=False, visible=True, tickvals=y_tickvals, scaleanchor="x", scaleratio=1)
    fig.add_trace(go.Scatter(x=[0, width, None ,0, width], y=[0, 0,None,Height, Height ],line_shape='linear',name=top_bot_label))
    fig.add_trace(go.Scatter(x=[0, 0, None, width, width], y=[0, Height, None, 0, Height], line_shape='linear', name=side_label))
    fig.add_trace(go.Scatter(x=x_infill_beam, y=y_infill_beam, line_shape='linear', name=labels[0]))
    #fig.add_trace(go.Scatter(x=[0, width], y=[Height, Height], line_shape='linear',name='test',legendgroup="g1"))
    return fig

def opt_test():
    xl_file = pd.read_csv(r'C:\Users\Sean Yu\Desktop\Summer Projects\Steel Framing optimizer\wsec.csv')
    num=np.linspace(1,50,num=50)
    Heights=100/num
    sol=[]
    dlist=[]
    demand=[1000,300]
    for abc in Heights:
        print(abc)
        [a,b,c,d]=momdesign(xl_file,abc)
        sol.append(d['W'])
        dlist.append(d)
    totw=sol*num
    return [num,Heights,sol,totw]

#streamlit UI
st.title("Steel Framing Optimizer")

#st.text("Test")
#Selectbox
st.sidebar.title("Inputs")
st.sidebar.subheader("Dimensions")
Height_input=st.sidebar.number_input("Height (ft)",min_value=0.0,format='%f',step=1.0)
width_input=st.sidebar.number_input("Width (ft)",min_value=0.0,format='%f',step=1.0)
st.sidebar.subheader("Depth Limits")
st.sidebar.markdown("If there are no specific limits please leave the inputs as 0")
depth_limit_b=st.sidebar.number_input("Depth Limit on Beams (in)",min_value=0.0,format='%f',step=0.01)
depth_limit_g=st.sidebar.number_input("Depth Limit on Girders(in)",min_value=0.0,format='%f',step=0.01)
st.sidebar.subheader("Loads")
DL_input=st.sidebar.number_input("Dead Load (psf)")
LL_input=st.sidebar.number_input("Live Load (psf)")
SL_input=st.sidebar.number_input("Snow Load (psf)")
RL_input=st.sidebar.number_input("Roof Load (psf)")
if st.sidebar.button("Submit"):
    if Height_input<=0:
        st.error("Please input a Height larger than 0")
    elif width_input<=0:
        st.error("Please input a width larger than 0")
    else:
        sol=frame_optimizer(xl_file,Height_input,width_input,DL_input,LL_input)
        if len(sol)==4:

            #fig1=visualizer(Height_input,width_input,sol[0],labels=[sol[1]['EDI_Std_Nomenclature'],sol[2]['EDI_Std_Nomenclature'],sol[3]['EDI_Std_Nomenclature']])
            fig2=visualizer_plotly(Height_input,width_input,sol[0],labels=[sol[1]['EDI_Std_Nomenclature'],sol[2]['EDI_Std_Nomenclature'],sol[3]['EDI_Std_Nomenclature']])
            #st.pyplot(fig1)
            st.plotly_chart(fig2)