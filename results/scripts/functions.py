#!/usr/bin/env python
# coding: utf-8

# ## Custom functions

# In[ ]:

import math
import numpy as np
import pandas as pd
from datetime import datetime 
import matplotlib.pyplot as plt
import json
import scipy.stats as sp
import sklearn as sk
from sklearn.linear_model import LinearRegression
import statsmodels.formula.api as smf
from ast import literal_eval
from IPython.display import Markdown as md
import re

def load_metadata():
    # load metadata to correct more errors
    path = '/Users/chrisiyer/_Current/thesis_folder/face_experiment/stimuli/'
    file = 'metadata_all_pairs_mb_altered.json'
    with open(path+file, 'r') as myfile:
        data=myfile.read()
    return json.loads(data)




######## EXCLUSIONS ########

def exclude_nofinish(data):
    
    df = data.copy()
    exclude = []
    trialcounts = []
    for j in df.experiment_id.unique():
        curr = df[(df.experiment_id == j) & (df.trial_type == 'summary')]
        ret = df[(df.experiment_id == j) & (df.trial_type == 'retrieval')]
        if (len(curr) < 1 and len(ret) < 33):
            exclude.append(j)
            trialcounts.append(len(df[df.experiment_id == j]))
    df = df[ [k not in exclude for k in df.experiment_id]]

    print(str(len(exclude)) + " EXPERIMENT IDS EXCLUDED:\n", exclude)
    print(trialcounts)
    return df

def exclude_practice(data, max_wrong = 5):
    df = data.copy()
    exclude = []

    for i in df.experiment_id.unique():
        enc_p = df[(df.experiment_id == i) & (df.trial_type == 'encoding_practice')]
        ret_p = df[(df.experiment_id == i) & (df.trial_type == 'retrieval_practice')]

        ex = False
        for j in range(len(enc_p) - max_wrong):
            if ~enc_p.iloc[j:j+max_wrong,].correct.any():
                ex = True

        for j in range(len(ret_p) - max_wrong):
            if ~ret_p.iloc[j:j+max_wrong,].correct.any():
                ex = True
        if ex: exclude.append(i)

    print(str(len(exclude)) + " EXPERIMENT IDS EXCLUDED:\n", exclude)
    df = df[ [k not in exclude for k in df.experiment_id]]
    return df

def exclude_timeout(data):
    df = data.copy()
    exclude = []
    for i in df.experiment_id.unique():
        enc = df[(df.experiment_id == i) & (df.trial_type == 'encoding')]
        ret = df[(df.experiment_id == i) & (df.trial_type == 'retrieval')]

        if len(enc[enc.timed_out != 1.0]) == 0 or len(ret[ret.timed_out != 1.0]) == 0:
            exclude.append(i)

    print(str(len(exclude)) + " EXPERIMENT IDS EXCLUDED:\n", exclude)
    df = df[ [k not in exclude for k in df.experiment_id]]
    return df

def exclude_chance_retrieval(data, alt, p = 0.05):
    df = data.copy()
    exclude = []
    
    for i_sub in df.experiment_id.unique():
        ret_acc = list(df[(df.experiment_id == i_sub) & 
                          (df.trial_type.str.contains('retrieval'))].correct)
        pv = sp.ttest_1samp(ret_acc, popmean = 0.5, alternative = alt).pvalue
        if pv > p:
            exclude.append(i_sub)           
    df = df[ [k not in exclude for k in df.experiment_id]]
        
    print(str(len(exclude)) + " EXPERIMENT IDS EXCLUDED:\n", exclude)
    return df

def exclude_simulated_chance_retrieval(data, p=0.05, n_iter=10000):
    np.random.seed(0)
    cutoff = np.percentile(np.random.binomial(n=40, p=0.5, size=n_iter)/40, 100*(1-p))
    
    df = data.copy()
    exclude = []
    for i_sub in df.experiment_id.unique():
        ret_acc = data[(data.experiment_id == i_sub) & 
                              (data.trial_type.str.contains('retrieval'))].correct.mean()
        if ret_acc < cutoff:
            exclude.append(i_sub)
            # print('at chance: ', ret_acc.mean())
#         else:
#             print('above chance: ', ret_acc.mean())
                  
    df = df[ [k not in exclude for k in df.experiment_id]] 
    print(str(len(exclude)) + " EXPERIMENT IDS EXCLUDED:\n", exclude)
    return df
    
                           
def age_filter(data):
    df = data.copy()
    exclude = []
    for i_sub in df.experiment_id.unique():
        curr = df[df.experiment_id == i_sub]
        if curr.age.unique()[~pd.isna(curr.age.unique())][0] > 60:
            exclude.append(i_sub)
         
    print("EXPERIMENT IDS EXCLUDED:\n", exclude)
    df = df[ [k not in exclude for k in df.experiment_id]]
    return df


######## OTHER HELPERS ########

def linregna(x,y):
    mask = ~np.isnan(x) & ~np.isnan(y)
    print(sp.linregress(x[mask], y[mask]))

def compute_dp(n_hit, n_old, n_fa, n_new):
    hitrate = n_hit/n_old
    farate = n_fa/n_new
    
    if hitrate == 1 or farate == 0:
        # Hautus's correction
        hitrate = (n_hit+0.5)/(n_old+1)
        farate = (n_fa + 0.5)/(n_old+1)
    
    return sp.norm.ppf(hitrate) - sp.norm.ppf(farate)

def tilt_to_number(tilt):
    num = int(re.search(r'\d+', tilt).group())
    if tilt.endswith('L'):
        num = -num
    return num
    
def number_to_tilt(num):
    if num < 0:
        s = str(-num) + 'L'
    elif num > 0:
        s = str(num) + 'R'
    else: 
        s = '00C'
    return s
        
def get_tilt_change(o_tilt, n_tilt):
    difference = tilt_to_number(o_tilt) - tilt_to_number(n_tilt)
    change = number_to_tilt(difference)

    return {
        'change': change,
        'difference': difference
    }

def get_viewpoint_difference(lrs, uds):
    keyUD = {
        'U': 30,
        'C': 0,
        'D': -30
    }
    one = [tilt_to_number(lrs[0]), keyUD[uds[0]]]
    two = [tilt_to_number(lrs[1]), keyUD[uds[1]]]
    return math.sqrt((one[0]-two[0])**2+(one[1]-two[1])**2) # Pythagorean theorem


def fix_practice_trials(ret):
    # take out the repetitions of a practice trial and only include the first occurrence of that face
    inds = []
    for i in range(1, len(ret)):
        if (ret.iloc[i]['old_identity'] == ret.iloc[i-1]['old_identity']) & (ret.iloc[i]['experiment_id'] == ret.iloc[i-1]['experiment_id']):
            inds.append(i)
    return ret.drop(ret.index[inds])

def filter_correct_encoding(ret,enc):
    rows_to_drop = []
    for i in range(len(ret)):
        old_id = ret.iloc[i].old_identity
        for j in range(len(enc)):
            if enc.iloc[j].oddity_identity == old_id and enc.iloc[j].correct == 0:
                rows_to_drop.append(i)
    return ret.drop(ret.index[rows_to_drop])

def parse_datetime(dt):
    if dt.endswith('M'): # this is almost always true (supposed to be default). but for some subs it saved differently
        return datetime.strptime(dt, '%m/%d/%Y, %I:%M:%S %p')
    elif dt.startswith('2022'):
        return datetime.strptime(dt, '%Y/%m/%d %H:%M:%S') # just for fcsk5v8jclx7u5y4bw6k
    else:
        return datetime.strptime(dt, '%d/%m/%Y, %H:%M:%S') # a3qtdc71as1oehdag7bd, 1k9b4c8lv780d9hqb8xq, n3rptlw5x3sjjrsdf90e

    
######## CALCULATE STATS ########  

# calculate a whole bunch of useful measures for each subject
def get_stats(data, only_correct_encoding = False, only_high_confidence = False):
    df_stat = pd.DataFrame(columns = ['experiment_id','iteration','race',
                                      
                                  'enc_acc', 'enc_acc_w', 'enc_acc_b', 'enc_acc_delta',
                                  'enc_rt', 'enc_rt_w', 'enc_rt_b', 'enc_rt_delta',
                                      
                                  'fil_acc', 'fil_rt', 'fil_acc_animals', 'fil_rt_animals', 
                                  'fil_acc_chairs', 'fil_rt_chairs', 'fil_acc_planes', 'fil_rt_planes',
                                      
                                  'enc_ret_delay',
                                  'ret_acc', 'ret_acc_w', 'ret_acc_b', 'ret_acc_delta',
                                  'ret_rt', 'ret_rt_w', 'ret_rt_b', 'ret_rt_delta',
                                  # breaking down by tilt
                                  'ret_acc_0', 'ret_acc_50', 'ret_acc_p50', 'ret_acc_n50', 
                                  'ret_acc_w_0', 'ret_acc_w_50', 'ret_acc_b_0', 'ret_acc_b_50',
                                  # retrieval distance/error instead of accuracy
                                  'ret_dist', 'ret_dist_0', 'ret_dist_50','ret_dist_w', 'ret_dist_b', 
                                  'ret_dist_w_0', 'ret_dist_w_50', 'ret_dist_b_0', 'ret_dist_b_50',
                                  'ret_dist_delta'
                                 ])
    tilts = data.old_original_tiltLR.unique()[~pd.isna(data.old_original_tiltLR.unique())]
    for tilt in tilts:
        df_stat['ret_acc_enc_' + tilt] = pd.NaT
        df_stat['ret_acc_w_enc_' + tilt] = pd.NaT
        df_stat['ret_acc_b_enc_' + tilt] = pd.NaT
        df_stat['ret_acc_0_enc_' + tilt] = pd.NaT
        df_stat['ret_acc_50_enc_' + tilt] = pd.NaT
        df_stat['ret_dist_enc_' + tilt] = pd.NaT
        df_stat['ret_dist_w_enc_' + tilt] = pd.NaT
        df_stat['ret_dist_b_enc_' + tilt] = pd.NaT
        df_stat['ret_dist_0_enc_' + tilt] = pd.NaT
        df_stat['ret_dist_50_enc_' + tilt] = pd.NaT
    
    for i_sub in data.experiment_id.unique():

        curr = []
        curr.extend([
            i_sub, # experiment_id
            data[data.experiment_id == i_sub].iteration.iloc[0], # iteration
        ]) 
        if len(data[(data.experiment_id == i_sub) & (data.trial_type == 'demographics')]) < 1:
            curr.append('') # race
        else: 
            curr.append(data[(data.experiment_id == i_sub) & (data.trial_type == 'demographics')].race.iloc[0]) # race

        enc = data[(data.experiment_id == i_sub) & (data.trial_type == 'encoding')]
        
        curr.extend([
            enc.correct.mean(),
            enc[['oddity_race','correct']].groupby('oddity_race').correct.mean()['white'],
            enc[['oddity_race','correct']].groupby('oddity_race').correct.mean()['black'],
            enc[['oddity_race','correct']].groupby('oddity_race').correct.mean()['white'] - 
                enc[['oddity_race','correct']].groupby('oddity_race').correct.mean()['black'],
            
            enc.rt.median(),
            enc[['oddity_race','rt']].groupby('oddity_race').rt.median()['white'],
            enc[['oddity_race','rt']].groupby('oddity_race').rt.median()['black'],
            enc[['oddity_race','rt']].groupby('oddity_race').rt.median()['white'] - 
                enc[['oddity_race','rt']].groupby('oddity_race').rt.median()['black'] 
        ])
        
        fil = data[(data.experiment_id == i_sub) & (data.trial_type == 'filler')]
        curr.extend([
            fil.correct.mean(),
            fil.rt.median(),
            fil[['choice_category','correct']].groupby('choice_category').correct.mean()['animals'],
            fil[['choice_category','rt']].groupby('choice_category').rt.median()['animals'],
            fil[['choice_category','correct']].groupby('choice_category').correct.mean()['chairs'],
            fil[['choice_category','rt']].groupby('choice_category').rt.median()['chairs'],
            fil[['choice_category','correct']].groupby('choice_category').correct.mean()['planes'],
            fil[['choice_category','rt']].groupby('choice_category').rt.median()['planes']
        ])
        
        ret = data[(data.experiment_id == i_sub) & ((data.trial_type == 'retrieval') | (data.trial_type == 'retrieval_practice'))]
        ret = fix_practice_trials(ret)
        if (only_correct_encoding): ret = filter_correct_encoding(ret,enc)
        if (only_high_confidence): ret = ret[(ret.response < 25) | (ret.response > 75)]
        
        curr.extend([          
            (parse_datetime(ret.iloc[0]['datetime']) - parse_datetime(enc.iloc[len(enc)-1]['datetime'])).seconds/60, 
                # enc_ret_delay
            ret.correct.mean(),
            ret[['old_race','correct']].groupby('old_race').correct.mean()['white'],
            ret[['old_race','correct']].groupby('old_race').correct.mean()['black'],
            ret[['old_race','correct']].groupby('old_race').correct.mean()['white'] - 
                ret[['old_race','correct']].groupby('old_race').correct.mean()['black'],
            ret.rt.median(),
            ret[['old_race','rt']].groupby('old_race').rt.median()['white'],
            ret[['old_race','rt']].groupby('old_race').rt.median()['black'],
            ret[['old_race','rt']].groupby('old_race').rt.median()['white'] - 
                ret[['old_race','rt']].groupby('old_race').rt.median()['black']
        ])
        
        # accuracy by tilt
        td = abs(ret[ret.tilted].tilt_difference.iloc[0]) # tilt difference, 25 or 50
        
        curr.extend([
            ret[~ret.tilted].correct.mean(),
            ret[ret.tilted].correct.mean(),
            ret[ret.tilt_difference == td].correct.mean(),
            ret[ret.tilt_difference == -td].correct.mean(),
            
            ret[(~ret.tilted) & (ret.old_race == 'white')].correct.mean(),
            ret[(ret.tilted) & (ret.old_race == 'white')].correct.mean(),
            ret[(~ret.tilted) & (ret.old_race == 'black')].correct.mean(),
            ret[(ret.tilted) & (ret.old_race == 'black')].correct.mean(),
            
        ])
        
        # now add slider error/distance metrics 
        k = {1.0: 0, 2.0: 100}
        diffs = [abs(k[ret.iloc[i].correct_response] - ret.iloc[i].response) for i in range(len(ret))]
        ret['diffs'] = diffs
           
        curr.extend([
            ret.diffs.mean(),
            ret[~ret.tilted].diffs.mean(),
            ret[ret.tilted].diffs.mean(),
            ret[ret.old_race == 'white'].diffs.mean(),
            ret[ret.old_race == 'black'].diffs.mean(),
            ret[(~ret.tilted) & (ret.old_race == 'white')].diffs.mean(),
            ret[(ret.tilted) & (ret.old_race == 'white')].diffs.mean(),
            ret[(~ret.tilted) & (ret.old_race == 'black')].diffs.mean(),
            ret[(ret.tilted) & (ret.old_race == 'black')].diffs.mean(),
           ret[ret.old_race == 'white'].diffs.mean() - ret[ret.old_race == 'black'].diffs.mean(), # ret_dist_delta
        ])
        
        # add encoding/original tilt data; this might not work for non-afc data yet
        for tilt in tilts: # should go in same order as df_stat columns
            curr.extend([
                ret[ret.old_original_tiltLR == tilt].correct.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (ret.old_race == 'white')].correct.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (ret.old_race == 'black')].correct.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (~ret.tilted)].correct.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (ret.tilted)].correct.mean(),
                ret[ret.old_original_tiltLR == tilt].diffs.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (ret.old_race == 'white')].diffs.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (ret.old_race == 'black')].diffs.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (~ret.tilted)].diffs.mean(),
                ret[(ret.old_original_tiltLR == tilt) & (ret.tilted)].diffs.mean(),
            ])

        df_stat.loc[len(df_stat)] = curr
               
    return df_stat


