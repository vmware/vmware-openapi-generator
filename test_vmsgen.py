import vmsgen

def test_tags_generation_from_none():
    expected = []
    actual = vmsgen.tags_from_service_name(None)
    assert expected == actual

def test_tags_generation_from_nonstring():
    expected = []
    actual = vmsgen.tags_from_service_name(1)
    assert expected == actual

def test_tags_generation_from_short_name():
    expected = ['']
    actual = vmsgen.tags_from_service_name('three.levels.deep')
    assert expected == actual

def test_tags_generation_from_proper_name():
    expected = ['levels_deep']
    actual = vmsgen.tags_from_service_name('more.than.three.levels.deep')
    assert expected == actual
