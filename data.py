import random
random.seed(123)

import numpy as np
import pandas as pd
import scipy, pyDOE
import matplotlib.pyplot as plt
import gp_fanova



# x = np.linspace(-1,1)[:,None]
# y = np.zeros((50,12))
# # effect = np.array([0]*3+[1]*3)
# effect = np.array([0]*3+[1]*3+[2]*3+[3]*3)[:,None]
# # effect = np.column_stack(([0]*2+[1]*2+[0]*2+[1]*2,))
# effect = np.array(pyDOE.fullfact([2,2]).tolist()*3).astype(int)
# effect = np.array(pyDOE.fullfact([3,2]).tolist()*2).astype(int)
#
# cov = np.eye(50)*.1
#
# y[:,:3] = gp_fanova._mu_sample + scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,0],cov,3).T
# y[:,3:6] = gp_fanova._mu_sample + scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,1],cov,3).T
# y[:,6:9] = gp_fanova._mu_sample + scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,2],cov,3).T
# y[:,9:12] = gp_fanova._mu_sample + scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,3],cov,3).T
# # y[:,12:] = gp_fanova._mu_sample + scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,3],cov,3).T
#
# # y[:,:3] = scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,0],cov,3).T
# # y[:,3:6] = scipy.stats.multivariate_normal.rvs(gp_fanova.alpha_samples[:,1],cov,3).T
#
# m = model.GP_FANOVA(x,y,effect)

# def sample_data(nk):
# 	y = np.zeros((50,sum(nk)))
#
# 	for k,nextk in zip(nk[:-1],nk[1:]):
# 		y[:,k:nextk]


def one_effect_data(effects=3,add_fake_effect=False):
	samples = 2
	x = np.linspace(-1,1)[:,None]
	y = np.zeros((50,effects*samples))
	# effect = np.array([0]*3+[1]*3)
	e = []
	for i in range(effects):
		e += [i]*samples

	effect = np.array(e)[:,None]

	m = gp_fanova.fanova.FANOVA(x,y,effect,)
	y = m.sample_prior()

	if add_fake_effect:
		temp = np.zeros((6,2))
		temp[:,0] = effect
		temp[:,1] = np.random.choice(effect,6,replace=False)
		effect = temp

	return x,y,effect

def two_effect_data():
	x = np.linspace(-1,1)[:,None]
	y = np.zeros((50,12))
	effect = np.array(pyDOE.fullfact([2,2]).tolist()*3).astype(int)

	cov = np.eye(50)*.1

	m = model.GP_FANOVA(x,y,effect,)
	m.sample_prior(update_data=True)

	return x,m.y,effect

def hsalinarum_data():
	import patsy

	data = pd.read_excel("data/hsalinarum/Raw_growth_data2.xlsx",sheetname='Raw data (OD600)SLIM')
	# time = np.arange(4,48,.5)
	time = np.arange(4,48,2)

	# temp = data[(data.Condition.isnull()) & ((data.Strain == 'ura3') | (data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR') | (data.Strain == 'trh2'))]
	temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR') | (data.Strain == 'trh2') | (data.Strain == 'idr1'))]
	# temp = data[(data.Condition.isnull()) & (data.Strain!='ura3')]

	y = temp[time].T.values
	y = np.log2(y)
	y = y - y[0,:]

	x = time
	x = (x-x.mean())/x.std()
	x = x[:,None]

	effect = patsy.dmatrix('C(Strain)+0',temp)
	effect = np.where(effect!=0)[1][:,None]

	# effect = (temp.Strain != "ura3").astype(int).values[:,None]

	return x,y,effect