def get_stats_byface(data, only_correct_encoding = False, only_high_confidence = False):
    
    meta = load_metadata()
    df_stat = pd.DataFrame(columns = ['identity', 'race', 'gender', 'enc_rt', 'enc_acc', 'ret_rt', 'ret_acc', 
                                      'ret_rt_0', 'ret_acc_0', 'ret_rt_50', 'ret_acc_50',
                                     'ret_dist', 'ret_dist_0', 'ret_dist_50', 'mb'])
    
    ids = data.old_identity.unique() # all ids that have data to them
    
    for i_id in ids[~np.isnan(ids)]:
        enc = data[data.oddity_identity == i_id] # all encoding trials
        ret = data[data.old_identity == i_id] # all retrieval trials
        ret = fix_practice_trials(ret)
        if only_correct_encoding: 
            enc_correct = enc[enc.correct == 1]
            ret = ret[ret.experiment_id.isin(enc_correct.experiment_id)]
        if (only_high_confidence): ret = ret[(ret.response < 25) | (ret.response > 75)]
            
        k = {1.0: 0, 2.0: 100}
        diffs = [abs(k[ret.iloc[i].correct_response] - ret.iloc[i].response) for i in range(len(ret))]
        ret['diffs'] = diffs
        _id = str(int(i_id)).zfill(3)

        df_stat.loc[len(df_stat)] = [ 
            _id,
            meta[_id]['race_common'],
            meta[_id]['gender_common'],
            enc.rt.median(), 
            enc.correct.mean(), 
            ret.rt.median(), 
            ret.correct.mean(),
            ret[~ret.tilted].rt.median(),
            ret[~ret.tilted].correct.mean(),
            ret[ret.tilted].rt.median(),
            ret[ret.tilted].correct.mean(),
            ret.diffs.mean(),
            ret[~ret.tilted].diffs.mean(),
            ret[ret.tilted].diffs.mean(),
            meta[_id]['mb_version1_gray_lm'] 
        ]
    return df_stat
   
    
def get_encoding_split_stats(data, only_correct_encoding=False, only_high_confidence = False):
    stats_enc_split = pd.DataFrame(columns = [
        'experiment_id', 
        
        'enc_acc_high',  'enc_acc_low', 'enc_acc_delta',
        'enc_rt_high','enc_rt_low','enc_rt_delta', 
        
        'ret_acc_high', 'ret_acc_low', 'ret_acc_delta', 
        'ret_acc_high_0', 'ret_acc_low_0', 'ret_acc_high_50', 'ret_acc_low_50', 
        'ret_dist_high', 'ret_dist_low', 'ret_dist_delta',
        'ret_dist_high_0', 'ret_dist_low_0', 'ret_dist_high_50', 'ret_dist_low_50', 
        ])
    
    for i_sub in data.experiment_id.unique():
        
        enc = data[(data.experiment_id == i_sub) & (data.trial_type == 'encoding')]
        high_rt_ids = []
        for i in range(len(enc)):
            if enc.iloc[i].rt >= np.median(enc.rt): high_rt_ids.append(enc.iloc[i].oddity_identity)

        ret = data[(data.experiment_id == i_sub) & ((data.trial_type == 'retrieval') | (data.trial_type == 'retrieval_practice'))]
        ret = fix_practice_trials(ret)
        if only_correct_encoding: ret = filter_correct_encoding(ret,enc)
        
        k = {1.0: 0, 2.0: 100}
        diffs = [abs(k[ret.iloc[i].correct_response] - ret.iloc[i].response) for i in range(len(ret))]
        ret['diffs'] = diffs

        enc1 = enc[enc.oddity_identity.isin(high_rt_ids)]
        enc2 = enc[~enc.oddity_identity.isin(high_rt_ids)]         
        ret1 = ret[ret.old_identity.isin(high_rt_ids)]
        ret2 = ret[~ret.old_identity.isin(high_rt_ids)]

        # now, get statistics
        curr = [
            i_sub,
            
            enc1.correct.mean(),
            enc2.correct.mean(),
            enc1.correct.mean() - enc2.correct.mean(),
            enc1.rt.median(),
            enc2.rt.median(),
            enc1.rt.median() - enc2.rt.median(),
            
            ret1.correct.mean(),
            ret2.correct.mean(),
            ret1.correct.mean() - ret2.correct.mean(),
            ret1[~ret1.tilted].correct.mean(),
            ret2[~ret2.tilted].correct.mean(),
            ret1[ret1.tilted].correct.mean(),
            ret2[ret2.tilted].correct.mean(),

            ret1.diffs.mean(),
            ret2.diffs.mean(),
            ret1.diffs.mean() - ret2.diffs.mean(),
            ret1[~ret1.tilted].diffs.mean(),
            ret2[~ret2.tilted].diffs.mean(),
            ret1[ret1.tilted].diffs.mean(),
            ret2[ret2.tilted].diffs.mean(),
        ]
        stats_enc_split.loc[len(stats_enc_split)] = curr
    return stats_enc_split


###################### RESULTS SUMMARY ######################
def results(data):
    data_dist = data[~pd.isna(data.ret_dist_delta)]
    
    print('\n--Encoding--')
    print(' - accuracy by race (Wilcoxon):')
    print(sp.wilcoxon(data.enc_acc_delta))
    print(' - RT by race (Wilcoxon):')
    print(sp.wilcoxon(data.enc_rt_delta))
    print(' - RT vs. accuracy (OLS):')
    print(sp.linregress(x=data.enc_rt, y=data.enc_acc))
    
    print('\n--Retrieval--')
    print(' - accuracy by tilt (Wilcoxon):')
    print(sp.wilcoxon(data.ret_acc_0, data.ret_acc_50))
    print(' - accuracy by race (Wilcoxon):')
    print(sp.wilcoxon(data.ret_acc_w, data.ret_acc_b))
    print(' - dist by race (Wilcoxon):')
    print(sp.wilcoxon(data_dist.ret_dist_w, data_dist.ret_dist_b))
    print(' - accuracy by tilt * race (OLS):')
    print(show_model_parameters(smf.ols("accuracy ~ tilt * race", data = {
        'accuracy': np.concatenate([data.ret_acc_w_0, data.ret_acc_b_0, 
                                    data.ret_acc_w_50, data.ret_acc_b_50]), 
        'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
        'race': np.concatenate([np.repeat(1, len(data)), np.repeat(0, len(data)), 
                                np.repeat(1, len(data)), np.repeat(0, len(data))])
        }),md_bool=False))

    print('\n--Encoding-Retrieval--')
    print(' - ∆enc_rt vs ∆ret_acc (OLS):')
    print(sp.linregress(x=data.enc_rt_delta, y=data.ret_acc_delta))
    print(' - ∆enc_acc vs ∆ret_acc (OLS):')
    print(sp.linregress(x=data.enc_acc_delta, y=data.ret_acc_delta))
    print(' - ∆enc_rt vs ∆ret_dist (OLS):')
    print(sp.linregress(x=data_dist.enc_rt_delta, y=data_dist.ret_dist_delta))
    print(' - ∆enc_acc vs ∆ret_dist (OLS):')
    print(sp.linregress(x=data_dist.enc_acc_delta, y=data_dist.ret_dist_delta))
    
def results_split(data):
    data_dist = data[~pd.isna(data.ret_dist_delta)]
    
    print('\n--Encoding--')
    print('accuracy by group (Wilcoxon):')
    print(sp.wilcoxon(data.enc_acc_delta))
    print('RT by group (Wilcoxon):')
    print(sp.wilcoxon(data.enc_rt_delta))

    print('\n--Retrieval--')
    print('accuracy by group (Wilcoxon):')
    print(sp.wilcoxon(data.ret_acc_low, data.ret_acc_high))
    print('dist by group (Wilcoxon):')
    print(sp.wilcoxon(data_dist.ret_dist_low, data_dist.ret_dist_high))
    print('accuracy by tilt*group (OLS):')
    print(show_model_parameters(smf.ols("accuracy ~ tilt * rt_group", data = {
        'accuracy': np.concatenate([data.ret_acc_low_0, data.ret_acc_high_0, 
                                    data.ret_acc_low_50, data.ret_acc_high_50]), 
        'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
        'rt_group': np.concatenate([np.repeat(1, len(data)), np.repeat(0, len(data)), 
                                np.repeat(1, len(data)), np.repeat(0, len(data))])
        }),md_bool=False))

    print('\n--Encoding-Retrieval--')
    print('∆enc_rt vs ∆ret_acc (OLS):')
    print(sp.linregress(x=data.enc_rt_delta, y=data.ret_acc_delta))
    print('∆enc_acc vs ∆ret_acc (OLS):')
    print(sp.linregress(x=data.enc_acc_delta, y=data.ret_acc_delta))
    print('∆enc_rt vs ∆ret_dist (OLS):')
    print(sp.linregress(x=data_dist.enc_rt_delta, y=data_dist.ret_dist_delta))
    print('∆enc_acc vs ∆ret_dist (OLS):')
    print(sp.linregress(x=data_dist.enc_acc_delta, y=data_dist.ret_dist_delta))
    
    
#################################### PLOTTING ####################################

def rand_jitter(arr, stdev=1):
    return arr + np.random.randn(len(arr)) * stdev

def get_sig(pvalue):
    if pvalue < 0.001:
        return "***"
    elif pvalue < 0.01:
        return "**"
    elif pvalue < 0.05:
        return "*"
    else:
        return "n.s."
    
######## MAIN SUMMARY ########

