from patsy.contrasts import Sum
# from sampler import SamplerContainer, Gibbs, Slice
import sampler; reload(sampler)
import numpy as np
import GPy, scipy

class GP_FANOVA(sampler.SamplerContainer):

	EFFECT_SUFFIXES = ['alpha','beta','gamma','delta','epsilon']

	def __init__(self,x,y,effect):
		""" Base model for the GP FANOVA framework.

		Input must be of the form:
		x: n x p
		y: n x r
		effect: r x k

		where n is the number of sample points, p is the input dimension,
		r is the number of replicates, and k is the number of effects.
		"""

		# store indexers
		self.x = x # independent variables
		self.y = y # dependent variables
		self.effect = effect # effect variables

		self.n = self.x.shape[0]
		assert self.y.shape[0] == self.n, 'x and y must have same first dimension shape!'
		self.p = self.x.shape[1]

		self.r = self.nt = self.y.shape[1]
		assert self.r == self.effect.shape[0], 'y second dimension must match effect first dimension'

		self.k = self.effect.shape[1] # number of effects
		self.mk = [np.unique(self.effect[:,i]).shape[0] for i in range(self.k)] # number of levels for each effect

		# SamplerContainer
		samplers = [sampler.Fixed('y_sigma','y_sigma',)]
		samplers += [sampler.Gibbs('mu',self.mu_index(),self.mu_conditional_params)]
		samplers += [sampler.Fixed('mu_sigma','mu_sigma',)]
		samplers += [sampler.Fixed('mu_lengthscale','mu_lengthscale',)]
		for i in range(self.k):
			for j in range(self.mk[i]-1):
				samplers.append(sampler.Gibbs('%s*_%d'%(GP_FANOVA.EFFECT_SUFFIXES[i],j),
										self.effect_contrast_index(i,j),
										lambda i=i,j=j : self.effect_contrast_conditional_params(i,j)))
			samplers += [sampler.Fixed('%s*_sigma'%GP_FANOVA.EFFECT_SUFFIXES[i],'%s*_sigma'%GP_FANOVA.EFFECT_SUFFIXES[i],)]
			samplers += [sampler.Fixed('%s*_lengthscale'%GP_FANOVA.EFFECT_SUFFIXES[i],'%s*_lengthscale'%GP_FANOVA.EFFECT_SUFFIXES[i],)]
		# samplers += [Slice('mu_sigma','mu_sigma',)]

		# add effect transforms
		for k in range(self.k):
			for l in range(self.mk[i]):
				samplers.append(sampler.Transform('%s_%d'%(GP_FANOVA.EFFECT_SUFFIXES[k],l),
										self.effect_index(k,l),
										lambda k=k,l=l : self.effect_sample(k,l)))

		sampler.SamplerContainer.__init__(self,*samplers)

		# contrasts
		self.contrasts = [self.effect_contrast_matrix(i) for i in range(self.k)]

	def offset(self):
		"""offset for the calculation of covariance matrices inverse"""
		return 1e-9

	def effect_index(self,k,l,):
		"""lth sample of kth effect"""
		return ['%s_%d(%lf)'%(GP_FANOVA.EFFECT_SUFFIXES[k],l,z) for z in self.x]

	def effect_contrast_index(self,k,l,):
		"""lth sample of kth effect"""
		return ['%s*_%d(%lf)'%(GP_FANOVA.EFFECT_SUFFIXES[k],l,z) for z in self.x]

	def mu_index(self):
		return ['mu(%lf)'%z for z in self.x]

	def y_k(self):
		sigma,ls = self.parameter_cache[['y_sigma','y_lengthscale']]

		sigma = np.power(10,sigma)
		ls = np.power(10,ls)

		return GPy.kern.White(self.p,variance=sigma)

	def mu_k(self,sigma=None,ls=None,history=None):
		if sigma is None:
			sigma = self.parameter_cache['mu_sigma']
		if ls is None:
			ls = self.parameter_cache['mu_lengthscale']
		if not history is None:
			sigma,ls = self.parameter_history.loc[history,'mu_sigma'],self.parameter_history.loc[history,'mu_lengthscale']

		sigma = np.power(10,sigma)
		ls = np.power(10,ls)

		return GPy.kern.RBF(self.p,variance=sigma,lengthscale=ls)

	def effect_contrast_k(self,i,sigma=None,ls=None,history=None):
		# sigma,ls = self.parameter_cache[["%s*_sigma"%GP_FANOVA.EFFECT_SUFFIXES[i],"%s*_lengthscale"%GP_FANOVA.EFFECT_SUFFIXES[i]]]
		if sigma is None:
			sigma = self.parameter_cache["%s*_sigma"%GP_FANOVA.EFFECT_SUFFIXES[i]]
		if ls is None:
			ls = self.parameter_cache["%s*_lengthscale"%GP_FANOVA.EFFECT_SUFFIXES[i]]
		if not history is None:
			sigma,ls = self.parameter_history.loc[history,"%s*_sigma"%GP_FANOVA.EFFECT_SUFFIXES[i]],self.parameter_history.loc[history,"%s*_lengthscale"%GP_FANOVA.EFFECT_SUFFIXES[i]]

		sigma = np.power(10,sigma)
		ls = np.power(10,ls)

		return GPy.kern.RBF(self.p,variance=sigma,lengthscale=ls)

	def effect_contrast_matrix(self,i):
		h = Sum().code_without_intercept(range(self.mk[i])).matrix

		return h

	def y_k_inv(self,x=None):
		if x is None:
			x = self.x

		k_y = self.y_k().K(x)
		chol_y = np.linalg.cholesky(k_y)
		chol_y_inv = np.linalg.inv(chol_y)
		y_inv = np.dot(chol_y_inv.T,chol_y_inv)

		return y_inv

	def mu_k_inv(self,x=None):
		if x is None:
			x = self.x

		k_m = self.mu_k().K(x) + np.eye(x.shape[0])*self.offset()
		chol_m = np.linalg.cholesky(k_m)
		chol_m_inv = np.linalg.inv(chol_m)
		m_inv = np.dot(chol_m_inv.T,chol_m_inv)

		return m_inv

	def contrast_k_inv(self,i,x=None):
		if x is None:
			x = self.x

		k_c = self.effect_contrast_k(i).K(x) + np.eye(x.shape[0])*self.offset()
		chol_c = np.linalg.cholesky(k_c)
		chol_c_inv = np.linalg.inv(chol_c)
		c_inv = np.dot(chol_c_inv.T,chol_c_inv)

		return c_inv

	def effect_contrast_array(self,i,history=None,deriv=False):

		if deriv:
			loc = self.derivative_history
		elif not history is None:
			loc = self.parameter_history
		else:
			loc = self.parameter_cache

		a = np.zeros((self.n,self.mk[i]-1))
		for j in range(self.mk[i]-1):
			if history is None:
				a[:,j] = loc[self.effect_contrast_index(i,j)]
			else:
				a[:,j] = loc.loc[history,self.effect_contrast_index(i,j)]
		return a

	def mu_conditional_params(self,history=None,cholesky=True,m_inv=None,y_inv=None):
		m = np.zeros(self.n)
		obs = np.zeros(self.n) # number of observations at each timepoint

		y_effect = np.zeros((self.n,self.r))
		for r in range(self.r):
			obs += 1 # all timepoints observed, need to update for nan's
			for i in range(self.k):
				y_effect[:,r] = self.y[:,r] - np.dot(self.effect_contrast_array(i,history), self.contrasts[i][self.effect[r,i]])

				# need to do interaction here

		m = np.mean(y_effect,1)

		if cholesky:

			if m_inv is None:
				m_inv = self.mu_k_inv()
			if y_inv is None:
				y_inv = self.y_k_inv()

			A = obs*y_inv + m_inv
			b = obs*np.dot(y_inv,m)

			chol_A = np.linalg.cholesky(A)
			chol_A_inv = np.linalg.inv(chol_A)
			A_inv = np.dot(chol_A_inv.T,chol_A_inv)

		else:
			obs_cov_inv = np.linalg.inv(self.y_k().K(self.x))

			A = obs*obs_cov_inv + np.linalg.inv(self.mu_k().K(self.x) + np.eye(self.n)*self.offset())
			b = obs*np.dot(obs_cov_inv,m)

			A_inv = np.linalg.inv(A)
		return np.dot(A_inv,b), A_inv

	def effect_contrast_conditional_params(self,i,j,cholesky=True,c_inv=None,y_inv=None):
		"""compute the conditional mean and covariance of an effect contrast function"""
		m = np.zeros(self.n)
		obs = np.zeros(self.n) # number of observations at each timepoint

		contrasts = self.effect_contrast_array(i)

		tot = 0
		# calculate residual for each replicate, r
		for r in range(self.r):
			e = self.effect[r,i]
			if self.contrasts[i][e,j] == 0: # don't use this observation
				continue
			obs += ~np.isnan(self.y[:,r])
			tot += 1

			resid = self.y[:,r] - self.parameter_cache[self.mu_index()] - np.dot(contrasts,self.contrasts[i][e,:])

			# add back in this contrast
			resid += contrasts[:,j] * self.contrasts[i][e,j]

			# scale by contrast value
			resid /= self.contrasts[i][e,j]

			m+= resid
		m /= tot

		if cholesky:
			if c_inv is None:
				c_inv = self.contrast_k_inv(i)

			if y_inv is None:
				y_inv = self.y_k_inv()

			A = obs*y_inv + c_inv
			b = obs*np.dot(y_inv,m)

			chol_A = np.linalg.cholesky(A)
			chol_A_inv = np.linalg.inv(chol_A)
			A_inv = np.dot(chol_A_inv.T,chol_A_inv)

		else:
			obs_cov_inv = np.linalg.inv(self.y_k().K(self.x))

			A = obs_cov_inv*obs + np.linalg.inv(self.effect_contrast_k(i).K(self.x) + np.eye(self.n)*self.offset())
			b = obs*np.dot(obs_cov_inv,m)

			A_inv = np.linalg.inv(A)
		return np.dot(A_inv,b), A_inv

	def effect_sample(self,i,j):

		return np.dot(self.effect_contrast_array(i),self.contrasts[i][j,:])