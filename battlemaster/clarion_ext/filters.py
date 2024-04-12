from typing import Mapping, Any, Union, List

import pyClarion as cl
from pyClarion import nd
from pyClarion.base.realizers import Pt


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
