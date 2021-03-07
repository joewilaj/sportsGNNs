import argparse, logging
import numpy as np
import networkx as nx
import node2vec
import node2vec_stack
import graph
import construct_from_data
import scipy.io
import pandas as pd
import pickle
import sys
import os
import tensorflow as tf
import keras
import warnings
import pdb
import requests
import datetime
import re
import matplotlib.pyplot as plt
import utils_data
import extract_team_GAT
import spektral
import tensorboard





from tensorflow.keras import backend as K
from tensorflow.keras import layers, initializers
from keras.engine.topology import Layer
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import Dense, Activation, Input, Lambda, Concatenate, Dropout, ReLU, Reshape,Flatten
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import plot_model
from datetime import date,timedelta




np.set_printoptions(threshold=sys.maxsize)
 

#Diffusion Convolution Network:

#Atwood, Towsley, Diffusion Convolutional Neural Network, November 15, 2015
#arXiv:1511.02136v6 [cs.LG]


#Convolution operations performed when constructing inputs in ncaabwalkod_train() and ncaabwalkod_test()

def DCNN_ncaabwalkod(height,node2vec_dim,N): 


    inputs = Input(shape=(4*height*node2vec_dim,))
    last_5_input = Input(shape = (10,))

    game_in = Concatenate()([inputs,last_5_input])

    dense1 = Dense(int(np.floor(4*node2vec_dim*height)),activation = 'tanh')(game_in)
    drop1 = Dropout(.6)(dense1)

    dense2 = Dense(int(np.floor(height*node2vec_dim)))(drop1)
    drop2 = Dropout(.3)(dense2)

    dense3 = Dense(int(np.floor(height*node2vec_dim/4)),activation = 'tanh')(drop2)
    drop3 = Dropout(.2)(dense3)


    prediction = Dense(1)(drop3)

    #pdb.set_trace()

    model = Model(inputs = [inputs,last_5_input], outputs = prediction)

    return model




#Graph Attention Network

#Velickovic, P.; Cucurull, G.; Casanova, A.; Romero, A.; Lio,
#P.; and Bengio, Y. 2018. Graph attention networks. International
#Conference on Learning Representations (ICLR)

#arXiv:1710.10903v3 [stat.ML]

#implemented with spektral: https://github.com/danielegrattarola/spektral



def ncaab_gat(node2vec_dim,N):

    channels = 40                       
    n_attn_heads = 3              
    dropout_rate = 0.1            
    l2_reg = 5e-4/2               


    node2vec_input = Input(shape=(2*(N+1),node2vec_dim))  
    A_input = Input(shape=(2*(N+1),2*(N+1)))

    team_inputs = Input(shape=(2,),dtype = tf.int64)
    line_input = Input(shape=(1,))
    last_5_input = Input(shape = (10,))




    graph_attention = spektral.layers.GATConv(channels, attn_heads=n_attn_heads, concat_heads=True, dropout_rate=dropout_rate, 
                            return_attn_coef=False, activation='elu', use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros', 
                            attn_kernel_initializer='glorot_uniform', kernel_regularizer=l2(l2_reg), bias_regularizer=None, 
                            attn_kernel_regularizer=l2(l2_reg), activity_regularizer=None, kernel_constraint=None, bias_constraint=None,
                            attn_kernel_constraint=None)([node2vec_input,A_input])



    #extracts nodes for link prediction

    game_vec = extract_team_GAT.Game_Vec(channels*n_attn_heads,N)([team_inputs,graph_attention])


    dense1 = Dense(int(np.floor(4*channels*n_attn_heads)),activation = 'tanh')(game_vec)
    drop1 = Dropout(.05)(dense1)

    dense2 = Dense(int(np.floor(channels*n_attn_heads/4)),activation = 'tanh')(drop1)
    drop2 = Dropout(.05)(dense2)

    drop2 = Reshape((int(np.floor(channels*n_attn_heads)),))(drop2)

    drop2 = Concatenate()([drop2,last_5_input])

    dense3 = Dense(int(np.floor(channels*n_attn_heads/6)))(drop2)
    drop3 = Dropout(.05)(dense3)


    prediction = Dense(1)(drop3)


    model = Model(inputs = [team_inputs,node2vec_input,A_input,last_5_input], outputs = prediction)

    return model


    #ARMA model
 
    #Filippo Maria Bianchi, Daniele Grattarola, Lorenzo Livi, Cesare Alippi
    #Graph Neural Networks with convolutional ARMA filters,January 15,2019
    #arXiv:1901.01343v7 [cs.LG] 

    #implemented with spektral: https://github.com/danielegrattarola/spektral




