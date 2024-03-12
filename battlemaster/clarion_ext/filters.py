from typing import Mapping, Any, Union

import pyClarion as cl
from pyClarion import nd
from pyClarion.base.realizers import Pt


class ReasoningPath(cl.Wrapped[Pt]):
    """
    Gates an activation propagator.

    pyClarion only has a way to Gate/filter a propagator _after_ it has ran. This wastes computation.
    This class completely severs a propagator by not even calling it and returning an empty output. Though it is
    intended to be compatible with the Gate filter by respecting the same API.
    """

    def __init__(
        self,
        base: Pt,
        controller: Union[cl.buffer, cl.flow_in],
        interface: cl.ParamSet.Interface,
        pidx: int,
        invert: bool = False
    ) -> None:
        """
        :param base: The base Process instance.
        :param controller: The gate controller.
        :param interface: Controller's feature interface.
        :param pidx: Lookup index of gating parameter in interface.
        :param invert: Option to invert the gating signal.
        """
        super().__init__(base=base, expected=(controller,))

        self.pidx = pidx
        self.interface = interface
        self.invert = invert

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        if self._should_skip(inputs):
            return nd.NumDict(default=0.)
        return self.base.call(inputs)

    def _should_skip(self, inputs: Mapping[Any, nd.NumDict]) -> bool:
        data, = self.extract_inputs(inputs)[:len(self.expected_top)]
        return not self.interface.params[self.pidx] in data
