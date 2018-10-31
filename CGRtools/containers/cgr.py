# -*- coding: utf-8 -*-
#
#  Copyright 2017, 2018 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of CGRtools.
#
#  CGRtools is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program; if not, see <https://www.gnu.org/licenses/>.
#
from collections import defaultdict
from collections.abc import MutableMapping
from itertools import repeat, zip_longest, chain
from typing import Tuple
from .query import DynamicContainer
from .molecule import MoleculeContainer, Bond, Atom
from ..algorithms import aromatize_cgr
from ..exceptions import InvalidData, InvalidAtom, InvalidStereo
from ..periodictable import H


class DynAtom(MutableMapping):
    __slots__ = ('reagent', 'product')

    def __init__(self, atom=None, p_atom=None):
        self.reagent = Atom() if atom is None else atom
        self.product = Atom() if p_atom is None else p_atom

    def __getitem__(self, key):
        if key.startswith('p_'):
            return self.product[key[2:]]
        return self.reagent[key]

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __getattr__(self, key):
        if key.startswith('p_'):
            return getattr(self.product, key[2:])
        return getattr(self.reagent, key)

    def __setattr__(self, key, value):
        if key.startswith('p_'):
            return setattr(self.product, key[2:], value)
        return setattr(self.reagent, key, value)

    def __len__(self):
        return len(self.reagent) + len(self.product)

    def __iter__(self):
        return chain(self.reagent, (f'p_{x}' for x in self.product))

    def __contains__(self, key):
        if key.startswith('p_'):
            return key[2:] in self.product
        return key in self.reagent

    def __delitem__(self, key):
        raise NotImplemented('attribute deletion impossible')

    def __eq__(self, other):
        if isinstance(other, DynAtom):
            return self.reagent == other.reagent and self.product == other.product
        return False

    def __gt__(self, other):
        if isinstance(other, DynAtom):
            return (self.reagent, self.product) > (other.reagent, other.product)
        raise TypeError('unorderable type')

    def __ge__(self, other):
        if isinstance(other, DynAtom):
            return (self.reagent, self.product) >= (other.reagent, other.product)
        raise TypeError('unorderable type')

    def __lt__(self, other):
        if isinstance(other, DynAtom):
            return (self.reagent, self.product) < (other.reagent, other.product)
        raise TypeError('unorderable type')

    def __le__(self, other):
        if isinstance(other, DynAtom):
            return (self.reagent, self.product) <= (other.reagent, other.product)
        raise TypeError('unorderable type')

    def __repr__(self):
        return f'{self.reagent}>>{self.product}'

    def __hash__(self):
        return hash((self.reagent, self.product))

    def copy(self):
        return type(self)(self.reagent.copy(), self.product.copy())

    def update(self, *args, **kwargs):
        """
        update atom

        :param args: tuple with 1 or 0 elements. element can be dict of atom attrs or atom object or atom class
        or DynAtom object or dict with 'atom' key with value equal to dict of atom attrs or atom object or atom class or
        DynAtom object.
        'atom' keyed dict also may contain atom attrs. this attrs has precedence other 'atom' key value attrs.
        :param kwargs: atom attrs. has precedence other args[0]
        """
        if args:
            if len(args) > 1:
                raise TypeError('update expected at most 1 arguments')

            value = args[0]
            if isinstance(value, dict) and 'atom' in value:
                value.update(kwargs)
                kwargs = value
                value = value.pop('atom')
        elif 'atom' in kwargs:
            value = kwargs.pop('atom')
        else:
            value = kwargs
            kwargs = ()

        if isinstance(value, DynAtom):
            p_value = value.product
            value = value.reagent
        else:
            p_value = value

        if kwargs:
            self.reagent.update(value, **{k: v for k, v in kwargs.items() if not k.startswith('p_')})
            self.product.update(p_value, **{k[2:]: v for k, v in kwargs.items() if k.startswith('p_')},
                                **{k: v for k, v in kwargs.items() if k in ('mark', 'mapping')})
        else:
            self.reagent.update(value)
            self.product.update(p_value)


