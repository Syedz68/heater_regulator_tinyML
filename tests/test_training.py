import pandas as pd
from heater_controller.training import chronological_split

def test_chronological_split_has_no_overlap():
    train, validation, test = chronological_split(pd.DataFrame({"x": range(100)}))
    assert (len(train), len(validation), len(test)) == (70, 15, 15)
    assert train.index.max() < validation.index.min() < test.index.min()