def demographics_plot(data):
    
    races = data[data.trial_type == 'demographics'].race.unique()
    race_counts = []
    for r in races:
        race_counts.append(len(data[(data.trial_type == 'demographics') & (data.race == r)]))
        
    genders = data[data.trial_type == 'demographics'].gender.unique()
    gender_counts = []
    for g in genders:
        gender_counts.append(len(data[(data.trial_type == 'demographics') & (data.gender == g)]))
        
    fig, ax = plt.subplots(1,2, figsize = (8,4))
    fig.suptitle('Subject demographics')
    ax[0].set_title('Reported race/ethnicity')
    ax[0].bar(races, race_counts)
    ax[0].set_xticks(range(len(races)))
    ax[0].set_xticklabels(races, rotation = 90)
    ax[1].set_title('Reported gender')
    ax[1].bar(genders, gender_counts)
    ax[1].set_xticks(range(len(genders)))
    ax[1].set_xticklabels(genders, rotation = 90)
    plt.show()
    
    print(races)
    print(race_counts)
    print(str(gender_counts[0]) + ' women, ' + str(gender_counts[1]) + ' men')
    


# In[1]:

def summary_plot(data):
    sz = (12,6)
    j = 0.1
    al = 0.2

    fig, ax = plt.subplots(1,2, figsize = sz, dpi=80)
    plt.setp(ax, xlabel = 'Task')
    
    ax[0].set_title('Task Accuracy, n=' + str(len(data)))
    ax[0].boxplot([data['enc_acc'], data['fil_acc'], data['ret_acc']])
    ax[0].set_xticks([1,2,3], ['Encoding', 'Filler', 'Retrieval'])
    ax[0].scatter(
        x= np.concatenate( (
            rand_jitter(np.repeat(1, len(data)), j),
            rand_jitter(np.repeat(2, len(data)), j),
            rand_jitter(np.repeat(3, len(data)), j) )), 
        y = np.concatenate( (
            data['enc_acc'],
            data['fil_acc'],
            data['ret_acc'])),
        alpha = al, color = 'gray'
        )
    ax[0].set_ylabel('Accuracy (%)')
    ax[0].set_ylim((0,1))
    ax[0].plot([0, 4],[0.5, 0.5], color='red', linestyle=':')

    ax[1].set_title('Task RT, n=' + str(len(data)))
    ax[1].boxplot([data['enc_rt'], data['fil_rt'], data.ret_rt[~pd.isna(data.ret_rt)]] )
    ax[1].set_xticks([1,2,3], ['Encoding', 'Filler', 'Retrieval'])
    ax[1].scatter(
        x= np.concatenate( (
            rand_jitter(np.repeat(1, len(data)), j),
            rand_jitter(np.repeat(2, len(data)), j),
            rand_jitter(np.repeat(3, len(data)), j) )), 
        y = np.concatenate( (
            data['enc_rt'],
            data['fil_rt'],
            data['ret_rt'])),
        alpha = al, color = 'gray'
        )
    ax[1].set_ylabel('RT (ms)')
    ax[1].set_ylim(bottom=0)
    
    plt.show()


def encoding_plots(data, save=False, dpi=200):
    color = ['blue','green']
    fig, ax = plt.subplots(1,3, figsize = (15,6), dpi=80)
    fig.suptitle('Encoding Performance')
    
    for c in [0,1,2]:
        if c < 2:
            ax[c].set_xticks([0,1])
            ax[c].set_xticklabels(['white','black'])
            ax[c].set_xlabel('Stimulus race classification')
        else:
            ax[c].set_ylabel('Mean accuracy')
            ax[c].set_ylim([0,1])
        
    
    # Accuracy
    ax[0].set_title('(a) Accuracy')
    ax[0].set_ylabel('Mean accuracy')
    ax[0].set_ylim([0,1.2])
    ax[0].set_yticks(np.linspace(0,1,6))
    ax[0].errorbar(x= [0, 1], 
                   y = [data['enc_acc_w'].mean(), data['enc_acc_b'].mean()],
                   yerr = [data['enc_acc_w'].std(), data['enc_acc_b'].std()], capsize =5, marker = 'o', 
                   mfc = 'black', mec='black', ms =8,ecolor='black',color='black')
    ax[0].scatter(x = rand_jitter(np.repeat(0, len(data)), 0.05),y = data['enc_acc_w'],color=color[0],alpha=0.4)
    ax[0].scatter(x = rand_jitter(np.repeat(1, len(data)), 0.05),y = data['enc_acc_b'],color=color[1],alpha=0.2)
    h = 0.02
    y = 1.1
    ax[0].plot([0, 0, 1, 1], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(data.enc_acc_delta).pvalue)
    ax[0].text(0.5,y+h*2, sig, ha ='center', fontsize=10)
        
    
    # RT
    ax[1].set_title('(b) Response time')
    ax[1].set_ylabel('Median RT (ms)')
    ax[1].set_ylim([min(data.enc_rt) - 500,max(data.enc_rt) + 1000])
    ax[1].errorbar(x= [0, 1], 
                   y = [data['enc_rt_w'].mean(), data['enc_rt_b'].mean()],
                   yerr = [data['enc_rt_w'].std(), data['enc_rt_b'].std()], capsize =5, marker = 'o', 
                   mfc = 'black', mec='black', ms =8,ecolor='black',color='black')
    ax[1].scatter(x = rand_jitter(np.repeat(0, len(data)), 0.05),y = data['enc_rt_w'],color=color[0],alpha=0.4)
    ax[1].scatter(x = rand_jitter(np.repeat(1, len(data)), 0.05),y = data['enc_rt_b'],color=color[1],alpha=0.2)
    ax[1].set_xticks([0,1], ['white', 'black'])
    h = 100
    y = 6000
    ax[1].plot([0, 0, 1, 1], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(data.enc_rt_delta).pvalue)
    ax[1].text(0.5,y+h*2, sig, ha ='center', fontsize=10)

    reg = sp.linregress(x=data.enc_rt, y=data.enc_acc)
    ax[2].set_title('(c) Response time vs. Accuracy')
    ax[2].set_xlabel('Median RT (ms)')
    ax[2].set_ylabel('Mean accuracy')
    if reg.pvalue < 0.05:
        ax[2].plot([0, 6000], [0*reg.slope+reg.intercept,6000*reg.slope+reg.intercept], color='red', ls = ':')
    #ax[0,2].text(5800,0.9, '*', ha ='center', fontsize=15)
    ax[2].scatter(data.enc_rt, data.enc_acc, color = 'gray')
    ax[2].set_xlim([0,6000])

    if save: plt.savefig('/Users/chrisiyer/Downloads/Fig1', dpi=dpi)
    plt.show()
 

def retrieval_plots(data, slider = False, mb=False, save=False, dpi=200):
    
    if slider: 
        measure = 'ret_dist'
        ylab = 'Retrieval slider error'
    else: 
        measure = 'ret_acc'
        ylab = 'Retrieval accuracy'
    if mb: 
        title = 'Residuals of ' + ylab
        ylab = 'Residuals of ' + ylab
    else: 
        title = ylab
    
    al = 0.2 #alpha
    buffer = 0.75
    jit = 2
    c = ['blue', 'green']

    fig, ax = plt.subplots(1,3, figsize = (15,6), dpi=80)
    fig.suptitle('Retrieval Performance')
    if slider: 
        plt.setp(ax, ylim = [0,100], xticks = ([0,50]))
    else:
        plt.setp(ax, ylim = [0,1], xticks = ([0,50]))
    for a in ax[[0,2]]:
        a.set_xticklabels(['untilted', 'tilted'])
        a.set_xlabel('Viewpoint at retrieval')
    
    ax[0].set_ylabel(ylab, size ='large')
    ax[0].set_title('(a) By viewpoint')
    ax[0].errorbar(x= [0, 50], 
                   y = data[[measure+'_0', measure+'_50']].mean(), 
                   yerr = data[[measure+'_0', measure+'_50']].std(),
                   capsize =5, marker = 'o', mfc = 'red', mec='red', ms =8,ecolor='black',color='black')
    ax[0].scatter(x = np.array([rand_jitter(np.repeat(0, len(data)), jit), 
                                rand_jitter(np.repeat(50, len(data)), jit)]).flatten(),
                  y = np.array([data[measure+'_0'].to_numpy(), data[measure+'_50'].to_numpy()]).flatten(),
                                 color='gray',alpha=0.2)
    ax[0].plot([ax[0].get_xlim()[0],ax[0].get_xlim()[1]],[0.5,0.5], color = 'red', ls = '--')

    ax[1].set_title('(b) By race classification')
    ax[1].set_xlabel('Stimulus race classification')
    ax[1].errorbar(x= [0,50], y = data[[measure + '_w', measure + '_b']].mean(), 
                   yerr = data[[measure + '_w', measure + '_b']].std(),
                   capsize =5, marker = 'o', mfc = 'black', mec='black', ms =8, ecolor='black', color='black')
    ax[1].scatter(x = rand_jitter(np.repeat(0, len(data)), jit), 
                  y =data[measure+'_w'], color=c[0], alpha=al)
    ax[1].scatter(x = rand_jitter(np.repeat(50, len(data)), jit), 
                  y = data[measure+'_b'], color=c[1], alpha=al)
    ax[1].set_xticklabels(['white', 'black'])
    
    h = 0.01
    y = 0.9
    ax[0].plot([0, 0, 50, 50], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(data.ret_acc_0, data.ret_acc_50).pvalue)
    ax[0].text(25,y+h*2, sig, ha ='center', fontsize=10)
    sig = get_sig(sp.wilcoxon(data.ret_acc_w, data.ret_acc_b).pvalue)
    ax[1].plot([0, 0, 50, 50], [y, y+h, y+h, y], lw=.5, color = 'black')
    ax[1].text(25,y+h*2, sig, ha ='center', fontsize=10)

    ax[2].set_title('(c) By viewpoint x race')
    ax[2].errorbar(x = np.array([0, 50])-buffer, 
                   y = data[[measure + '_w_0', measure + '_w_50']].mean(),
                   yerr = data[[measure + '_w_0', measure + '_w_50']].std(), 
                   capsize =5, marker = 'o', mfc = c[0], mec=c[0], ms =8,ecolor=c[0],color=c[0], label = 'white')
    ax[2].errorbar(x = np.array([0, 50])+buffer, 
                   y = data[[measure + '_b_0', measure + '_b_50']].mean(),
                   yerr = data[[measure + '_b_0', measure + '_b_50']].std(),
                   capsize =5, marker = 'o', mfc = c[1], mec=c[1], ms =8,ecolor=c[1],color=c[1], label = 'black')
    ax[2].scatter(x = np.array([rand_jitter(np.repeat(0-buffer, len(data)), jit/10), 
                                rand_jitter(np.repeat(50-buffer, len(data)), jit/10)]).flatten(),
                  y = np.array([data[measure+'_w_0'].to_numpy(), data[measure+'_w_50'].to_numpy()]).flatten(), 
                  color=c[0], alpha = 0.02)
    ax[2].scatter(x = np.array([rand_jitter(np.repeat(0+buffer, len(data)), jit/10), 
                                rand_jitter(np.repeat(50+buffer, len(data)), jit/10)]).flatten(),
                  y =  np.array([data[measure+'_b_0'].to_numpy(), data[measure+'_b_50'].to_numpy()]).flatten(),
                  color=c[1], alpha = 0.02)
    ax[2].set_xticks([0,50])
    sig = get_sig(
        smf.ols("accuracy ~ tilt * race", data = {
        'accuracy': np.concatenate([data.ret_acc_w_0, data.ret_acc_b_0, 
                                    data.ret_acc_w_50, data.ret_acc_b_50]), 
        'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
        'race': np.concatenate([np.repeat(1, len(data)), np.repeat(0, len(data)), 
                                np.repeat(1, len(data)), np.repeat(0, len(data))])
        }).fit().pvalues[-1])
    ax[2].text(25,0.58, sig, ha ='center', fontsize=10)
    ax[2].legend()
    
    if save: plt.savefig('/Users/chrisiyer/Downloads/Fig2', dpi=dpi)
    plt.show() 

    
def encoding_delta_plot(df_stat, slider=False, save=False, dpi=200):
    fig, ax = plt.subplots(1, 2, figsize=(10,5), dpi=80)
    fig.suptitle('Relating Encoding and Retrieval Bias')
    if slider:
        measure = 'ret_dist_delta'
        ylab = '∆ Retrieval slider error (white - black)'
    else: 
        measure = 'ret_acc_delta'
        ylab = '∆ Retrieval accuracy (white - black)'
        
        
    ax[0].set_title('(a) Encoding accuracy')
    ax[0].set_xlabel('∆ Encoding accuracy (white - black; ms)')
    ax[0].set_ylabel(ylab)
    ax[0].scatter(df_stat.enc_acc_delta, df_stat[measure])
    lr = sp.linregress(df_stat.enc_acc_delta, df_stat[measure])
    (x1,x2) = ax[0].get_xlim()
    if lr.pvalue < 0.05:
        ax[0].plot([x1,x2], np.array([x1,x2])*lr.slope + lr.intercept, color='red', ls='--')
    
    ax[1].set_title('(b) Encoding response time')
    ax[1].set_xlabel('∆ Median encoding RT (white - black)')
    ax[1].set_ylabel(ylab)
    ax[1].scatter(df_stat.enc_rt_delta, df_stat[measure])
    lr = sp.linregress(df_stat.enc_rt_delta, df_stat[measure])
    (x1,x2) = ax[1].get_xlim()
    if lr.pvalue < 0.05:
        ax[1].plot([x1,x2], np.array([x1,x2])*lr.slope + lr.intercept, color='red', ls='--')
        
    if save: plt.savefig('/Users/chrisiyer/Downloads/Fig3', dpi=dpi)
    plt.show()
    