def ncaab_ARMA(node2vec_dim,N):

    channels = 80                                                        


    node2vec_input = Input(shape=(2*(N+1),node2vec_dim))  
    A_input = Input(shape=(2*(N+1),2*(N+1)))

    team_inputs = Input(shape=(2,),dtype = tf.int64)
    last_5_input = Input(shape = (10,))




    ARMA = spektral.layers.ARMAConv(channels, order=4, iterations=1, share_weights=False, gcn_activation='relu', 
                            dropout_rate=0.2, activation='elu', use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros',
                            kernel_regularizer=None, bias_regularizer=None, activity_regularizer=None, 
                            kernel_constraint=None, bias_constraint=None)([node2vec_input,A_input])




    #extracts nodes for link prediction


    game_vec = extract_team_GAT.Game_Vec(channels,N)([team_inputs,ARMA])



    dense1 = Dense(int(np.floor(4*channels)),activation = 'tanh')(game_vec)
    drop1 = Dropout(.05)(dense1)

    dense2 = Dense(int(np.floor(channels/4)),activation = 'tanh')(drop1)
    drop2 = Dropout(.03)(dense2)

    drop2 = Reshape((int(np.floor(channels)),))(drop2)

    drop2 = Concatenate()([drop2,last_5_input])

    dense3 = Dense(int(np.floor(channels/3)))(drop2)
    drop3 = Dropout(.01)(dense3)


    prediction = Dense(1)(drop3)

    model = Model(inputs = [team_inputs,node2vec_input,A_input,last_5_input], outputs = prediction)

    return model


def ncaab_gin(node2vec_dim,N):

    channels = 80                                                   


    node2vec_input = Input(shape=(2*(N+1),node2vec_dim))  
    A_input = Input(shape=(2*(N+1),2*(N+1)))

    team_inputs = Input(shape=(2,),dtype = tf.int64)
    last_5_input = Input(shape = (10,))


    A_input_sp = extract_team_GAT.To_Sparse()(A_input)



    GIN = spektral.layers.GINConv(channels, epsilon=None, mlp_hidden=[channels, channels], mlp_activation='relu', aggregate='sum', activation=None, 
                                  use_bias=True, kernel_initializer='glorot_uniform', bias_initializer='zeros', kernel_regularizer=None,
                                  bias_regularizer=None, activity_regularizer=None, kernel_constraint=None,
                                  bias_constraint=None)([node2vec_input,A_input_sp])



    #extracts nodes for link prediction


    game_vec = extract_team_GAT.Game_Vec(channels,N)([team_inputs,GIN])



    dense1 = Dense(int(np.floor(4*channels)),activation = 'tanh')(game_vec)
    drop1 = Dropout(.01)(dense1)

    dense2 = Dense(int(np.floor(channels/4)),activation = 'tanh')(drop1)
    drop2 = Dropout(.01)(dense2)

    drop2 = Reshape((int(np.floor(channels)),))(drop2)

    drop2 = Concatenate()([drop2,last_5_input])

    dense3 = Dense(int(np.floor(channels/3)))(drop2)
    drop3 = Dropout(.01)(dense3)


    prediction = Dense(1)(drop3)

    model = Model(inputs = [team_inputs,node2vec_input,A_input,last_5_input], outputs = prediction)

    return model