class DynBond(MutableMapping):
    __slots__ = ('reagent', 'product')

    def __init__(self, bond=None, p_bond=None):
        self.reagent = Bond() if bond is None else bond
        self.product = Bond() if p_bond is None else p_bond

    def __getitem__(self, key):
        if key.startswith('p_'):
            return self.product[key[2:]]
        return self.reagent[key]

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getattr__(self, key):
        if key.startswith('p_'):
            return getattr(self.product, key[2:])
        return getattr(self.reagent, key)

    def __setattr__(self, key, value):
        if key.startswith('p_'):
            return setattr(self.product, key[2:], value)
        return setattr(self.reagent, key, value)

    def __len__(self):
        return len(self.reagent) + len(self.product)

    def __iter__(self):
        return chain(self.reagent, (f'p_{x}' for x in self.product))

    def __contains__(self, key):
        if key.startswith('p_'):
            return key[2:] in self.product
        return key in self.reagent

    def __delitem__(self, key):
        raise NotImplemented('attribute deletion impossible')

    def __repr__(self):
        return f'{self.reagent}>>{self.product}'

    def __hash__(self):
        return hash((self.reagent, self.product))

    def update(self, *args, **kwargs):
        """
        update bond
        :param args: tuple with 1 or 0 elements. element can be Bond|DynBond object or dict of bond attrs or
        dict with 'bond' key with value equal to Bond|DynBond object or dict of bond attrs.
        bond keyed dict also may contain bond attrs. this attrs has precedence other 'bond' key value attrs.
        :param kwargs: bond attrs. has precedence other args[0]
        """
        if args:
            if len(args) > 1:
                raise TypeError('update expected at most 1 arguments')

            value = args[0]
            if isinstance(value, dict) and 'bond' in value:
                value.update(kwargs)
                kwargs = value
                value = value.pop('bond')
        elif 'bond' in kwargs:
            value = kwargs.pop('bond')
        else:
            value = kwargs
            kwargs = ()

        if isinstance(value, DynBond):
            p_value = value.product
            value = value.reagent
        else:
            p_value = value

        if kwargs:
            self.reagent.update(value, **{k: v for k, v in kwargs.items() if not k.startswith('p_')})
            self.product.update(p_value, **{k[2:]: v for k, v in kwargs.items() if k.startswith('p_')})
        else:
            self.reagent.update(value)
            self.product.update(p_value)

    def copy(self):
        return type(self)(self.reagent.copy(), self.product.copy())