def hsalinarum_pq_data():
	import patsy

	data = pd.read_excel("data/hsalinarum/Raw_growth_data2.xlsx",sheetname='Raw data (OD600)SLIM')
	# time = np.arange(4,48,.5)
	time = np.arange(4,48,2)

	# temp = data[(data.Condition.isnull()) & ((data.Strain == 'ura3') | (data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR') | (data.Strain == 'trh2'))]
	temp = data[(data.Condition.isnull() | (data.Condition=='0.333mM PQ')) & ((data.Strain == 'rosR') | (data.Strain == 'idr1'))]
	# temp = data[(data.Condition.isnull()) & (data.Strain!='ura3')]

	temp.Condition[temp.Condition.isnull()] = ''

	y = temp[time].T.values
	y = np.log2(y)
	y = y - y[0,:]

	x = time
	x = (x-x.mean())/x.std()
	x = x[:,None]

	effect1 = patsy.dmatrix('C(Strain)+0',temp)
	effect1 = np.where(effect1!=0)[1]

	effect2 = patsy.dmatrix('C(Condition)+0',temp)
	effect2 = np.where(effect2!=0)[1]

	print effect1, effect2

	effect = np.column_stack((effect1,effect2))

	# effect = (temp.Strain != "ura3").astype(int).values[:,None]

	return x,y,effect

def hsalinarum_osmo_data(strain = None):
	import patsy

	if strain is None:
		strain = 'phoU'

	tidy = pd.read_csv("data/hsalinarum/tidy_normalize_all.csv")
	tidy['Experiment_Well'] = tidy.Experiment + "_" + tidy.Well.astype(str)
	pivot = tidy.pivot('Experiment_Well','time','OD')

	g = tidy.groupby(['Strain','standard','paraquat','peroxide','osmotic','heatshock'])
	ind = g.get_group(('ura3',1,0,0,0,0)).Experiment_Well.unique().tolist() + g.get_group(('ura3',0,0,0,1,0)).Experiment_Well.unique().tolist() + \
			g.get_group((strain,1,0,0,0,0)).Experiment_Well.unique().tolist() + g.get_group((strain,0,0,0,1,0)).Experiment_Well.unique().tolist()

	temp = pivot.loc[ind,:]

	time = np.arange(4,42,2)

	# data = pd.read_excel("data/hsalinarum/Raw_growth_data2.xlsx",sheetname='Raw data (OD600)SLIM')

	# temp = data[(data.Condition.isnull()) & ((data.Strain == 'ura3') | (data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR') | (data.Strain == 'trh2'))]
	# temp = data[(data.Condition.isnull() | (data.Condition=='2.9M NaCl')) & ((data.Strain == 'trh2') | (data.Strain == 'idr1'))]
	# temp = data[(data.Condition.isnull()) & (data.Strain!='ura3')]

	# temp.Condition[temp.Condition.isnull()] = ''

	y = temp[time].T.values
	# y = np.log2(y)
	# y = y - y[0,:]

	x = time
	x = (x-x.mean())/x.std()
	x = x[:,None]

	# effect1 = patsy.dmatrix('C(Strain)+0',temp)
	# effect1 = np.where(effect1!=0)[1]
	#
	# effect2 = patsy.dmatrix('C(Condition)+0',temp)
	# effect2 = np.where(effect2!=0)[1]
	#
	# print effect1, effect2
	#
	# effect = np.column_stack((effect1,effect2))

	effect = np.repeat([[0,0]],g.get_group(('ura3',1,0,0,0,0)).Experiment_Well.unique().shape[0],0)
	effect = np.row_stack((effect,np.repeat([[0,1]],g.get_group(('ura3',0,0,0,1,0)).Experiment_Well.unique().shape[0],0)))
	effect = np.row_stack((effect,np.repeat([[1,0]],g.get_group((strain,1,0,0,0,0)).Experiment_Well.unique().shape[0],0)))
	effect = np.row_stack((effect,np.repeat([[1,1]],g.get_group((strain,0,0,0,1,0)).Experiment_Well.unique().shape[0],0)))

	#  [[0,0] * g.get_group(('ura3',1,0,0,0,0)).shape[0]] + [[0,1] * g.get_group(('ura3',0,1,0,0,0)).shape[0]] + \
	# 		[[1,0] * g.get_group((strain,1,0,0,0,0)).shape[0]] + [[1,1] * g.get_group((strain,0,1,0,0,0)).shape[0]]
	# effect = np.array(effect)

	return x,y,effect


