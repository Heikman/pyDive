"""
Copyright 2014 Heiko Burau

This file is part of pyDive.

pyDive is free software: you can redistribute it and/or modify
it under the terms of of either the GNU General Public License or
the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
pyDive is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License and the GNU Lesser General Public License
for more details.

You should have received a copy of the GNU General Public License
and the GNU Lesser General Public License along with pyDive.
If not, see <http://www.gnu.org/licenses/>.
"""
__doc__ = None

from .. import IPParallelClient as com
import numpy as np

cloned_ndarray_id = 0

class cloned_ndarray(object):
    """Represents a multidimensional, homogenous array of fixed-size elements which is cloned
    on the cluster nodes. *Cloned* means that every participating :term:`engine` holds an independent, local numpy-array
    of the user-defined shape. The user can then do e.g. some manual stuff on the local arrays or
    some computation with :mod:`pyDive.algorithm` on them.

    Note that there exists no 'original' array as the name might suggest but something like that can be
    generated by :meth:`merge`.
    """
    def __init__(self, shape, dtype=np.float, target_ranks='all', no_allocation=False):
        """Creates an :class:`pyDive.cloned_ndarray.cloned_ndarray.cloned_ndarray` instance.
        This is a low-level method for instanciating a cloned_array.
        Cloned arrays should  be constructed using 'empty', 'zeros'
        or 'empty_targets_like' (see :mod:`pyDive.cloned_ndarray.factories`).

        :param ints shape: size of the array on each axis
        :param numpy-dtype dtype: datatype of a single data value
        :param ints target_ranks: list of :term:`engine`-ids that share this array.\
            Or 'all' for all engines.
        :param bool no_allocation: if ``True`` no actual memory, i.e. *numpy-array*, will be
            allocated on :term:`engine`. Useful when you want to assign an existing numpy array manually.
        """
        self.shape = list(shape)
        self.dtype = dtype
        self.nbytes = np.dtype(dtype).itemsize * np.prod(self.shape)
        self.target_ranks = target_ranks
        self.view = com.getView()

        if self.target_ranks == 'all':
            self.target_ranks = list(self.view.targets)

        # generate a unique variable name used on target representing this instance
        global cloned_ndarray_id
        self.name = 'cloned_ndarray' + str(cloned_ndarray_id)
        cloned_ndarray_id += 1

        if no_allocation:
            self.view.push({self.name : None}, targets=self.target_ranks)
        else:
            self.view.push({'myshape' : self.shape, 'dtype' : self.dtype}, targets=self.target_ranks)
            self.view.execute('%s = np.empty(myshape, dtype=dtype)' % self.name, targets=self.target_ranks)

    def __del__(self):
        self.view.execute('del %s' % self.name, targets=self.target_ranks)

    def __repr__(self):
        return self.name

    def __setitem__(self, key, value):
        # if args is [:] then assign value to the entire ndarray
        if key == slice(None):
            assert isinstance(value, np.ndarray), "assignment available for numpy-arrays only"

            view = com.getView()
            view.push({'np_array' : value}, targets=self.target_ranks)
            view.execute("%s = np_array.copy()" % self.name, targets=self.target_ranks)

            return

        if not isinstance(key, list) and not isinstance(key, tuple):
            key = (key,)

        assert len(key) == len(self.shape)

        # assign value to sub-array of self
        sub_array = self[key]
        sub_array[:] = value

    def __getitem__(self, args):
        if not isinstance(args, list) and not isinstance(args, tuple):
            args = (args,)

        assert len(args) == len(self.shape),\
            "number of arguments (%d) does not correspond to the dimension (%d)"\
                 % (len(args), len(self.shape))

        # shape of the new sliced ndarray
        new_shape, clean_view = helper.window_of_shape(self.shape, args)

        result = pyDive.cloned.hollow_engines_like(new_shape, self.dtype, self)

        self.view.push({'args' : args}, targets=self.target_ranks)
        self.view.execute('%s = %s[args]' % (result.name, self.name), targets=self.target_ranks)

        return result

    def ranks(self):
        return self.target_ranks

    def merge(self, op):
        """Merge all local arrays in a pair-wise operation into a single numpy-array.

        :param op: Merging operation. Expects two numpy-arrays and returns one.
        :return: merged numpy-array.
        """
        result = self.view.pull(self.name, targets=self.target_ranks[0])
        for target in self.target_ranks[1:]:
            result = op(result, self.view.pull(self.name, targets=target))
        return result

    def sum(self):
        """Add up all local arrays.

        :return: numpy-array.
        """
        return self.merge(lambda x, y: x+y)
