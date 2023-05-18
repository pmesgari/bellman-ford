import pytest
from helpers import get_files, load
from main import Topology


logs = [x.split('.')[0] for x in get_files('solutions')]
topologies = [x.split('.')[0] for x in get_files('topologies')]

test_cases = []
for t in topologies:
    if t not in logs:
        continue
    test_cases.append((t, load(f'solutions/{t}.txt')))

@pytest.mark.parametrize(
    'topology, expected',
    test_cases
)
def test_dv(topology, expected):
    topo = Topology()
    topo.from_config_file(f'topologies/{topology}.txt')
    topo.run()

    for key, value in topo.nodes.items():
        assert key in expected
        assert set([f'{node}{weight}' for node, weight in value.dv.items()]) == set(expected[key].split(','))

        