def hsalinarum_strain_data(strains=['trmB'],time=None):
	import patsy

	tidy = pd.read_csv("data/hsalinarum/tidy_normalize_all.csv")
	tidy['Experiment_Well'] = tidy.Experiment + "_" + tidy.Well.astype(str)
	pivot = tidy.pivot('Experiment_Well','time','OD')

	g = tidy.groupby(['Strain','standard'])

	ind = []
	effect = []

	# for i,tup in enumerate([('ura3',1),('trmB',1)]):
	for i,tup in enumerate(zip(['ura3']+strains,[1]*(len(strains)+1))):
		temp = g.get_group(tup).Experiment_Well.unique().tolist()
		ind += temp
		effect += [i]*len(temp)
	# ind = g.get_group(('ura3',1)).Experiment_Well.unique().tolist() + g.get_group(('trmB',1)).Experiment_Well.unique().tolist()

	temp = pivot.loc[ind,:]

	if time is None:
		time = np.arange(4,42,2)

	y = temp[time].T.values

	x = time
	x = (x-x.mean())/x.std()
	x = x[:,None]

	effect = np.array(effect)[:,None]

	return x,y,effect

def hsalinarum_replicate_data():
	import patsy

	data = pd.read_excel("data/hsalinarum/Raw_growth_data2.xlsx",sheetname='Raw data (OD600)SLIM')
	# time = np.arange(4,48,.5)
	time = np.arange(4,48,4)

	# temp = data[(data.Condition.isnull()) & ((data.Strain == 'ura3') | (data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR'))]
	# temp = data[(data.Condition.isnull()) & ((data.Strain=='trmB') | (data.Strain == 'rosR') | (data.Strain == 'trh2'))]
	temp = data[(data.Condition.isnull()) & ((data.Strain == 'ura3'))]
	# temp = data[(data.Condition.isnull()) & (data.Strain!='ura3')]

	temp.Condition[temp.Condition.isnull()] = ''

	y = temp[time].T.values
	y = np.log2(y)
	y = y - y[0,:]

	x = time
	x = (x-x.mean())/x.std()
	x = x[:,None]

	effect = patsy.dmatrix('C(Experiment):C(Well)+0',temp)
	effect = np.where(effect!=0)[1][:,None]

	return x,y,effect

def hsalinarum_beer_data(sample=1):
	data = pd.read_csv("data/hsalinarum/beer_et_al_2014/composite.csv",index_col=range(3))

	x = data.columns.values.astype(float);
	y = data.values
	effect = np.array(data.index.labels).T
	effect_map = [list(l) for l in list(data.index.levels)]

	select = x < 50
	x = x[select]
	y = y[:,select]

	select = np.arange(0,x.shape[0],sample)
	x = x[select]
	y = y[:,select]

	# select = effect[:,0] != 4
	# y = y[select,:]
	# effect = effect[select,:]

	x = (x-x.mean())/x.std()
	x = x[:,None]
	y = y.T

	return x,y,effect,effect_map

def plot_model_vs_true(m,mean,effect,interaction):

	nrows = 3
	ncols = sum([e.shape[1] for e in effect])

	plt.subplot(nrows,ncols,1)
	plt.plot(m.parameter_history[m.mu_index()].T.values,c='k',alpha=.1); plt.plot(mean,c='r');

	ind = 0
	for i in range(len(effect)):
		for j in range(effect[i].shape[1]):
			plt.subplot(nrows,ncols,ncols+1+ind)
			plt.plot(m.parameter_history[m.effect_index(i,j)].T.values,c='k',alpha=.1); plt.plot(effect[i][:,j],c='r');
			plt.title("%d, %d" %(i,j))
			ind += 1

	ind = 0
	for i in range(interaction.shape[1]):
		for j in range(interaction.shape[2]):
			plt.subplot(nrows,ncols,2*ncols+1+ind)
			plt.plot(m.parameter_history[m.effect_interaction_index(1,j,0,i)].T.values,c='k',alpha=.1); plt.plot(interaction[:,i,j],c='r');
			plt.title("%d, %d" %(i,j))
			ind += 1