def tilt_chance_hist(data):
    
    b= 15
    x_axis = np.linspace(0,1,50)
    fig, ax = plt.subplots(1,2, figsize= (16,4))
    fig.suptitle('Core dataset, retrieval accuracy (untilted/tilted) against std-matched Gaussian')
    plt.setp(ax, ylabel='count', xlabel = 'Retrieval accuracy', xlim=[0,1])
    
    ax[0].set_title('Untilted (tilt = 0˚)')
    ax[0].hist(data.ret_acc_0, bins = b)
    ax[0].plot(x_axis, sp.norm.pdf(x_axis, 0.5, data.ret_acc_0.std()), color ='red', ls = '--')
   
    ax[1].set_title('Tilted (tilt = 50˚)')
    ax[1].hist(data.ret_acc_50, bins = b)
    ax[1].plot(x_axis, sp.norm.pdf(x_axis, 0.5, data.ret_acc_50.std()), color ='red', ls = '--')
    plt.show()

    
    
######## OTHER PLOTS ########

def encoding_view_helper(enc, colname, xlab, title_addon):
    acc = pd.DataFrame(columns = enc[colname].unique())
    rt = pd.DataFrame(columns = enc[colname].unique())
    for i_sub in enc.experiment_id.unique():
        curr = enc[enc.experiment_id == i_sub]
        acc.loc[curr.experiment_id.iloc[0]] = curr.groupby(colname).correct.mean()
        rt.loc[curr.experiment_id.iloc[0]] = curr.groupby(colname).rt.median()
        
    data = {
        'data_acc': acc.transpose().mean(axis=1),
        'std_acc': acc.transpose().std(axis=1),
        'data_rt': rt.transpose().mean(axis=1),
        'std_rt': rt.transpose().std(axis=1)
    }
    fig, ax = plt.subplots(1,2, figsize = (12,4))
    plt.setp(ax, xlabel = xlab)
    fig.suptitle('Encoding performance by ' + title_addon)
    ax[0].set_title('Accuracy')
    ax[0].errorbar(x = data['data_acc'].index, y = data['data_acc'], yerr= data['std_acc'],
                  capsize = 5, marker = 'o', mfc = 'red', mec='red', ms=8,ecolor='black',color='black', ls='none')
    ax[0].set_ylim(0,1)
    ax[0].set_ylabel('Hit rate (%)')
    for tick in ax[0].get_xticklabels():
         tick.set_rotation(45)
    ax[1].set_title('RT')
    ax[1].errorbar(x = data['data_rt'].index, y = data['data_rt'], yerr= data['std_rt'],
                  capsize = 5, marker = 'o', mfc = 'red', mec='red', ms=8,ecolor='black',color='black', ls='none')
    ax[1].set_ylim(0,5000)
    for tick in ax[1].get_xticklabels():
         tick.set_rotation(45)
    ax[1].set_ylabel('RT (ms)')
    plt.show()
    

def encoding_view_plots(df):
    enc = df[df.trial_type == 'encoding']
    
    enc['oddity_tilt'] = enc['oddity_tiltLR'] + '_' + enc['oddity_tiltUD']
    encoding_view_helper(enc, 'oddity_tilt',
                        xlab = 'Oddity viewpoint',
                        title_addon = 'oddity viewpoint')
    
    enc['typical_offset'] = pd.NaT
    for i in range(len(enc)):
        enc['typical_offset'].iloc[i]= get_viewpoint_difference(
            literal_eval(enc.iloc[i].typicals_tiltsLR),
            literal_eval(enc.iloc[i].typicals_tiltsUD))
    encoding_view_helper(enc, 'typical_offset', 
                         xlab = 'Typical-typical viewpoint difference',
                         title_addon = 'typical offset')
    enc['oddity_offset'] = pd.NaT
    for i in range(len(enc)):
        diff1 = get_viewpoint_difference(
            [enc.iloc[i].oddity_tiltLR, literal_eval(enc.iloc[i].typicals_tiltsLR)[0]],
            [enc.iloc[i].oddity_tiltUD, literal_eval(enc.iloc[i].typicals_tiltsUD)[0]])
        diff2 = get_viewpoint_difference(
            [enc.iloc[i].oddity_tiltLR, literal_eval(enc.iloc[i].typicals_tiltsLR)[1]],
            [enc.iloc[i].oddity_tiltUD, literal_eval(enc.iloc[i].typicals_tiltsUD)[1]])
        
        enc['oddity_offset'].iloc[i]= np.min([diff1,diff2])
        
    encoding_view_helper(enc, 'oddity_offset', 
                         xlab = 'Minimum oddity-typical viewpoint difference',
                         title_addon = 'oddity-typical offset')
    
    
    
def filler_plot(data):
    sz = (12,6)
    j = 0.01

    fig, ax = plt.subplots(1,2, figsize = sz)
    fig.suptitle('Filler task')
    plt.setp(ax, xticklabels=["Animals", "Chairs", "Planes"], xlabel = 'Stimulus Category')
    
    ax[0].set_title('Accuracy')
    ax[0].boxplot([data['fil_acc_animals'], data['fil_acc_chairs'], data['fil_acc_planes']] )
    ax[0].scatter(
        x= np.concatenate( (
            rand_jitter(np.repeat(1, len(data)), j),
            rand_jitter(np.repeat(2, len(data)), j),
            rand_jitter(np.repeat(3, len(data)), j) )), 
        y = np.concatenate( (
            data['fil_acc_animals'],
            data['fil_acc_chairs'],
            data['fil_acc_planes'])),
        alpha = 0.4, color = 'gray'
        )
    ax[0].set_ylabel('Accuracy (%)')
    ax[0].set_ylim((0,1))

    ax[1].set_title('Response time')
    ax[1].boxplot([data['fil_rt_animals'], data['fil_rt_chairs'], data['fil_rt_planes']] )
    ax[1].scatter(
        x= np.concatenate( (
            rand_jitter(np.repeat(1, len(data)), j),
            rand_jitter(np.repeat(2, len(data)), j),
            rand_jitter(np.repeat(3, len(data)), j) )), 
        y = np.concatenate( (
            data['fil_acc_animals'],
            data['fil_acc_chairs'],
            data['fil_acc_planes'])),
        alpha = 0.4, color = 'gray'
        )
    ax[1].set_ylabel('RT (ms)')
    ax[1].set_ylim(bottom=0)
    
    plt.show()
    
    
def filler_delay_plot(data):
    # enc_ret_delay vs. ret_acc
    fig, ax = plt.subplots(1, 1, figsize=(5,5))
    fig.suptitle('Encoding-Retrieval Delay vs. Retrieval Accuracy')
    ax.scatter(data.enc_ret_delay/60, data.ret_acc)
    ax.set_xlabel('Encoding-Retrieval Delay (minutes)')
    ax.set_ylabel('Retrieval Accuracy (%)')
    plt.show()


def encoding_filler_plot(df_stat):
    # encoding rt and accuracy vs. filler rt and accuracy
    sz = (8,8)

    fig, ax = plt.subplots(2, 2, figsize=sz)
    fig.suptitle('Encoding vs. Filler')
    
    ax[0][0].set_title('Encoding RT vs. Filler RT')
    ax[0][0].scatter(df_stat.enc_rt, df_stat.fil_rt)
    
    ax[0][1].set_title('Encoding RT vs. Filler Accuracy')
    ax[0][1].scatter(df_stat.enc_rt, df_stat.fil_acc)
    
    ax[1][0].set_title('Encoding Accuracy vs. Filler RT')
    ax[1][0].scatter(df_stat.enc_acc, df_stat.fil_rt)
    
    ax[1][1].set_title('Encoding Accuracy vs. Filler Accuracy')
    ax[1][1].scatter(df_stat.enc_acc, df_stat.fil_acc)
    
#     x = [min(df_stat.enc_acc), max(df_stat.enc_acc)]
#     y = np.array(x)*0.2957676255992874 + 0.6621217477696362
    
#     ax[1][1].plot(x,y, color='red', linestyle=':')
    
    plt.show()

    
def slider_response_plot(data):
    ret = data[((data.trial_type == 'retrieval') | (data.trial_type == 'retrieval_practice'))]
    ret = fix_practice_trials(ret)
    d = ret[['response','tilted', 'correct_response']]
    for i in range(len(d)):
        if d.correct_response.iloc[i] == 1:
            # flip it
            d.iloc[i,0] = 100 - d.iloc[i,0]
    
    plt.figure(figsize = (10,5))
    plt.suptitle('Distribution of slider responses')
    plt.xlabel('High confidence incorrect -> High confidence correct')
    plt.ylabel('Count')
    
    plt.hist(d[d.tilted].response, color = 'red', label = 'tilted', alpha = 0.4, bins = 40)
    plt.hist(d[~d.tilted].response, color = 'blue', label = 'untilted', alpha = 0.4, bins = 40)
    #plt.xticks(np.arange(0,110,10))
    plt.legend()
    plt.show() 
    
def hits_confidence_by_tilt_plot(df):
    t = []
    n = []
    for i_sub in df.experiment_id.unique():
        ret = df[(df.experiment_id == i_sub) & ((df.trial_type == 'retrieval') | (df.trial_type == 'retrieval_practice'))]
        t.append(ret[(ret.tilted) & (ret.correct)].response.mean())
        n.append(ret[(~ret.tilted) & (ret.correct)].response.mean())
        
    plt.figure(figsize=(4,4))
    plt.suptitle('Confidence by tilt condition on hit trials (retrieval)')
    plt.boxplot([np.array(n)[~np.isnan(n)], np.array(t)[~np.isnan(t)]])
    plt.scatter(rand_jitter(np.repeat(1, len(n)), 0.05), n, alpha = 0.1)
    plt.scatter(rand_jitter(np.repeat(2, len(t)), 0.05), t, alpha = 0.1)
    plt.xticks([1,2], ['untilted', 'tilted'])
    
    h = 1
    y = 110
    plt.plot([1, 1, 2, 2], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(n,t).pvalue)
    plt.text(1.5,y+h*2, sig, ha ='center', fontsize=10)
    plt.show()
    print(sp.wilcoxon(n,t))
    
def retrieval_race_scatter_plot(data, slider = False):
    plt.figure(figsize = (4,4))
    plt.suptitle('Retrieval accuracy white vs. black')

    if slider: 
        plt.scatter(data.ret_dist_w, data.ret_dist_b)
        plt.plot([50,50], [0,100], color='red', linestyle = ':')
        plt.plot([0,100], [50,50], color='red', linestyle = ':')
        plt.xlabel('Slider error on white faces (%)')
        plt.ylabel('Slider error on black faces (%)')
    else:
        plt.scatter(data.ret_acc_w, data.ret_acc_b)
        plt.plot([0.5,0.5], [0,1], color='red', linestyle = ':')
        plt.plot([0,1], [0.5,0.5], color='red', linestyle = ':')
        plt.xlabel('Retrieval accuracy on white faces (%)')
        plt.ylabel('Retrieval accuracy on black faces (%)')
    plt.show()

def encoding_retrieval_plot(df_stat):
    # encoding rt and accuracy vs. retrieval rt and accuracy
    sz = (10,12)

    fig, ax = plt.subplots(3, 2, figsize=sz)
    fig.suptitle('Encoding vs. Retrieval')
    
    ax[0][0].set_title('Encoding RT vs. Retrieval RT')
    ax[0][0].scatter(df_stat.enc_rt, df_stat.ret_rt)
    
    ax[0][1].set_title('Encoding RT vs. Retrieval Accuracy')
    ax[0][1].scatter(df_stat.enc_rt, df_stat.ret_acc)
    
    ax[1][0].set_title('Encoding Accuracy vs. Retrieval RT')
    ax[1][0].scatter(df_stat.enc_acc, df_stat.ret_rt)
    
    ax[1][1].set_title('Encoding Accuracy vs. Retrieval Accuracy')
    ax[1][1].scatter(df_stat.enc_acc, df_stat.ret_acc)
    
    ax[2][0].set_title('Encoding RT vs. Retrieval Slider Error')
    ax[2][0].scatter(df_stat.enc_rt, df_stat.ret_dist)
    
    ax[2][1].set_title('Encoding Accuracy vs. Retrieval Slider Error')
    ax[2][1].scatter(df_stat.enc_acc, df_stat.ret_dist)
    
    plt.show()