def main():

    #select model type and year


    
    model_type = 'ncaabwalkod'
    #model_type = 'ncaab_gat'
    #model_type = 'ncaab_ARMA'
    #model_type = 'ncaab_gin'

    year = 2021

    #select day range on which to test the model

    startdate = datetime.datetime(year,3,6)
    stopdate = datetime.datetime(year,3,7)



    #plots = 'on'
    plots = 'off'





    start_day = (startdate-datetime.datetime(year-1,10,12)).days
    stop_day = (stopdate-datetime.datetime(year-1,10,12)).days

    startstring = startdate.strftime("%m_%d_%Y")
    stopstring = stopdate.strftime("%m_%d_%Y")

    now = datetime.datetime.now()
    datestring = now.strftime("%m_%d_%Y")

    today = (now-datetime.datetime(year-1,10,12)).days

    TeamList = pd.read_excel('data/TeamLists.xls',sheet_name = year-2015,header = None)
    TeamList = TeamList.to_numpy(dtype = object,copy = True)

    #edgeweights when constructing the Offense and Defense Statistic graphs SOffDef, G_orc

    weights = pd.read_excel('data/weights.xls',sheet_name = 0,header = 0)
    weights = weights.to_numpy(dtype = object,copy = True)





    with open('pickles/ncaabdata_pickled/'+str(year)+'ncaabdata.pkl', 'rb') as Data: 
        Data_Full = pickle.load(Data)



    N = Data_Full.shape[2]

    for i in range(364):
        for j in range(36):
            for k in range(N):
                if Data_Full[i,j,k] is None:
                    Data_Full[i,j,k] = 0


    schedule, HomeAway = utils_data.format_schedule(Data_Full,TeamList,year)

    #if year < 2021:
    #    Lines = utils_data.Lines(Data_Full,schedule,HomeAway,TeamList_Lines,year)


    #if year == 2021:
    #    Lines = utils_data.Lines_2021(Data_Full,schedule,HomeAway,TeamList_Lines,year)

    Lines = np.zeros((N,364),dtype = float)


    ats_bets = 0
    ats_wins = 0
    total_bets = 0
    total_wins = 0
    money_line_wins = 0
    moneyline_count = 0
    window = 0  #parameter to constrain the test set to games where the model prediction and vegas prediction differ more than 'window'
    push = 0
    ties = 0

    loss = 0
    runs = 0


    test_games_all = np.zeros((5000,8),dtype = object)
    test_count = 0

    #For each day a game occurs, the model constructs a training and validation set using all games played previously in the season
    #The model is tested on games occuring the current day     


    for day in range(start_day,stop_day):



        if np.sum(schedule[:,day+1]) != -1*N:
            
            runs = runs + 1

            #Construct S_oracle and Pts


            #Graph constructed according to:

            #Balreira, Miceli, Tegtmeyer,  An Oracle method to predict NFL games,
            #http://ramanujan.math.trinity.edu/bmiceli/research/NFLRankings_revised_print.pdf

            #using data from https://github.com/roclark/sportsipy 


            S_OffDef, A_OffDef = construct_from_data.construct_S_orc(Data_Full,schedule,HomeAway,weights,day)




            #Vegas_Graph = construct_from_data.Vegas_Graph(schedule,Lines,day)
            A_Veg = A_OffDef[0:N+1,N+1:2*(N+1)]

            ARMA = spektral.utils.convolution.normalized_laplacian(A_OffDef)
            ARMA = spektral.utils.convolution.rescale_laplacian(ARMA)

            #ARMA_Veg = spektral.utils.convolution.normalized_laplacian(A_Veg)
            #ARMA_Veg = spektral.utils.convolution.rescale_laplacian(ARMA_Veg)


            epsilon = .001 #hyperparameter to perform PageRank

            #hyperparameters for node2vec
            #Grover, Leskovec, node2vec: Scalable Feature Learning for Networks, July 3, 2016 #arXiv:1607.00653v1 [cs.SI]

            node2vec_dim = 80
            node2vec_p = 1
            node2vec_q = 1

            height = 6
            n2v_walklen = 12
            n2v_numwalks = 20
            n2v_wsize = 10
            n2v_iter = 1
            n2v_workers = 8



            if model_type == 'ncaabwalkod' or model_type == 'ncaab_gat' or model_type == 'ncaab_ARMA' or model_type == 'ncaab_gin':

                G_orc = (1-epsilon)*(S_OffDef) + epsilon*(1/2*(N+1))*np.ones((2*(N+1),2*(N+1)),dtype = float)
                G_orc = utils_data.sto_mat(G_orc)

                PageRank_Off, PageRank_Def = construct_from_data.PageRank(G_orc,TeamList)

                args_N = node2vec_stack.node2vec_input(S_OffDef,'emb/ncaab'+str(year)+'node2vec_OffDef.txt',node2vec_dim,n2v_walklen,
                                                            n2v_numwalks,n2v_wsize,n2v_iter,n2v_workers,node2vec_p,node2vec_q,True,True,False,False)

                featurevecs = node2vec_stack.feat_N(args_N)

                feature_node2vec = np.zeros((2*(N+1),node2vec_dim),dtype = float)

                for j in range(2*(N+1)):
                    feature_node2vec[j,:] = featurevecs[str(j)]



                #if plots == 'on':
                #    utils_data.plot_node2vec(feature_node2vec_Veg,TeamList_Lines,PageRank_Off,PageRank_Def,Vegas_Graph)
                

                if model_type == 'ncaabwalkod':
    
    
                    S_OffDef_stack = np.zeros((2*(N+1),2*(N+1),height),dtype = float)

                    for j in range(height):
                        S_OffDef_stack[:,:,j] = np.linalg.matrix_power(S_OffDef,j+1)


                    x_train, y_train, last_5_train = construct_from_data.Training_Set_ncaabwalkod(Data_Full,Lines,schedule,HomeAway,day,
                                                                                                S_OffDef_stack,feature_node2vec,height,node2vec_dim)


                elif model_type == 'ncaab_gat':



                    x_train, y_train,feature_train,A_Train,last_5_train = construct_from_data.GAT_training_set(Data_Full,
                                                                                                                    Lines,schedule,HomeAway,
                                                                                                                    day,feature_node2vec,
                                                                                                                    A_OffDef)

                    

                elif model_type == 'ncaab_ARMA':

                    x_train, y_train,feature_train,A_Train,last_5_train = construct_from_data.GAT_training_set(Data_Full,
                                                                                                                    Lines,schedule,HomeAway,
                                                                                                                    day,feature_node2vec,
                                                                                                                    ARMA)

                elif model_type == 'ncaab_gin':

                    x_train, y_train,feature_train,A_Train, last_5_train = construct_from_data.gin_training_set(Data_Full,
                                                                                                                    Lines,schedule,HomeAway,
                                                                                                                    day,feature_node2vec,
                                                                                                                    ARMA)



            call_backs = EarlyStopping(monitor='val_loss', min_delta=0, patience=150, verbose=1, restore_best_weights= True)

            #Train the model on all previous games

            #opt = SGD(lr = .001)


            opt = Adam(learning_rate=0.001)         

            if model_type == 'ncaabwalkod':
                model = DCNN_ncaabwalkod(height,node2vec_dim,N)
                model.compile(loss='mean_squared_error', optimizer= opt, metrics=['accuracy'])
                model.fit([x_train,last_5_train],y_train, 
                            epochs = 10, batch_size = 15, validation_split = 0.05,callbacks = [call_backs]) 
            
                model.summary()

            elif model_type == 'ncaab_gat':
                model = ncaab_gat(node2vec_dim,N)
                model.compile(loss='mean_squared_error', optimizer= opt, metrics=['accuracy'])
                model.fit([x_train,feature_train,A_Train,last_5_train],y_train, 
                            epochs = 5,batch_size = 1,validation_split = 0.05,callbacks = [call_backs])
                model.summary()

            elif model_type == 'ncaab_ARMA':
                model = ncaab_ARMA(node2vec_dim,N)
                model.compile(loss='mean_squared_error', optimizer= opt, metrics=['accuracy'])
                model.fit([x_train,feature_train,A_Train,last_5_train],y_train, 
                            epochs = 5,batch_size = 1,validation_split = 0.05,callbacks = [call_backs])
                model.summary()

            elif model_type == 'ncaab_gin':
                model = ncaab_gin(node2vec_dim,N)
                model.compile(loss='mean_squared_error', optimizer= opt, metrics=['accuracy'])
                model.fit([x_train,feature_train,A_Train,last_5_train],y_train, 
                            epochs = 5,batch_size = 1,validation_split = 0.05,callbacks = [call_backs])
                model.summary()



            
            games, gameteams, testgamecount = construct_from_data.Test_Games(TeamList,Data_Full,schedule,HomeAway,Lines,day)



            
            if model_type == 'ncaabwalkod':
                x_test, last_5_test, test_y = construct_from_data.Test_Set_ncaabwalkod(Data_Full,games,testgamecount,S_OffDef_stack,
                                                                            feature_node2vec,height,node2vec_dim,day,year)

                Pred = model.predict([x_test,last_5_test])

                if year < 2021:
                    Eval = model.evaluate([x_test,last_5_test],test_y,verbose=0)
                    loss = loss + Eval[0]

            #test the model, print predictions, the ATS Win %, ML Win % and the MSE for the test set

            elif model_type == 'ncaab_gat':

                

                x_test,feature_test,A_test,last_5_test, test_y = construct_from_data.GAT_test_set(Data_Full,games,
                                                                                                                testgamecount,feature_node2vec,
                                                                                                                A_OffDef,day,year)

                Pred = model.predict([x_test,feature_test,A_test,last_5_test],batch_size=1)
                if year < 2021:
                    Eval = model.evaluate([x_test,feature_test,A_test,last_5_test],test_y,verbose=0,batch_size=1)
                    loss = loss + Eval[0]


            elif model_type == 'ncaab_ARMA':
                x_test,feature_test,A_test,last_5_test, test_y = construct_from_data.GAT_test_set(Data_Full,games,
                                                                                                                testgamecount,feature_node2vec,
                                                                                                                ARMA,day,year)

                Pred = model.predict([x_test,feature_test,A_test,last_5_test],batch_size=1)
                if year < 2021:
                    Eval = model.evaluate([x_test,feature_test,A_test,last_5_test],test_y,verbose=0,batch_size=1)
                    loss = loss + Eval[0]


            elif model_type == 'ncaab_gin':

                

                x_test,feature_test,A_test,last_5_test, test_y = construct_from_data.gin_test_set(Data_Full,games,
                                                                                                                testgamecount,feature_node2vec,
                                                                                                                A_OffDef,day,year)

                Pred = model.predict([x_test,feature_test,A_test,last_5_test],batch_size=1)
                if year < 2021:
                    Eval = model.evaluate([x_test,feature_test,A_test,last_5_test],test_y,verbose=0,batch_size=1)
                    loss = loss + Eval[0]



            results= np.round(Pred,decimals = 1)
            games = np.concatenate((games,Pred),axis = 1)

            test_count = test_count + games.shape[0]

            test_games_all[(test_count - games.shape[0]):test_count,:] = games 


            gameteams = np.concatenate((gameteams,results),axis = 1)


            df = pd.DataFrame(gameteams)
            df.style.set_properties(**{'text-align': 'left'})
            df1 = df.to_string(index=False,header = False)

            print(df1)

            if today == day+1:
                if model_type == 'ncaabwalkod':
                    df.to_excel('predictions/'+datestring+'_DCNN_predictions.xls', header = ['Home','Away',model_type + ' prediction'],index=False)

                if model_type == 'ncaab_gat':
                    df.to_excel('predictions/'+datestring+'_GAT_predictions.xls', header = ['Home','Away',model_type + ' prediction'],index=False)

                if model_type == 'ncaab_ARMA':
                    df.to_excel('predictions/'+datestring+'_ARMA_predictions.xls', header = ['Home','Away',model_type + ' prediction'],index=False)

                if model_type == 'ncaab_gin':
                    df.to_excel('predictions/'+datestring+'_GIN_predictions.xls', header = ['Home','Away',model_type + ' prediction'],index=False)

            
            bet_stats = utils_data.Model_Eval_ML_ATS(games,testgamecount,ats_bets,ats_wins,total_bets,total_wins,
                                                     money_line_wins,moneyline_count,window,push,ties)

            ats_bets = bet_stats[0]
            ats_wins = bet_stats[1]
            money_line_wins = bet_stats[4]
            moneyline_count = bet_stats[5]
            push = bet_stats[7]
            ties = bet_stats[8]


    test_games_all = test_games_all[~np.all(test_games_all == 0, axis=1)]



    print(model_type)
    print(startstring + ' to ' + stopstring)


    #Evaluate model against Vegas


    #if (ats_bets - push) != 0 and (moneyline_count - ties) != 0:

    #ats_win_percentage = ats_wins/(ats_bets - push)
    if (moneyline_count - ties) != 0:
        moneyline_win_percentage = money_line_wins/(moneyline_count - ties)

    #print('ats win %: ' + str(round(ats_win_percentage,3)))
        print('ml win %: ' + str(round(moneyline_win_percentage,3)))
        
    if year < 2021:
        print('MSE: '  + str(round((loss/runs),1)))


    #if today != day + 1:
    #    utils_data.eval_plots(test_games_all,window)



if __name__ == "__main__":
    main()