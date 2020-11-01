#
# Copyright 2019 Bernhard Walter
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
import json

from IPython.display import display

from cadquery import Compound

from jupyter_cadquery.cad_display import CadqueryDisplay, get_default
from jupyter_cadquery.widgets import UNSELECTED, SELECTED, EMPTY
from jupyter_cadquery.utils import Color

PART_ID = 0


#
# Simple Part and Assembly classes
#


class _CADObject(object):
    def __init__(self):
        self.color = Color((232, 176, 36))

    def next_id(self):
        global PART_ID
        PART_ID += 1
        return PART_ID

    def to_nav_dict(self):
        raise NotImplementedError("not implemented yet")

    def to_state(self):
        raise NotImplementedError("not implemented yet")

    def collect_shapes(self):
        raise NotImplementedError("not implemented yet")

    def to_assembly(self):
        raise NotImplementedError("not implemented yet")

    def show(self, grid=False, axes=False):
        raise NotImplementedError("not implemented yet")


class _Part(_CADObject):
    def __init__(self, shape, name="Part", color=None, show_faces=True, show_edges=True):
        super().__init__()
        self.name = name
        self.id = self.next_id()

        if color is not None:
            if isinstance(color, (list, tuple)) and isinstance(color[0], Color):
                self.color = color
            elif isinstance(color, Color):
                self.color = color
            else:
                self.color = Color(color)
        self.shape = shape
        self.set_states(show_faces, show_edges)

    def set_states(self, show_faces, show_edges):
        self.state_faces = SELECTED if show_faces else UNSELECTED
        self.state_edges = SELECTED if show_edges else UNSELECTED

    def to_nav_dict(self):
        if isinstance(self.color, (tuple, list)):
            color = (c.web_color for c in self.color)
        else:
            color = self.color.web_color
        return {
            "type": "leaf",
            "name": self.name,
            "id": self.id,
            "color": color,
        }

    def to_state(self):
        return {str(self.id): [self.state_faces, self.state_edges]}

    def collect_shapes(self):
        return {
            "name": self.name,
            "shape": self.shape,
            "color": self.color,
        }

    def compound(self):
        return self.shape[0]

    def compounds(self):
        return [self.compound()]


class _Faces(_Part):
    def __init__(self, faces, name="Faces", color=None, show_faces=True, show_edges=True):
        super().__init__(faces, name, color, show_faces, show_edges)
        self.color = Color(color or (255, 0, 255))


class _Edges(_CADObject):
    def __init__(self, edges, name="Edges", color=None):
        super().__init__()
        self.shape = edges
        self.name = name
        self.id = self.next_id()
        self.color = Color(color or (255, 0, 255))

    def to_nav_dict(self):
        return {
            "type": "leaf",
            "name": self.name,
            "id": self.id,
            "color": self.color.web_color,
        }

    def to_state(self):
        return {str(self.id): [EMPTY, SELECTED]}

    def collect_shapes(self):
        return {
            "name": self.name,
            "shape": [edge for edge in self.shape],
            "color": self.color,
        }


class _Vertices(_CADObject):
    def __init__(self, vertices, name="Vertices", color=None):
        super().__init__()
        self.shape = vertices
        self.name = name
        self.id = self.next_id()
        self.color = Color(color or (255, 0, 255))

    def to_nav_dict(self):
        return {
            "type": "leaf",
            "name": self.name,
            "id": self.id,
            "color": self.color.web_color,
        }

    def to_state(self):
        return {str(self.id): [SELECTED, EMPTY]}

    def collect_shapes(self):
        return {
            "name": self.name,
            "shape": [edge for edge in self.shape],
            "color": self.color,
        }


class _Assembly(_CADObject):
    def __init__(self, objects, name="Assembly"):
        super().__init__()
        self.name = name
        self.id = self.next_id()
        self.objects = objects

    def to_nav_dict(self):
        return {
            "type": "node",
            "name": self.name,
            "id": self.id,
            "children": [obj.to_nav_dict() for obj in self.objects],
        }

    def to_state(self):
        result = {}
        for obj in self.objects:
            result.update(obj.to_state())
        return result

    def collect_shapes(self):
        result = []
        for obj in self.objects:
            result.append(obj.collect_shapes())
        return result

    def obj_mapping(self, parents=None):
        parents = parents or ()
        result = {}
        for i, obj in enumerate(self.objects):
            if isinstance(obj, _Assembly):
                for k, v in obj.obj_mapping((*parents, i)).items():
                    result[k] = v
            else:
                result[str(obj.id)] = (*parents, i)
        return result

    @staticmethod
    def reset_id():
        global PART_ID
        PART_ID = 0

    def compounds(self):
        result = []
        for obj in self.objects:
            result += obj.compounds()
        return result

    def compound(self):
        return Compound._makeCompound(self.compounds())


def _show(assembly, **kwargs):
    for k in kwargs:
        if get_default(k) is None:
            raise KeyError("Paramater %s is not a valid argument for show()" % k)

    d = CadqueryDisplay()
    widget = d.create(
        states=assembly.to_state(),
        shapes=assembly.collect_shapes(),
        mapping=assembly.obj_mapping(),
        tree=assembly.to_nav_dict(),
        **kwargs,
    )

    d.info.ready_msg(d.cq_view.grid.step)

    d.display(widget)

    return d