def serial_position_plot(data):
    ret = data[((data.trial_type == 'retrieval') | (data.trial_type == 'retrieval_practice'))]
    ret = fix_practice_trials(ret)
    m = ret[['old_original_index','correct']].groupby('old_original_index').mean()
    s = ret[['old_original_index','correct']].groupby('old_original_index').std()
    
    plt.plot(m)
    plt.suptitle('Recency / Primacy Effects')
    plt.xlabel('Serial position at encoding')
    plt.ylabel('Average retrieval hitrate (%)')
    plt.ylim([0,1])
    plt.show()
    

def encoding_tilt_helper(ret, colname, xlab, title_addon):
    acc = pd.DataFrame(columns = ret[colname].unique())
    acc0 = acc.copy()
    acc50 = acc.copy()
    accw = acc.copy() 
    accb = acc.copy()

    for i_sub in ret.experiment_id.unique():
        curr = ret[ret.experiment_id == i_sub]
        acc.loc[curr.experiment_id.iloc[0]] = curr.groupby(colname).correct.mean()
        acc0.loc[curr.experiment_id.iloc[0]] = curr[~curr.tilted].groupby(colname).correct.mean()
        acc50.loc[curr.experiment_id.iloc[0]] = curr[curr.tilted].groupby(colname).correct.mean()
        accw.loc[curr.experiment_id.iloc[0]] = curr[curr.old_race == 'white'].groupby(colname).correct.mean()
        accb.loc[curr.experiment_id.iloc[0]] = curr[curr.old_race == 'black'].groupby(colname).correct.mean()

        zipped_acc = sorted(zip(acc.transpose().index,acc.transpose().mean(axis=1),acc.transpose().std(axis=1)))
        zipped_acc0 = sorted(zip(acc0.transpose().index,acc0.transpose().mean(axis=1),acc0.transpose().std(axis=1)))
        zipped_acc50 = sorted(zip(acc50.transpose().index,acc50.transpose().mean(axis=1),acc50.transpose().std(axis=1)))
        zipped_accw = sorted(zip(accw.transpose().index,accw.transpose().mean(axis=1),accw.transpose().std(axis=1)))
        zipped_accb = sorted(zip(accb.transpose().index,accb.transpose().mean(axis=1),accb.transpose().std(axis=1)))

    data = {
        'index': [x for x,_,_ in zipped_acc],
        'mean_acc':  [x for _,x,_ in zipped_acc],
        'std_acc': [x for _,_,x in zipped_acc],
        'mean_acc0':  [x for _,x,_ in zipped_acc0],
        'std_acc0':  [x for _,_,x in zipped_acc0],
        'mean_acc50':  [x for _,x,_ in zipped_acc50],
        'std_acc50':  [x for _,_,x in zipped_acc50],
        'mean_accw':  [x for _,x,_ in zipped_accw],
        'std_accw':  [x for _,_,x in zipped_accw],
        'mean_accb': [x for _,x,_ in zipped_accb],
        'std_accb':  [x for _,_,x in zipped_accb],
    }
    sz = (12,4)
    c = ['blue', 'green']
    buffer = 2
    al = 0.05

    fig, ax = plt.subplots(1, 3, figsize=sz)
    plt.suptitle('Hitrate by ' + title_addon + '. n=' + str(len(data['mean_acc'])) + ', ±1 SD')
    plt.setp(ax, ylim=[0,1], xlabel=xlab, ylabel = 'Retrieval hit rate (%)')
    if colname != 'oddity_tilt':
        plt.setp(ax, ylim=[0,1], xlabel=xlab, ylabel = 'Retrieval hit rate (%)', xticks = data['index'])
        x1 = data['index'] - np.repeat(buffer, len(data['mean_acc']))
        x2 = data['index'] + np.repeat(buffer, len(data['mean_acc']))
    else:
        x1 = x2 = data['data_acc'].index

    ax[0].errorbar(x= data['index'], y = data['mean_acc'], yerr = data['std_acc'], capsize =5, 
                   marker = 'o', mfc = 'red', mec='red', ms =8, ecolor='black',color='black')

    for i in range(len(acc.transpose())):
        ax[0].scatter(x = np.repeat(acc.transpose().index[i], len(acc)), y =acc.transpose().iloc[i],
                     color = 'gray', alpha = al)

    ax[1].set_title('By race')
    ax[1].errorbar(x= x1, y = data['mean_accw'], yerr = data['std_accw'], 
                   capsize =5, marker = 'o', mfc = c[0], mec=c[0], ms =8, ecolor=c[0], color=c[0], label='white')
    ax[1].errorbar(x= x2,y = data['mean_accb'], yerr = data['std_accb'], 
                   capsize =5, marker = 'o', mfc = c[1], mec=c[1], ms =8, ecolor=c[1], color=c[1], label='black')
    for i in range(len(accw.transpose())):
        ax[1].scatter(x = np.repeat(accw.transpose().index[i] - buffer, len(accw)), y =accw.transpose().iloc[i],
                     color = 'gray', alpha = al)  
    for i in range(len(accb.transpose())):
        ax[1].scatter(x = np.repeat(accb.transpose().index[i] + buffer, len(accb)), y =accb.transpose().iloc[i],
                     color = 'gray', alpha = al)
    ax[1].legend(loc = 'lower right')

    c = ['salmon', 'orange']
    ax[2].set_title('By retrieval tilt')
    ax[2].set_title('By tilt')
    ax[2].errorbar(x= x1, y = data['mean_acc0'], yerr = data['std_acc0'], 
                   capsize =5, marker = 'o', mfc = c[0], mec=c[0], ms =8, ecolor=c[0], color=c[0], label='untilted')
    ax[2].errorbar(x= x2, y = data['mean_acc50'], yerr = data['std_acc50'], 
                   capsize =5, marker = 'o', mfc = c[1], mec=c[1], ms =8, ecolor=c[1], color=c[1], label='tilted')
    for i in range(len(accw.transpose())):
        ax[2].scatter(x = np.repeat(acc0.transpose().index[i] - buffer , len(acc0)), y =acc0.transpose().iloc[i],
                     color = 'gray', alpha = al)  
    for i in range(len(accb.transpose())):
        ax[2].scatter(x = np.repeat(acc50.transpose().index[i] + buffer, len(acc50)), y =acc50.transpose().iloc[i],
                     color = 'gray', alpha = al)
    ax[2].legend(loc = 'lower right')

    for a in ax:
        for tick in a.get_xticklabels():
            tick.set_rotation(45)

    plt.show()

    

def encoding_tilt_plots(df):
    ret = df[df.trial_type.str.contains('retrieval')]
    ret = fix_practice_trials(ret)

    # define new columns
    ret['oddity_tilt'] = pd.NaT
    ret['oddity_tilt_simple'] = pd.NaT
    ret['typical_offset'] = pd.NaT
    ret['oddity_offset'] = pd.NaT
    for i in range(len(ret)):
        old_id = ret.iloc[i].old_identity
        exp_id = ret.iloc[i].experiment_id
        enc_trial = df[(df.experiment_id == exp_id) & (df.oddity_identity == old_id)]
        ret['oddity_tilt'].iloc[i] = enc_trial['oddity_tiltLR'].iloc[0] + '_' + enc_trial['oddity_tiltUD'].iloc[0]
        ret['oddity_tilt_simple'].iloc[i] = abs(tilt_to_number(enc_trial.oddity_tiltLR.iloc[0]))
        ret['typical_offset'].iloc[i] = get_viewpoint_difference(
            literal_eval(enc_trial.typicals_tiltsLR.iloc[0]),
            literal_eval(enc_trial.typicals_tiltsUD.iloc[0]))
        diff1 = get_viewpoint_difference(
            [enc_trial.oddity_tiltLR.iloc[0], literal_eval(enc_trial.typicals_tiltsLR.iloc[0])[0]],
            [enc_trial.oddity_tiltUD.iloc[0], literal_eval(enc_trial.typicals_tiltsUD.iloc[0])[0]])
        diff2 = get_viewpoint_difference(
            [enc_trial.oddity_tiltLR.iloc[0], literal_eval(enc_trial.typicals_tiltsLR.iloc[0])[1]],
            [enc_trial.oddity_tiltUD.iloc[0], literal_eval(enc_trial.typicals_tiltsUD.iloc[0])[1]])
        ret['oddity_offset'].iloc[i]= np.min([diff1,diff2])
    
#     encoding_tilt_helper(ret, 'oddity_tilt',
#                         xlab = 'Oddity viewpoint',
#                         title_addon = 'oddity viewpoint at encoding')
    encoding_tilt_helper(ret, 'oddity_tilt_simple',
                        xlab = 'Oddity viewpoint',
                        title_addon = 'oddity viewpoint at encoding')
    encoding_tilt_helper(ret, 'typical_offset', 
                         xlab = 'Typical-typical viewpoint difference',
                         title_addon = 'typicals offset at encoding')
    encoding_tilt_helper(ret, 'oddity_offset', 
                         xlab = 'Minimum oddity-typical viewpoint difference',
                         title_addon = 'oddity-typical offset')



def retrieval_split_plot(data, slider=False, save=False, dpi=200):
    if slider:
        measure = 'ret_dist'
        ylab = 'Retrieval Slider Error'
        ylims = (0,100)
    else:
        measure = 'ret_acc'
        ylab = 'Retrieval Accuracy'
        ylims = (0,1)
    
    c = ['darkorchid', 'hotpink']
    buffer = 2
    al = 0.1
    
    fig, ax = plt.subplots(1,2, figsize = (10,5), dpi = 80)
    fig.suptitle('Retrieval performance by split-half encoding RT grouping')
    plt.setp(ax, ylim = ylims, xticks = [0,50])
    
    ax[0].set_title('(a) By group')
    ax[0].set_ylabel(ylab)
    ax[0].set_xlabel('Median split-half encoding RT group')
    ax[0].set_xticklabels(['low','high'])
    ax[0].errorbar(x= np.array([0, 50]), 
             y = data[[measure+'_low', measure+'_high']].mean(), 
             yerr = data[[measure+'_low', measure+'_high']].std(),
            capsize =5, marker = 'o', mfc = 'black', mec='black', ms =8, ecolor='black', color='black')
    ax[0].scatter(x = rand_jitter(np.repeat(0, len(data)), 1), y = data[measure+'_low'], color=c[0], alpha=al, label = 'low RT')
    ax[0].scatter(x = rand_jitter(np.repeat(50, len(data)), 1), y = data[measure+'_high'], color=c[1], alpha=al, label = 'high RT')
    h = 0.02
    y = 0.9
    sig = get_sig(sp.wilcoxon(data[measure+'_low'], data[measure+'_high']).pvalue)
    ax[0].plot([0, 0, 50, 50], [y, y+h, y+h, y], lw=.5, color = 'black')
    ax[0].text(25,y+h, sig, ha ='center', fontsize=10)
    
    ax[1].set_title('(b) By group x tilt')
    ax[1].set_ylabel(ylab)
    ax[1].set_xlabel('Tilt condition at retrieval')
    ax[1].set_xticklabels(['untilted','tilted'])
    ax[1].errorbar(x= np.array([0, 50])-buffer, 
                   y = data[[measure+'_low_0', measure+'_low_50']].mean(), 
                   yerr = data[[measure+'_low_0', measure+'_low_50']].std(),
                   capsize =5, marker = 'o', mfc = c[0], mec=c[0], ms =8, ecolor=c[0], color=c[0], label = 'low RT')
    
    ax[1].errorbar(x= np.array([0, 50])+buffer, 
                   y = data[[measure+'_high_0', measure+'_high_50']].mean(), 
                   yerr = data[[measure+'_high_0', measure+'_high_50']].std(),
                   capsize =5, marker = 'o', mfc = c[1], mec=c[1], ms =8, ecolor=c[1], color=c[1], label = 'high RT')

    ax[1].scatter(x = rand_jitter(np.repeat(0-buffer, len(data)), 1),y = data[measure+'_low_0'], color='gray', alpha=al)
    ax[1].scatter(x = rand_jitter(np.repeat(0+buffer, len(data)), 1),y = data[measure+'_high_0'], color='gray', alpha=al)
    ax[1].scatter(x = rand_jitter(np.repeat(50-buffer, len(data)), 1),y = data[measure+'_low_50'], color='gray', alpha=al)
    ax[1].scatter(x = rand_jitter(np.repeat(50+buffer, len(data)), 1),y = data[measure+'_high_50'], color='gray', alpha=al)
    ax[1].text(25,0.63, 'n.s.', ha ='center', fontsize=10)
    ax[1].legend(loc = 'lower center')
    
    if save: plt.savefig('/Users/chrisiyer/Downloads/Fig4', dpi=dpi)
    plt.show()
    print('Test for panel A: \n', sp.wilcoxon(data[measure+'_low'], data[measure+'_high']))
    print('Test for panel B: \n', 
         show_model_parameters(smf.ols("measure ~ tilt * rt_group", data = {
        'measure': np.concatenate([data[measure+'_low_0'], 
                                    data[measure+'_high_0'], 
                                    data[measure+'_low_50'], 
                                    data[measure+'_high_50']]), 
        'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
        'rt_group': np.concatenate([np.repeat(0, len(data)), np.repeat(1, len(data)), 
                                    np.repeat(0, len(data)), np.repeat(1, len(data))])
        }), md_bool=False))    

    
    
