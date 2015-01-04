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

def getFirstSubIdx(slice_obj, begin, end):
    if slice_obj.start > begin:
        if slice_obj.start >= end: return None
        return slice_obj.start
    i = (begin-1 - slice_obj.start) / slice_obj.step + 1
    idx = slice_obj.start + i * slice_obj.step
    if idx >= end or idx >= slice_obj.stop: return None
    return idx

def view_of_shape(shape, window):
    new_shape = []
    clean_view = []
    for s, w in zip(shape, window):
        if type(w) is int:
            clean_view.append(w)
            continue
        # create a clean, wrapped slice object
        clean_slice = slice(*w.indices(s))
        clean_view.append(clean_slice)
        # new size of axis i
        new_shape.append((clean_slice.stop-1 - clean_slice.start) / clean_slice.step + 1)
    return new_shape, clean_view

def createLocalSlices(slices, distaxis, idx_ranges):
    # create local slice objects for each engine

    local_slices = [list(slices) for i in range(len(idx_ranges))]
    distaxis_slice = slices[distaxis]
    for i in range(len(idx_ranges)):
        begin, end = idx_ranges[i]

        local_slices[i][distaxis] = slice(distaxis_slice.start + distaxis_slice.step * begin,\
                                          distaxis_slice.start + distaxis_slice.step * end,\
                                          distaxis_slice.step)

    return local_slices