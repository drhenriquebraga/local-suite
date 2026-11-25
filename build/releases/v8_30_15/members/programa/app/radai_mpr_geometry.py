"""Patient-coordinate MPR without changing the acquired grid or RT references."""
from itertools import product
import numpy as np
from scipy.ndimage import affine_transform


class PatientGrid:
    """Regular LPS grid, expressed as (superior, posterior, left) array indices."""
    def __init__(self, shape, spacing, origin, direction):
        shape = np.asarray(shape, dtype=int)
        spacing = np.asarray(spacing)
        direction = np.asarray(direction).reshape(3, 3)
        self.original_shape = tuple(shape)
        self.original_to_world = direction[:, ::-1] * spacing
        self.origin = np.asarray(origin)
        corners = np.array(list(product(*[(0, n - 1) for n in shape])))
        positions = corners @ self.original_to_world.T + self.origin
        self.lower = positions.min(axis=0)
        inverse = np.linalg.inv(self.original_to_world)
        step = 1.0 / np.linalg.norm(inverse, axis=0)
        # Cover both extreme voxel centres; align exactly with cardinal acquisitions.
        size = np.ceil(np.maximum(0, np.ptp(positions,axis=0) / step - 1.e-5)).astype(int) + 1
        self.shape = tuple(int(s) for s in size[::-1])
        self.spacing = tuple(float(s) for s in step[::-1])
        self.matrix = inverse @ (np.eye(3)[:, ::-1] * step[::-1])
        self.offset = inverse @ (self.lower - self.origin)
        self.inverse = np.linalg.inv(self.matrix)
        # Pure axis permutations need no interpolation; preserve native samples exactly.
        axes = np.argmax(np.abs(self.matrix), axis=0)
        perm = np.zeros((3,3))
        perm[axes,np.arange(3)] = np.sign(self.matrix[axes,np.arange(3)])
        self.axes = tuple(axes) if (len(set(axes)) == 3 and np.allclose(perm,self.matrix,rtol=0,atol=1e-8)
                    and tuple(shape[axes]) == self.shape and np.allclose(self.offset,np.rint(self.offset),rtol=0,atol=1e-7)) else None

    def indices(self, lps):
        return ((np.asarray(lps) - self.lower)[::-1] / self.spacing)

    def sample(self, arr, axis, index, order=0, fill=0):
        if self.axes is not None:
            block = arr.transpose(self.axes)
            for k, native in enumerate(self.axes):
                if self.matrix[native,k] < 0:
                    block = np.flip(block,k)
            return block.take(index,axis=axis)
        order_axes = [axis] + [k for k in range(3) if k != axis]
        matrix = self.matrix[:, order_axes]
        offset = self.offset + self.matrix[:,axis] * index
        shape = (1,) + tuple(self.shape[k] for k in order_axes[1:])
        return affine_transform(arr, matrix, offset, output_shape=shape, order=order,
                                mode='grid-constant', cval=fill, prefilter=False)[0]

    def apply_plane(self, arr, axis, index, selected, value):
        """Paint original voxel centres covered by a selection in one physical slab."""
        yy, xx = np.nonzero(selected)
        if not len(yy):
            return
        other = [k for k in range(3) if k != axis]
        spans = [(0, 0)] * 3
        spans[axis] = (index - .5, index + .5)
        spans[other[0]] = (yy.min() - .5, yy.max() + .5)
        spans[other[1]] = (xx.min() - .5, xx.max() + .5)
        bounds = np.array(list(product(*spans))) @ self.matrix.T + self.offset
        lo = np.maximum(0,np.floor(bounds.min(axis=0)).astype(int))
        hi = np.minimum(arr.shape,np.ceil(bounds.max(axis=0)).astype(int)+1)
        if np.any(lo >= hi):
            return
        # Work in axial slabs to bound memory on thin oblique planes.
        for k in range(lo[0],hi[0]):
            rows,cols=np.ogrid[lo[1]:hi[1],lo[2]:hi[2]]
            ij=[]
            for j in range(3):
                m=self.inverse[j]
                coord=(k-self.offset[0])*m[0]+(rows-self.offset[1])*m[1]+(cols-self.offset[2])*m[2]
                ij.append(np.floor(coord+.5).astype(int))
            y,x=ij[other[0]],ij[other[1]]
            inside=(ij[axis]==index)&(y>=0)&(y<selected.shape[0])&(x>=0)&(x<selected.shape[1])
            where=inside & selected[y.clip(0,selected.shape[0]-1),x.clip(0,selected.shape[1]-1)]
            target=arr[k,lo[1]:hi[1],lo[2]:hi[2]]
            if isinstance(value,np.ndarray):
                target[where]=value[k,lo[1]:hi[1],lo[2]:hi[2]][where]
            else:
                target[where]=value


def original_traces(rings, grid, axis, index):
    """Exact intersections of saved vectors with a patient plane. Never infer a volume."""
    other = [k for k in range(3) if k != axis]
    h, w = (grid.shape[k] for k in other)
    polygons, points = [], []
    def normalized(coords):
        y, x = coords[:,other[0]], coords[:,other[1]]
        if axis:
            y = h - 1 - y
        return np.column_stack(((x+.5)/w,(y+.5)/h)).tolist()
    for ring in rings:
        coords = (ring-grid.lower)[:,::-1]/grid.spacing
        delta = coords[:,axis] - index
        if np.max(np.abs(delta))*grid.spacing[axis] < .002:
            polygons.append(normalized(coords))
            continue
        following = np.roll(coords, -1, axis=0)
        crosses = (delta > 0) != (np.roll(delta,-1) > 0)
        if np.any(crosses):
            a, b = coords[crosses], following[crosses]
            at = (-delta[crosses]/(b[:,axis]-a[:,axis]))[:,None]
            points.extend(normalized(a+(b-a)*at))
    return dict(width=w,height=h,polygons=polygons,points=points)
