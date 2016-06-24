from base import Base
from sample import Transform
import numpy as np
from patsy.contrasts import Helmert


class FANOVA(Base):

	EFFECT_SUFFIXES = ['alpha','beta','gamma','delta','epsilon']

	def __init__(self,x,y,effect,interactions=False,effect_transforms=True,interaction_transforms=True,helmert_convert=False,*args,**kwargs):
		self.effect = effect
		self.k = self.effect.shape[1] # number of effects
		self.mk = [np.unique(self.effect[:,i]).shape[0] for i in range(self.k)] # number of levels for each effect

		self.effect_transforms = effect_transforms
		self.interaction_transforms = interaction_transforms
		self.interactions = interactions
		self.helmert_convert = helmert_convert

		self.contrasts = [self.buildEffectContrastMatrix(i) for i in range(self.k)]
		self.contrasts_interaction = {}
		self.projectionMatrices = {i:self._projectionMatrix(i) for i in range(self.k)}
		for i in range(self.k):
			for j in range(i):
				if self.interactions:
 					self.contrasts_interaction[(j,i)] = np.kron(self.contrasts[j],self.contrasts[i])
					self.projectionMatrices[(j,i)] = self._projectionMatrix(j,i)
		self._effect_interaction_index = {} # starting index for each interaction in function matrix

		Base.__init__(self,x,y,*args,**kwargs)

	def has_interaction(self,i,k):
		return self.interactions

	def effect_suffix(self,k):
		if self.k <= len(FANOVA.EFFECT_SUFFIXES):
			return FANOVA.EFFECT_SUFFIXES[k]
		else:
			return 'effect%d'%k

	def _additional_samplers(self):
		ret = []

		for k in range(self.k):
			if self.effect_transforms:
				for l in range(self.mk[k]):
					ret.append(Transform('%s_%d'%(self.effect_suffix(k),l),
											self.effect_index_to_cache(k,l),
											lambda k=k,l=l : self.effect_sample(k,l)))
				ret.append(Transform("%s_finiteSampleVariance"%self.effect_suffix(k),
											self.fsvIndexToCache(k),
											lambda k=k:self.finitePopulationVarianceSample(k)))

		for k in range(self.k):
			for i in range(k+1,self.k):
				if self.interaction_transforms:
					if self.has_interaction(i,k):
						for l in range(self.mk[k]):
							for j in range(self.mk[i]):
								ret.append(Transform('(%s,%s)_(%d,%d)'%(self.effect_suffix(k),self.effect_suffix(i),l,j),
												self.effect_index_to_cache(k,l,i,j),
												lambda k=k,l=l,i=i,j=j : self.effect_sample(k,l,i,j)))

		return ret

	def effect_contrast_array(self,i,k=None,deriv=False):

		if k is None:
			ind = range(self.effect_index(i,0),self.effect_index(i+1,0))
		else:
			if i == k-1:
				ind = range(self.effect_interaction_index(i,0,k,0),self.effect_interaction_index(i,0,k+1,0))
			else:
				ind = range(self.effect_interaction_index(i,0,k,0),self.effect_interaction_index(i+1,0,k,0))
		return self.function_matrix(only=ind)

	def effectArray(self,i,k=None):
		"""Get an array of effects from the parameter cache."""

		if k is None:
			a = np.zeros((self.n,self.mk[i]))
			for j in range(self.mk[i]):
				a[:,j] = self.parameterCurrent("%s_%d"%(self.effect_suffix(i),j))

			return a

		return None

	def effect_sample(self,i,j,k=None,l=None):

		if k is None:
			return np.dot(self.effect_contrast_array(i),self.contrasts[i][j,:])

		return np.dot(self.effect_contrast_array(i,k),self.contrasts_interaction[(i,k)][j*self.mk[k]+l,:])

	def finitePopulationVarianceSample(self,i,k=None):
		"""Transform function for the finite population variance for an effect."""
		if k is None:
			a = self.effectArray(i)
			p = self.projectionMatrices[i]
			return 1./(self.mk[i]-1)*np.diag(np.dot(a,np.dot(p,a.T)))

		return None

	def effectContrastMatrix(self,i,k=None,full=False):
		if not full:
			if k is None:
				return self.contrasts[i]
			elif k < i:
				return self.effectContrastMatrix(k,i,full)
			else:
				return self.contrasts_interaction[(i,k)]
		else:
			if k is None:
				a = np.zeros((self.mk[i],self.f))
				a[:,self.effect_index(i,0):self.effect_index(i+1,0)] = self.contrasts[i]
				return a
			elif k < i:
				return self.effectContrastMatrix(k,i,full)
			else:
				a = np.zeros((self.mk[i]*self.mk[k],self.f))
				if i == k-1:
					ind = range(self.effect_interaction_index(i,0,k,0),self.effect_interaction_index(i,0,k+1,0))
				else:
					ind = range(self.effect_interaction_index(i,0,k,0),self.effect_interaction_index(i+1,0,k,0))
				a[:,ind] = self.contrasts_interaction[(i,k)]
				return a

	def buildEffectContrastMatrix(self,i):
		def convert(c):
			n = c.shape[1]
			for i in range(n):
				j = n-i-1
				c[:,j]/=c[j+1,j]
				s = np.power(c[j+1,:],2).sum()
				c[:,j]*=(np.sqrt(1-1./(n+1)-s+np.power(c[j+1,j],2)))
			return c

		h = Helmert().code_without_intercept(range(self.mk[i])).matrix

		if self.helmert_convert:
			h = convert(h)
		return h

	def _projectionMatrix(self,i,k=None):
		if k is None:
			c = np.ones((self.mk[i],1))
			return np.eye(c.shape[0]) - np.dot(c,np.dot(np.linalg.inv(np.dot(c.T,c)),c.T))

		return None

	def function_names(self):
		fxn_names = {0:'mean'}

		ind = 1
		for i in range(self.k):
			for j in range(self.mk[i]-1):
				fxn_names[ind] = "%s*_%d" % (self.effect_suffix(i),j)
				ind += 1

		for i in range(self.k):
			for j in range(self.mk[i]-1):
				for k in range(i+1,self.k):
					for l in range(self.mk[k]-1):
						fxn_names[ind] = "(%s,%s)*_(%d,%d)" % (self.effect_suffix(i),self.effect_suffix(k),j,l)
						ind += 1

		return fxn_names

	def effect_index_to_cache(self,k,l,i=None,j=None,contrast=False):
		"""return effect index to parameter cache"""

		s = ''
		if contrast:
			s = '*'

		if not i is None:
			if k > i:
				return self.effect_index_to_cache(i,j,k,l,contrast)

		if i is None:
			return ["%s%s_%d(%s)" % (self.effect_suffix(k),s,l,z) for z in self._observation_index_base()]

		return ["(%s,%s)%s_(%d,%d)(%s)" % (self.effect_suffix(k),self.effect_suffix(i),s,l,j,z) for z in self._observation_index_base()]

	def fsvIndexToCache(self,i,k=None):
		"""indices for the finite population variance estimates"""

		if k is None:
			return ["%s_finitePopulationVariance(%s)" % (self.effect_suffix(i),z) for z in self._observation_index_base()]

		return None

	def effect_index(self,i,j):
		"""index of effect function in design matrix."""
		return 1 + sum([m-1 for m in self.mk[:i]]) + j

	def effect_interaction_index(self,i,j,k,l):
		"""index of interaction function in design matrix."""
		if i > k:
			return self.effect_interaction_index(k,l,i,j)

		if k >= self.k:
			return self.f

		if j >= self.mk[i]:
			import logging
			logger = logging.getLogger(__name__)
			logger.warning("%d is out of range of effect %d with size %d" % (j,i,self.mk[i]))
			return -1
		if l >= self.mk[k]:
			import logging
			logger = logging.getLogger(__name__)
			logger.warning("%d is out of range of effect %d with size %d" % (l,k,self.mk[k]))
			return -1

		return self._effect_interaction_index[(i,k)] + j*(self.mk[i]-1) + l

		# mean + effects + interactions before i + interactions with i before k + i interactions before j + l
		# return 1 + sum([m-1 for m in self.mk]) + \
		# 			sum([[(self.mk[m]-1)*(self.mk[l]-1) for l in range(m,self.k)] for m in range(i)]) + \
		# 			sum([(m-1)*(self.mk[i]-1) for m in self.mk[:k]]) + \
		# 			(j-1)*(self.mk[k]-1) + l

	def prior_groups(self):
		g = [[0]]

		ind = 1
		for i in range(self.k):
			g.append(range(ind,ind+self.mk[i]-1))
			ind += self.mk[i]-1

		for i in range(self.k):
			for k in range(i+1,self.k):
				if self.has_interaction(i,k):
					c = (self.mk[i]-1) * (self.mk[k]-1)
					g.append(range(ind,ind+c))
					ind += c

		return g

	def _build_design_matrix(self):
		d = 1
		for i in range(self.k):
			d += self.mk[i] - 1
			for j in range(i):
				if self.interactions:
					d += (self.mk[i] - 1) * (self.mk[j] - 1)

		x = np.zeros((self.m,d))
		x[:,0] = 1

		for s in range(self.m):
			ind = 1
			for i in range(self.k):
				x[s,ind:ind+self.mk[i]-1] = self.contrasts[i][self.effect[s,i],:]
				ind += self.mk[i]-1

			for i in range(self.k):
				for j in range(i+1,self.k):
					if self.interactions:
						z = self.effect[s,i] * self.mk[j] + self.effect[s,j]
						x[s,ind:ind+(self.mk[i]-1)*(self.mk[j]-1)] = self.contrasts_interaction[(i,j)][z,:]
						self._effect_interaction_index[(i,j)] = ind
						ind += (self.mk[i]-1)*(self.mk[j]-1)

		return x

	def relativeInteraction(self,i,j,k,l,i0=None,k0=None):
		if not self.interactions:
			return None

		if i0 is None:
			i0 = 0
		if k0 is None:
			k0 = 0

		return self.parameterSamples("(%s,%s)_(%d,%d)" %(self.effect_suffix(i),self.effect_suffix(k),j,l)).values -\
				self.parameterSamples("(%s,%s)_(%d,%d)" %(self.effect_suffix(i),self.effect_suffix(k),j,k0)).values -\
				self.parameterSamples("(%s,%s)_(%d,%d)" %(self.effect_suffix(i),self.effect_suffix(k),i0,l)).values +\
				self.parameterSamples("(%s,%s)_(%d,%d)" %(self.effect_suffix(i),self.effect_suffix(k),i0,k0)).values