def encoding_byface_plot(data, color = ['blue','green']):
    plt.figure(figsize = (4,4))

    plt.suptitle('Encoding performance by oddity identity')
    plt.scatter(data[data.race =='white'].enc_rt, data[data.race =='white'].enc_acc, color = color[0], label = 'white')
    plt.scatter(data[data.race =='black'].enc_rt, data[data.race =='black'].enc_acc, color = color[1], label = 'black')
    plt.xlabel('Median encoding RT (ms)')
    plt.ylabel('Mean encoding accuracy (%)')
    plt.legend(loc = 'lower right')
    plt.show()

def encoding_byface_group_plot(data, color = ['blue','green']):
    fig, ax = plt.subplots(1,2, figsize = (10,5))
    fig.suptitle('Encoding measures by oddity race')
    plt.setp(ax, xticks = [0,1], xticklabels = ['white', 'black'], xlabel='Race (via classification)')
    
    w = data[data.race == 'white']
    b = data[data.race == 'black']
    
    # Accuracy
    ax[0].set_title('Accuracy')
    ax[0].set_ylabel('Average accuracy (%)')
    ax[0].set_ylim([0,1.1])
    ax[0].errorbar(x= [0, 1], 
                   y = [w['enc_acc'].mean(), b['enc_acc'].mean()],
                   yerr = [w['enc_acc'].std(), b['enc_acc'].std()], capsize =5, marker = 'o', 
                   mfc = 'black', mec='black', ms =8,ecolor='black',color='black')
    ax[0].scatter(x = rand_jitter(np.repeat(0, len(w)), 0.05),y = w['enc_acc'],color=color[0],alpha=0.4)
    ax[0].scatter(x = rand_jitter(np.repeat(1, len(b)), 0.05),y = b['enc_acc'],color=color[1],alpha=0.2)
    
    h = 0.02
    y = 1.01
    ax[0].plot([0, 0, 1, 1], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(w.enc_acc, b.enc_acc).pvalue)
    ax[0].text(0.5,y+h*2, sig, ha ='center', fontsize=10)
    
    # RT
    ax[1].set_title('RT')
    ax[1].set_ylabel('Average response time (ms)')
    ax[1].set_ylim([min(data.enc_rt) - 500,max(data.enc_rt) + 500])
    ax[1].errorbar(x= [0, 1], 
                   y = [w['enc_rt'].mean(), b['enc_rt'].mean()],
                   yerr = [w['enc_rt'].std(), b['enc_rt'].std()], capsize =5, marker = 'o', 
                   mfc = 'black', mec='black', ms =8,ecolor='black',color='black')
    ax[1].scatter(x = rand_jitter(np.repeat(0, len(w)), 0.05),y = w['enc_rt'],color=color[0],alpha=0.4)
    ax[1].scatter(x = rand_jitter(np.repeat(1, len(b)), 0.05),y = b['enc_rt'],color=color[1],alpha=0.2)
    ax[1].set_xticks([0,1], ['white', 'black'])
    
    h = 100
    y = 4000
    ax[1].plot([0, 0, 1, 1], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(w.enc_rt, b.enc_rt).pvalue)
    ax[1].text(0.5,y+h, sig, ha ='center', fontsize=10)
    
    plt.show()

def retrieval_byface_plots(data, slider = False, mb=False):
    
    w = data[data.race == 'white']
    b = data[data.race == 'black']
    
    if slider: 
        measure = 'ret_dist'
        ylab = 'retrieval slider error'
    else: 
        measure = 'ret_acc'
        ylab = 'retrieval accuracy'
    if mb: 
        title = 'Residuals of ' + ylab
        ylab = 'Residuals of ' + ylab
    else: 
        title = ylab
    
    al = 0.2 #alpha
    buffer = 0.03
    c = ['blue', 'green']

    fig, ax = plt.subplots(1,3, figsize = (12,4))
    fig.suptitle(title + ', by tilt and race, per face.')
    plt.setp(ax, ylabel = ylab)
    
    for a in ax[[0,2]]:
        a.set_xticks([0,50])
        a.set_xticklabels(['untilted', 'tilted'])
        a.set_xlabel('Tilt condition at retrieval')
    
    ax[0].set_title('By tilt')
    ax[0].errorbar(x= [0, 1], 
                   y = [data[measure+'_0'].mean(), data[measure+'_50'].mean()],
                   yerr = [data[measure+'_0'].std(), data[measure+'_50'].std()], capsize =5, marker = 'o', 
                   mfc = 'red', mec='red', ms =8,ecolor='black',color='black')
    ax[0].scatter(x = np.array([rand_jitter(np.repeat(0, len(data)), buffer), 
                                rand_jitter(np.repeat(1, len(data)), buffer)]).flatten(),
                  y = np.array([data[measure+'_0'].to_numpy(), data[measure+'_50'].to_numpy()]).flatten(),
                                 color='gray',alpha=0.2)
    h = 0.02
    y = 1.0
    ax[0].plot([0, 0, 1, 1], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(data[measure+'_0'], data[measure+'_50']).pvalue)
    ax[0].text(0.5,y+h, sig, ha ='center', fontsize=10)
    
    ax[1].set_title('By race')
    ax[1].set_xlabel('Race category (via classification judgement)')
    ax[1].errorbar(x= [0,1], y = [w.mean()[measure], b.mean()[measure]], 
                   yerr = [w.std()[measure], b.std()[measure]],
                   capsize =5, marker = 'o', mfc = 'black', mec='black', ms =8, ecolor='black', color='black')
    ax[1].scatter(x = rand_jitter(np.repeat(0, len(w)), 0.05), 
                  y =w[measure], color=c[0], alpha=al)
    ax[1].scatter(x = rand_jitter(np.repeat(1, len(b)), 0.05), 
                  y = b[measure], color=c[1], alpha=al)
    ax[1].set_xticks([0,1])
    ax[1].set_xticklabels(['white', 'black'])
    
    ax[1].plot([0, 0, 1, 1], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(w[measure], b[measure]).pvalue)
    ax[1].text(0.5,y+h, sig, ha ='center', fontsize=10)

    ax[2].set_title('By tilt and race')
    ax[2].errorbar(x = np.array([0, 1])-buffer, y = [w[measure+'_0'].mean(), w[measure+'_50'].mean()],
                   yerr = [w[measure+'_0'].std(), w[measure+'_50'].std()], capsize =5, marker = 'o', 
                   mfc = c[0], mec=c[0], ms =8,ecolor=c[0],color=c[0], label = 'white')
    ax[2].errorbar(x = np.array([0, 1])+buffer, 
                   y = [b[measure+'_0'].mean(), b[measure+'_50'].mean()],
                   yerr = [b[measure+'_0'].std(), b[measure+'_50'].std()], capsize =5, marker = 'o', 
                   mfc = c[1], mec=c[1], ms =8,ecolor=c[1],color=c[1], label = 'black')
    ax[2].scatter(x = np.array([rand_jitter(np.repeat(0-buffer, len(w)), 0.05), 
                                rand_jitter(np.repeat(1-buffer, len(w)), 0.05)]).flatten(),
                  y = np.array([w[measure+'_0'].to_numpy(), w[measure+'_50'].to_numpy()]).flatten(), 
                  color='gray', alpha = 0.1)
    ax[2].scatter(x = np.array([rand_jitter(np.repeat(0+buffer, len(b)), 0.05), 
                                rand_jitter(np.repeat(1+buffer, len(b)), 0.05)]).flatten(),
                  y =  np.array([b[measure+'_0'].to_numpy(), b[measure+'_50'].to_numpy()]).flatten(),
                  color='gray', alpha = 0.1)
    ax[2].set_xticks([0,1])
    ax[2].set_xticklabels(['untilted', 'tilted'])
    
    # significance level
    sig = get_sig(smf.ols("accuracy ~ tilt * race", data = {
    'accuracy': np.concatenate([w[measure+'_0'], b[measure+'_0'], w[measure+'_50'], b[measure+'_50']]),
    'tilt': np.concatenate([np.repeat(0, len(data)), np.repeat(1, len(data))]),
    'race': np.concatenate([np.repeat(1, len(w)), np.repeat(0, len(b)), 
                            np.repeat(1, len(w)), np.repeat(0, len(b))])
    }).fit().pvalues[-1])
    ax[2].text(0.5,w[measure+'_0'].mean(), sig, ha ='center', fontsize=10)

    ax[2].legend()
    
    plt.show() 



def encoding_retrieval_byface_plot(data, colors = ['lightblue', 'blue']):
    # compare encoding RT, acc to retrieval RT, acc; by face
    
    w = data[data.race == 'white']
    b = data[data.race == 'black']
    fig, ax = plt.subplots(2,2, figsize = (8,8))
    fig.suptitle('Encoding measures predicting retrieval measures, by face')
    
    for i in range(len(ax)):
        # 0: encoding acc, 1: encoding RT
        m1 = ['enc_acc', 'enc_rt'][i]
        
        for j in range(len(ax[i])):
            # 0: retrieval acc, 1: retrieval RT
            m2 = ['ret_acc', 'ret_rt'][j]
            
            ax[i][j].set_title(m1 + ' vs. ' + m2)
            ax[i][j].scatter(w[m1], w[m2], label = 'white', color = colors[0])
            ax[i][j].scatter(b[m1], b[m2], label = 'black', color = colors[1], alpha = 0.5)
            

    plt.legend()
    plt.show()
    
def encoding_retrieval_byface_slider_plot(data, colors = ['lightblue', 'blue']):
    # compare encoding RT, acc to retrieval RT, acc; by face  
    w = data[data.race == 'white']
    b = data[data.race == 'black']
    fig, ax = plt.subplots(1,2, figsize = (8,4))
    fig.suptitle('Encoding measures predicting retrieval slider error, by face')
    for i in range(len(ax)):
        # 0: encoding acc, 1: encoding RT
        m1 = ['enc_acc', 'enc_rt'][i]         
        ax[i].set_title(m1 + ' vs. ' + 'ret_dist')
        ax[i].scatter(w[m1], w['ret_dist'], label = 'white', color = colors[0])
        ax[i].scatter(b[m1], b['ret_dist'], label = 'black', color = colors[1], alpha = 0.5)
    plt.legend()
    plt.show()
    

def stim_attributes_plot(data, meta):
    att = ['mb_version1_gray_lm', 'facial_hair', 'lighting', 'quality', 'gender_common']
    m = ['enc_acc', 'enc_rt', 'ret_acc', 'ret_rt']
    key = {
        'enc_acc': 'Encoding accuracy (%)',
        'enc_rt': 'Encoding RT (ms)',
        'ret_acc': 'Retrieval accuracy (%)',
        'ret_rt': 'Retrieval RT (ms)',
        'mb_version1_gray_lm': 'Model-Estimated Memorability',
        'gender_common': 'Gender (via classification)',
        'facial_hair': 'Facial hair',
        'lighting': 'Original lighting when photographed',
        'quality': 'Stimulus quality estimate'
    }
    fig, ax = plt.subplots(len(att), len(m), figsize = (25,25))
    fig.suptitle('Stimulus attributes vs. behavioral measures')
    
    for i in range(len(att)):
        for j in range(len(m)):
            ax[i][j].set_title(key[att[i]] + " vs. " + key[m[j]])
            ax[i][j].set_xlabel(key[att[i]])
            ax[i][j].set_ylabel(key[m[j]])
            
            att_arr = [meta[iden][att[i]] for iden in data.identity]
            ax[i][j].scatter(att_arr, data[m[j]])
            
def stim_attributes_slider_plot(data, meta):
    att = ['mb_version1_gray_lm', 'facial_hair', 'lighting', 'quality', 'gender_common']
    key = {
        'ret_dist': 'Retrieval Slider Error (0-100)',
        'mb_version1_gray_lm': 'Model-Estimated Memorability',
        'gender_common': 'Gender (via classification)',
        'facial_hair': 'Facial hair',
        'lighting': 'Original lighting when photographed',
        'quality': 'Stimulus quality estimate'
    }
    fig, ax = plt.subplots(1, len(att),  figsize = (20,4))
    fig.suptitle('Stimulus attributes vs. slider error')
    
    for i in range(len(att)):
        
        ax[i].set_title(key[att[i]])
        ax[i].set_xlabel(key[att[i]])
        ax[i].set_ylabel(key['ret_dist'])
        att_arr = [meta[iden][att[i]] for iden in data.identity]
        ax[i].scatter(att_arr, data['ret_dist'])
    plt.show()
            

    
    
