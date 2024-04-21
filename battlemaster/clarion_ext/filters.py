from typing import Mapping, Any, Union, List

import pyClarion as cl
from pyClarion import nd
from pyClarion.base.realizers import Pt

from battlemaster.clarion_ext.numdicts_ext import is_empty


class ReasoningPath(cl.Wrapped[Pt]):
    """
    Gates an activation propagator.

    pyClarion only has a way to Gate/filter a propagator _after_ it has ran. This wastes computation.
    This class completely severs a propagator by not even calling it and returning an empty output. Though it is
    intended to be somewhat compatible with the Gate filter by respecting the same API except it allows for multiple
    controllers and interfaces.
    """

    def __init__(
        self,
        base: Pt,
        controllers: List[Union[cl.buffer, cl.flow_in]],
        interfaces: List[cl.ParamSet.Interface],
        pidxs: List[int]
    ) -> None:
        """
        :param base: The base Process instance.
        :param controller: The gate controller.
        :param interface: Controller's feature interface.
        :param pidx: Lookup index of gating parameter in interface.
        """
        if len(controllers) != len(interfaces) or len(controllers) != len(pidxs):
            raise ValueError('Controllers, interfaces, and pidxs must be the same length')

        super().__init__(base=base, expected=tuple(controllers))

        self.pidxs = pidxs
        self.interfaces = interfaces

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        if self._should_skip(inputs):
            return nd.NumDict(default=0.)
        return self.base.call(inputs)

    def _should_skip(self, inputs: Mapping[Any, nd.NumDict]) -> bool:
        data = nd.merge(*self.extract_inputs(inputs)[:len(self.interfaces)])
        for i in range(len(self.interfaces)):
            interface = self.interfaces[i]
            pidx = self.pidxs[i]
            if not interface.params[pidx] in data:
                return True
        return False


class SwitchIfEmpty(cl.Process):
    """
    If the the inputs from the primary sources are empty, returns the inputs from the alternative sources.
    """
    _serves = cl.ConstructType.flow_tt

    def __init__(self, primary_sources: List[cl.Symbol], alternative_sources: List[cl.Symbol]):
        super().__init__(expected=[*primary_sources, *alternative_sources])
        self._primary_sources = primary_sources
        self._alternative_sources = alternative_sources

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        primary_inputs = self._get_input_from_sources(inputs, self._primary_sources)
        if not is_empty(primary_inputs):
            return primary_inputs

        return self._get_input_from_sources(inputs, self._alternative_sources)

    def _get_input_from_sources(self, inputs: Mapping[Any, nd.NumDict], sources: List[cl.Symbol]) -> nd.NumDict:
        result = nd.MutableNumDict({}, default=0.)
        for source in sources:
            expanded_address = cl.expand_address(self.client, source)
            source_input = inputs[expanded_address]
            result.update(source_input)
        return result


