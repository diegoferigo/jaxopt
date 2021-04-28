# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Base definitions useful across the project."""

from typing import Any
from typing import NamedTuple

import jax
import jax.numpy as jnp


class OptimizeResults(NamedTuple):
  error: float
  nit: int
  x: Any


@jax.tree_util.register_pytree_node_class
class LinearOperator(object):

  def __init__(self, A):
    self.A = jnp.array(A)

  def shape(self):
    return self.A.shape

  def matvec(self, x):
    """Computes dot(A, x)."""
    return jnp.dot(self.A, x)

  def matvec_element(self, x, idx):
    """Computes dot(A, x)[idx]."""
    return jnp.dot(self.A[idx], x)

  def rmatvec(self, x):
    """Computes dot(A.T, x)."""
    return jnp.dot(self.A.T, x)

  def rmatvec_element(self, x, idx):
    """Computes dot(A.T, x)[idx]."""
    return jnp.dot(self.A[:, idx], x)

  def update_matvec(self, Ax, delta, idx):
    """Updates dot(A, x) when x[idx] += delta."""
    if len(Ax.shape) == 1:
      return Ax + delta * self.A[:, idx]
    elif len(Ax.shape) == 2:
      return Ax + jnp.outer(self.A[:, idx], delta)
    else:
      raise ValueError("Ax should be a vector or a matrix.")

  def update_rmatvec(self, ATx, delta, idx):
    """Updates dot(A.T, x) when x[idx] += delta."""
    if len(ATx.shape) == 1:
      return ATx + delta * self.A[idx]
    elif len(ATx.shape) == 2:
      raise NotImplementedError
    else:
      raise ValueError("Ax should be a vector or a matrix.")

  def column_l2_norms(self, squared=False):
    ret = jnp.sum(self.A ** 2, axis=0)
    if not squared:
      ret = jnp.sqrt(ret)
    return ret

  def tree_flatten(self):
    return (self.A,), None

  @classmethod
  def tree_unflatten(cls, aux_data, children):
    del aux_data
    return cls(*children)


class CompositeLinearFunction(object):
  """
  A function of the form::

    fun(x, params_fun) = subfun(linop(x), params_fun) + vdot(x, b)
  """

  def __init__(self, subfun, linop, b=None, lipschitz_fun=None):
    self.subfun = subfun
    self.linop = linop
    self.b = jnp.array(b) if b is not None else b
    self.lipschitz_fun = lipschitz_fun

  def __call__(self, x, params_fun):
    if self.b is None:
      return self.subfun(self.linop.matvec(x), params_fun)
    else:
      return self.subfun(self.linop.matvec(x), params_fun) + jnp.vdot(x, self.b)

  def column_lipschitz_constants(self, params_fun):
    ret = self.linop.column_l2_norms(squared=True)
    if self.lipschitz_fun is not None:
      ret *= self.lipschitz_fun(params_fun)
    return ret