def encoding_split_delta_plot(df_stat, slider=False, save=False, dpi=200):
    fig, ax = plt.subplots(1, 2, figsize=(10,5), dpi=80)
    fig.suptitle('Relating Encoding and Retrieval Bias based on RT Grouping')
    if slider:
        ax[0].set_title('(a) encoding response time')
        ax[0].set_xlabel('∆ Median Encoding RT (highRT group - lowRT group; ms)')
        ax[0].set_ylabel('∆ Retrieval Slider error (highRT - lowRT)')
        ax[0].scatter(df_stat.enc_rt_delta, df_stat.ret_dist_delta)
        ax[1].set_title('(b) encoding accuracy')
        ax[1].set_xlabel('∆ Encoding Accuracy (highRT - lowRT)')
        ax[1].set_ylabel('∆ Retrieval Slider error (highRT - lowRT)')
        ax[1].scatter(df_stat.enc_acc_delta, df_stat.ret_dist_delta)
    else:
        ax[0].set_title('(a) encoding accuracy')
        ax[0].set_xlabel('∆ Median Encoding RT (highRT group - lowRT group; ms)')
        ax[0].set_ylabel('∆ Retrieval Accuracy (highRT - lowRT)')
        ax[0].scatter(df_stat.enc_rt_delta, df_stat.ret_acc_delta)
        ax[1].set_title('(b) encoding response time')
        ax[1].set_xlabel('∆ Encoding Accuracy (highRT - lowRT)')
        ax[1].set_ylabel('∆ Retrieval Accuracy (highRT - lowRT)')
        ax[1].scatter(df_stat.enc_acc_delta, df_stat.ret_acc_delta)
        
    if save: plt.savefig('/Users/chrisiyer/Downloads/Fig5', dpi=dpi)
    plt.show()
    
    
def mb_race_plot(meta):
    w = []
    b = []
    for k in meta.keys():
        if meta[k]['race_common'] == 'white': 
            w.append(meta[k]['mb_version1_gray_lm'])
        elif meta[k]['race_common'] == 'black':
            b.append(meta[k]['mb_version1_gray_lm'])
    
    plt.figure(figsize = (6,6))
    plt.hist(w, color = 'blue', label='white', bins = 20, alpha = 0.5)
    plt.hist(b, color = 'green', label='black', bins = 20, alpha = 0.5)
    plt.legend()
    plt.show()

def mb_race_acc_plot(data, meta):
    
    c = ['blue', 'green']

    fig, ax = plt.subplots(1, 2,  figsize = (8,4))
    fig.suptitle('Memorability vs. retrieval performance')
       
    ax[0].set_title('Memorability vs. hit rate')
    ax[0].set_xlabel('Memorability')
    ax[0].set_ylabel('Hit rate (%)')
    ax[0].scatter([meta[iden]['mb_version1_gray_lm'] for iden in data[data.race == 'white'].identity], 
                  data[data.race == 'white']['ret_acc'], color = c[0], label = 'white')
    ax[0].scatter([meta[iden]['mb_version1_gray_lm'] for iden in data[data.race == 'black'].identity], 
                  data[data.race == 'black']['ret_acc'], color = c[1], label = 'black')
    
    ax[1].set_title('Memorability vs. slider errror')
    ax[1].set_xlabel('Memorability')
    ax[1].set_ylabel('Slider error (0-100)')
    ax[1].scatter([meta[iden]['mb_version1_gray_lm'] for iden in data[data.race == 'white'].identity], 
                  data[data.race == 'white']['ret_dist'], color = c[0], label = 'white')
    ax[1].scatter([meta[iden]['mb_version1_gray_lm'] for iden in data[data.race == 'black'].identity], 
                  data[data.race == 'black']['ret_dist'], color = c[1], label = 'black')
    
    plt.legend()
    plt.show()
        

def ret_tests(data):
    print(sp.ttest_ind(data.ret_acc_0, data.ret_acc_50))
    print(sp.ttest_ind(data.ret_acc_w, data.ret_acc_b))
    print(show_model_parameters(smf.ols("accuracy ~ tilt * race", data = {
        'accuracy': np.concatenate([data.ret_acc_w_0, data.ret_acc_b_0, 
                                    data.ret_acc_w_50, data.ret_acc_b_50]), 
        'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
        'race': np.concatenate([np.repeat(1, len(data)), np.repeat(0, len(data)), 
                                np.repeat(1, len(data)), np.repeat(0, len(data))])
        }), md_bool=False))
    
def ret_tests_byface(data):

    print(sp.ttest_ind(data.ret_acc_0, 
                   data.ret_acc_50))
    print(sp.ttest_ind(data[data.race == 'white'].ret_acc, 
                   data[data.race == 'black'].ret_acc))
    # interaction
    w = data[data.race=='white']
    b = data[data.race=='black']
    print(show_model_parameters(smf.ols("accuracy ~ tilt * race", data = {
        'accuracy': np.concatenate([w.ret_acc_0, b.ret_acc_0, w.ret_acc_50,b.ret_acc_50]),
        'tilt': np.concatenate([np.repeat(0, len(data)), np.repeat(1, len(data))]),
        'race': np.concatenate([np.repeat(1, len(w)), np.repeat(0, len(b)), 
                                np.repeat(1, len(w)), np.repeat(0, len(b))])
        }), md_bool=False))


def main_plots(data, save=False, dpi=200):
    encoding_plots(data,save, dpi)
    retrieval_plots(data,save, dpi)
    encoding_delta_plot(data,save, dpi)

def compare_versions(data_dict, slider=False, mb=False, save=False, dpi=200, encoding_only=False):
    color = ['lightblue', 'lightgreen']
    # intervals = np.linspace(0,1,len([*data_dict]))
    intervals = [0.2,0.6]
    buffer = 0.05
    jit = 0.01
    al = 0.2 #alpha
        
    fig, ax = plt.subplots(1,2, figsize = (12,6), dpi=80)
    fig.suptitle('Encoding Performance')
    ax[0].set_title('(a) Accuracy')
    ax[0].set_ylabel('Mean accuracy')
    ax[0].set_xlabel('Subject reported race')
    ax[0].set_ylim([0,1.2])
    ax[0].set_yticks(np.linspace(0,1,6))
    ax[0].set_xticklabels([*data_dict], rotation=30)
    ax[0].set_xticks(intervals)
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        ax[0].errorbar(x= [x1, x2], 
                   y = [data['enc_acc_w'].mean(), data['enc_acc_b'].mean()],
                   yerr = [data['enc_acc_w'].std(), data['enc_acc_b'].std()], capsize =5, marker = 'o', 
                   mfc = 'black', mec='black', ms =8,ecolor='black',color='black')
        ax[0].scatter(x = rand_jitter(np.repeat(x1, len(data)), jit),y = data['enc_acc_w'],color=color[0],alpha=al, label='white_stims')
        ax[0].scatter(x = rand_jitter(np.repeat(x2, len(data)), jit),y = data['enc_acc_b'],color=color[1],alpha=al,label='black_stims')
        h = 0.02
        y = 1.1
        ax[0].plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=.5, color = 'black')
        sig = get_sig(sp.wilcoxon(data.enc_acc_delta).pvalue)
        ax[0].text(intervals[i],y+h*2, sig, ha ='center', fontsize=10)
        
    ax[1].set_title('(b) Response time')
    ax[1].set_ylabel('Median RT (ms)')
    ax[1].set_xlabel('Subject reported race')
    ax[1].set_ylim([min(data.enc_rt) - 500,max(data.enc_rt) + 500])
    ax[1].set_xticklabels([*data_dict], rotation=30)
    ax[1].set_xticks(intervals)
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        ax[1].errorbar(x= [x1, x2], 
                       y = [data['enc_rt_w'].mean(), data['enc_rt_b'].mean()],
                       yerr = [data['enc_rt_w'].std(), data['enc_rt_b'].std()], capsize =5, marker = 'o', 
                       mfc = 'black', mec='black', ms =8,ecolor='black',color='black')
        ax[1].scatter(x = rand_jitter(np.repeat(x1, len(data)), jit),y = data['enc_rt_w'],color=color[0],alpha=al,label='white_stims')
        ax[1].scatter(x = rand_jitter(np.repeat(x2, len(data)), jit),y = data['enc_rt_b'],color=color[1],alpha=al,label='black_stims')
        h = 100
        y = 5000
        ax[1].plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=.5, color = 'black')
        sig = get_sig(sp.wilcoxon(data.enc_rt_delta).pvalue)
        ax[1].text(intervals[i],y+h*2, sig, ha ='center', fontsize=10)
        
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax[0].legend(by_label.values(), ['white','black'], loc='lower right', title='stimulus race classification')
    plt.savefig('/Users/chrisiyer/Downloads/compare_encoding', dpi=dpi)
    plt.show()
    
    if encoding_only:
        return
        
    ## RETRIEVAL
    fig, ax = plt.subplots(1,3, figsize = (15,6), dpi=80)
    fig.suptitle('Retrieval across conditions')
    
    if slider: 
        measure = 'ret_dist'
        ylab = 'Retrieval slider error'
        plt.setp(ax, ylim = [0,110])
    else: 
        measure = 'ret_acc'
        ylab = 'Retrieval accuracy'
        plt.setp(ax, ylim = [0,1.1])
    if mb: 
        title = 'Residuals of ' + ylab
        ylab = 'Residuals of ' + ylab
    else: 
        title = ylab
    
    ax[0].set_ylabel(ylab, size ='large')
    ax[0].set_title('(a) By viewpoint')
    ax[0].set_xlabel('Subject reported race')
    ax[0].set_xticklabels([*data_dict], rotation=30)
    ax[0].set_xticks(intervals)
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        ax[0].errorbar(x= [x1, x2], 
                   y = data[[measure+'_0', measure+'_50']].mean(), 
                   yerr = data[[measure+'_0', measure+'_50']].std(),
                   capsize =5, marker = 'o', mfc = 'red', mec='red', ms =8,ecolor='black',color='black')
        ax[0].scatter(x = np.array([rand_jitter(np.repeat(x1, len(data)), jit), 
                                rand_jitter(np.repeat(x2, len(data)), jit)]).flatten(),
                  y = np.array([data[measure+'_0'].to_numpy(), data[measure+'_50'].to_numpy()]).flatten(),
                                 color='gray',alpha=0.2)
        h = 0.01
        y = 0.9
        ax[0].plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=.5, color = 'black')
        sig = get_sig(sp.wilcoxon(data.ret_acc_0, data.ret_acc_50).pvalue)
        ax[0].text(intervals[i],y+h*2, sig, ha ='center', fontsize=10)
        

    ax[1].set_title('(b) By race classification')
    ax[1].set_xlabel('Subject reported race')
    ax[1].set_xticklabels([*data_dict], rotation=30)
    ax[1].set_xticks(intervals)
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        ax[1].errorbar(x= [x1,x2], y = data[[measure + '_w', measure + '_b']].mean(), 
                   yerr = data[[measure + '_w', measure + '_b']].std(),
                   capsize =5, marker = 'o', mfc = 'black', mec='black', ms =8, ecolor='black', color='black')
        ax[1].scatter(x = rand_jitter(np.repeat(x1, len(data)), jit), 
                  y =data[measure+'_w'], color=color[0], alpha=al)
        ax[1].scatter(x = rand_jitter(np.repeat(x2, len(data)), jit), 
                  y = data[measure+'_b'], color=color[1], alpha=al)
        h = 0.01
        y = 0.9
        ax[1].plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=.5, color = 'black')
        sig = get_sig(sp.wilcoxon(data.ret_acc_w, data.ret_acc_b).pvalue)
        ax[1].text(intervals[i],y+h*2, sig, ha ='center', fontsize=10)

    ax[2].set_title('(c) By viewpoint x race')
    ax[2].set_xticklabels([*data_dict], rotation=30)
    ax[2].set_xlabel('Subject reported race')
    ax[2].set_xticks(intervals)
    buffer = buffer/2
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        ax[2].errorbar(x = np.array([x1, x2])-buffer, 
                       y = data[[measure + '_w_0', measure + '_w_50']].mean(),
                       yerr = data[[measure + '_w_0', measure + '_w_50']].std(), 
                       capsize =5, marker = 'o', mfc = color[0], mec=color[0], ms =8,ecolor=color[0],color=color[0])
        ax[2].errorbar(x = np.array([x1, x2])+buffer, 
                       y = data[[measure + '_b_0', measure + '_b_50']].mean(),
                       yerr = data[[measure + '_b_0', measure + '_b_50']].std(),
                       capsize =5, marker = 'o', mfc = color[1], mec=color[1], ms =8,ecolor=color[1],color=color[1])
        
        sig = get_sig(
            smf.ols("accuracy ~ tilt * race", data = {
            'accuracy': np.concatenate([data.ret_acc_w_0, data.ret_acc_b_0, 
                                        data.ret_acc_w_50, data.ret_acc_b_50]), 
            'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
            'race': np.concatenate([np.repeat(1, len(data)), np.repeat(0, len(data)), 
                                    np.repeat(1, len(data)), np.repeat(0, len(data))])
            }).fit().pvalues[-1])
        ax[2].text(intervals[i],1.0, sig, ha ='center', fontsize=10)
        
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    # ax[1].legend(by_label.values(), ['white','black'], loc='lower right', title='stimulus race classification')
    plt.savefig('/Users/chrisiyer/Downloads/compare_retrieval', dpi=dpi)
    plt.show()
 