class CGRContainer(MoleculeContainer):
    """
    storage for CGRs. has similar to molecules behavior
    """

    node_attr_dict_factory = DynAtom
    edge_attr_dict_factory = DynBond

    def __dir__(self):
        if self.__visible is None:
            self.__visible = super().__dir__() + [self.get_center_atoms.__name__]
        return self.__visible

    def add_stereo(self, atom1, atom2, mark, p_mark=None):
        if mark not in (1, -1) and p_mark not in (1, -1):
            raise InvalidData('stereo marks invalid')
        if not self.has_edge(atom1, atom2):
            raise InvalidAtom('atom or bond not found')

        n_atom1 = self.nodes[atom1]
        if n_atom1.get('s_stereo') or n_atom1.get('p_stereo'):
            raise self._stereo_exception3

        tmp_s = [(x, y['s_bond']) for x, y in self[atom1].items() if y.get('s_bond')]
        tmp_p = [(x, y['p_bond']) for x, y in self[atom1].items() if y.get('p_bond')]
        neighbors = [x for x, _ in tmp_s]

        if mark and (n_atom1['s_z'] or any(self.nodes[x]['s_z'] for x in neighbors)):
            raise self._stereo_exception1
        elif p_mark and (n_atom1['p_z'] or any(self.nodes[x]['p_z'] for x in neighbors)):
            raise self._stereo_exception1

        neighbors_e = [self.nodes[x]['element'] for x in neighbors]
        implicit_s, implicit_p = self.atom_implicit_h(atom1)
        if mark and (implicit_s > 1 or implicit_s == 1 and 'H' in neighbors_e or neighbors_e.count('H') > 1):
            raise self._stereo_exception4
        elif p_mark and (implicit_p > 1 or implicit_p == 1 and 'H' in neighbors_e or neighbors_e.count('H') > 1):
            raise self._stereo_exception4

        if mark:
            bonds = [x for _, x in tmp_s]
            total = implicit_s + len(neighbors)
            if total == 4:  # tetrahedron
                self._tetrahedron_parse(atom1, atom2, mark, neighbors, bonds, implicit_s)
            else:
                raise self._stereo_exception2
        if p_mark:
            bonds = [x for _, x in tmp_p]
            total = implicit_p + len(neighbors)
            if total == 4:  # tetrahedron
                self._tetrahedron_parse(atom1, atom2, p_mark, neighbors, bonds, implicit_p, label='p')
            else:
                raise self._stereo_exception2

    def get_center_atoms(self, stereo=False):
        """ get list of atoms of reaction center (atoms with dynamic: bonds, stereo, charges, radicals).
        """
        nodes = set()
        for n, attr in self.nodes(data=True):
            if attr['s_charge'] != attr['p_charge'] or attr.get('s_radical') != attr.get('p_radical') or \
                   stereo and attr.get('s_stereo') != attr.get('p_stereo'):
                nodes.add(n)

        for *n, attr in self.edges(data=True):
            if attr.get('s_bond') != attr.get('p_bond') or stereo and attr.get('s_stereo') != attr.get('p_stereo'):
                nodes.update(n)

        return list(nodes)

    def reset_query_marks(self, copy=False):
        """
        set or reset hyb and neighbors marks to atoms.

        :param copy: if True return copy of graph and keep existing as is
        :return: graph if copy True else None
        """
        g = self.copy() if copy else self
        for i in g:
            label = dict(s_hyb=1, p_hyb=1, sp_hyb=1, s_neighbors=0, p_neighbors=0, sp_neighbors=0)
            # hyb 1- sp3; 2- sp2; 3- sp1; 4- aromatic
            for b, h, n in (('s_bond', 's_hyb', 's_neighbors'), ('p_bond', 'p_hyb', 'p_neighbors')):
                for node, bond in g[i].items():
                    b_type = bond.get(b)
                    if b_type and g.nodes[node]['element'] != 'H':
                        label[n] += 1
                    if b_type in (1, None) or label[h] in (3, 4):
                        continue
                    elif b_type == 4:
                        label[h] = 4
                    elif b_type == 3 or (b_type == 2 and label[h] == 2):  # Если есть 3-я или две 2-х связи, то sp1
                        label[h] = 3
                    elif b_type == 2 and label[h] != 3:
                        # Если есть 2-я связь, но до этого не было найдено другой 2-й, 3-й, или аром.
                        label[h] = 2

            for n, m, h in (('s_hyb', 'p_hyb', 'sp_hyb'), ('s_neighbors', 'p_neighbors', 'sp_neighbors')):
                label[h] = (label[n], label[m]) if label[n] != label[m] else label[n]

            g.nodes[i].update(label)
        if copy:
            return g
        self.flush_cache()

    def implicify_hydrogens(self):
        """
        remove explicit hydrogens if possible

        :return: number of removed hydrogens
        """
        explicit = defaultdict(list)
        hydrogens = set()
        for_remove = []
        c = 0
        for n, attr in self.nodes(data='element'):
            if attr == 'H':
                for m in self.neighbors(n):
                    if self.nodes[m]['element'] != 'H':
                        explicit[m].append(n)
                    else:
                        hydrogens.add(m)
                        hydrogens.add(n)

        for n, h in explicit.items():
            s_atom, p_atom = self.atom(n)
            self_n = self[n]

            s_bonds = [y['s_bond'] for x, y in self_n.items() if x not in h and y.get('s_bond')]
            p_bonds = [y['p_bond'] for x, y in self_n.items() if x not in h and y.get('p_bond')]

            s_implicit = s_atom.get_implicit_h(s_bonds)
            p_implicit = p_atom.get_implicit_h(p_bonds)

            if not s_implicit and any(self_n[x].get('s_bond') for x in h):
                hydrogens.update(h)
            elif not p_implicit and any(self_n[x].get('p_bond') for x in h):
                hydrogens.update(h)
            else:
                for x in h:
                    for_remove.append(x)

        for x in for_remove:
            if x not in hydrogens:
                self.remove_node(x)
                c += 1

        self.flush_cache()
        return c

    def explicify_hydrogens(self):
        """
        add explicit hydrogens to atoms

        :return: number of added atoms
        """
        tmp = []
        for n, attr in self.nodes(data='element'):
            if attr != 'H':
                si, pi = self.atom_implicit_h(n)
                if si or pi:
                    for s_mark, p_mark in zip_longest(repeat(1, si), repeat(1, pi)):
                        tmp.append((n, s_mark, p_mark))

        for n, s_mark, p_mark in tmp:
            self.add_bond(n, self.add_atom(H()), s_mark, p_mark)

        self.flush_cache()
        return len(tmp)

    def aromatize(self) -> Tuple[int, int]:
        """
        convert structure to aromatic form

        :return: number of processed s and p rings
        """
        res = aromatize_cgr(self)
        if res[0] or res[1]:
            self.flush_cache()
        return res

    def atom_implicit_h(self, atom):
        r, p = self.atom(atom)
        ri = r.get_implicit_h([x for *_, x in self.edges(atom, data='s_bond')])
        pi = p.get_implicit_h([x for *_, x in self.edges(atom, data='p_bond')])
        return DynamicContainer(ri, pi)

    def atom_explicit_h(self, atom):
        rh = sum(self.nodes[x]['element'] == 'H' for x, a in self[atom].items() if a.get('s_bond'))
        ph = sum(self.nodes[x]['element'] == 'H' for x, a in self[atom].items() if a.get('p_bond'))
        return DynamicContainer(rh, ph)

    def atom_total_h(self, atom):
        rh, ph = self.atom_explicit_h(atom)
        ri, pi = self.atom_implicit_h(atom)
        return DynamicContainer(ri + rh, pi + ph)

    def check_valence(self):
        errors = []
        for x in self.nodes():
            try:
                s_atom, p_atom = self.atom(x)
            except InvalidAtom as e:
                errors.append('atom %d has error: %s' % (x, e))
            else:
                if s_atom.get_valence(*self._get_atom_environment(x)) is None or \
                        p_atom.get_valence(*self._get_atom_environment(x, 'p')) is None:
                    errors.append('atom %d has invalid valence' % x)

        return errors

    def _prepare_stereo(self):
        return {}

    def _fix_stereo_stage_2(self, stereo):
        while True:
            failed_stereo = []
            for n, m, mark in stereo:
                try:
                    self.add_stereo(n, m, *mark)
                except InvalidStereo:
                    failed_stereo.append((n, m, mark))
                except InvalidAtom:
                    continue
            if failed_stereo and len(stereo) > len(failed_stereo):
                stereo = failed_stereo
                continue
            break

    def __check_bonding(self, n, m, mark, p_mark):
        for atom, reverse in ((n, m), (m, n)):
            s_atom, p_atom = self.atom(atom)
            if mark:
                bn, ng = self._get_atom_environment(atom)
                ng.append(self.nodes[reverse]['element'])
                bn.append(mark)
                if not s_atom.get_valence(bn, ng):
                    raise InvalidData('valence error')
            if p_mark:
                bn, ng = self._get_atom_environment(atom, 'p')
                ng.append(self.nodes[reverse]['element'])
                bn.append(p_mark)
                if not p_atom.get_valence(bn, ng):
                    raise InvalidData('valence error')

    __visible = None