def age_plot(data, slider=False, save=False, bias=True):
    # plot subject's age vs. their encoding (RT, acc) and retrieval (acc or dist) performance
    m = max(data.age)
        
    fig, ax = plt.subplots(1,4,figsize = (16,4), dpi = 80)
    fig.suptitle('Encoding and retrieval performance by age')
    plt.setp(ax, xlabel= 'Age (years)', xlim = [min(data.age), max(data.age)])
    ax[0].set_title('(a) Encoding accuracy')
    ax[0].set_ylabel('Encoding accuracy')
    ax[0].set_ylim([0,1.1])
    ax[0].scatter(x = data.age, y = data.enc_acc)
    test = sp.linregress(data.age, data.enc_acc)
    if test.pvalue < 0.05:
        ax[0].plot([0,m], np.array([0,m])*test.slope + test.intercept, '--', color = 'red')
    
    ax[1].set_title('(b) Encoding RT')
    ax[1].set_ylabel('Median RT (ms)')
    ax[1].set_ylim([0,max(data.enc_rt) + 100])
    ax[1].scatter(x = data.age, y = data.enc_rt)
    test = sp.linregress(data.age, data.enc_rt)
    if test.pvalue < 0.05:
        ax[1].plot([0,m], np.array([0,m])*test.slope + test.intercept, '--', color = 'red')
    
    if slider: 
        measure = 'ret_dist'
        ylab = 'Mean retrieval slider error'
        ax[2].set_ylim([0,110])
    else: 
        measure = 'ret_acc'
        ylab = 'Retrieval accuracy'
        ax[2].set_ylim([0,1.1])
    
    ax[2].set_title('(c) ' + ylab)
    ax[2].set_ylabel(ylab)
    ax[2].scatter(x = data.age, y = data[measure])
    test = sp.linregress(data.age, data[measure])
    if test.pvalue < 0.05:
        ax[2].plot([0,1], np.array([0,1])*test.slope + test.intercept, '--', color = 'red')
        
    ax[3].set_title('Untilted vs. tilted')
    ax[3].set_ylabel('Difference in ' + ylab)
    ax[3].scatter(x = data.age, y = data[measure + '_0'] - data[measure + '_50'])
    test = sp.linregress(data.age, data[measure + '_0'] - data[measure + '_50'])
    if test.pvalue < 0.05:
        ax[3].plot([0,1], np.array([0,1])*test.slope + test.intercept, '--', color = 'red')
        
    plt.show()

def age_bias_plot(data, slider = False, save=False):
    # and vs. their encoding bias(es) (RT, acc) and retrieval bias (acc or dist)
    m = max(data.age)
    fig, ax = plt.subplots(1,3, figsize = (12,4), dpi = 80)
    fig.suptitle('Encoding and retrieval *BIAS* by age')
    plt.setp(ax, xlabel= 'Age (years)', xlim = [min(data.age), max(data.age)])
    ax[0].set_title('(a) Encoding accuracy bias')
    ax[0].set_ylabel('White - black encoding accuracy')
    ax[0].scatter(x = data.age, y = data.enc_acc_delta)
    test = sp.linregress(data.age, data.enc_acc_delta)
    if test.pvalue < 0.05:
        ax[0].plot([0,m], np.array([0,m])*test.slope + test.intercept, '--', color = 'red')
    
    ax[1].set_title('(b) Encoding RT bias')
    ax[1].set_ylabel('White - black median RT (ms)')
    ax[1].scatter(x = data.age, y = data.enc_rt_delta)
    test = sp.linregress(data.age, data.enc_rt_delta)
    if test.pvalue < 0.05:
        ax[1].plot([0,m], np.array([0,m])*test.slope + test.intercept, '--', color = 'red')
    
    if slider: 
        measure = 'ret_dist'
        ylab = 'Mean retrieval slider error'
        ax[2].set_ylim([0,110])
    else: 
        measure = 'ret_acc'
        ylab = 'Retrieval accuracy bias'
        ax[2].set_ylim([0,1.1])
    
    ax[2].set_title('(c) ' + ylab)
    ax[2].set_ylabel(ylab)
    ax[2].scatter(x = data.age, y = data[measure + '_delta'])
    test = sp.linregress(data.age, data[measure + '_delta'])
    if test.pvalue < 0.05:
        ax[2].plot([0,1], np.array([0,1])*test.slope + test.intercept, '--', color = 'red')
        
    plt.show()

        
###### FROM TYLER ######

def show_model_parameters(m_, idx_ =-1, md_bool=True):
    
    # fit model 
    m_ = m_.fit() 
    # extract significant figures from float 
    def sigfigs(x):
        d = int(str('%.2e'%x)[('%.2e'%x).find('-')+1:])
        n = np.round(float(str('%.02e'%x)[0:3]))
        return n, d
    
    # extract model parameters 
    beta, pval, df_model = m_.params[idx_], m_.pvalues[idx_], m_.df_model
    rsqrd, df_resid, tvalues = m_.rsquared, m_.df_resid, m_.tvalues[idx_]
    
    # show exact p values up to three significant figures 
    if sigfigs(pval)[1] < 4:
        stat_str = "$\\beta = %.2f$, $F(%d, %d)$ = $%.02f, P = %.03f $"
        report = stat_str%(beta, df_model, df_resid, tvalues, pval, )
    else:
        stat_str = "$\\beta = %.2f$, $F(%d, %d)$ = $%.02f, P = %.0f $ x $ 10 ^{-%d} $"
        report = stat_str%(beta, df_model, df_resid, tvalues, sigfigs(pval)[0], sigfigs(pval)[1])
    # return markdown visualization 
    if md_bool: return md(report) #, report
    else: return report
    
def show_ols_parameters(x, y, idx_ = 1, md_bool=True):
    
    m_ = smf.ols("y ~ x", data = {
        "y": y,
        "x": x
    }).fit()
    
    def sigfigs(x):
        d = int(str('%.2e'%x)[('%.2e'%x).find('-')+1:])
        n = np.round(float(str('%.02e'%x)[0:3]))
        return n, d
    # extract model parameters 
    beta, pval, df_model = m_.params[idx_], m_.pvalues[idx_], m_.df_model
    rsqrd, df_resid, tvalues = m_.rsquared, m_.df_resid, m_.tvalues[idx_]
    
    # show exact p values up to three significant figures 
    if sigfigs(pval)[1] < 4:
        stat_str = "$\\beta = %.2f$,  $F(%d, %d)$ = $%.02f,  P = %.03f $"
        report = stat_str%(beta, df_model, df_resid, tvalues, pval, )
    else:
        stat_str = "$\\beta = %.2f$,  $F(%d, %d)$ = $%.02f,  P = %.0f $ x $ 10 ^{-%d} $"
        report = stat_str%(beta, df_model, df_resid, tvalues, sigfigs(pval)[0], sigfigs(pval)[1])
    # return markdown visualization 
    if md_bool: return md(report) #, report
    else: return report
    
    
    
def compare_plot_retrieval(data_dict, data, save=False, slider=False, mb=False, dpi=200):

    fig, ax = plt.subplots(1,3, figsize = (15,6), dpi=80)
    fig.suptitle('Retrieval Performance')
    
    if slider: 
        measure = 'ret_dist'
        ylab = 'Retrieval slider error'
        plt.setp(ax, ylim = [0,110])
    else: 
        measure = 'ret_acc'
        ylab = 'Retrieval accuracy'
        plt.setp(ax, ylim = [0,1.1])
    if mb: 
        title = 'Residuals of ' + ylab
        ylab = 'Residuals of ' + ylab
    else: 
        title = ylab

    jit = 2
    al = 0.3
    ax[0].set_xticks([0,50])
    ax[0].set_xticklabels(['untilted', 'tilted'])
    ax[0].set_xlabel('Viewpoint at retrieval')
    ax[0].set_ylabel(ylab, size ='large')
    ax[0].set_title('(a) By viewpoint')
    ax[0].errorbar(x= [0, 50], 
                   y = data[[measure+'_0', measure+'_50']].mean(), 
                   yerr = data[[measure+'_0', measure+'_50']].std(),
                   capsize =5, marker = 'o', mfc = 'red', mec='red', ms =8,ecolor='black',color='black')
    ax[0].scatter(x = np.array([rand_jitter(np.repeat(0, len(data)), jit), 
                                rand_jitter(np.repeat(50, len(data)), jit)]).flatten(),
                  y = np.array([data[measure+'_0'].to_numpy(), data[measure+'_50'].to_numpy()]).flatten(),
                                 color='gray',alpha=al)
    ax[0].plot([ax[0].get_xlim()[0],ax[0].get_xlim()[1]],[0.5,0.5], color = 'red', ls = '--')
    
    h = 0.01
    y = 0.9
    ax[0].plot([0, 0, 50, 50], [y, y+h, y+h, y], lw=.5, color = 'black')
    sig = get_sig(sp.wilcoxon(data.ret_acc_0, data.ret_acc_50).pvalue)
    ax[0].text(25,y+h*2, sig, ha ='center', fontsize=10)
    
    color = ['lightblue', 'lightgreen']
    intervals = [0.2,0.6]
    buffer = 0.05
    jit = 0.01
    al = 0.4 #alpha
    
    ax[1].set_title('(b) By race classification')
    ax[1].set_xlabel('Subject reported race')
    ax[1].set_xticklabels([*data_dict], rotation=30)
    ax[1].set_xticks(intervals)
    
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        ax[1].errorbar(x= [x1,x2], y = data[[measure + '_w', measure + '_b']].mean(), 
                   yerr = data[[measure + '_w', measure + '_b']].std(),
                   capsize =5, marker = 'o', mfc = 'black', mec='black', ms =8, ecolor='black', color='black')
        ax[1].scatter(x = rand_jitter(np.repeat(x1, len(data)), jit), 
                  y =data[measure+'_w'], color=color[0], alpha=al)
        ax[1].scatter(x = rand_jitter(np.repeat(x2, len(data)), jit), 
                  y = data[measure+'_b'], color=color[1], alpha=al)
        
        h = 0.01
        y = 0.9
        ax[1].plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=.5, color = 'black')
        sig = get_sig(sp.wilcoxon(data.ret_acc_w, data.ret_acc_b).pvalue)
        ax[1].text(intervals[i],y+h*2, sig, ha ='center', fontsize=10)

    ax[2].set_title('(c) By viewpoint x race')
    ax[2].set_xticklabels([*data_dict], rotation=30)
    ax[2].set_xlabel('Subject reported race')
    ax[2].set_xticks(intervals)
    buffer = buffer/2
    
    for i in range(len(intervals)):
        data = data_dict[[*data_dict][i]]
        x1,x2 = (intervals[i]-buffer, intervals[i]+buffer)
        
        if i == 0:
            labels = ['white', 'black']
        else:
            labels = ['','']
            
        ax[2].errorbar(x = np.array([x1, x2])-buffer, 
                       y = data[[measure + '_w_0', measure + '_w_50']].mean(),
                       yerr = data[[measure + '_w_0', measure + '_w_50']].std(), 
                       capsize =5, marker = 'o', mfc = color[0], mec=color[0], ms =8,
                       ecolor=color[0],color=color[0], label=labels[0])
        ax[2].errorbar(x = np.array([x1, x2])+buffer, 
                       y = data[[measure + '_b_0', measure + '_b_50']].mean(),
                       yerr = data[[measure + '_b_0', measure + '_b_50']].std(),
                       capsize =5, marker = 'o', mfc = color[1], mec=color[1], ms =8,
                       ecolor=color[1],color=color[1], label=labels[1])
        
        sig = get_sig(
            smf.ols("accuracy ~ tilt * race", data = {
            'accuracy': np.concatenate([data.ret_acc_w_0, data.ret_acc_b_0, 
                                        data.ret_acc_w_50, data.ret_acc_b_50]), 
            'tilt': np.concatenate([np.repeat(0, 2*len(data)), np.repeat(1, 2*len(data))]),
            'race': np.concatenate([np.repeat(1, len(data)), np.repeat(0, len(data)), 
                                    np.repeat(1, len(data)), np.repeat(0, len(data))])
            }).fit().pvalues[-1])
        ax[2].text(intervals[i],1.0, sig, ha ='center', fontsize=10)
    
    #ax[1].legend(loc='lower right', title='stimulus race classification')
    ax[2].legend(loc='lower right', title='stimulus race classification')

    plt.savefig('/Users/chrisiyer/Downloads/compare_retrieval', dpi=dpi)
    plt.show()

   